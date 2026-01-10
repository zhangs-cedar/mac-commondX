#!/usr/bin/env python3
"""状态栏图标"""

import objc
import yaml
from pathlib import Path
from Foundation import NSObject, NSTimer
from AppKit import (
    NSStatusBar, NSMenu, NSMenuItem, NSImage, NSColor, NSApplication,
    NSSize, NSRect, NSPoint, NSBezierPath, NSAffineTransform,
    NSUserNotificationCenter, NSUserNotification, NSButton, NSStackView, NSAlert, NSApp
)
from cedar.utils import print

from .archive_manager import compress_to_zip, decompress_archive
from .utils import copy_to_clipboard

# 配置文件路径
CONFIG_PATH = Path.home() / "Library/Application Support/CommondX/user.yaml"

# 所有可用的智能操作选项
SMART_OPS_OPTIONS = {
    "compress": {"title": "压缩文件", "action": "smartCompress:"},
    "decompress": {"title": "解压缩文件", "action": "smartDecompress:"},
    "md_to_html": {"title": "MD 转 HTML", "action": "smartMdToHtml:"},
    "md_to_pdf": {"title": "MD 转 PDF", "action": "smartMdToPdf:"},
    "copy_paths": {"title": "复制文件路径", "action": "smartCopyPaths:"},
}


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
            self.enabled_ops = self._load_smart_ops_config()  # 加载配置
            self.update_icon(0)
            self.setup_menu()
            cut_manager.on_state_change = self.on_cut_state_change
        return self
    
    def _load_smart_ops_config(self):
        """
        加载智能操作配置
        
        按照流程图设计：配置选项控制操作选项的显示
        """
        print("[DEBUG] [StatusBar] 加载智能操作配置...")
        try:
            if CONFIG_PATH.exists():
                data = yaml.safe_load(CONFIG_PATH.read_text()) or {}
                enabled = data.get('smart_ops', {})
                print(f"[DEBUG] [StatusBar] 从配置文件读取: {enabled}")
                
                # 如果配置为空，默认启用所有选项
                if not enabled:
                    enabled = {key: True for key in SMART_OPS_OPTIONS.keys()}
                    self._save_smart_ops_config(enabled)
                    print(f"[DEBUG] [StatusBar] 配置为空，使用默认配置（全部启用）")
                
                # 验证配置完整性（确保所有选项都有配置）
                for key in SMART_OPS_OPTIONS.keys():
                    if key not in enabled:
                        enabled[key] = True
                        print(f"[DEBUG] [StatusBar] 补充缺失配置项: {key} = True")
                
                print(f"[DEBUG] [StatusBar] ✓ 配置加载成功: {enabled}")
                return enabled
        except Exception as e:
            print(f"[ERROR] [StatusBar] 加载配置失败: {e}")
        
        # 默认启用所有选项
        default = {key: True for key in SMART_OPS_OPTIONS.keys()}
        print(f"[DEBUG] [StatusBar] 使用默认配置: {default}")
        return default
    
    def _save_smart_ops_config(self, enabled):
        """
        保存智能操作配置
        
        按照流程图设计：配置保存后立即生效
        """
        print(f"[DEBUG] [StatusBar] 保存智能操作配置: {enabled}")
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            print(f"[DEBUG] [StatusBar] 配置文件路径: {CONFIG_PATH}")
            
            # 读取现有配置（保留其他配置项）
            data = {}
            if CONFIG_PATH.exists():
                data = yaml.safe_load(CONFIG_PATH.read_text()) or {}
                print(f"[DEBUG] [StatusBar] 读取现有配置: {list(data.keys())}")
            
            # 更新智能操作配置
            data['smart_ops'] = enabled
            CONFIG_PATH.write_text(yaml.dump(data))
            print(f"[DEBUG] [StatusBar] ✓ 配置保存成功，共 {len(enabled)} 个选项")
        except Exception as e:
            print(f"[ERROR] [StatusBar] 保存配置失败: {e}")
    
    def on_cut_state_change(self, files):
        """
        剪切状态变化
        
        按照流程图设计：更新菜单显示和图标状态
        """
        count = len(files)
        print(f"[DEBUG] [StatusBar] 剪切状态变化: {count} 个文件")
        
        if count > 0:
            self.start_cut_animation(count)
            title = files[0] if count == 1 else f"待移动 {count} 个文件"
            self.files_header.setTitle_(title)
            print(f"[DEBUG] [StatusBar] 更新菜单标题: {title}")
        else:
            self.update_icon(0)
            self.files_header.setTitle_("无待移动文件")
            print("[DEBUG] [StatusBar] 无待移动文件，重置图标和标题")
            
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
        """
        设置菜单
        
        按照流程图设计构建完整的菜单结构
        """
        print("[DEBUG] [StatusBar] 开始设置菜单...")
        from .license_manager import license_manager
        from .permission import check_accessibility
        
        status, code, remaining = license_manager.get_status()
        menu = NSMenu.alloc().init()
        
        # 【步骤 1】许可信息
        print(f"[DEBUG] [StatusBar] 添加许可信息区域 - status={status}")
        if status != "activated":
            title = f"试用期 (剩余 {remaining} 天)" if status == "trial" else "⚠ 试用期已结束"
            _add_menu_item(menu, self, title, enabled=False)
            _add_menu_item(menu, self, "激活 / 购买...", "showActivationInput:")
        else:
             _add_menu_item(menu, self, "✓ 已激活", enabled=False)

        menu.addItem_(NSMenuItem.separatorItem())
        
        # 【步骤 2】功能区
        print("[DEBUG] [StatusBar] 添加功能区...")
        self.files_header = _add_menu_item(menu, self, "无待移动文件", enabled=False)
        _add_menu_item(menu, self, "清空列表", "clearCut:")
        
        # 【步骤 3】文件智能操作子菜单（根据配置动态构建）
        print("[DEBUG] [StatusBar] 构建文件智能操作子菜单...")
        self.smart_ops_menu = self._build_smart_ops_menu()
        
        # 主菜单项：使用简洁的标题
        smart_ops_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("文件智能操作", None, "")
        smart_ops_item.setSubmenu_(self.smart_ops_menu)
        menu.addItem_(smart_ops_item)
        print("[DEBUG] [StatusBar] ✓ 文件智能操作子菜单已添加")
        
        # 【步骤 4】配置选项子菜单（按照流程图：与文件智能操作平级）
        print("[DEBUG] [StatusBar] 构建配置选项子菜单...")
        self.config_menu = self._build_config_menu()
        
        # 主菜单项：使用简洁的标题
        config_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("配置选项", None, "")
        config_item.setSubmenu_(self.config_menu)
        menu.addItem_(config_item)
        print("[DEBUG] [StatusBar] ✓ 配置选项子菜单已添加")
        
        menu.addItem_(NSMenuItem.separatorItem())
        
        # 【步骤 5】系统设置
        print("[DEBUG] [StatusBar] 添加系统设置区域...")
        perm_ok = check_accessibility()
        if perm_ok:
            _add_menu_item(menu, self, "已获得系统权限", enabled=False)
        else:
            _add_menu_item(menu, self, "未获得系统权限 (点击授权)", "checkPermission:")
        
        self.autostart_item = _add_menu_item(menu, self, "开机自启", "toggleAutostart:")
        self.autostart_item.setState_(1 if self._is_autostart_enabled() else 0)
        print(f"[DEBUG] [StatusBar] 开机自启状态: {self.autostart_item.state() == 1}")
        
        menu.addItem_(NSMenuItem.separatorItem())
        
        # 【步骤 6】关于和退出
        print("[DEBUG] [StatusBar] 添加关于和退出...")
        _add_menu_item(menu, self, "关于", "showAbout:")
        _add_menu_item(menu, self, "退出", "quit:", "q")
        
        self.menu = menu
        self.status_item.setMenu_(menu)
        print("[DEBUG] [StatusBar] ✓ 菜单设置完成")
    
    def _build_smart_ops_menu(self):
        """
        根据配置构建智能操作菜单
        
        按照流程图设计：
        1. 说明项
        2. 操作选项（根据配置显示）
        """
        print("[DEBUG] [StatusBar] 构建智能操作菜单...")
        menu = NSMenu.alloc().init()
        
        # 【步骤 1】添加说明项（禁用状态，仅用于提示）
        _add_menu_item(menu, self, "💡 重复 ⌘+X 时自动显示", enabled=False)
        menu.addItem_(NSMenuItem.separatorItem())
        print("[DEBUG] [StatusBar] 已添加说明项")
        
        # 【步骤 2】根据配置添加操作选项（按照流程图：操作选项根据配置显示）
        enabled_count = 0
        for key, option in SMART_OPS_OPTIONS.items():
            if self.enabled_ops.get(key, True):
                _add_menu_item(menu, self, option["title"], option["action"])
                enabled_count += 1
                print(f"[DEBUG] [StatusBar] 已添加操作选项: {option['title']}")
        print(f"[DEBUG] [StatusBar] 操作选项构建完成，共 {enabled_count} 个")
        
        print(f"[DEBUG] [StatusBar] ✓ 智能操作菜单构建完成")
        return menu
    
    def _build_config_menu(self):
        """
        构建配置选项子菜单
        
        按照流程图设计：
        1. 配置标题（禁用）
        2. 配置选项（复选框，可点击）
        """
        print("[DEBUG] [StatusBar] 构建配置选项菜单...")
        menu = NSMenu.alloc().init()
        
        # 【步骤 1】添加配置标题（禁用状态）
        _add_menu_item(menu, self, "⚙️ 配置显示项", enabled=False)
        print("[DEBUG] [StatusBar] 已添加配置标题")
        
        # 【步骤 2】为每个选项添加复选框菜单项
        for key, option in SMART_OPS_OPTIONS.items():
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                option['title'], "toggleSmartOp:", ""
            )
            item.setTarget_(self)
            item.setRepresentedObject_(key)
            # 设置状态：1=选中（NSOnState），0=未选中（NSOffState）
            # NSMenuItem 会自动显示复选框，无需在标题中添加 ☑
            is_enabled = self.enabled_ops.get(key, True)
            item.setState_(1 if is_enabled else 0)
            menu.addItem_(item)
            print(f"[DEBUG] [StatusBar] 已添加配置项: {option['title']} (状态={'启用' if is_enabled else '禁用'})")
        
        print(f"[DEBUG] [StatusBar] ✓ 配置选项菜单构建完成")
        return menu
    
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
    
    @objc.IBAction
    def toggleSmartOp_(self, sender):
        """
        切换智能操作选项的显示状态
        
        按照流程图设计：配置选项通过复选框控制操作选项的显示
        """
        # 从 representedObject 获取 key
        key = sender.representedObject()
        if not key:
            print(f"[ERROR] [StatusBar] 无法获取选项 key")
            return
        
        print(f"[DEBUG] [StatusBar] 切换选项状态: {key}")
        
        # 【步骤 1】切换状态
        current_state = self.enabled_ops.get(key, True)
        new_state = not current_state
        self.enabled_ops[key] = new_state
        print(f"[DEBUG] [StatusBar] 状态切换: {current_state} -> {new_state}")
        
        # 【步骤 2】保存配置
        self._save_smart_ops_config(self.enabled_ops)
        
        # 【步骤 3】更新菜单项状态
        sender.setState_(1 if new_state else 0)
        
        # 【步骤 4】重新构建两个菜单（更新显示的操作项和配置项）
        print("[DEBUG] [StatusBar] 重新构建菜单以更新显示的操作项和配置项...")
        self.smart_ops_menu = self._build_smart_ops_menu()
        self.config_menu = self._build_config_menu()
        
        # 更新主菜单中的子菜单
        for item in self.menu.itemArray():
            if item.title() == "文件智能操作":
                item.setSubmenu_(self.smart_ops_menu)
                print("[DEBUG] [StatusBar] ✓ 文件智能操作子菜单已更新")
            elif item.title() == "配置选项":
                item.setSubmenu_(self.config_menu)
                print("[DEBUG] [StatusBar] ✓ 配置选项子菜单已更新")
        
        status = "已启用" if new_state else "已禁用"
        print(f"[DEBUG] [StatusBar] ✓ {SMART_OPS_OPTIONS[key]['title']} {status}")
    
    def show_smart_operations_menu(self, files):
        """
        显示文件智能操作菜单
        
        按照流程图设计：
        - 触发条件：选择与上次相同时触发
        - 菜单显示：在状态栏图标位置显示菜单，支持键盘导航（上下键选择，回车确认，ESC 取消）
        
        Args:
            files: 文件路径列表
        """
        print("[DEBUG] [StatusBar] 显示文件智能操作菜单（按照流程图：选择与上次相同）")
        if not files:
            print("[DEBUG] [StatusBar] 文件列表为空，不显示菜单")
            return
        
        # 【步骤 1】更新缓存的文件列表
        self.cached_files = files
        print(f"[DEBUG] [StatusBar] 缓存文件列表: {len(files)} 个文件")
        
        # 【步骤 2】获取状态栏按钮
        button = self.status_item.button()
        if not button:
            print("[ERROR] [StatusBar] 无法获取状态栏按钮，菜单显示失败")
            return
        
        # 【步骤 3】临时替换菜单为智能操作菜单
        original_menu = self.status_item.menu()
        self.status_item.setMenu_(self.smart_ops_menu)
        print("[DEBUG] [StatusBar] 已临时替换菜单")
        
        # 【步骤 4】获取按钮位置并显示菜单
        frame = button.frame()
        point = NSPoint(frame.origin.x, frame.origin.y - frame.size.height)
        print(f"[DEBUG] [StatusBar] 菜单显示位置: ({point.x}, {point.y})")
        
        # 使用 popUpMenuPositioningItem 显示菜单，支持键盘导航
        # 按照流程图：支持键盘上下键选择，回车确认，ESC 取消
        self.smart_ops_menu.popUpMenuPositioningItem_atLocation_inView_(
            None, point, button
        )
        
        # 【步骤 5】恢复原菜单
        self.status_item.setMenu_(original_menu)
        print("[DEBUG] [StatusBar] ✓ 菜单已显示，支持键盘导航（上下键选择，回车确认，ESC 取消）")
    
    def _reset_last_selection(self):
        """重置 last_selection（允许下次重新开始）"""
        if self.cut_manager:
            print("[DEBUG] [StatusBar] 重置 last_selection")
            self.cut_manager.last_selection = None
    
    def _execute_smart_operation(self, operation_name, operation_func, files=None):
        """
        执行智能操作的通用方法
        
        按照流程图设计：
        - 操作完成后重置 last_selection = None（允许下次重新开始）
        
        Args:
            operation_name: 操作名称（用于日志）
            operation_func: 操作函数，接收 files 参数，返回 (success, msg) 或 (success, msg, output)
            files: 文件列表，如果为 None 则自动获取
        """
        print(f"[DEBUG] [StatusBar] 开始执行 {operation_name} 操作")
        
        # 【步骤 1】获取文件列表
        if files is None:
            files = self._get_selected_files()
            if not files:
                print(f"[DEBUG] [StatusBar] {operation_name} 操作取消：无文件")
                return
        
        print(f"[DEBUG] [StatusBar] {operation_name} 操作文件数量: {len(files)}")
        
        # 【步骤 2】执行操作
        print(f"[DEBUG] [StatusBar] 调用操作函数: {operation_name}")
        result = operation_func(files)
        
        # 【步骤 3】处理结果（支持两种返回格式）
        if isinstance(result, tuple) and len(result) >= 2:
            success, msg = result[0], result[1]
            if success:
                print(f"[DEBUG] [StatusBar] ✓ {operation_name} 成功: {msg}")
            else:
                print(f"[DEBUG] [StatusBar] ✗ {operation_name} 失败: {msg}")
        
        # 【步骤 4】操作完成后，重置 last_selection（按照流程图设计）
        print(f"[DEBUG] [StatusBar] {operation_name} 操作完成，重置 last_selection")
        self._reset_last_selection()
    
    @objc.IBAction
    def smartCompress_(self, sender):
        """压缩文件"""
        def _compress(files):
            success, msg, output_path = compress_to_zip(files)
            self.send_notification("✅ 压缩成功" if success else "❌ 压缩失败", msg)
            return success, msg
        
        self._execute_smart_operation("压缩文件", _compress)
    
    @objc.IBAction
    def smartDecompress_(self, sender):
        """解压缩文件"""
        def _decompress(files):
            all_success = True
            for archive_path in files:
                success, msg, output_dir = decompress_archive(archive_path)
                self.send_notification("✅ 解压成功" if success else "❌ 解压失败", msg)
                if not success:
                    all_success = False
            return all_success, "解压完成"
        
        self._execute_smart_operation("解压缩文件", _decompress)
    
    @objc.IBAction
    def smartMdToHtml_(self, sender):
        """MD 转 HTML"""
        def _md_to_html(files):
            from .utils import convert_md_to_html
            all_success = True
            for md_path in files:
                if not md_path.lower().endswith(('.md', '.markdown')):
                    self.send_notification("⚠️ 跳过", f"{Path(md_path).name} 不是 Markdown 文件")
                    continue
                success, msg, output_path = convert_md_to_html(md_path)
                self.send_notification("✅ 转换成功" if success else "❌ 转换失败", msg)
                if not success:
                    all_success = False
            return all_success, "转换完成"
        
        self._execute_smart_operation("MD 转 HTML", _md_to_html)
    
    @objc.IBAction
    def smartMdToPdf_(self, sender):
        """MD 转 PDF"""
        def _md_to_pdf(files):
            from .utils import convert_md_to_pdf
            all_success = True
            for md_path in files:
                if not md_path.lower().endswith(('.md', '.markdown')):
                    self.send_notification("⚠️ 跳过", f"{Path(md_path).name} 不是 Markdown 文件")
                    continue
                success, msg, output_path = convert_md_to_pdf(md_path)
                self.send_notification("✅ 转换成功" if success else "❌ 转换失败", msg)
                if not success:
                    all_success = False
            return all_success, "转换完成"
        
        self._execute_smart_operation("MD 转 PDF", _md_to_pdf)
    
    @objc.IBAction
    def smartCopyPaths_(self, sender):
        """复制文件路径"""
        def _copy_paths(files):
            paths_text = "\n".join(files)
            copy_to_clipboard(paths_text)
            count = len(files)
            msg = f"已复制 {count} 个文件路径" if count > 1 else "已复制文件路径"
            self.send_notification("✅ 已复制路径", msg)
            return True, msg
        
        self._execute_smart_operation("复制文件路径", _copy_paths)
    
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
