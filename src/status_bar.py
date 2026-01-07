#!/usr/bin/env python3
"""状态栏图标模块"""

import objc
from Foundation import NSObject, NSTimer
from AppKit import (
    NSStatusBar, NSMenu, NSMenuItem, NSImage, NSColor,
    NSSize, NSRect, NSPoint, NSBezierPath, NSFont,
    NSApplication, NSUserNotificationCenter, NSUserNotification,
    NSAffineTransform
)


class StatusBarIcon(NSObject):
    """状态栏图标"""
    
    def initWithCutManager_(self, cut_manager):
        self = objc.super(StatusBarIcon, self).init()
        if self:
            self.cut_manager = cut_manager
            self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)  # 可变长度
            self.animation_timer = None
            self.animation_frame = 0
            self.setup_icon()
            self.setup_menu()
            
            # 注册状态变化回调
            cut_manager.on_state_change = self.on_cut_state_change
        return self
    
    def setup_icon(self):
        """设置图标"""
        self.update_icon(0)
    
    def on_cut_state_change(self, files):
        """剪切状态变化回调"""
        count = len(files)
        
        # 触发剪切动画（如果文件数增加）
        if count > 0:
            self.start_cut_animation(count)
        else:
            self.update_icon(0)
            
        if count > 0:
            # 更新菜单标题
            if count == 1:
                self.files_header.setTitle_(f"待移动: {files[0]}")
            else:
                self.files_header.setTitle_(f"待移动 {count} 个文件")
        else:
            self.files_header.setTitle_("无待移动文件")
            
    def start_cut_animation(self, final_count):
        """播放剪切动作动画"""
        if self.animation_timer:
            self.animation_timer.invalidate()
            self.animation_timer = None
            
        self.animation_frame = 0
        self.target_count = final_count
        
        # 创建定时器，每 0.05 秒更新一次，播放 6 帧
        self.animation_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.05, self, "animateIcon:", None, True
        )
        
    def animateIcon_(self, timer):
        """动画回调"""
        self.animation_frame += 1
        
        # 简单的“剪切”动作：张开 -> 闭合
        # 0: 初始, 1: 张开, 2: 张大, 3: 闭合中, 4: 闭合, 5: 恢复
        angle_map = [0, 15, 30, 15, 0, 0]
        
        if self.animation_frame < len(angle_map):
            self.update_icon(self.target_count, angle=angle_map[self.animation_frame])
        else:
            timer.invalidate()
            self.animation_timer = None
            self.update_icon(self.target_count)

    def update_icon(self, count, angle=0):
        """更新图标显示"""
        size = NSSize(22, 22)
        image = NSImage.alloc().initWithSize_(size)
        image.lockFocus()
        
        # 绘制剪刀图标 (SF Symbols 风格 - 缩小居中版)
        NSColor.labelColor().setStroke()
        
        # 整体缩放系数 (0.8 = 缩小到 80%)
        scale = 0.8
        
        # 基础变换：缩放 + 居中
        base_transform = NSAffineTransform.transform()
        offset_x = (22 - (22 * scale)) / 2
        offset_y = (22 - (22 * scale)) / 2
        base_transform.translateXBy_yBy_(offset_x, offset_y)
        base_transform.scaleBy_(scale)
        base_transform.concat()
        
        # 绘制左部分（带旋转）
        left_path = NSBezierPath.bezierPath()
        left_path.setLineWidth_(1.5)
        left_path.setLineJoinStyle_(1)
        left_path.setLineCapStyle_(1)
        
        left_path.appendBezierPathWithOvalInRect_(NSRect(NSPoint(4, 3), NSSize(5, 5))) # 左手柄
        left_path.moveToPoint_(NSPoint(6.5, 8))
        left_path.lineToPoint_(NSPoint(16, 19)) # 左刀刃
        
        if angle > 0:
            # 绕中心点 (11, 11) 逆时针旋转
            left_transform = NSAffineTransform.transform()
            left_transform.translateXBy_yBy_(11, 11)
            left_transform.rotateByDegrees_(angle)
            left_transform.translateXBy_yBy_(-11, -11)
            left_path.transformUsingAffineTransform_(left_transform)
            
        left_path.stroke()
        
        # 绘制右部分（带旋转）
        right_path = NSBezierPath.bezierPath()
        right_path.setLineWidth_(1.5)
        right_path.setLineJoinStyle_(1)
        right_path.setLineCapStyle_(1)
        
        right_path.appendBezierPathWithOvalInRect_(NSRect(NSPoint(13, 3), NSSize(5, 5))) # 右手柄
        right_path.moveToPoint_(NSPoint(15.5, 8))
        right_path.lineToPoint_(NSPoint(6, 19)) # 右刀刃
        
        if angle > 0:
            # 绕中心点 (11, 11) 顺时针旋转
            right_transform = NSAffineTransform.transform()
            right_transform.translateXBy_yBy_(11, 11)
            right_transform.rotateByDegrees_(-angle)
            right_transform.translateXBy_yBy_(-11, -11)
            right_path.transformUsingAffineTransform_(right_transform)
            
        right_path.stroke()
        
        # 如果有剪切文件，显示数量徽章
        if count > 0:
            # 红色圆圈背景
            badge_rect = NSRect(NSPoint(12, 0), NSSize(10, 10))
            NSColor.systemRedColor().setFill()
            NSBezierPath.bezierPathWithOvalInRect_(badge_rect).fill()
            
            # 白色数字
            # NSColor.whiteColor().setFill()
            # font = NSFont.boldSystemFontOfSize_(7)
            
            # 绘制数字（简化处理，居中显示）
            # ...
        
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
