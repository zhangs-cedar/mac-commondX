#!/usr/bin/env python3
"""状态栏图标模块"""

import objc
from Foundation import NSObject
from AppKit import (
    NSStatusBar, NSMenu, NSMenuItem, NSImage, NSColor,
    NSSize, NSRect, NSPoint, NSBezierPath, NSFont,
    NSApplication, NSUserNotificationCenter, NSUserNotification
)


class StatusBarIcon(NSObject):
    """状态栏图标"""
    
    def initWithCutManager_(self, cut_manager):
        self = objc.super(StatusBarIcon, self).init()
        if self:
            self.cut_manager = cut_manager
            self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)  # 可变长度
            self.setup_icon()
            self.setup_menu()
            
            # 注册状态变化回调
            cut_manager.on_state_change = self.on_cut_state_change
        return self
    
    def setup_icon(self):
        """设置图标"""
        self.update_icon(0)
    
    def update_icon(self, count):
        """更新图标显示"""
        size = NSSize(22, 22)
        image = NSImage.alloc().initWithSize_(size)
        image.lockFocus()
        
        # 绘制剪刀图标
        NSColor.labelColor().setStroke()
        
        # 简化的剪刀形状
        path = NSBezierPath.bezierPath()
        path.setLineWidth_(1.5)
        
        # 左刀片
        path.moveToPoint_(NSPoint(4, 18))
        path.lineToPoint_(NSPoint(11, 11))
        path.lineToPoint_(NSPoint(4, 4))
        
        # 右刀片
        path.moveToPoint_(NSPoint(18, 18))
        path.lineToPoint_(NSPoint(11, 11))
        path.lineToPoint_(NSPoint(18, 4))
        
        path.stroke()
        
        # 如果有剪切文件，显示数量徽章
        if count > 0:
            # 红色圆圈背景
            badge_rect = NSRect(NSPoint(12, 0), NSSize(10, 10))
            NSColor.systemRedColor().setFill()
            NSBezierPath.bezierPathWithOvalInRect_(badge_rect).fill()
            
            # 白色数字
            NSColor.whiteColor().setFill()
            font = NSFont.boldSystemFontOfSize_(7)
            text = str(count) if count < 10 else "+"
            
            # 绘制数字（简化处理，居中显示）
            attrs = {
                "NSFont": font,
                "NSColor": NSColor.whiteColor()
            }
        
        image.unlockFocus()
        image.setTemplate_(count == 0)  # 无文件时使用模板模式适应深色/浅色主题
        
        self.status_item.setImage_(image)
        
        # 更新标题显示数量
        if count > 0:
            self.status_item.setTitle_(f" {count}")
        else:
            self.status_item.setTitle_("")
    
    def setup_menu(self):
        """设置右键菜单"""
        menu = NSMenu.alloc().init()
        
        # 剪切文件列表标题
        self.files_header = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "无待移动文件", None, ""
        )
        self.files_header.setEnabled_(False)
        menu.addItem_(self.files_header)
        
        menu.addItem_(NSMenuItem.separatorItem())
        
        # 清空剪切
        clear_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "清空剪切列表", "clearCut:", "")
        clear_item.setTarget_(self)
        menu.addItem_(clear_item)
        
        menu.addItem_(NSMenuItem.separatorItem())
        
        # 开机自启
        self.autostart_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "开机自启", "toggleAutostart:", "")
        self.autostart_item.setTarget_(self)
        self.autostart_item.setState_(1 if self._is_autostart_enabled() else 0)
        menu.addItem_(self.autostart_item)
        
        menu.addItem_(NSMenuItem.separatorItem())
        
        # 关于
        about_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "关于 CommondX", "showAbout:", "")
        about_item.setTarget_(self)
        menu.addItem_(about_item)
        
        # 退出
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "退出", "quit:", "q")
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)
        
        self.menu = menu
        self.status_item.setMenu_(menu)
    
    def on_cut_state_change(self, files):
        """剪切状态变化回调"""
        count = len(files)
        self.update_icon(count)
        
        if count > 0:
            # 更新菜单标题
            if count == 1:
                self.files_header.setTitle_(f"待移动: {files[0]}")
            else:
                self.files_header.setTitle_(f"待移动 {count} 个文件")
        else:
            self.files_header.setTitle_("无待移动文件")
    
    @objc.IBAction
    def clearCut_(self, sender):
        """清空剪切列表"""
        self.cut_manager.clear()
        self.send_notification("已清空", "剪切列表已清空")
    
    @objc.IBAction
    def toggleAutostart_(self, sender):
        """切换开机自启"""
        from .launch_agent import toggle_autostart
        enabled = toggle_autostart()
        self.autostart_item.setState_(1 if enabled else 0)
        status = "已开启" if enabled else "已关闭"
        self.send_notification("开机自启", status)
    
    def _is_autostart_enabled(self):
        """检查是否已开启开机自启"""
        try:
            from .launch_agent import is_autostart_enabled
            return is_autostart_enabled()
        except:
            return False
    
    @objc.IBAction
    def showAbout_(self, sender):
        """显示关于"""
        self.send_notification(
            "CommondX",
            "Mac 文件剪切移动工具\n使用 Cmd+X 剪切，Cmd+V 移动"
        )
    
    @objc.IBAction
    def quit_(self, sender):
        """退出应用"""
        NSApplication.sharedApplication().terminate_(None)
    
    def send_notification(self, title, message):
        """发送系统通知"""
        center = NSUserNotificationCenter.defaultUserNotificationCenter()
        if center:
            notification = NSUserNotification.alloc().init()
            notification.setTitle_(title)
            notification.setInformativeText_(message)
            center.deliverNotification_(notification)
        else:
            print(f"[Notification] {title}: {message}")
