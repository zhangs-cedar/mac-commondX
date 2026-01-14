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
from .utils import copy_to_clipboard, get_clipboard_content


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
            self.COPY_INTERVAL = 5.0  # 5秒内的连续复制视为"连续"（放宽限制）
            self.last_triggered_content = None  # 最近一次触发的内容
            self.last_triggered_time = 0  # 最近一次触发的时间
            self.TRIGGER_COOLDOWN = 3.0  # 触发冷却时间，避免重复触发
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
    
    def on_copy(self):
        """
        ⌘+C 回调函数（全局监听）
        
        检测连续两次 ⌘+C 复制相同内容时，调用 Kimi API 进行翻译、解释等处理。
        
        触发条件：
        1. 连续两次复制的内容相同
        2. 时间间隔在 5 秒内（避免间隔太久）
        3. 不在冷却时间内（3秒内不重复触发相同内容，避免快速复制时多个弹窗）
        """
        print("[App] on_copy() 被调用（全局监听）")
        import time
        import json
        
        # #region agent log
        try:
            with open('/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"app.py:on_copy","message":"函数入口，检查初始状态","data":{"last_content_len":len(self.last_clipboard_content) if self.last_clipboard_content else 0,"last_time":self.last_copy_time,"current_time":time.time(),"time_diff":time.time()-self.last_copy_time if self.last_copy_time > 0 else None},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        
        # 【优化】使用剪贴板变化序列号确保读取到最新内容
        from AppKit import NSPasteboard, NSStringPboardType
        pb = NSPasteboard.generalPasteboard()
        
        # 记录回调时的changeCount（此时可能还没更新）
        initial_change_count = pb.changeCount()
        
        # 延迟并多次尝试读取，直到读取到新内容
        max_attempts = 10
        attempt = 0
        current_content = None
        last_content = None
        
        while attempt < max_attempts:
            time.sleep(0.05)  # 每次等待50ms
            attempt += 1
            
            # 检查剪贴板是否变化
            current_change_count = pb.changeCount()
            temp_content = pb.stringForType_(NSStringPboardType)
            
            # 如果changeCount变化了，说明剪贴板已更新
            if current_change_count != initial_change_count:
                if temp_content:
                    current_content = temp_content
                    print(f"[App] ✓ 读取到剪贴板新内容（尝试{attempt}次，changeCount: {initial_change_count} -> {current_change_count}）")
                    break
            
            # 如果内容稳定（连续两次读取相同），也认为读取成功
            if temp_content and temp_content == last_content and attempt >= 3:
                current_content = temp_content
                print(f"[App] ✓ 内容已稳定（尝试{attempt}次，内容连续相同）")
                break
            
            last_content = temp_content
        
        # 如果多次尝试后仍未读取到，使用最后一次读取的内容
        if not current_content:
            current_content = pb.stringForType_(NSStringPboardType)
            if current_content:
                print(f"[App] ⚠️ 使用当前剪贴板内容（尝试{max_attempts}次后）")
        
        # 如果还是读取不到，使用工具函数读取
        if not current_content:
            current_content = get_clipboard_content()
        
        current_time = time.time()
        
        # #region agent log
        try:
            with open('/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"app.py:on_copy","message":"读取剪贴板内容后","data":{"current_len":len(current_content) if current_content else 0,"current_preview":current_content[:50] if current_content else None,"last_len":len(self.last_clipboard_content) if self.last_clipboard_content else 0,"last_preview":self.last_clipboard_content[:50] if self.last_clipboard_content else None},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        
        print(f"[App] 剪贴板内容长度: {len(current_content) if current_content else 0}")
        
        # 计算时间差
        time_diff = current_time - self.last_copy_time if self.last_copy_time > 0 else float('inf')
        
        # #region agent log
        try:
            with open('/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"app.py:on_copy","message":"时间间隔检查","data":{"time_diff":time_diff,"COPY_INTERVAL":self.COPY_INTERVAL,"within_interval":time_diff < self.COPY_INTERVAL},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        
        # 内容比较（优化：更详细的比较信息）
        content_equal = False
        if current_content and self.last_clipboard_content:
            content_equal = current_content == self.last_clipboard_content
            if not content_equal:
                # 内容不同时，输出调试信息
                print(f"[App] 内容不同 - 当前长度={len(current_content)}, 上次长度={len(self.last_clipboard_content)}")
                print(f"[App] 当前内容预览: {repr(current_content[:50])}")
                print(f"[App] 上次内容预览: {repr(self.last_clipboard_content[:50])}")
        elif not current_content:
            print(f"[App] ⚠️ 当前剪贴板内容为空")
        elif not self.last_clipboard_content:
            print(f"[App] ℹ️ 这是第一次复制，记录内容（下次复制相同内容时触发）")
        
        # #region agent log
        try:
            with open('/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"app.py:on_copy","message":"内容比较结果","data":{"content_equal":content_equal,"current_repr":repr(current_content[:100]) if current_content else None,"last_repr":repr(self.last_clipboard_content[:100]) if self.last_clipboard_content else None},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        
        # 检测连续两次复制相同内容
        # 条件1：内容相同
        # 条件2：时间间隔在合理范围内（避免间隔太久）
        # 条件3：防重复触发（冷却时间内不重复触发相同内容）
        time_since_last_trigger = current_time - self.last_triggered_time if self.last_triggered_time > 0 else float('inf')
        is_same_as_last_trigger = current_content == self.last_triggered_content if current_content and self.last_triggered_content else False
        in_cooldown = is_same_as_last_trigger and time_since_last_trigger < self.TRIGGER_COOLDOWN
        
        should_trigger = (current_content and 
            content_equal and 
            time_diff < self.COPY_INTERVAL and
            not in_cooldown)
        
        # #region agent log
        try:
            with open('/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"F","location":"app.py:on_copy","message":"防重复检查","data":{"last_triggered_content_len":len(self.last_triggered_content) if self.last_triggered_content else 0,"time_since_last_trigger":time_since_last_trigger,"is_same_as_last_trigger":is_same_as_last_trigger,"in_cooldown":in_cooldown,"TRIGGER_COOLDOWN":self.TRIGGER_COOLDOWN},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        
        # #region agent log
        try:
            with open('/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"ALL","location":"app.py:on_copy","message":"触发条件检查（含防重复）","data":{"has_content":bool(current_content),"content_equal":content_equal,"time_diff":time_diff,"within_interval":time_diff < self.COPY_INTERVAL,"in_cooldown":in_cooldown,"should_trigger":should_trigger},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        
        # 【调试优化】输出详细的触发条件信息
        if not should_trigger and current_content:
            reason_parts = []
            if not content_equal:
                reason_parts.append("内容不同")
            if time_diff >= self.COPY_INTERVAL:
                reason_parts.append(f"时间间隔过长({time_diff:.2f}s > {self.COPY_INTERVAL}s)")
            if in_cooldown:
                reason_parts.append(f"冷却中(剩余{self.TRIGGER_COOLDOWN - time_since_last_trigger:.2f}s)")
            if reason_parts:
                print(f"[App] 未触发原因: {', '.join(reason_parts)}")
        
        if should_trigger:
            # 【防多弹窗】检查是否已有弹窗正在显示
            if self._current_alert is not None:
                print(f"[App] ⚠️ 已有弹窗正在显示，跳过本次触发")
                return
            
            # 【防重复优化】立即更新触发状态，防止快速连续触发
            self.last_triggered_content = current_content
            self.last_triggered_time = current_time
            
            print(f"[App] ✓ 检测到连续两次复制相同内容，调用 Kimi API...")
            print(f"[App] 内容预览: {current_content[:100]}...")
            
            # 调用 Kimi API 插件
            from .plugins.kimi_api_plugin import execute as kimi_execute
            success, msg, result = kimi_execute(current_content, "translate")
            
            if success:
                print(f"[App] ✓ Kimi API 调用成功，结果显示弹窗")
                # 显示结果弹窗
                if self.status_bar:
                    # 标记弹窗正在显示
                    self._current_alert = True
                    try:
                        self.status_bar.show_kimi_result_popup(current_content, result)
                    finally:
                        # 弹窗关闭后清除标记
                        self._current_alert = None
                
                # #region agent log
                try:
                    with open('/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run2","hypothesisId":"F","location":"app.py:on_copy","message":"已触发并记录触发信息","data":{"triggered_content_len":len(current_content) if current_content else 0,"triggered_time":current_time},"timestamp":int(time.time()*1000)})+'\n')
                except: pass
                # #endregion
            else:
                print(f"[App] ✗ Kimi API 调用失败: {msg}")
                # API 调用失败时清除标记
                self._current_alert = None
                if self.status_bar:
                    self.status_bar.send_notification("Kimi API 调用失败", msg)
        else:
            # 不触发时的详细日志（已在上面输出，这里简化）
            pass
        
        # 更新记录
        # #region agent log
        try:
            with open('/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"app.py:on_copy","message":"更新记录前","data":{"old_last_content_len":len(self.last_clipboard_content) if self.last_clipboard_content else 0,"new_content_len":len(current_content) if current_content else 0},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        
        self.last_clipboard_content = current_content
        self.last_copy_time = current_time
        
        # #region agent log
        try:
            with open('/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"app.py:on_copy","message":"更新记录后","data":{"last_content_len":len(self.last_clipboard_content) if self.last_clipboard_content else 0,"last_time":self.last_copy_time},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
    
    def applicationWillTerminate_(self, _):
        """退出"""
        if self.event_tap:
            self.event_tap.stop()
        print("CommondX 已退出")
