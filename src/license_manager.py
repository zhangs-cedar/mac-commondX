#!/usr/bin/env python3
"""
许可证管理模块
- 生成唯一机器码
- 验证激活码
- 3天免费试用
"""

import subprocess
import hashlib
import hmac
import json
import time
from pathlib import Path
from typing import Tuple

# 配置
APP_NAME = "CommondX"
TRIAL_DAYS = 3  # 试用期天数
# 密钥 (与 tools/keygen.py 一致，实际项目中应混淆)
SECRET_KEY = b"cedar_commondx_2026_secret"

# 路径
APP_SUPPORT = Path.home() / "Library/Application Support" / APP_NAME
if not APP_SUPPORT.exists():
    APP_SUPPORT.mkdir(parents=True, exist_ok=True)

LICENSE_FILE = APP_SUPPORT / "license.key"
CONFIG_FILE = APP_SUPPORT / "config.json"


class LicenseManager:
    def __init__(self):
        self.machine_code = self._generate_machine_code()
        self.is_activated = self._check_activation()
        self.trial_start_time = self._load_trial_start()
    
    def _get_hardware_uuid(self) -> str:
        """获取 Mac 硬件 UUID"""
        try:
            result = subprocess.run(
                ['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice'],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'IOPlatformUUID' in line:
                    # 格式: "IOPlatformUUID" = "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
                    uuid = line.split('"')[-2]
                    return uuid
        except Exception as e:
            print(f"[License] Failed to get hardware UUID: {e}")
        return "UNKNOWN"
    
    def _generate_machine_code(self) -> str:
        """生成用户友好的机器码"""
        uuid = self._get_hardware_uuid()
        # 取 UUID 的 hash 前 8 位作为短码
        hash_val = hashlib.md5(uuid.encode()).hexdigest()[:8].upper()
        return f"CMDX-{hash_val}"
    
    def _load_trial_start(self) -> float:
        """加载试用开始时间"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    return config.get('trial_start', 0)
            except:
                pass
        # 首次运行，记录开始时间
        return self._start_trial()
    
    def _start_trial(self) -> float:
        """开始试用期"""
        start_time = time.time()
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'trial_start': start_time}, f)
        except Exception as e:
            print(f"[License] Failed to save trial config: {e}")
        return start_time
    
    def _calculate_activation_code(self, machine_code: str) -> str:
        """计算激活码 (HMAC-SHA256)"""
        h = hmac.new(SECRET_KEY, machine_code.encode('utf-8'), hashlib.sha256)
        hex_digest = h.hexdigest()[:16].upper()
        # 格式化为 XXXX-XXXX-XXXX-XXXX
        return f"{hex_digest[:4]}-{hex_digest[4:8]}-{hex_digest[8:12]}-{hex_digest[12:16]}"
    
    def verify_activation_code(self, code: str) -> bool:
        """验证激活码是否匹配当前机器"""
        code = code.strip().upper().replace(" ", "")
        expected = self._calculate_activation_code(self.machine_code)
        return hmac.compare_digest(code, expected)
    
    def _check_activation(self) -> bool:
        """检查是否已激活"""
        if LICENSE_FILE.exists():
            try:
                with open(LICENSE_FILE, 'r') as f:
                    saved_code = f.read().strip()
                return self.verify_activation_code(saved_code)
            except:
                pass
        return False
    
    def activate(self, code: str) -> bool:
        """尝试激活"""
        if self.verify_activation_code(code):
            try:
                with open(LICENSE_FILE, 'w') as f:
                    f.write(code.strip().upper())
                self.is_activated = True
                return True
            except Exception as e:
                print(f"[License] Failed to save license: {e}")
        return False
    
    def get_trial_remaining_days(self) -> int:
        """获取试用期剩余天数"""
        elapsed_days = (time.time() - self.trial_start_time) / (24 * 3600)
        remaining = TRIAL_DAYS - elapsed_days
        return max(0, int(remaining) + 1)  # 向上取整
    
    def is_trial_expired(self) -> bool:
        """试用期是否已过期"""
        elapsed_days = (time.time() - self.trial_start_time) / (24 * 3600)
        return elapsed_days >= TRIAL_DAYS
    
    def is_valid(self) -> bool:
        """是否可用 (已激活 或 试用期内)"""
        if self.is_activated:
            return True
        return not self.is_trial_expired()
    
    def get_status(self) -> Tuple[str, str, int]:
        """获取状态
        Returns:
            (status, machine_code, remaining_days)
            status: "activated" | "trial" | "expired"
        """
        if self.is_activated:
            return "activated", self.machine_code, 0
        
        remaining = self.get_trial_remaining_days()
        if remaining > 0:
            return "trial", self.machine_code, remaining
        else:
            return "expired", self.machine_code, 0


# 单例
license_manager = LicenseManager()
