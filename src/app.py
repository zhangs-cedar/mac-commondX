#!/usr/bin/env python3
"""
CommondX 应用主逻辑

【工作流程说明】
按照流程图顺序：
1. EventTap 捕获 ⌘+X 事件
2. EventTap 检查是否为 Finder 窗口
3. EventTap 检查许可证
4. EventTap 调用 on_cut()（如果许可证有效）
5. on_cut() 调用 cut_manager.cut() 处理文件选择
6. 如果选择相同，显示智能操作弹窗
7. 处理用户选择的操作（复制路径/压缩/解压）
"""

import objc
from Foundation import NSObject, NSTimer
from AppKit import NSApp
from cedar.utils import print

from .event_tap import EventTap
from .cut_manager import CutManager
from .status_bar import StatusBarIcon
from .license_manager import license_manager
from .permission import check_accessibility, request_accessibility, open_accessibility_settings
from .archive_manager import compress_to_zip, decompress_archive
from .utils import copy_to_clipboard


class CommondXApp(NSObject):
    """CommondX 应用代理"""
    
    def init(self):
        self = objc.super(CommondXApp, self).init()
        if self:
            self.cut_manager = self.event_tap = self.status_bar = None
            self._current_alert = None  # 当前弹窗引用
        return self
    
    def applicationDidFinishLaunching_(self, _):
        """应用启动"""
        print("CommondX 启动中...")
        self.license_status, code, self.remaining = license_manager.get_status()
        print(f"License: {self.license_status}, Code: {code}, Remaining: {self.remaining}d")
        
        self.cut_manager = CutManager()
        self.status_bar = StatusBarIcon.alloc().initWithCutManager_(self.cut_manager)
        # 传入许可证无效时的回调函数
        self.event_tap = EventTap(
            on_cut=self.on_cut,
            on_paste=self.on_paste,
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
        """
        许可证无效时的回调函数
        
        由 EventTap 在检测到许可证无效时调用，用于显示激活提示。
        注意：这个函数在系统事件回调中被调用，所以不能执行耗时操作。
        """
        print("[5] [App] 许可证无效，显示激活提示")
        self.status_bar.show_activation_required()
    
    def _restoreEventTap_(self, timer):
        """
        延迟恢复 Event Tap（由定时器调用）
        
        在弹窗关闭后延迟调用，确保系统完全退出模态状态后再恢复 Event Tap。
        会尝试多次，直到成功或达到最大尝试次数。
        """
        if not hasattr(self, '_restore_event_tap_attempts'):
            self._restore_event_tap_attempts = 0
        if not hasattr(self, '_restore_event_tap_max_attempts'):
            self._restore_event_tap_max_attempts = 3
        
        self._restore_event_tap_attempts += 1
        attempt = self._restore_event_tap_attempts
        max_attempts = self._restore_event_tap_max_attempts
        
        print(f"[7.4] [App] 延迟恢复 Event Tap（尝试 {attempt}/{max_attempts}）...")
        
        if self.event_tap:
            if self.event_tap.ensure_enabled():
                print(f"[7.4] [App] ✓ Event Tap 已确保启用（尝试 {attempt}）")
                self._restore_event_tap_attempts = 0  # 成功后重置计数器
                return
            else:
                print(f"[7.4] [App] ✗ Event Tap 确保启用失败（尝试 {attempt}），尝试重新启动...")
                if self.event_tap.running:
                    self.event_tap.stop()
                if self.event_tap.start():
                    print(f"[7.4] [App] ✓ Event Tap 已重新启动（尝试 {attempt}）")
                    self._restore_event_tap_attempts = 0  # 成功后重置计数器
                    return
                else:
                    print(f"[7.4] [App] ✗ Event Tap 重新启动失败（尝试 {attempt}）")
        
        # 如果达到最大尝试次数，记录警告
        if attempt >= max_attempts:
            print(f"[7.4] [App] ⚠️ Event Tap 恢复失败，已达到最大尝试次数 {max_attempts}")
    
    def on_cut(self):
        """
        ⌘+X 回调函数
        
        【调用时机】
        当用户在 Finder 中按下 ⌘+X 时，EventTap 会调用这个函数。
        注意：此时已经通过了许可证检查（在 EventTap 中完成）。
        
        【工作流程】
        1. 调用 cut_manager.cut() 处理文件选择
        2. 如果选择与上次相同，显示智能操作弹窗
        3. 如果选择不同，执行正常的剪切操作
        """
        print("[5] [App] on_cut() 被调用（已通过许可证检查）")
        
        # 【步骤 6】调用 cut_manager.cut() 处理文件选择
        print("[6] [App] 调用 cut_manager.cut()...")
        success, should_show_dialog = self.cut_manager.cut()
        print(f"[6] [App] cut_manager.cut() 返回 - success={success}, should_show_dialog={should_show_dialog}")
        print(f"[6] [App] 当前 last_selection={self.cut_manager.last_selection}")
        
        if not success:
            print("[6] [App] cut() 失败（无文件或文件无效），返回 False")
            return False
        
        # 【步骤 7】如果应该显示智能操作菜单（选择与上次相同）
        if should_show_dialog:
            print("[7] [App] 需要显示智能操作菜单（选择与上次相同）")
            files = self.cut_manager.last_selection
            print(f"[7] [App] 文件列表: {files}")
            
            if not files:
                print("[7] [App] 文件列表为空，跳过菜单显示")
                return True
            
            # 【步骤 7.1】显示状态栏菜单（支持键盘上下键导航）
            print("[7.1] [App] 显示文件智能操作菜单...")
            if self.status_bar:
                self.status_bar.show_smart_operations_menu(files)
                print("[7.1] [App] ✓ 菜单已显示，用户可以使用键盘上下键选择操作")
            else:
                print("[7.1] [App] ✗ 状态栏未初始化，无法显示菜单")
            
            # 注意：菜单选择后会自动调用对应的处理方法（smartCompress_、smartDecompress_ 等）
            # 这些方法会处理操作并重置 last_selection
            # 如果用户没有选择任何操作（按 ESC 或点击外部），保持 last_selection 不变
            
            return True
        
        # 【步骤 8】正常剪切操作（选择与上次不同）
        print("[8] [App] 执行正常剪切操作（选择与上次不同）")
        import time
        print(f"[DEBUG] [App] 调试日志 - sessionId=debug-session, runId=run2, hypothesisId=F, location=app.py:on_cut, message=执行正常剪切操作, data={{has_cut_files={self.cut_manager.has_cut_files}, count={self.cut_manager.count}, timestamp={time.time()}}}, timestamp={int(time.time() * 1000)}")
        if self.cut_manager.has_cut_files:
            count = self.cut_manager.count
            print(f"[8] [App] 已剪切 {count} 个文件")
            # self.status_bar.send_notification("已剪切", f"{count} 个文件待移动")
        else:
            print("[8] [App] 无剪切文件")
        
        return True
    
    def _handle_file_operation(self, action, files):
        """
        处理文件智能操作
        
        Args:
            action: 操作类型 ("copy"、"compress"、"decompress" 或 None)
            files: 文件路径列表
        """
        print(f"[7.3] [App] _handle_file_operation() - action={action}, files_count={len(files) if files else 0}")
        
        if not action or not files:
            print(f"[7.3] [App] 参数无效，退出 - action={action}")
            return
        
        if action == "copy":
            print("[7.3] [App] 执行复制路径操作...")
            paths_text = "\n".join(files)
            copy_to_clipboard(paths_text)
            count = len(files)
            msg = f"已复制 {count} 个文件路径" if count > 1 else "已复制文件路径"
            self.status_bar.send_notification("✅ 已复制路径", msg)
            print(f"[7.3] [App] ✓ 复制路径完成: {count} 个文件")
        
        elif action == "compress":
            print("[7.3] [App] 执行压缩操作...")
            success, msg, output_path = compress_to_zip(files)
            if success:
                self.status_bar.send_notification("✅ 压缩成功", msg)
                print(f"[7.3] [App] ✓ 压缩成功: {msg}")
            else:
                self.status_bar.send_notification("❌ 压缩失败", msg)
                print(f"[7.3] [App] ✗ 压缩失败: {msg}")
        
        elif action == "decompress":
            print("[7.3] [App] 执行解压操作...")
            for archive_path in files:
                success, msg, output_dir = decompress_archive(archive_path)
                if success:
                    self.status_bar.send_notification("✅ 解压成功", msg)
                    print(f"[7.3] [App] ✓ 解压成功: {msg}")
                else:
                    self.status_bar.send_notification("❌ 解压失败", msg)
                    print(f"[7.3] [App] ✗ 解压失败: {msg}")
        else:
            print(f"[7.3] [App] 未知操作类型: {action}")
    
    def on_paste(self):
        """
        ⌘+V 回调函数
        
        注意：许可证检查已在 EventTap 中完成。
        """
        print("[App] on_paste() 被调用")
        if not self.cut_manager.has_cut_files:
            print("[App] 无待移动文件，返回 False")
            return False
        print("[App] 执行粘贴（移动）操作...")
        ok, msg = self.cut_manager.paste()
        print(f"[App] 粘贴操作完成: {msg}")
        return True
    
    def applicationWillTerminate_(self, _):
        """退出"""
        if self.event_tap:
            self.event_tap.stop()
        print("CommondX 已退出")
