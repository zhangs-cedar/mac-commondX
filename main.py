#!/usr/bin/env python3
"""CommondX - Mac 文件剪切移动工具"""

import sys
import os
from pathlib import Path

# 配置路径管理 - 在导入其他模块之前设置所有路径环境变量
# 应用数据目录
APP_DATA_DIR = Path.home() / "Library/Application Support/CommondX"

# "/Users/zhangsong/Library/Application Support/CommondX"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ['APP_DATA_DIR'] = str(APP_DATA_DIR)

# 配置文件路径
CONFIG_PATH = APP_DATA_DIR / "config.yaml"
os.environ['CONFIG_PATH'] = str(CONFIG_PATH)

# 许可证文件路径
LICENSE_PATH = APP_DATA_DIR / "license.yaml"
os.environ['LICENSE_PATH'] = str(LICENSE_PATH)

# 日志路径
from cedar.utils import print, create_name
LOG_PATH = Path(__file__).parent / "logs" / f"{create_name()}commondx.log"
os.environ['LOG_PATH'] = str(LOG_PATH)

# LaunchAgent 相关路径
os.environ['PLIST_PATH'] = str(Path.home() / "Library/LaunchAgents/com.liuns.commondx.plist")
os.environ['LOG_DIR'] = str(Path.home() / "Library/Logs")

# 打印所有配置路径（调试用）
print(f"[DEBUG] [Main] 配置路径初始化:")
print(f"[DEBUG] [Main]   APP_DATA_DIR = {APP_DATA_DIR}") 
print(f"[DEBUG] [Main]   CONFIG_PATH = {CONFIG_PATH}")
print(f"[DEBUG] [Main]   LICENSE_PATH = {LICENSE_PATH}")
print(f"[DEBUG] [Main]   LOG_PATH = {LOG_PATH}")
print(f"[DEBUG] [Main]   PLIST_PATH = {os.environ.get('PLIST_PATH')}")
print(f"[DEBUG] [Main]   LOG_DIR = {os.environ.get('LOG_DIR')}")

# 添加 src 路径
sys.path.insert(0, str(Path(__file__).parent))

from AppKit import NSApplication
from PyObjCTools import AppHelper
from src.app import CommondXApp


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(2)  # Accessory 模式
    app.setDelegate_(CommondXApp.alloc().init())
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
