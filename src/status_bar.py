#!/usr/bin/env python3
"""状态栏图标"""

import objc
from Foundation import NSObject, NSTimer
from AppKit import (
    NSStatusBar, NSMenu, NSMenuItem, NSImage, NSColor, NSApplication,
    NSSize, NSRect, NSPoint, NSBezierPath, NSAffineTransform,
    NSUserNotificationCenter, NSUserNotification
)
from cedar.utils import print


class StatusBarIcon(NSObject):
    """状态栏图标"""
    
    def initWithCutManager_(self, cut_manager):
        self = objc.super(StatusBarIcon, self).init()
        if self:
            self.cut_manager = cut_manager
            self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
            self.animation_timer = None
            self.animation_frame = 0
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
    
    def _item(self, menu, title, action=None, key="", enabled=True):
        """创建菜单项"""
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
        if action:
            item.setTarget_(self)
        item.setEnabled_(enabled)
        menu.addItem_(item)
        return item
    
    def setup_menu(self):
        """设置菜单"""
        from .license_manager import license_manager
        from .permission import check_accessibility
        
        status, code, remaining = license_manager.get_status()
        menu = NSMenu.alloc().init()
        
        # 许可状态
        if status == "activated":
            self._item(menu, "✓ 已激活", enabled=False)
        else:
            title = f"试用期 (剩余 {remaining} 天)" if status == "trial" else "⚠ 试用期已结束"
            self._item(menu, title, enabled=False)
            self._item(menu, f"机器码: {code}", "copyMachineCode:")
            self._item(menu, "输入激活码...", "showActivationInput:")
            self._item(menu, "购买激活码 (¥2.00)", "openBuyPage:")
        
        menu.addItem_(NSMenuItem.separatorItem())
        self.files_header = self._item(menu, "无待移动文件", enabled=False)
        menu.addItem_(NSMenuItem.separatorItem())
        self._item(menu, "清空剪切列表", "clearCut:")
        menu.addItem_(NSMenuItem.separatorItem())
        
        # 权限
        perm_ok = check_accessibility()
        self.permission_item = self._item(menu, "✓ 已授权" if perm_ok else "⚠ 未授权", enabled=False)
        self._item(menu, "检查权限", "checkPermission:")
        self._item(menu, "打开辅助功能设置", "openAccessibilitySettings:")
        menu.addItem_(NSMenuItem.separatorItem())
        
        # 自启
        self.autostart_item = self._item(menu, "开机自启", "toggleAutostart:")
        self.autostart_item.setState_(1 if self._is_autostart_enabled() else 0)
        menu.addItem_(NSMenuItem.separatorItem())
        
        self._item(menu, "关于 CommondX", "showAbout:")
        self._item(menu, "退出", "quit:", "q")
        
        self.menu = menu
        self.status_item.setMenu_(menu)
    
    def _copy_to_clipboard(self, text):
        """复制到剪贴板"""
        from AppKit import NSPasteboard, NSStringPboardType
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setString_forType_(text, NSStringPboardType)
    
    def _show_alert(self, title, msg, with_input=False):
        """显示弹窗"""
        from AppKit import NSAlert, NSTextField, NSApp, NSRunningApplication, NSApplicationActivateIgnoringOtherApps
        
        policy = NSApp.activationPolicy()
        NSApp.setActivationPolicy_(0)
        NSApp.activateIgnoringOtherApps_(True)
        NSRunningApplication.currentApplication().activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(msg)
        alert.addButtonWithTitle_("确定" if not with_input else "激活")
        if with_input:
            alert.addButtonWithTitle_("取消")
            field = NSTextField.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(250, 24)))
            field.setPlaceholderString_("XXXX-XXXX-XXXX-XXXX")
            field.setEditable_(True)
            field.setSelectable_(True)
            field.setBezeled_(True)
            field.setDrawsBackground_(True)
            alert.setAccessoryView_(field)
            alert.window().makeKeyAndOrderFront_(None)
            alert.window().makeFirstResponder_(field)
        
        result = alert.runModal()
        NSApp.setActivationPolicy_(policy)
        
        if with_input:
            return (result == 1000, field.stringValue().strip() if result == 1000 else "")
        return result == 1000
    
    @objc.IBAction
    def copyMachineCode_(self, sender):
        """复制机器码"""
        from .license_manager import license_manager
        self._copy_to_clipboard(license_manager.machine_code)
        self.send_notification("已复制", f"机器码 {license_manager.machine_code}")
    
    @objc.IBAction
    def showActivationInput_(self, sender):
        """激活码输入"""
        from .license_manager import license_manager
        ok, code = self._show_alert("输入激活码", f"机器码: {license_manager.machine_code}\n\n请输入激活码：", True)
        if not ok:
            return
        if license_manager.activate(code):
            self._show_alert("激活成功", "感谢支持！请重启应用。")
            self.setup_menu()
        else:
            self._show_alert("激活失败", "激活码无效，请检查。")
    
    @objc.IBAction
    def openBuyPage_(self, sender):
        """打开购买页面"""
        from AppKit import NSWorkspace, NSURL
        from .license_manager import license_manager
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_("https://wj.qq.com/s2/25468218/6ee1/"))
        self._copy_to_clipboard(license_manager.machine_code)
        self.send_notification("已打开购买页面", f"机器码已复制: {license_manager.machine_code}")
    
    def show_activation_required(self):
        """提示需要激活"""
        from .license_manager import license_manager
        self.send_notification("试用期已结束", f"机器码: {license_manager.machine_code}")
    
    @objc.IBAction
    def clearCut_(self, sender):
        self.cut_manager.clear()
        self.send_notification("已清空", "剪切列表已清空")
    
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
        
        self.permission_item.setTitle_("✓ 已授权" if ok else "⚠ 未授权")
        if ok:
            self.send_notification("权限检查", "已获得辅助功能权限")
    
    @objc.IBAction
    def openAccessibilitySettings_(self, sender):
        from .permission import open_accessibility_settings
        open_accessibility_settings()
    
    @objc.IBAction
    def toggleAutostart_(self, sender):
        from .launch_agent import toggle_autostart
        enabled = toggle_autostart()
        self.autostart_item.setState_(1 if enabled else 0)
        self.send_notification("开机自启", "已开启" if enabled else "已关闭")
    
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
        self._show_alert("CommondX", "Mac 文件剪切移动工具\n\n• Cmd+X 剪切\n• Cmd+V 移动\n\n版本: 1.0.0\n作者: Cedar")
    
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
