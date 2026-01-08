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
from cedar.utils import print


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
        from .license_manager import license_manager
        status, machine_code, remaining = license_manager.get_status()
        
        menu = NSMenu.alloc().init()
        
        # 激活状态
        if status == "activated":
            status_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "✓ 已激活", None, ""
            )
            status_item.setEnabled_(False)
            menu.addItem_(status_item)
        elif status == "trial":
            # 试用期
            status_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"试用期 (剩余 {remaining} 天)", None, ""
            )
            status_item.setEnabled_(False)
            menu.addItem_(status_item)
            
            # 机器码
            machine_code_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"机器码: {machine_code}", "copyMachineCode:", ""
            )
            machine_code_item.setTarget_(self)
            menu.addItem_(machine_code_item)
            
            # 输入激活码
            activate_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "输入激活码...", "showActivationInput:", ""
            )
            activate_item.setTarget_(self)
            menu.addItem_(activate_item)
            
            # 购买
            buy_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "购买激活码 (¥2.00)", "openBuyPage:", ""
            )
            buy_item.setTarget_(self)
            menu.addItem_(buy_item)
        else:
            # 试用期已过
            status_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "⚠ 试用期已结束", None, ""
            )
            status_item.setEnabled_(False)
            menu.addItem_(status_item)
            
            # 机器码
            machine_code_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"机器码: {machine_code}", "copyMachineCode:", ""
            )
            machine_code_item.setTarget_(self)
            menu.addItem_(machine_code_item)
            
            # 输入激活码
            activate_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "输入激活码...", "showActivationInput:", ""
            )
            activate_item.setTarget_(self)
            menu.addItem_(activate_item)
            
            # 购买
            buy_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "购买激活码 (¥2.00)", "openBuyPage:", ""
            )
            buy_item.setTarget_(self)
            menu.addItem_(buy_item)
        
        menu.addItem_(NSMenuItem.separatorItem())
        
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
    def copyMachineCode_(self, sender):
        """复制机器码到剪贴板"""
        from AppKit import NSPasteboard, NSStringPboardType
        from .license_manager import license_manager
        
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setString_forType_(license_manager.machine_code, NSStringPboardType)
        self.send_notification("已复制", f"机器码 {license_manager.machine_code} 已复制到剪贴板")
    
    @objc.IBAction
    def showActivationInput_(self, sender):
        """显示激活码输入框"""
        from AppKit import NSAlert, NSTextField, NSApp
        from .license_manager import license_manager
        
        alert = NSAlert.alloc().init()
        alert.setMessageText_("输入激活码")
        alert.setInformativeText_(f"您的机器码: {license_manager.machine_code}\n\n请输入购买的激活码：")
        alert.addButtonWithTitle_("激活")
        alert.addButtonWithTitle_("取消")
        
        input_field = NSTextField.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(250, 24)))
        input_field.setPlaceholderString_("XXXX-XXXX-XXXX-XXXX")
        input_field.setEditable_(True)
        input_field.setSelectable_(True)
        input_field.setBezeled_(True)
        input_field.setDrawsBackground_(True)
        alert.setAccessoryView_(input_field)
        
        # 激活窗口并聚焦输入框
        NSApp.activateIgnoringOtherApps_(True)
        alert.window().makeFirstResponder_(input_field)
        
        response = alert.runModal()
        
        if response == 1000:  # 点击了激活
            code = input_field.stringValue().strip()
            if license_manager.activate(code):
                self.send_notification("激活成功", "感谢您的支持！请重启应用。")
                self.setup_menu()  # 刷新菜单
            else:
                self.send_notification("激活失败", "激活码无效，请检查是否输入正确")
    
    @objc.IBAction
    def openBuyPage_(self, sender):
        """打开购买页面"""
        from AppKit import NSWorkspace, NSURL
        from .license_manager import license_manager
        
        # 腾讯问卷购买页面
        buy_url = "https://wj.qq.com/s2/25468218/6ee1/"
        url = NSURL.URLWithString_(buy_url)
        NSWorkspace.sharedWorkspace().openURL_(url)
        
        # 复制机器码到剪贴板，方便用户填写
        from AppKit import NSPasteboard, NSStringPboardType
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setString_forType_(license_manager.machine_code, NSStringPboardType)
        
        self.send_notification("已打开购买页面", f"机器码已复制: {license_manager.machine_code}")
    
    def show_activation_required(self):
        """显示需要激活的提示"""
        from .license_manager import license_manager
        self.send_notification("试用期已结束", f"机器码: {license_manager.machine_code}\n请购买激活码继续使用")
    
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
        from AppKit import NSAlert, NSApp
        
        alert = NSAlert.alloc().init()
        alert.setMessageText_("CommondX")
        alert.setInformativeText_(
            "Mac 文件剪切移动工具\n\n"
            "使用方法:\n"
            "• Cmd+X 剪切文件/文件夹\n"
            "• Cmd+V 移动到目标位置\n"
            "• Cmd+Z 撤销移动\n\n"
            "版本: 1.0.0\n"
            "作者: Cedar"
        )
        alert.addButtonWithTitle_("确定")
        
        NSApp.activateIgnoringOtherApps_(True)
        alert.runModal()
    
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
