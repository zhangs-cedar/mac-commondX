#!/usr/bin/env python3
"""
CommondX 应用主逻辑
负责协调各个模块的初始化和交互
"""

import sys
import os
from pathlib import Path

import objc
from Foundation import NSObject
from AppKit import NSApplication
from cedar.utils import print

# 导入模块
from .event_tap import EventTap, check_accessibility, request_accessibility
from .cut_manager import CutManager
from .status_bar import StatusBarIcon
from .license_manager import license_manager

class CommondXApp(NSObject):
    """CommondX 应用代理"""
    
    def init(self):
        self = objc.super(CommondXApp, self).init()
        if self:
            self.cut_manager = None
            self.event_tap = None
            self.status_bar = None
        return self
    
    def applicationDidFinishLaunching_(self, notification):
        """应用启动完成"""
        print("CommondX 启动中...")
        
        # 0. 检查激活状态
        status, machine_code, remaining = license_manager.get_status()
        print(f"License: {status}, Machine Code: {machine_code}, Remaining: {remaining} days")
        
        # 1. 权限检查
        if not check_accessibility():
            print("需要辅助功能权限，正在请求...")
            request_accessibility()
        
        # 2. 初始化核心逻辑
        self.cut_manager = CutManager()
        
        # 3. 初始化 UI
        self.status_bar = StatusBarIcon.alloc().initWithCutManager_(self.cut_manager)
        
        # 4. 初始化事件监听
        self.event_tap = EventTap(
            on_cut=self.on_cut,
            on_paste=self.on_paste
        )
        
        if self.event_tap.start():
            print("CommondX 已启动")
            if status == "activated":
                self.status_bar.send_notification("CommondX", "已启动，使用 Cmd+X 剪切文件")
            elif status == "trial":
                self.status_bar.send_notification("CommondX", f"试用期还剩 {remaining} 天")
            else:
                self.status_bar.send_notification("CommondX", "试用期已结束，请购买激活码")
        else:
            print("启动失败，请检查辅助功能权限")
            self.status_bar.send_notification(
                "CommondX 启动失败",
                "请在 系统设置 > 隐私与安全 > 辅助功能 中授权"
            )
    
    def on_cut(self):
        """Cmd+X 回调"""
        # 检查是否可用 (已激活 或 试用期内)
        if not license_manager.is_valid():
            self.status_bar.show_activation_required()
            return True
            
        if self.cut_manager.cut():
            count = self.cut_manager.count
            self.status_bar.send_notification(
                "已剪切",
                f"{count} 个文件等待移动，到目标文件夹按 Cmd+V"
            )
            return True
        return False
    
    def on_paste(self):
        """Cmd+V 回调"""
        # 检查是否可用 (已激活 或 试用期内)
        if not license_manager.is_valid():
            self.status_bar.show_activation_required()
            return True
            
        if self.cut_manager.has_cut_files:
            success, msg = self.cut_manager.paste()
            self.status_bar.send_notification(
                "移动完成" if success else "移动失败",
                msg
            )
            return True
        return False
    
    def applicationWillTerminate_(self, notification):
        """应用即将退出"""
        if self.event_tap:
            self.event_tap.stop()
        print("CommondX 已退出")
