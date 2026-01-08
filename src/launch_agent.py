#!/usr/bin/env python3
"""开机自启管理 - LaunchAgent"""

import plistlib
import subprocess
from pathlib import Path
from cedar.utils import print

APP_ID = "com.liuns.commondx"
PLIST_PATH = Path.home() / f"Library/LaunchAgents/{APP_ID}.plist"
LOG_DIR = Path.home() / "Library/Logs"

# 应用路径候选
APP_PATHS = [
    Path("/Applications/CommondX.app/Contents/MacOS/CommondX"),
    Path.home() / "Applications/CommondX.app/Contents/MacOS/CommondX",
    Path(__file__).parent / "commondx.py",  # 开发模式
]


def _get_app_path() -> str:
    """获取应用路径"""
    for p in APP_PATHS:
        if p.exists():
            return str(p)
    return str(APP_PATHS[-1])


def _create_plist() -> dict:
    """创建 plist 配置"""
    app = _get_app_path()
    args = ["/usr/bin/python3", app] if app.endswith(".py") else [app]
    return {
        "Label": APP_ID,
        "ProgramArguments": args,
        "RunAtLoad": True,
        "KeepAlive": False,
        "StandardOutPath": str(LOG_DIR / "CommondX.log"),
        "StandardErrorPath": str(LOG_DIR / "CommondX.error.log"),
    }


def is_autostart_enabled() -> bool:
    """检查是否已开启"""
    return PLIST_PATH.exists()


def enable_autostart() -> bool:
    """启用开机自启"""
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_bytes(plistlib.dumps(_create_plist()))
    subprocess.run(['launchctl', 'load', str(PLIST_PATH)], capture_output=True)
    print(f"已启用开机自启")
    return True


def disable_autostart() -> bool:
    """禁用开机自启"""
    if PLIST_PATH.exists():
        subprocess.run(['launchctl', 'unload', str(PLIST_PATH)], capture_output=True)
        PLIST_PATH.unlink()
        print("已禁用开机自启")
    return False


def toggle_autostart() -> bool:
    """切换开机自启状态"""
    return disable_autostart() if is_autostart_enabled() else enable_autostart()
