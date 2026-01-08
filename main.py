#!/usr/bin/env python3
"""CommondX - Mac 文件剪切移动工具"""

import sys
from pathlib import Path

# 日志配置
from cedar.utils import print, create_name
import os
os.environ['LOG_PATH'] = str(Path(__file__).parent / "logs" / f"{create_name()}commondx.log")
print(os.environ['LOG_PATH'])
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
