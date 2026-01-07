#!/usr/bin/env python3
"""开机自启管理模块 - LaunchAgent"""

import os
import plistlib
import subprocess

APP_ID = "com.liuns.commondx"
PLIST_NAME = f"{APP_ID}.plist"


def get_plist_path():
    """获取 LaunchAgent plist 路径"""
    return os.path.expanduser(f"~/Library/LaunchAgents/{PLIST_NAME}")


def get_app_path():
    """获取应用路径"""
    # 优先使用打包后的 .app 路径
    app_locations = [
        "/Applications/CommondX.app/Contents/MacOS/CommondX",
        os.path.expanduser("~/Applications/CommondX.app/Contents/MacOS/CommondX"),
    ]
    
    for path in app_locations:
        if os.path.exists(path):
            return path
    
    # 开发模式：使用当前脚本路径
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "commondx.py"))


def create_plist():
    """创建 LaunchAgent plist 文件"""
    app_path = get_app_path()
    
    plist_content = {
        "Label": APP_ID,
        "ProgramArguments": [app_path] if app_path.endswith(".py") else [app_path],
        "RunAtLoad": True,
        "KeepAlive": False,
        "StandardOutPath": os.path.expanduser("~/Library/Logs/CommondX.log"),
        "StandardErrorPath": os.path.expanduser("~/Library/Logs/CommondX.error.log"),
    }
    
    # 如果是 Python 脚本，需要通过 python3 运行
    if app_path.endswith(".py"):
        plist_content["ProgramArguments"] = ["/usr/bin/python3", app_path]
    
    return plist_content


def is_autostart_enabled():
    """检查是否已开启开机自启"""
    plist_path = get_plist_path()
    return os.path.exists(plist_path)


def enable_autostart():
    """启用开机自启"""
    plist_path = get_plist_path()
    
    # 确保目录存在
    os.makedirs(os.path.dirname(plist_path), exist_ok=True)
    
    # 写入 plist
    plist_content = create_plist()
    with open(plist_path, 'wb') as f:
        plistlib.dump(plist_content, f)
    
    # 加载 LaunchAgent
    subprocess.run(['launchctl', 'load', plist_path], capture_output=True)
    
    print(f"已启用开机自启: {plist_path}")
    return True


def disable_autostart():
    """禁用开机自启"""
    plist_path = get_plist_path()
    
    if os.path.exists(plist_path):
        # 卸载 LaunchAgent
        subprocess.run(['launchctl', 'unload', plist_path], capture_output=True)
        # 删除 plist
        os.remove(plist_path)
        print("已禁用开机自启")
    
    return False


def toggle_autostart():
    """切换开机自启状态"""
    if is_autostart_enabled():
        disable_autostart()
        return False
    else:
        enable_autostart()
        return True
