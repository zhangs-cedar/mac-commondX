#!/usr/bin/env python3
"""状态栏图标"""

import objc
from pathlib import Path
from Foundation import NSObject, NSTimer
from AppKit import (
    NSStatusBar, NSMenu, NSMenuItem, NSImage, NSColor, NSApplication,
    NSSize, NSRect, NSPoint, NSBezierPath, NSAffineTransform,
    NSUserNotificationCenter, NSUserNotification
)
from cedar.utils import print

from .archive_manager import compress_to_zip, decompress_archive
from .utils import copy_to_clipboard


def _add_menu_item(menu, target, title, action=None, key="", enabled=True):
    """创建菜单项（类外函数避免 PyObjC 冲突）"""
    item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
    if action:
        item.setTarget_(target)
    item.setEnabled_(enabled)
    menu.addItem_(item)
    return item


class StatusBarIcon(NSObject):
    """状态栏图标"""
    
    def initWithCutManager_(self, cut_manager):
        self = objc.super(StatusBarIcon, self).init()
        if self:
            self.cut_manager = cut_manager
            self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
            self.animation_timer = None
            self.animation_frame = 0
            self.cached_files = []  # 缓存上次获取的文件列表
            self.update_icon(0)
            self.setup_menu()
            cut_manager.on_state_change = self.on_cut_state_change
        return self
    
    def on_cut_state_change(self, files):
        """剪切状态变化"""
        count = len(files)
        if count > 0:
            self.start_cut_animation(count)
            self.files_header.setTitle_(files[0] if count == 1 else f"待移动 {count} 个文件")
        else:
            self.update_icon(0)
            self.files_header.setTitle_("无待移动文件")
            
    def start_cut_animation(self, count):
        """播放剪切动画"""
        if self.animation_timer:
            self.animation_timer.invalidate()
        self.animation_frame = 0
        self.target_count = count
        self.animation_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.05, self, "animateIcon:", None, True
        )
        
    def animateIcon_(self, timer):
        """动画回调"""
        angles = [0, 15, 30, 15, 0, 0]
        self.animation_frame += 1
        if self.animation_frame < len(angles):
            self.update_icon(self.target_count, angles[self.animation_frame])
        else:
            timer.invalidate()
            self.animation_timer = None
            self.update_icon(self.target_count)

    def _draw_blade(self, angle, is_left):
        """绘制剪刀刀刃"""
        path = NSBezierPath.bezierPath()
        path.setLineWidth_(1.5)
        path.setLineJoinStyle_(1)
        path.setLineCapStyle_(1)
        
        if is_left:
            path.appendBezierPathWithOvalInRect_(NSRect(NSPoint(4, 3), NSSize(5, 5)))
            path.moveToPoint_(NSPoint(6.5, 8))
            path.lineToPoint_(NSPoint(16, 19))
        else:
            path.appendBezierPathWithOvalInRect_(NSRect(NSPoint(13, 3), NSSize(5, 5)))
            path.moveToPoint_(NSPoint(15.5, 8))
            path.lineToPoint_(NSPoint(6, 19))
        
        if angle > 0:
            t = NSAffineTransform.transform()
            t.translateXBy_yBy_(11, 11)
            t.rotateByDegrees_(angle if is_left else -angle)
            t.translateXBy_yBy_(-11, -11)
            path.transformUsingAffineTransform_(t)
        path.stroke()

    def update_icon(self, count, angle=0):
        """更新图标"""
        image = NSImage.alloc().initWithSize_(NSSize(22, 22))
        image.lockFocus()
        NSColor.labelColor().setStroke()
        
        # 缩放居中
        t = NSAffineTransform.transform()
        t.translateXBy_yBy_(2.2, 2.2)
        t.scaleBy_(0.8)
        t.concat()
        
        self._draw_blade(angle, True)
        self._draw_blade(angle, False)
        
        if count > 0:
            NSColor.systemRedColor().setFill()
            NSBezierPath.bezierPathWithOvalInRect_(NSRect(NSPoint(12, 0), NSSize(10, 10))).fill()
        
        image.unlockFocus()
        image.setTemplate_(count == 0)
        self.status_item.setImage_(image)
        self.status_item.setTitle_(f" {count}" if count > 0 else "")
    
    def _show_alert(self, title, msg, with_input=False):
        """显示弹窗"""
        from AppKit import NSAlert, NSTextField, NSApp
        NSApp.setActivationPolicy_(0)
        NSApp.activateIgnoringOtherApps_(True)
        
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(msg)
        alert.addButtonWithTitle_("确定" if not with_input else "激活")
        
        field = None
        if with_input:
            alert.addButtonWithTitle_("取消")
            field = NSTextField.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(250, 24)))
            field.setPlaceholderString_("激活码")
            field.setEditable_(True)
            field.setSelectable_(True)
            field.setBezeled_(True)
            field.setDrawsBackground_(True)
            alert.setAccessoryView_(field)
            alert.window().makeFirstResponder_(field)
        
        result = alert.runModal()
        NSApp.setActivationPolicy_(2)
        
        if with_input:
            return (result == 1000, field.stringValue().strip() if result == 1000 else "")
        return result == 1000
    
    def setup_menu(self):
        """设置菜单"""
        from .license_manager import license_manager
        from .permission import check_accessibility
        
        status, code, remaining = license_manager.get_status()
        menu = NSMenu.alloc().init()
        
        # 许可信息
        if status != "activated":
            title = f"试用期 (剩余 {remaining} 天)" if status == "trial" else "⚠ 试用期已结束"
            _add_menu_item(menu, self, title, enabled=False)
            _add_menu_item(menu, self, "激活 / 购买...", "showActivationInput:")
        else:
             _add_menu_item(menu, self, "✓ 已激活", enabled=False)

        menu.addItem_(NSMenuItem.separatorItem())
        
        # 功能区
        self.files_header = _add_menu_item(menu, self, "无待移动文件", enabled=False)
        _add_menu_item(menu, self, "清空列表", "clearCut:")
        
        # 文件智能操作子菜单
        self.smart_ops_menu = NSMenu.alloc().init()
        
        # 添加说明项（禁用状态，仅用于提示）
        # 当用户重复 ⌘+X 选择相同文件时，会自动显示此菜单
        _add_menu_item(self.smart_ops_menu, self, "💡 重复 ⌘+X 时自动显示", enabled=False)
        self.smart_ops_menu.addItem_(NSMenuItem.separatorItem())
        
        # 操作选项
        _add_menu_item(self.smart_ops_menu, self, "压缩文件", "smartCompress:")
        _add_menu_item(self.smart_ops_menu, self, "解压缩文件", "smartDecompress:")
        _add_menu_item(self.smart_ops_menu, self, "MD 转 HTML", "smartMdToHtml:")
        _add_menu_item(self.smart_ops_menu, self, "MD 转 PDF", "smartMdToPdf:")
        _add_menu_item(self.smart_ops_menu, self, "复制文件路径", "smartCopyPaths:")
        # _add_menu_item(self.smart_ops_menu, self, "自定义脚本", "smartCustomScript:")
        
        # 主菜单项：使用简洁的标题
        smart_ops_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("文件智能操作", None, "")
        smart_ops_item.setSubmenu_(self.smart_ops_menu)
        menu.addItem_(smart_ops_item)
        
        menu.addItem_(NSMenuItem.separatorItem())
        
        # 权限状态
        perm_ok = check_accessibility()
        if perm_ok:
            _add_menu_item(menu, self, "已获得系统权限", enabled=False)
        else:
            _add_menu_item(menu, self, "未获得系统权限 (点击授权)", "checkPermission:")
        
        self.autostart_item = _add_menu_item(menu, self, "开机自启", "toggleAutostart:")
        self.autostart_item.setState_(1 if self._is_autostart_enabled() else 0)
        
        menu.addItem_(NSMenuItem.separatorItem())
        _add_menu_item(menu, self, "关于", "showAbout:")
        _add_menu_item(menu, self, "退出", "quit:", "q")
        
        self.menu = menu
        self.status_item.setMenu_(menu)
    
    @objc.IBAction
    def showActivationInput_(self, sender):
        """激活/购买"""
        from .license_manager import license_manager
        from AppKit import NSAlert, NSApp
        
        NSApp.setActivationPolicy_(0)
        NSApp.activateIgnoringOtherApps_(True)
        
        while True:
            alert = NSAlert.alloc().init()
            alert.setMessageText_("CommondX 激活")
            alert.setInformativeText_(f"机器码: {license_manager.machine_code}\n\n请选择操作：")
            alert.addButtonWithTitle_("⭐ 购买激活码")
            alert.addButtonWithTitle_("输入激活码")
            alert.addButtonWithTitle_("复制机器码")
            alert.addButtonWithTitle_("关闭")
            
            resp = alert.runModal()
            
            if resp == 1000:  # 购买激活码
                self.openBuyPage_(sender)
                # 继续显示弹窗
            elif resp == 1001:  # 输入激活码
                ok, code = self._show_alert("🔑 输入激活码", "请输入激活码：", True)
                if ok and code:
                    if license_manager.activate(code):
                        self._show_alert("🎉 激活成功", "感谢支持！祝您使用愉快～")
                        self.setup_menu()
                        break  # 激活成功退出
                    else:
                        self._show_alert("❌ 激活失败", "激活码无效，请检查后重试")
                # 继续显示弹窗
            elif resp == 1002:  # 复制机器码
                copy_to_clipboard(license_manager.machine_code)
                self.send_notification("✅ 已复制", "机器码已复制到剪贴板")
                # 继续显示弹窗
            else:  # 关闭
                break
        
        NSApp.setActivationPolicy_(2)

    @objc.IBAction
    def copyMachineCode_(self, sender):
         copy_to_clipboard(sender)
         
    @objc.IBAction
    def openBuyPage_(self, sender):
        """打开购买"""
        from AppKit import NSWorkspace, NSURL
        from .license_manager import license_manager
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_("https://wj.qq.com/s2/25468218/6ee1/"))
        copy_to_clipboard(license_manager.machine_code)

    
    def show_activation_required(self):
        """提示需要激活"""
        from .license_manager import license_manager
        self.send_notification("⏰ 试用期已结束", f"机器码: {license_manager.machine_code}")
    
    @objc.IBAction
    def clearCut_(self, sender):
        self.cut_manager.clear()
        self.send_notification("🗑️ 已清空", "剪切列表已清空")
    
    def _get_selected_files(self):
        """
        获取选中的文件列表
        
        Returns:
            list: 文件路径列表，如果获取失败返回 None
        """
        print("[DEBUG] [StatusBar] 获取选中的文件...")
        files = self.cut_manager.get_finder_selection()
        
        if not files:
            if self.cached_files:
                files = self.cached_files
                print(f"[DEBUG] [StatusBar] 使用缓存的文件列表: {len(files)} 个文件")
            else:
                print("[DEBUG] [StatusBar] 未选中文件且无缓存")
                self.send_notification("⚠️ 未选中文件", "请在 Finder 中选中文件")
                return None
        else:
            self.cached_files = files
            print(f"[DEBUG] [StatusBar] 获取到文件列表: {len(files)} 个文件")
        
        return files
    
    def show_smart_operations_menu(self, files):
        """
        显示文件智能操作菜单
        
        在状态栏图标位置显示菜单，支持键盘上下键导航。
        
        Args:
            files: 文件路径列表
        """
        print("[DEBUG] [StatusBar] 显示文件智能操作菜单")
        if not files:
            print("[DEBUG] [StatusBar] 文件列表为空，不显示菜单")
            return
        
        # 更新缓存的文件列表
        self.cached_files = files
        print(f"[DEBUG] [StatusBar] 缓存文件列表: {len(files)} 个文件")
        
        # 获取状态栏按钮
        button = self.status_item.button()
        if button:
            # 临时替换菜单为智能操作菜单
            original_menu = self.status_item.menu()
            self.status_item.setMenu_(self.smart_ops_menu)
            
            # 获取按钮位置并显示菜单
            frame = button.frame()
            point = NSPoint(frame.origin.x, frame.origin.y - frame.size.height)
            # 使用 popUpMenuPositioningItem 显示菜单，支持键盘导航
            self.smart_ops_menu.popUpMenuPositioningItem_atLocation_inView_(
                None, point, button
            )
            
            # 恢复原菜单
            self.status_item.setMenu_(original_menu)
            print("[DEBUG] [StatusBar] ✓ 菜单已显示，支持键盘导航（上下键选择，回车确认，ESC 取消）")
        else:
            print("[ERROR] [StatusBar] 无法获取状态栏按钮，菜单显示失败")
    
    def _reset_last_selection(self):
        """重置 last_selection（允许下次重新开始）"""
        if self.cut_manager:
            print("[DEBUG] [StatusBar] 重置 last_selection")
            self.cut_manager.last_selection = None
    
    @objc.IBAction
    def smartCompress_(self, sender):
        """压缩文件"""
        print("[DEBUG] [StatusBar] 执行压缩文件操作")
        files = self._get_selected_files()
        if not files:
            return
        
        success, msg, output_path = compress_to_zip(files)
        if success:
            self.send_notification("✅ 压缩成功", msg)
            print(f"[DEBUG] [StatusBar] ✓ 压缩成功: {msg}")
        else:
            self.send_notification("❌ 压缩失败", msg)
            print(f"[DEBUG] [StatusBar] ✗ 压缩失败: {msg}")
        
        # 操作完成后，重置 last_selection（允许下次重新开始）
        self._reset_last_selection()
    
    @objc.IBAction
    def smartDecompress_(self, sender):
        """解压缩文件"""
        print("[DEBUG] [StatusBar] 执行解压缩文件操作")
        files = self._get_selected_files()
        if not files:
            return
        
        for archive_path in files:
            success, msg, output_dir = decompress_archive(archive_path)
            if success:
                self.send_notification("✅ 解压成功", msg)
                print(f"[DEBUG] [StatusBar] ✓ 解压成功: {msg}")
            else:
                self.send_notification("❌ 解压失败", msg)
                print(f"[DEBUG] [StatusBar] ✗ 解压失败: {msg}")
        
        # 操作完成后，重置 last_selection（允许下次重新开始）
        self._reset_last_selection()
    
    @objc.IBAction
    def smartMdToHtml_(self, sender):
        """MD 转 HTML"""
        print("[DEBUG] [StatusBar] 执行 MD 转 HTML 操作")
        files = self._get_selected_files()
        if not files:
            return
        
        from .utils import convert_md_to_html
        for md_path in files:
            if not md_path.lower().endswith(('.md', '.markdown')):
                self.send_notification("⚠️ 跳过", f"{Path(md_path).name} 不是 Markdown 文件")
                continue
            
            success, msg, output_path = convert_md_to_html(md_path)
            if success:
                self.send_notification("✅ 转换成功", msg)
                print(f"[DEBUG] [StatusBar] ✓ MD 转 HTML 成功: {msg}")
            else:
                self.send_notification("❌ 转换失败", msg)
                print(f"[DEBUG] [StatusBar] ✗ MD 转 HTML 失败: {msg}")
        
        # 操作完成后，重置 last_selection（允许下次重新开始）
        self._reset_last_selection()
    
    @objc.IBAction
    def smartMdToPdf_(self, sender):
        """MD 转 PDF"""
        print("[DEBUG] [StatusBar] 执行 MD 转 PDF 操作")
        files = self._get_selected_files()
        if not files:
            return
        
        from .utils import convert_md_to_pdf
        for md_path in files:
            if not md_path.lower().endswith(('.md', '.markdown')):
                self.send_notification("⚠️ 跳过", f"{Path(md_path).name} 不是 Markdown 文件")
                continue
            
            success, msg, output_path = convert_md_to_pdf(md_path)
            if success:
                self.send_notification("✅ 转换成功", msg)
                print(f"[DEBUG] [StatusBar] ✓ MD 转 PDF 成功: {msg}")
            else:
                self.send_notification("❌ 转换失败", msg)
                print(f"[DEBUG] [StatusBar] ✗ MD 转 PDF 失败: {msg}")
        
        # 操作完成后，重置 last_selection（允许下次重新开始）
        self._reset_last_selection()
    
    @objc.IBAction
    def smartCopyPaths_(self, sender):
        """复制文件路径"""
        print("[DEBUG] [StatusBar] 执行复制文件路径操作")
        files = self._get_selected_files()
        if not files:
            return
        
        paths_text = "\n".join(files)
        copy_to_clipboard(paths_text)
        count = len(files)
        msg = f"已复制 {count} 个文件路径" if count > 1 else "已复制文件路径"
        self.send_notification("✅ 已复制路径", msg)
        print(f"[DEBUG] [StatusBar] ✓ 复制路径完成: {count} 个文件")
        
        # 操作完成后，重置 last_selection（允许下次重新开始）
        self._reset_last_selection()
    
    @objc.IBAction
    def checkPermission_(self, sender):
        """检查权限"""
        from .permission import check_accessibility, open_accessibility_settings
        delegate = NSApplication.sharedApplication().delegate()
        
        if delegate and hasattr(delegate, 'retry_permission_check'):
            ok = delegate.retry_permission_check()
        else:
            ok = check_accessibility()
            if not ok:
                open_accessibility_settings()
        
        if ok:
            self.send_notification("✅ 权限检查", "已获得辅助功能权限")
            self.setup_menu()  # 刷新菜单隐藏权限项
    
    @objc.IBAction
    def openAccessibilitySettings_(self, sender):
        from .permission import open_accessibility_settings
        open_accessibility_settings()
    
    @objc.IBAction
    def toggleAutostart_(self, sender):
        from .launch_agent import toggle_autostart
        enabled = toggle_autostart()
        self.autostart_item.setState_(1 if enabled else 0)
        self.send_notification("⚙️ 开机自启", "✅ 已开启" if enabled else "❌ 已关闭")
    
    def _is_autostart_enabled(self):
        try:
            from .launch_agent import is_autostart_enabled
            return is_autostart_enabled()
        except:
            return False
    
    @objc.IBAction
    def showAbout_(self, sender):
        from AppKit import NSApp
        NSApp.activateIgnoringOtherApps_(True)
        self._show_alert("✂️ CommondX", "Mac 文件剪切移动工具\n\n• ⌘+X 剪切\n• ⌘+V 移动\n\n版本: 1.0.0\n作者: Cedar 🐱\n微信: z858998813")
    
    @objc.IBAction
    def quit_(self, sender):
        NSApplication.sharedApplication().terminate_(None)
    
    def send_notification(self, title, msg):
        """发送通知"""
        center = NSUserNotificationCenter.defaultUserNotificationCenter()
        if center:
            n = NSUserNotification.alloc().init()
            n.setTitle_(title)
            n.setInformativeText_(msg)
            center.deliverNotification_(n)
        else:
            print(f"[Notification] {title}: {msg}")
