#!/usr/bin/env python3
import time
import objc
import threading
import traceback
from Foundation import NSObject, NSTimer
from AppKit import NSPasteboard, NSStringPboardType
from cedar.utils import print

from .event_tap import EventTap
from .cut_manager import CutManager
from .status_bar import StatusBarIcon
from .license_manager import license_manager
from .permission import check_accessibility, request_accessibility
from .utils import get_clipboard_content

class CommondXApp(NSObject):
    def init(self):
        self = objc.super(CommondXApp, self).init()
        if self:
            self.cut_manager = self.event_tap = self.status_bar = None
            
            # AI 触发相关状态
            self.last_clipboard_content = None
            self.last_copy_time = 0
            self.last_triggered_content = None
            self.last_triggered_time = 0
            
            # 配置项
            self.COPY_INTERVAL = 5.0      # 5秒内双击触发
            self.TRIGGER_COOLDOWN = 3.0   # 触发后冷却
            self._is_processing_api = False # 线程锁
            
        return self
    
    def applicationDidFinishLaunching_(self, _):
        self.cut_manager = CutManager()
        self.status_bar = StatusBarIcon.alloc().initWithCutManager_(self.cut_manager)
        self.event_tap = EventTap(
            on_cut=self.on_cut,
            on_paste=self.on_paste,
            on_copy=self.on_copy,
            on_license_invalid=self._on_license_invalid
        )
        self._try_start()
    
    def _try_start(self):
        if check_accessibility():
            return self.event_tap.start()
        request_accessibility()
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, self, "_checkPermission:", None, True
        )
    
    def _checkPermission_(self, timer):
        if check_accessibility():
            timer.invalidate()
            self.event_tap.start()

    def on_copy(self):
        """⌘+C 回调处理"""
        try:
            # 读取剪贴板内容
            content = self._read_clipboard_safe()
            now = time.time()
            if not content: return

            # 触发逻辑判断
            if self._should_trigger(content, now):
                # 开启异步线程处理 API，避免卡顿
                thread = threading.Thread(target=self._call_ai_task, args=(content,))
                thread.daemon = True
                thread.start()
            
            self.last_clipboard_content = content
            self.last_copy_time = now
            
        except Exception as e:
            print(f"on_copy error: {e}")

    def _should_trigger(self, content, now):
        if self._is_processing_api: return False
        
        c_strip = content.strip()
        l_strip = self.last_clipboard_content.strip() if self.last_clipboard_content else ""
        
        if len(c_strip) < 2: return False # 太短不触发
        
        time_diff = now - self.last_copy_time
        is_double_copy = (c_strip == l_strip) and (0.1 < time_diff < self.COPY_INTERVAL)
        
        # 冷却检查：防止对同一内容短时间内重复弹窗
        is_cooling = (c_strip == (self.last_triggered_content or "").strip()) and \
                     (now - self.last_triggered_time < self.TRIGGER_COOLDOWN)
        
        return is_double_copy and not is_cooling

    def _call_ai_task(self, content):
        """后台 API 任务"""
        self._is_processing_api = True
        self.last_triggered_content = content
        self.last_triggered_time = time.time()
        
        from .plugins.kimi_api_plugin import execute
        success, msg, result = execute(content, "translate")
        
        if success:
            # 回到主线程弹出 UI
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "showResult:", result, False
            )
        self._is_processing_api = False

    @objc.signature(b'v@:@')
    def showResult_(self, result):
        if self.status_bar:
            self.status_bar.show_kimi_result_popup(self.last_triggered_content, result)

    def _read_clipboard_safe(self):
        pb = NSPasteboard.generalPasteboard()
        for _ in range(3): # 尝试 3 次解决系统同步延迟
            res = pb.stringForType_(NSStringPboardType)
            if res: return res
            time.sleep(0.05)
        return get_clipboard_content()
    def on_cut(self):
        """⌘+X 回调函数"""
        success, should_show_dialog = self.cut_manager.cut()
        if not success:
            return False
        
        if should_show_dialog:
            files = self.cut_manager.last_selection
            if files and self.status_bar:
                self.status_bar.show_smart_operations_menu(files)
            return True
        
        return True
    
    def on_paste(self):
        """⌘+V 回调函数"""
        if not self.cut_manager.has_cut_files:
            return False
        ok, msg = self.cut_manager.paste()
        return True
    
    def _read_clipboard_content(self):
        """高效读取剪贴板内容"""
        pb = NSPasteboard.generalPasteboard()
        # 尝试多次读取以应对系统剪贴板更新延迟
        for _ in range(3):
            content = pb.stringForType_(NSStringPboardType)
            if content:
                return content
            time.sleep(0.05)
        return get_clipboard_content()

    def applicationWillTerminate_(self, _):
        """退出应用"""
        if self.event_tap:
            self.event_tap.stop()
        print("CommondX 已退出")