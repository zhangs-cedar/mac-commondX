#!/usr/bin/env python3
"""许可证管理 - 机器码生成、激活码验证、试用期管理"""

import os
import subprocess
import hashlib
import time
from pathlib import Path
from cedar.utils import print, create_name, load_config, write_config
TRIAL_DAYS = 21  # 初始试用期21天
ACTIVATION_DAYS = 365  # 每次激活码激活延长1年（365天）
EXTEND_DAYS = 7  # 每次延长7天
EXTEND_INTERVAL_DAYS = 7  # 每7天可以延长一次
DAY_SECS = 86400

# 许可证文件路径（与配置文件分离）- 从环境变量读取
LICENSE_PATH = Path(os.getenv('LICENSE_PATH', str(Path.home() / "Library/Application Support/CommondX/license.yaml")))
LICENSE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load() -> dict:
    """加载许可证数据"""
    try:
        if LICENSE_PATH.exists():
            return load_config(str(LICENSE_PATH)) or {}
        return {}
    except:
        return {}


def _save(data: dict):
    """保存许可证数据到新文件"""
    write_config(data, str(LICENSE_PATH))


class LicenseManager:
    def __init__(self):
        self._data = _load()
        self.machine_code = self._gen_machine_code()
        self.trial_start = self._data.get('trial_start') or self._init_trial()
        # 不再使用 is_activated，改为检查试用期是否有效
    
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
    
    def _generate_activation_code(self) -> str:
        """
        根据机器码生成激活码（使用 MD5 哈希）
        
        使用年份 + 机器码进行 MD5 哈希，取前2位作为激活码
        
        Returns:
            str: 激活码（2位）
        """
        # 年份（用于生成激活码）
        year = create_name("date_only")
        
        # 组合字符串：年份 + 机器码
        combined = year + self.machine_code
        print(f"[DEBUG] [License] 组合字符串: {combined}")
        
        # 使用 MD5 哈希加密，取前2位作为激活码
        # MD5 特性：
        # 1. 雪崩效应：输入的任意字符变化都会导致哈希值完全不同
        # 2. 确定性：相同输入总是产生相同的哈希值
        # 3. 只取前2位：2位十六进制有256种可能（00-FF），可能存在碰撞
        #    但对于激活码验证场景，只要"年份+机器码"正确，就能生成正确的激活码
        hash_obj = hashlib.md5(combined.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        activation_code = hash_hex[:2].upper()  # 取前2位，转大写
        
        print(f"[DEBUG] [License] MD5 哈希值: {hash_hex}")
        print(f"[DEBUG] [License] 生成激活码（2位）: {activation_code}")
        
        return activation_code
    
    def has_activation_code(self) -> bool:
        """检查是否已输入过激活码（但不表示永久激活）"""
        code = self._data.get('activation_code', '')
        return bool(code) and self.verify(code)
    
    def verify(self, code: str) -> bool:
        """
        验证激活码
        
        Args:
            code: 用户输入的激活码
            
        Returns:
            bool: 如果激活码正确返回 True，否则返回 False
        """
        expected_code = self._generate_activation_code()
        input_code = code.strip().upper().replace(" ", "")
        is_valid = input_code == expected_code
        print(f"[DEBUG] [License] 验证激活码 - 输入: {input_code}, 期望: {expected_code}, 有效: {is_valid}")
        return is_valid
    
    def activate(self, code: str) -> bool:
        """
        激活码激活：延长试用期1年
        
        每个激活码只能使用一次，不能重复激活。
        每次激活码激活时，延长试用期365天（1年）。
        
        Args:
            code: 激活码
            
        Returns:
            bool: 如果激活成功返回 True，否则返回 False
        """
        # 1. 验证激活码格式和正确性
        if not self.verify(code):
            print("[DEBUG] [License] 激活码验证失败")
            return False
        
        # 2. 检查激活码是否已使用过
        normalized_code = code.strip().upper()
        saved_code = self._data.get('activation_code', '').strip().upper()
        
        if saved_code and saved_code == normalized_code:
            print(f"[DEBUG] [License] 激活码已使用过，无法重复激活 - 激活码: {normalized_code}")
            return False
        
        # 3. 执行激活逻辑
        self._data['activation_code'] = normalized_code
        
        # 延长试用期1年：将 trial_start 向后推365天（增加 trial_start，减少已过去天数）
        # 逻辑：trial_start 增大 → elapsed_days 减小 → remaining_days 增大
        self.trial_start += ACTIVATION_DAYS * DAY_SECS
        self._data['trial_start'] = self.trial_start
        self._data['last_activation_time'] = time.time()
        _save(self._data)
        
        rem = self.remaining_days()
        print(f"[DEBUG] [License] ✓ 激活成功，试用期已延长1年，剩余 {rem} 天")
        return True
    
    def _elapsed_days(self) -> float:
        return (time.time() - self.trial_start) / DAY_SECS
    
    def remaining_days(self) -> int:
        return max(0, int(TRIAL_DAYS - self._elapsed_days()) + 1)
    
    def is_expired(self) -> bool:
        return self._elapsed_days() >= TRIAL_DAYS
    
    def is_valid(self) -> bool:
        """
        检查许可证是否有效
        
        Returns:
            bool: 如果试用期未过期返回 True，否则返回 False
        """
        from cedar.utils import print
        is_expired = self.is_expired()
        is_valid = not is_expired
        rem = self.remaining_days()
        print(f"[4] [License] 检查许可证 - 剩余天数={rem}, 已过期={is_expired}, 有效={is_valid}")
        return is_valid
    
    def can_extend_trial(self) -> bool:
        """
        检查是否可以延长试用期
        
        每7天可以延长一次，延长7天
        
        Returns:
            bool: 如果可以延长返回 True，否则返回 False
        """
        last_extend = self._data.get('last_extend_time', 0)
        if last_extend == 0:
            # 从未延长过，可以延长
            return True
        
        elapsed_since_extend = (time.time() - last_extend) / DAY_SECS
        can_extend = elapsed_since_extend >= EXTEND_INTERVAL_DAYS
        print(f"[DEBUG] [License] 检查是否可以延长试用期 - 上次延长: {last_extend}, 已过 {elapsed_since_extend:.1f} 天, 可延长: {can_extend}")
        return can_extend
    
    def extend_trial(self) -> bool:
        """
        延长试用期7天
        
        每7天可以延长一次，延长7天
        
        Returns:
            bool: 如果延长成功返回 True，否则返回 False
        """
        if not self.can_extend_trial():
            print("[DEBUG] [License] 距离上次延长不足7天，无法延长")
            return False
        
        # 延长试用期7天：将 trial_start 向后推7天（增加 trial_start，减少已过去天数）
        # 逻辑：trial_start 增大 → elapsed_days 减小 → remaining_days 增大
        self.trial_start += EXTEND_DAYS * DAY_SECS
        self._data['trial_start'] = self.trial_start
        self._data['last_extend_time'] = time.time()
        _save(self._data)
        
        rem = self.remaining_days()
        print(f"[DEBUG] [License] ✓ 试用期已延长7天，剩余 {rem} 天")
        return True
    
    def extend_trial_unlimited(self) -> bool:
        """
        延长试用期7天（无限制，每次都可以延长）
        
        用于访问官网续期功能，不检查时间间隔限制
        
        Returns:
            bool: 总是返回 True（延长成功）
        """
        # 延长试用期7天：将 trial_start 向后推7天（增加 trial_start，减少已过去天数）
        # 逻辑：trial_start 增大 → elapsed_days 减小 → remaining_days 增大
        self.trial_start += EXTEND_DAYS * DAY_SECS
        self._data['trial_start'] = self.trial_start
        self._data['last_website_extend_time'] = time.time()
        _save(self._data)
        
        rem = self.remaining_days()
        print(f"[DEBUG] [License] ✓ 访问官网续期成功，试用期已延长7天，剩余 {rem} 天")
        return True
    
    def get_status(self) -> tuple:
        """
        获取许可证状态
        
        Returns:
            tuple: (status: str, machine_code: str, remaining_days: int)
                - status: "trial"（试用期有效）或 "expired"（已过期）
                - machine_code: 机器码
                - remaining_days: 剩余天数（过期时为0）
        """
        rem = self.remaining_days()
        return ("trial", self.machine_code, rem) if rem > 0 else ("expired", self.machine_code, 0)


license_manager = LicenseManager()
