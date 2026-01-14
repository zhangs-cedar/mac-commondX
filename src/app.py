#!/usr/bin/env python3
"""
CommondX 应用主逻辑 - 优化版

主要改进：
1. 增强了 ⌘+C 触发 AI 的稳定性，增加了内容清洗（strip）和长度校验。
2. 增加了防抖锁，防止多次 API 调用导致弹窗堆叠。
3. 优化了触发时间窗口，提升响应灵敏度。
"""

import time
import objc
import traceback
from Foundation import NSObject, NSTimer
from AppKit import NSPasteboard, NSStringPboardType
from cedar.utils import print

from .event_tap import EventTap
from .cut_manager import CutManager
from .status_bar import StatusBarIcon
from .license_manager import license_manager
from .permission import check_accessibility, request_accessibility, open_accessibility_settings
from .utils import get_clipboard_content


class CommondXApp(NSObject):
    """CommondX 应用代理"""
    
    def init(self):
        self = objc.super(CommondXApp, self).init()
        if self:
            self.cut_manager = self.event_tap = self.status_bar = None
            self._current_alert = None
            
            # Kimi API 相关变量优化
            self.last_clipboard_content = None
            self.last_copy_time = 0
            self.COPY_INTERVAL = 5.0      # 最大间隔 5 秒
            self.MIN_TRIGGER_INTERVAL = 0.2 # 最小间隔 0.2 秒，防止按键抖动
            self.TRIGGER_COOLDOWN = 3.0   # 相同内容的冷却时间
            self.last_triggered_content = None
            self.last_triggered_time = 0
            self._is_processing_kimi = False # API 处理锁
            
        return self
    
    def applicationDidFinishLaunching_(self, _):
        """应用启动"""
        print("CommondX 启动中...")
        self.license_status, code, self.remaining = license_manager.get_status()
        
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
        """尝试启动逻辑"""
        if check_accessibility():
            return self._start_event_tap()
        
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
            self._start_event_tap()
        elif self._perm_count >= 30:
            timer.invalidate()
    
    def _start_event_tap(self):
        """启动事件监听"""
        if not self.event_tap.start():
            self.status_bar.send_notification("启动失败", "请重启应用")
            return
        print("CommondX 已启动")
    
    def _on_license_invalid(self):
        """许可证无效回调"""
        self.status_bar.show_activation_required()

    def _should_trigger_kimi(self, current_content, current_time):
        """
        核心逻辑优化：检查是否应该触发 Kimi API
        """
        if not current_content or not isinstance(current_content, str):
            return False
        
        # 1. 清洗内容：去除首尾空格/换行，确保匹配率
        curr_strip = current_content.strip()
        last_strip = self.last_clipboard_content.strip() if self.last_clipboard_content else ""
        
        # 2. 长度校验：避免复制单个字符时误触
        if len(curr_strip) < 2:
            return False
            
        # 3. 时间间隔检查
        time_diff = current_time - self.last_copy_time if self.last_copy_time > 0 else float('inf')
        
        # 4. 内容一致性检查
        content_equal = (curr_strip == last_strip)
        
        # 5. 冷却逻辑检查
        time_since_last_trigger = current_time - self.last_triggered_time if self.last_triggered_time > 0 else float('inf')
        is_same_as_last_trigger = (curr_strip == (self.last_triggered_content.strip() if self.last_triggered_content else ""))
        in_cooldown = is_same_as_last_trigger and time_since_last_trigger < self.TRIGGER_COOLDOWN
        
        # 触发条件：内容一致 AND 时间在有效窗口内 AND 未处于冷却 AND 当前未在处理
        should_trigger = (
            content_equal and 
            self.MIN_TRIGGER_INTERVAL < time_diff < self.COPY_INTERVAL and
            not in_cooldown and
            not self._is_processing_kimi
        )
        
        return should_trigger

    def on_copy(self):
        """
        ⌘+C 回调函数（全局监听优化版）
        """
        try:
            current_content = self._read_clipboard_content()
            current_time = time.time()
            
            if not current_content:
                return

            if self._should_trigger_kimi(current_content, current_time):
                # 开启防抖锁
                self._is_processing_kimi = True
                self.last_triggered_content = current_content
                self.last_triggered_time = current_time
                
                print(f"[App] ✓ 检测到连续复制，调用 Kimi API...")
                
                # 调用插件
                from .plugins.kimi_api_plugin import execute as kimi_execute
                # 这里保持同步调用以确保 UI 响应顺序，如果网络极慢建议改用后台线程
                success, msg, result = kimi_execute(current_content, "translate")
                
                if success:
                    if self.status_bar:
                        self.status_bar.show_kimi_result_popup(current_content, result)
                else:
                    print(f"[App] ✗ Kimi 调用失败: {msg}")
                    self.status_bar.send_notification("Kimi 异常", msg)
                
                # 释放锁
                self._is_processing_kimi = False
            
            # 更新记录
            self.last_clipboard_content = current_content
            self.last_copy_time = current_time
            
        except Exception as e:
            print(f"[ERROR] [App] on_copy 逻辑异常: {e}")
            self._is_processing_kimi = False
            traceback.print_exc()

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