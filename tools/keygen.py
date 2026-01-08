#!/usr/bin/env python3
"""
CommondX 激活码生成工具
开发者专用 - 根据用户机器码生成对应激活码

使用方法:
    python tools/keygen.py CMDX-A1B2C3D4
"""

import sys
import hashlib
import hmac
from cedar.utils import print

# 必须与 src/license_manager.py 中的密钥一致
SECRET_KEY = b"cedar_commondx_2026_secret"


def generate_activation_code(machine_code: str) -> str:
    """根据机器码生成激活码"""
    machine_code = machine_code.strip().upper()
    
    # 验证格式
    if not machine_code.startswith("CMDX-"):
        print(f"警告: 机器码格式不正确，应为 CMDX-XXXXXXXX")
    
    # 计算 HMAC
    h = hmac.new(SECRET_KEY, machine_code.encode('utf-8'), hashlib.sha256)
    hex_digest = h.hexdigest()[:16].upper()
    
    # 格式化为 XXXX-XXXX-XXXX-XXXX
    return f"{hex_digest[:4]}-{hex_digest[4:8]}-{hex_digest[8:12]}-{hex_digest[12:16]}"


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
