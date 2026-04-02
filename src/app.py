#!/usr/bin/env python3
"""
CommondX 应用主逻辑
"""

import objc
from Foundation import NSObject, NSTimer
from cedar.utils import print

from .event_tap import EventTap
from .cut_manager import CutManager
from .status_bar import StatusBarIcon
from .permission import check_accessibility, request_accessibility, open_accessibility_settings


class CommondXApp(NSObject):
    """CommondX 应用代理"""
    
    def init(self):
        self = objc.super(CommondXApp, self).init()
        if self:
            self.cut_manager = self.event_tap = self.status_bar = None
        return self
    
    def applicationDidFinishLaunching_(self, _):
        """应用启动"""
        print("CommondX 启动中...")
        
        self.cut_manager = CutManager()
        self.status_bar = StatusBarIcon.alloc().initWithCutManager_(self.cut_manager)
        
        # 传入回调函数
        self.event_tap = EventTap(
            on_cut=self.on_cut,
            on_paste=self.on_paste,
            on_copy=None,
        )
        self._try_start()
    
    def _try_start(self):
        """尝试启动"""
        if check_accessibility():
            return self._start_event_tap()
        
        print("需要辅助功能权限...")
        request_accessibility()
        self.status_bar.send_notification("需要授权", "请在系统设置中授权")
        self._perm_count = 0
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, self, "_checkPermission:", None, True
        )
    
    def _checkPermission_(self, timer):
        """定时检查权限"""
        self._perm_count += 1
        if check_accessibility():
            timer.invalidate()
            print("已获得权限")
            self._start_event_tap()
        elif self._perm_count >= 30:
            timer.invalidate()
            print("权限检查超时")
            self.status_bar.send_notification("授权超时", "请点击菜单'检查权限'重试")
    
    def retry_permission_check(self):
        """手动检查权限"""
        if self.event_tap and self.event_tap.running:
            return True
        if check_accessibility():
            self._start_event_tap()
            return True
        open_accessibility_settings()
        self.status_bar.send_notification("请授权", "请在设置中授权 CommondX")
        return False
    
    def _start_event_tap(self):
        """启动事件监听"""
        if not self.event_tap.start():
            print("启动失败")
            self.status_bar.send_notification("启动失败", "请重启应用")
            return
        
        print("CommondX 已启动")
        self.status_bar.send_notification("CommondX", "已启动，⌘+X 剪切文件")
    
    def on_cut(self):
        """⌘+X 回调函数 (仅 Finder)"""
        print("[App] on_cut() 被调用")
        success, should_show_dialog = self.cut_manager.cut()
        
        if not success:
            return False
        
        if should_show_dialog:
            files = self.cut_manager.last_selection
            if files:
                self.status_bar.show_smart_operations_menu(files)
            return True
        
        return True
    
    def on_paste(self):
        """⌘+V 回调函数 (仅 Finder)"""
        if not self.cut_manager.has_cut_files:
            return False
        ok, msg = self.cut_manager.paste()
        return True

    def applicationWillTerminate_(self, _):
        """退出应用"""
        if self.event_tap:
            self.event_tap.stop()
        print("CommondX 已退出")
