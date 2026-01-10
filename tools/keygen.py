#!/usr/bin/env python3
"""
CommondX 激活码生成工具
开发者专用 - 根据用户机器码生成对应激活码

使用方法:
    python tools/keygen.py CMDX-A1B2C3D4
"""

import sys
import hashlib
from cedar.utils import print, create_name


def generate_activation_code(machine_code: str) -> str:
    """
    根据机器码生成激活码（使用 MD5 哈希）
    
    使用年份 + 机器码进行 MD5 哈希，取前2位作为激活码
    
    Args:
        machine_code: 机器码，格式如 CMDX-A1B2C3D4
        
    Returns:
        str: 激活码（2位十六进制，如 "A3"、"F2"）
    """
    machine_code = machine_code.strip().upper()  # 机器码
    
    if not machine_code.startswith("CMDX-"):
        print(f"警告: 机器码格式不正确，应为 CMDX-XXXXXXXX")
    
    # 年份（用于生成激活码）
    year = create_name("date_only")
    
    # 组合字符串：年份 + 机器码
    combined = year + machine_code
    print(f"[DEBUG] 组合字符串: {combined}")
    
    # 使用 MD5 哈希加密，取前2位作为激活码
    # MD5 特性：
    # 1. 雪崩效应：输入的任意字符变化都会导致哈希值完全不同
    # 2. 确定性：相同输入总是产生相同的哈希值
    # 3. 只取前2位：2位十六进制有256种可能（00-FF），可能存在碰撞
    #    但对于激活码验证场景，只要"年份+机器码"正确，就能生成正确的激活码
    hash_obj = hashlib.md5(combined.encode('utf-8'))
    hash_hex = hash_obj.hexdigest()
    activation_code = hash_hex[:2].upper()  # 取前2位，转大写
    
    print(f"[DEBUG] MD5 哈希值: {hash_hex}")
    print(f"[DEBUG] 生成激活码（2位）: {activation_code}")
    
    return activation_code


def main():
    if len(sys.argv) < 2:
        print("用法: python tools/keygen.py <机器码>")
        print("示例: python tools/keygen.py CMDX-A1B2C3D4")
        sys.exit(1)
    
    machine_code = sys.argv[1]
    activation_code = generate_activation_code(machine_code)
    
    print(f"\n机器码: {machine_code}")
    print(f"激活码: {activation_code}")
    print("\n请将激活码发送给用户。")


if __name__ == "__main__":
    main()
