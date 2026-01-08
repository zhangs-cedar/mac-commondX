#!/usr/bin/env python3
"""辅助功能权限管理模块"""

import subprocess
from cedar.utils import print


def check_accessibility() -> bool:
    """检查辅助功能权限"""
    from ApplicationServices import AXIsProcessTrusted
    return AXIsProcessTrusted()


def request_accessibility() -> bool:
    """请求辅助功能权限（弹出系统授权对话框）"""
    from ApplicationServices import AXIsProcessTrustedWithOptions
    from Foundation import NSDictionary
    
    options = NSDictionary.dictionaryWithObject_forKey_(
        True, "AXTrustedCheckOptionPrompt"
    )
    return AXIsProcessTrustedWithOptions(options)


def open_accessibility_settings():
    """打开系统设置 - 辅助功能页面"""
    # macOS 13+ 使用新的 URL scheme
    url = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    subprocess.run(['open', url], check=False)
    print("[Permission] 已打开辅助功能设置")
