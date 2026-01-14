#!/usr/bin/env python3
"""
CommondX 应用主逻辑

修复说明：
针对 ⌘+C 触发 AI 逻辑，改为异步线程监听，解决系统剪贴板更新延迟导致的“需按三次”问题。
"""

import time
import objc
import threading
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
            self._current_alert = None  # 当前弹窗引用
            
            # Kimi API 相关变量
            self.last_clipboard_content = None
            self.last_copy_time = 0
            self.COPY_INTERVAL = 5.0  # 5秒内的连续复制视为"连续"
            self.last_triggered_content = None  # 最近一次触发的内容
            self.last_triggered_time = 0  # 最近一次触发的时间
            self.TRIGGER_COOLDOWN = 3.0  # 触发冷却时间
        return self
    
    def applicationDidFinishLaunching_(self, _):
        """应用启动"""
        print("CommondX 启动中...")
        self.license_status, code, self.remaining = license_manager.get_status()
        print(f"License: {self.license_status}, Code: {code}, Remaining: {self.remaining}d")
        
        self.cut_manager = CutManager()
        self.status_bar = StatusBarIcon.alloc().initWithCutManager_(self.cut_manager)
        
        # 传入回调函数
        self.event_tap = EventTap(
            on_cut=self.on_cut,
            on_paste=self.on_paste,
            on_copy=self.on_copy,
            on_license_invalid=self._on_license_invalid
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
        msgs = {
            "trial": f"试用期剩余 {self.remaining} 天",
            "expired": "试用期已结束，请购买激活码延长1年"
        }
        msg = msgs.get(self.license_status, "已启动，⌘+X 剪切文件")
        self.status_bar.send_notification("CommondX", msg)
    
    def _on_license_invalid(self):
        """许可证无效时的回调"""
        print("[App] 许可证无效，显示激活提示")
        self.status_bar.show_activation_required()
    
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

    # --- ⌘+C AI 触发逻辑修复区 ---

    def on_copy(self):
        """
        ⌘+C 回调函数（全局监听）
        修复：开启异步线程处理，避开系统正在写入剪贴板的时间锁。
        """
        print("[App] on_copy() 触发，开启异步检查线程")
        thread = threading.Thread(target=self._async_copy_check)
        thread.daemon = True
        thread.start()

    def _async_copy_check(self):
        """异步检查剪贴板内容"""
        # 核心修复：等待 150ms，确保系统已完成内容写入
        time.sleep(0.15)
        
        # 使用工具函数读取最新内容
        current_content = get_clipboard_content()
        current_time = time.time()
        
        if not current_content:
            return

        # 检查是否满足触发条件
        if self._should_trigger_kimi(current_content, current_time):
            print(f"[App] ✓ 检测到连续两次复制，内容长度: {len(current_content)}")
            self._execute_kimi_workflow(current_content)
        
        # 更新状态记录
        self.last_clipboard_content = current_content
        self.last_copy_time = current_time

    def _should_trigger_kimi(self, current_content, current_time):
        """判断是否满足 AI 触发逻辑"""
        if not self.last_clipboard_content:
            return False
            
        # 1. 内容比对（去除首尾空格干扰）
        content_equal = (current_content.strip() == self.last_clipboard_content.strip())
        
        # 2. 时间间隔检查
        time_diff = current_time - self.last_copy_time
        
        # 3. 冷却与重复触发检查
        is_in_cooldown = (current_content == self.last_triggered_content and 
                         (current_time - self.last_triggered_time) < self.TRIGGER_COOLDOWN)
        
        return content_equal and time_diff < self.COPY_INTERVAL and not is_in_cooldown

    def _execute_kimi_workflow(self, content):
        """执行 Kimi API 插件逻辑"""
        if self._current_alert:
            return
        
        self.last_triggered_content = content
        self.last_triggered_time = time.time()
        
        # 调用插件
        from .plugins.kimi_api_plugin import execute as kimi_execute
        success, msg, result = kimi_execute(content, "translate")
        
        if success and self.status_bar:
            self._current_alert = True
            # 将 UI 弹出任务调度回主线程执行，确保稳定性
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                self._showUiResult_, [content, result], False
            )
        else:
            print(f"[App] Kimi 调用失败: {msg}")

    def _showUiResult_(self, args):
        """主线程 UI 渲染方法"""
        content, result = args
        try:
            self.status_bar.show_kimi_result_popup(content, result)
        finally:
            self._current_alert = None

    def applicationWillTerminate_(self, _):
        """退出应用"""
        if self.event_tap:
            self.event_tap.stop()
        print("CommondX 已退出")