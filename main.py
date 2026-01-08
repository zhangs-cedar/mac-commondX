#!/usr/bin/env python3
"""
CommondX - Mac 文件剪切移动工具
实现 Windows 风格的 Cmd+X 剪切、Cmd+V 移动

入口脚本
"""

import sys
import os
from pathlib import Path
from AppKit import NSApplication
from PyObjCTools import AppHelper
from cedar.utils import print, create_name
os.environ['LOG_PATH'] = os.path.join(os.path.dirname(
    __file__), "logs", create_name() + 'commondx.log')

print(os.environ['LOG_PATH'])
print("CommondX 启动中...")

# 添加 src 到路径以确保模块可被导入
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from src.app import CommondXApp
except ImportError:
    # 尝试直接从当前目录导入（兼容开发环境）
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from src.app import CommondXApp


def main():
    # 1. 创建应用实例
    app = NSApplication.sharedApplication()

    # 2. 设置为 accessory 应用（只显示状态栏图标，不显示 Dock 图标）
    # NSApplicationActivationPolicyAccessory = 2
    app.setActivationPolicy_(2)

    # 3. 创建并设置代理
    delegate = CommondXApp.alloc().init()
    app.setDelegate_(delegate)

    # 4. 启动运行循环
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
