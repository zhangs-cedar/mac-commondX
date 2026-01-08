#!/usr/bin/env python3
"""
CommondX 应用主逻辑
负责协调各个模块的初始化和交互
"""

import sys
import os
from pathlib import Path

import objc
from Foundation import NSObject, NSTimer
from AppKit import NSApplication
from cedar.utils import print

# 导入模块
from .event_tap import EventTap
from .cut_manager import CutManager
from .status_bar import StatusBarIcon
from .license_manager import license_manager
from .permission import check_accessibility, request_accessibility, open_accessibility_settings

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
        self.license_status, machine_code, self.remaining = license_manager.get_status()
        print(f"License: {self.license_status}, Machine Code: {machine_code}, Remaining: {self.remaining} days")
        
        # 1. 初始化核心逻辑
        self.cut_manager = CutManager()
        
        # 2. 初始化 UI
        self.status_bar = StatusBarIcon.alloc().initWithCutManager_(self.cut_manager)
        
        # 3. 初始化事件监听
        self.event_tap = EventTap(on_cut=self.on_cut, on_paste=self.on_paste)
        
        # 4. 尝试启动
        self._try_start()
    
    def _try_start(self):
        """尝试启动事件监听"""
        if not check_accessibility():
            print("需要辅助功能权限，正在请求...")
            request_accessibility()
            self.status_bar.send_notification(
                "需要授权",
                "请在系统设置中授权后，程序将自动启动"
            )
            # 每2秒检查一次权限，最多30次（60秒）
            self._permission_check_count = 0
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                2.0, self, "_checkPermission:", None, True
            )
            return
        
        self._start_event_tap()
    
    def _checkPermission_(self, timer):
        """定时检查权限"""
        self._permission_check_count += 1
        
        if check_accessibility():
            timer.invalidate()
            print("已获得辅助功能权限")
            self._start_event_tap()
        elif self._permission_check_count >= 30:
            timer.invalidate()
            print("权限检查超时，请手动授权后点击菜单中的'检查权限'")
            self.status_bar.send_notification("授权超时", "请点击菜单中的'检查权限'重试")
    
    def retry_permission_check(self):
        """手动重新检查权限（供菜单调用）"""
        if self.event_tap and self.event_tap.running:
            return True  # 已经在运行了
        
        if check_accessibility():
            self._start_event_tap()
            return True
        else:
            open_accessibility_settings()
            self.status_bar.send_notification("请授权", "请在打开的设置中授权 CommondX")
            return False
    
    def _start_event_tap(self):
        """启动事件监听"""
        if self.event_tap.start():
            print("CommondX 已启动")
            if self.license_status == "activated":
                self.status_bar.send_notification("CommondX", "已启动，使用 Cmd+X 剪切文件")
            elif self.license_status == "trial":
                self.status_bar.send_notification("CommondX", f"试用期还剩 {self.remaining} 天")
            else:
                self.status_bar.send_notification("CommondX", "试用期已结束，请购买激活码")
        else:
            print("启动失败")
            self.status_bar.send_notification("CommondX 启动失败", "请重启应用")
    
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
