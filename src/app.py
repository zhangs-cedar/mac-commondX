#!/usr/bin/env python3
"""CommondX 应用主逻辑"""

import objc
from Foundation import NSObject, NSTimer
from AppKit import NSApp
from cedar.utils import print

from .event_tap import EventTap
from .cut_manager import CutManager
from .status_bar import StatusBarIcon
from .license_manager import license_manager
from .permission import check_accessibility, request_accessibility, open_accessibility_settings
from .file_dialog import show_file_operations_dialog
from .archive_manager import compress_to_zip, decompress_archive


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
        self.event_tap = EventTap(on_cut=self.on_cut, on_paste=self.on_paste)
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
            "activated": "已启动，Cmd+X 剪切文件",
            "trial": f"试用期剩余 {self.remaining} 天",
            "expired": "试用期已结束，请购买激活码"
        }
        self.status_bar.send_notification("CommondX", msgs.get(self.license_status, ""))
    
    def _check_license(self):
        """检查许可，无效则提示"""
        if license_manager.is_valid():
            return True
        self.status_bar.show_activation_required()
        return False
    
    def on_cut(self):
        """Cmd+X 回调"""
        print("[DEBUG] on_cut() 进入")
        
        if not self._check_license():
            print("[DEBUG] on_cut() 许可证检查失败，退出")
            return True
        
        print(f"[DEBUG] on_cut() 调用 cut_manager.cut()")
        success, should_show_dialog = self.cut_manager.cut()
        print(f"[DEBUG] on_cut() cut_manager.cut() 返回: success={success}, should_show_dialog={should_show_dialog}")
        print(f"[DEBUG] on_cut() last_selection={self.cut_manager.last_selection}")
        print(f"[DEBUG] on_cut() _current_alert={self._current_alert}")
        
        if not success:
            print("[DEBUG] on_cut() cut() 失败，退出")
            return False
        
        # 如果应该显示智能操作弹窗（连续两次相同选择）
        if should_show_dialog:
            print("[DEBUG] on_cut() 需要显示智能操作弹窗")
            files = self.cut_manager.last_selection
            print(f"[DEBUG] on_cut() 获取的文件列表: {files}")
            
            if files:
                # 如果已有弹窗，先关闭它
                if self._current_alert:
                    print("[DEBUG] on_cut() 检测到已有弹窗，先关闭它")
                    NSApp.stopModal()
                    self._current_alert = None
                    print("[DEBUG] on_cut() 已关闭旧弹窗")
                
                # 显示新弹窗（runModal 是阻塞的，返回时弹窗已关闭）
                print("[DEBUG] on_cut() 准备显示弹窗")
                action, alert = show_file_operations_dialog(files)
                print(f"[DEBUG] on_cut() 弹窗返回: action={action}, alert={alert}")
                self._current_alert = alert
                print(f"[DEBUG] on_cut() 保存弹窗引用: _current_alert={self._current_alert}")
                
                print("[DEBUG] on_cut() 调用 _handle_file_operation()")
                self._handle_file_operation(action, files)
                print(f"[DEBUG] on_cut() _handle_file_operation() 执行完成，action={action}")
                
                # 弹窗操作完成后，重置 last_selection，避免后续一直触发弹窗
                print(f"[DEBUG] on_cut() 重置前 last_selection={self.cut_manager.last_selection}")
                self.cut_manager.last_selection = None
                print(f"[DEBUG] on_cut() 重置后 last_selection={self.cut_manager.last_selection}")
                self._current_alert = None
                print(f"[DEBUG] on_cut() 清空弹窗引用: _current_alert={self._current_alert}")
            else:
                print("[DEBUG] on_cut() 文件列表为空，跳过弹窗")
            
            print("[DEBUG] on_cut() 弹窗处理完成，退出")
            return True
        
        # 正常剪切操作
        print("[DEBUG] on_cut() 正常剪切操作")
        if self.cut_manager.has_cut_files:
            print(f"[DEBUG] on_cut() 有剪切文件: count={self.cut_manager.count}")
            self.status_bar.send_notification("已剪切", f"{self.cut_manager.count} 个文件待移动")
        else:
            print("[DEBUG] on_cut() 无剪切文件")
        
        print("[DEBUG] on_cut() 退出")
        return True
    
    def _handle_file_operation(self, action, files):
        """处理文件智能操作"""
        print(f"[DEBUG] _handle_file_operation() 进入: action={action}, files={files}")
        
        if not action or not files:
            print(f"[DEBUG] _handle_file_operation() 参数无效，退出: action={action}, files={files}")
            return
        
        if action == "copy":
            print("[DEBUG] _handle_file_operation() 执行复制路径操作")
            # 复制路径
            from AppKit import NSPasteboard, NSStringPboardType
            pb = NSPasteboard.generalPasteboard()
            pb.clearContents()
            paths_text = "\n".join(files)
            pb.setString_forType_(paths_text, NSStringPboardType)
            count = len(files)
            msg = f"已复制 {count} 个文件路径" if count > 1 else "已复制文件路径"
            self.status_bar.send_notification("✅ 已复制路径", msg)
            print(f"[DEBUG] _handle_file_operation() 复制路径完成: {count} 个文件")
        
        elif action == "compress":
            print("[DEBUG] _handle_file_operation() 执行压缩操作")
            # 压缩为 ZIP
            success, msg, output_path = compress_to_zip(files)
            if success:
                self.status_bar.send_notification("✅ 压缩成功", msg)
                print(f"[DEBUG] _handle_file_operation() 压缩成功: {msg}")
            else:
                self.status_bar.send_notification("❌ 压缩失败", msg)
                print(f"[DEBUG] _handle_file_operation() 压缩失败: {msg}")
        
        elif action == "decompress":
            print("[DEBUG] _handle_file_operation() 执行解压操作")
            # 解压压缩文件
            for archive_path in files:
                success, msg, output_dir = decompress_archive(archive_path)
                if success:
                    self.status_bar.send_notification("✅ 解压成功", msg)
                    print(f"[DEBUG] _handle_file_operation() 解压成功: {msg}")
                else:
                    self.status_bar.send_notification("❌ 解压失败", msg)
                    print(f"[DEBUG] _handle_file_operation() 解压失败: {msg}")
        else:
            print(f"[DEBUG] _handle_file_operation() 未知操作类型: {action}")
        
        print(f"[DEBUG] _handle_file_operation() 退出")
    
    def on_paste(self):
        """Cmd+V 回调"""
        if not self._check_license():
            return True
        if not self.cut_manager.has_cut_files:
            return False
        ok, msg = self.cut_manager.paste()
        self.status_bar.send_notification("移动完成" if ok else "移动失败", msg)
        return True
    
    def applicationWillTerminate_(self, _):
        """退出"""
        if self.event_tap:
            self.event_tap.stop()
        print("CommondX 已退出")
