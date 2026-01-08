#!/usr/bin/env python3
"""
许可证管理模块
- 生成唯一机器码
- 验证激活码
- 30天免费试用
"""

import subprocess
import hashlib
import hmac
import time
import yaml
from pathlib import Path
from typing import Tuple
from cedar.utils import print

# 配置常量
SECRET_KEY = b"cedar_commondx_2026_secret"
TRIAL_DAYS = 21

# 用户数据文件
USER_DATA = Path.home() / "Library/Application Support/CommondX/user.yaml"
USER_DATA.parent.mkdir(parents=True, exist_ok=True)


def _load_data() -> dict:
    if USER_DATA.exists():
        try:
            with open(USER_DATA, 'r') as f:
                return yaml.safe_load(f) or {}
        except:
            pass
    return {}


def _save_data(data: dict):
    with open(USER_DATA, 'w') as f:
        yaml.dump(data, f)


class LicenseManager:
    def __init__(self):
        self._data = _load_data()
        self.machine_code = self._generate_machine_code()
        self.trial_start_time = self._data.get('trial_start') or self._start_trial()
        self.is_activated = self._check_activation()
    
    def _get_hardware_uuid(self) -> str:
        try:
            result = subprocess.run(
                ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'IOPlatformUUID' in line:
                    return line.split('"')[-2]
        except Exception as e:
            print(f"[License] Failed to get hardware UUID: {e}")
        return "UNKNOWN"
    
    def _generate_machine_code(self) -> str:
        uuid = self._get_hardware_uuid()
        hash_val = hashlib.md5(uuid.encode()).hexdigest()[:8].upper()
        return f"CMDX-{hash_val}"
    
    def _start_trial(self) -> float:
        start_time = time.time()
        self._data['trial_start'] = start_time
        _save_data(self._data)
        return start_time
    
    def _calculate_activation_code(self, machine_code: str) -> str:
        h = hmac.new(SECRET_KEY, machine_code.encode('utf-8'), hashlib.sha256)
        return h.hexdigest()[:2].upper()
    
    def verify_activation_code(self, code: str) -> bool:
        code = code.strip().upper().replace(" ", "")
        expected = self._calculate_activation_code(self.machine_code)
        return hmac.compare_digest(code, expected)
    
    def _check_activation(self) -> bool:
        saved_code = self._data.get('activation_code', '')
        return bool(saved_code) and self.verify_activation_code(saved_code)
    
    def activate(self, code: str) -> bool:
        if self.verify_activation_code(code):
            self._data['activation_code'] = code.strip().upper()
            _save_data(self._data)
            self.is_activated = True
            return True
        return False
    
    def get_trial_remaining_days(self) -> int:
        elapsed = (time.time() - self.trial_start_time) / 86400
        return max(0, int(TRIAL_DAYS - elapsed) + 1)
    
    def is_trial_expired(self) -> bool:
        return (time.time() - self.trial_start_time) / 86400 >= TRIAL_DAYS
    
    def is_valid(self) -> bool:
        return self.is_activated or not self.is_trial_expired()
    
    def get_status(self) -> Tuple[str, str, int]:
        if self.is_activated:
            return "activated", self.machine_code, 0
        remaining = self.get_trial_remaining_days()
        if remaining > 0:
            return "trial", self.machine_code, remaining
        return "expired", self.machine_code, 0


license_manager = LicenseManager()
