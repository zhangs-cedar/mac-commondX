#!/usr/bin/env python3
"""许可证管理 - 机器码生成、激活码验证、试用期管理"""

import subprocess
import hashlib
import hmac
import time
import yaml
from pathlib import Path
from cedar.utils import print

SECRET_KEY = b"cedar_commondx_2026_secret"
TRIAL_DAYS = 21
DAY_SECS = 86400

USER_DATA = Path.home() / "Library/Application Support/CommondX/user.yaml"
USER_DATA.parent.mkdir(parents=True, exist_ok=True)


def _load() -> dict:
    try:
        return yaml.safe_load(USER_DATA.read_text()) or {} if USER_DATA.exists() else {}
    except:
        return {}


def _save(data: dict):
    USER_DATA.write_text(yaml.dump(data))


class LicenseManager:
    def __init__(self):
        self._data = _load()
        self.machine_code = self._gen_machine_code()
        self.trial_start = self._data.get('trial_start') or self._init_trial()
        self.is_activated = self._check_activated()
    
    def _get_uuid(self) -> str:
        try:
            r = subprocess.run(['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                               capture_output=True, text=True, timeout=5)
            for line in r.stdout.split('\n'):
                if 'IOPlatformUUID' in line:
                    return line.split('"')[-2]
        except Exception as e:
            print(f"获取UUID失败: {e}")
        return "UNKNOWN"
    
    def _gen_machine_code(self) -> str:
        h = hashlib.md5(self._get_uuid().encode()).hexdigest()[:8].upper()
        return f"CMDX-{h}"
    
    def _init_trial(self) -> float:
        t = time.time()
        self._data['trial_start'] = t
        _save(self._data)
        return t
    
    def _calc_code(self, code: str) -> str:
        return hmac.new(SECRET_KEY, code.encode(), hashlib.sha256).hexdigest()[:2].upper()
    
    def _check_activated(self) -> bool:
        code = self._data.get('activation_code', '')
        return bool(code) and self.verify(code)
    
    def verify(self, code: str) -> bool:
        return hmac.compare_digest(code.strip().upper().replace(" ", ""), self._calc_code(self.machine_code))
    
    def activate(self, code: str) -> bool:
        if not self.verify(code):
            return False
        self._data['activation_code'] = code.strip().upper()
        _save(self._data)
        self.is_activated = True
        return True
    
    def _elapsed_days(self) -> float:
        return (time.time() - self.trial_start) / DAY_SECS
    
    def remaining_days(self) -> int:
        return max(0, int(TRIAL_DAYS - self._elapsed_days()) + 1)
    
    def is_expired(self) -> bool:
        return self._elapsed_days() >= TRIAL_DAYS
    
    def is_valid(self) -> bool:
        return self.is_activated or not self.is_expired()
    
    def get_status(self) -> tuple:
        if self.is_activated:
            return "activated", self.machine_code, 0
        rem = self.remaining_days()
        return ("trial", self.machine_code, rem) if rem > 0 else ("expired", self.machine_code, 0)


license_manager = LicenseManager()
