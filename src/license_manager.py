#!/usr/bin/env python3
"""
许可证管理模块
- 生成唯一机器码
- 验证激活码
- 3天免费试用
- 所有配置直接存储在 config.yaml
"""

import subprocess
import hashlib
import hmac
import time
import yaml
from pathlib import Path
from typing import Tuple
from cedar.utils import print

# 密钥 (与 tools/keygen.py 一致)
SECRET_KEY = b"cedar_commondx_2026_secret"

# 配置文件路径
CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


def _load_yaml():
    """加载 config.yaml"""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[License] 读取配置失败: {e}")
        return {}


def _save_yaml(data: dict):
    """保存 config.yaml"""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    except Exception as e:
        print(f"[License] 保存配置失败: {e}")


class LicenseManager:
    def __init__(self):
        self._config = _load_yaml()
        self._license = self._config.get('license', {})
        self.machine_code = self._generate_machine_code()
        self.trial_days = self._license.get('trial_days', 3)
        self.trial_start_time = self._load_trial_start()
        self.is_activated = self._check_activation()
    
    def _get_hardware_uuid(self) -> str:
        """获取 Mac 硬件 UUID"""
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
        """生成用户友好的机器码"""
        uuid = self._get_hardware_uuid()
        hash_val = hashlib.md5(uuid.encode()).hexdigest()[:8].upper()
        return f"CMDX-{hash_val}"
    
    def _load_trial_start(self) -> float:
        """加载试用开始时间"""
        trial_start = self._license.get('trial_start', 0)
        if trial_start > 0:
            return trial_start
        # 首次运行，记录开始时间
        return self._start_trial()
    
    def _start_trial(self) -> float:
        """开始试用期"""
        start_time = time.time()
        self._license['trial_start'] = start_time
        self._config['license'] = self._license
        _save_yaml(self._config)
        return start_time
    
    def _calculate_activation_code(self, machine_code: str) -> str:
        """计算激活码 (HMAC-SHA256)"""
        h = hmac.new(SECRET_KEY, machine_code.encode('utf-8'), hashlib.sha256)
        hex_digest = h.hexdigest()[:16].upper()
        return f"{hex_digest[:4]}-{hex_digest[4:8]}-{hex_digest[8:12]}-{hex_digest[12:16]}"
    
    def verify_activation_code(self, code: str) -> bool:
        """验证激活码是否匹配当前机器"""
        code = code.strip().upper().replace(" ", "")
        expected = self._calculate_activation_code(self.machine_code)
        return hmac.compare_digest(code, expected)
    
    def _check_activation(self) -> bool:
        """检查是否已激活"""
        saved_code = self._license.get('activation_code', '')
        if saved_code:
            return self.verify_activation_code(saved_code)
        return False
    
    def activate(self, code: str) -> bool:
        """尝试激活"""
        if self.verify_activation_code(code):
            self._license['activation_code'] = code.strip().upper()
            self._config['license'] = self._license
            _save_yaml(self._config)
            self.is_activated = True
            return True
        return False
    
    def get_trial_remaining_days(self) -> int:
        """获取试用期剩余天数"""
        elapsed_days = (time.time() - self.trial_start_time) / (24 * 3600)
        remaining = self.trial_days - elapsed_days
        return max(0, int(remaining) + 1)
    
    def is_trial_expired(self) -> bool:
        """试用期是否已过期"""
        elapsed_days = (time.time() - self.trial_start_time) / (24 * 3600)
        return elapsed_days >= self.trial_days
    
    def is_valid(self) -> bool:
        """是否可用 (已激活 或 试用期内)"""
        return self.is_activated or not self.is_trial_expired()
    
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
        return "expired", self.machine_code, 0


# 单例
license_manager = LicenseManager()
