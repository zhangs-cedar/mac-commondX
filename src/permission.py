#!/usr/bin/env python3
"""辅助功能权限管理"""

import subprocess
from ApplicationServices import AXIsProcessTrusted, AXIsProcessTrustedWithOptions
from Foundation import NSDictionary

ACCESSIBILITY_URL = "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"


def check_accessibility() -> bool:
    """检查权限"""
    return AXIsProcessTrusted()


def request_accessibility() -> bool:
    """请求权限（弹窗）"""
    opts = NSDictionary.dictionaryWithObject_forKey_(True, "AXTrustedCheckOptionPrompt")
    return AXIsProcessTrustedWithOptions(opts)


def open_accessibility_settings():
    """打开辅助功能设置"""
    subprocess.run(['open', ACCESSIBILITY_URL], check=False)
