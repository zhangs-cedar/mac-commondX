#!/usr/bin/env python3
"""状态栏图标"""

import objc
import os
from pathlib import Path
from Foundation import NSObject, NSTimer
from AppKit import (
    NSStatusBar, NSMenu, NSMenuItem, NSImage, NSColor, NSApplication,
    NSSize, NSRect, NSPoint, NSBezierPath, NSAffineTransform,
    NSUserNotificationCenter, NSUserNotification, NSButton, NSStackView, NSAlert, NSApp,
    NSFloatingWindowLevel, NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary
)
from cedar.utils import print, load_config, write_config

from .utils import copy_to_clipboard
from .plugins.compress_plugin import execute as compress_execute
from .plugins.decompress_plugin import execute as decompress_execute
from .plugins.md_to_html_plugin import execute as md_to_html_execute
from .plugins.open_terminal_plugin import execute as open_terminal_execute
from .plugins.pdf_editor_plugin import execute as pdf_editor_execute

# 配置文件路径 - 从环境变量读取
_config_path_str = os.getenv('CONFIG_PATH')
CONFIG_PATH = Path(_config_path_str)

# 所有可用的智能操作选项
SMART_OPS_OPTIONS = {
    "compress": {"title": "压缩文件", "action": "smartCompress:"},
    "decompress": {"title": "解压缩文件", "action": "smartDecompress:"},
    "md_to_html": {"title": "MD 转 HTML", "action": "smartMdToHtml:"},
    "copy_paths": {"title": "复制文件路径", "action": "smartCopyPaths:"},
    "open_terminal": {"title": "打开终端", "action": "smartOpenTerminal:"},
    "pdf_editor": {"title": "PDF WORD 等在线免费转化工具", "action": "smartPdfEditor:"},
}

# 文件类型定义
FILE_TYPES = {
    "archive": {"name": "压缩包", "extensions": [".zip", ".tar", ".gz", ".bz2", ".rar", ".7z", ".tgz", ".tar.gz", ".tar.bz2"]},
    "markdown": {"name": "Markdown", "extensions": [".md", ".markdown"]},
    "image": {"name": "图片", "extensions": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp", ".svg"]},
    "text": {"name": "文本文件", "extensions": [".txt", ".log", ".conf", ".config", ".ini", ".csv", ".tsv"]},
    "code": {"name": "代码文件", "extensions": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".go", ".rs", ".swift"]},
    "pdf": {"name": "PDF 文件", "extensions": [".pdf"]},
    "document": {"name": "Office 文档", "extensions": [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".rtf"]},
    "other": {"name": "其他", "extensions": []}  # 其他所有文件类型
}

# 所有文件类型键（用于默认配置）
ALL_FILE_TYPES = list(FILE_TYPES.keys())

# 每个操作的默认支持文件类型
DEFAULT_SUPPORTED_TYPES = {
    "compress": ALL_FILE_TYPES,  # 压缩文件支持所有类型
    "decompress": ["archive"],  # 解压缩文件仅支持压缩包
    "md_to_html": ["markdown"],  # MD转HTML仅支持Markdown
    "copy_paths": ALL_FILE_TYPES,  # 复制文件路径支持所有类型
    "open_terminal": ALL_FILE_TYPES,  # 打开终端支持所有类型
    "pdf_editor": ["pdf", "document"],  # PDF WORD 等在线免费转化工具支持 PDF 和 Office 文档
}


def _add_menu_item(menu, target, title, action=None, key="", enabled=True):
    """创建菜单项（类外函数避免 PyObjC 冲突）"""
    item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key)
    if action:
        item.setTarget_(target)
    item.setEnabled_(enabled)
    menu.addItem_(item)
    return item


def _setup_edit_menu(app):
    """
    【关键修复】创建标准的应用程序菜单（包含编辑菜单）。
    没有这个，Cmd+C/Cmd+V 快捷键将无法触发 copy:/paste: 事件。
    
    参考：test/test_alert_input.py 中的修复方案
    """
    print("[DEBUG] [StatusBar] 正在构建应用程序 Edit 菜单...")
    
    # 检查是否已经有主菜单
    existing_menu = app.mainMenu()
    if existing_menu:
        # 检查是否已经有 Edit 菜单
        menu_items = existing_menu.itemArray()
        for item in menu_items:
            if item.title() == "Edit":
                print("[DEBUG] [StatusBar] ✓ Edit 菜单已存在，跳过创建")
                return
    
    # 创建新的菜单栏
    menubar = NSMenu.alloc().init()
    
    # 1. 应用主菜单 (App Menu)
    app_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("App", None, "")
    menubar.addItem_(app_menu_item)
    
    # 2. 编辑菜单 (Edit Menu) - 这是复制粘贴生效的关键
    edit_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Edit", None, "")
    edit_menu = NSMenu.alloc().initWithTitle_("Edit")
    
    # 添加标准的编辑操作
    # 剪切 (Cmd+X)
    edit_menu.addItemWithTitle_action_keyEquivalent_("Cut", "cut:", "x")
    # 复制 (Cmd+C)
    edit_menu.addItemWithTitle_action_keyEquivalent_("Copy", "copy:", "c")
    # 粘贴 (Cmd+V)
    edit_menu.addItemWithTitle_action_keyEquivalent_("Paste", "paste:", "v")
    # 全选 (Cmd+A)
    edit_menu.addItemWithTitle_action_keyEquivalent_("Select All", "selectAll:", "a")
    
    # 将子菜单关联到菜单项
    edit_menu_item.setSubmenu_(edit_menu)
    menubar.addItem_(edit_menu_item)
    
    # 设置为主菜单
    app.setMainMenu_(menubar)
    print("[DEBUG] [StatusBar] ✓ Edit 菜单已创建并设置为主菜单")


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
            self.ops_order = self._load_smart_ops_order()  # 加载顺序配置
            self.update_icon(0)
            self.setup_menu()
            cut_manager.on_state_change = self.on_cut_state_change
        return self
    
    def _load_smart_ops_config(self):
        """
        加载智能操作配置（支持新格式：包含 enabled 和 supported_types）
        
        按照流程图设计：配置选项控制操作选项的显示
        兼容旧配置格式（简单的 enabled: true/false）
        """
        print("[DEBUG] [StatusBar] 加载智能操作配置...")
        try:
            if CONFIG_PATH.exists():
                data = load_config(str(CONFIG_PATH)) or {}
                smart_ops = data.get('smart_ops', {})
                print(f"[DEBUG] [StatusBar] 从配置文件读取: {smart_ops}")
                
                # 如果配置为空，使用默认配置
                if not smart_ops:
                    smart_ops = self._get_default_smart_ops_config()
                    self._save_smart_ops_config(smart_ops)
                    print(f"[DEBUG] [StatusBar] 配置为空，使用默认配置")
                
                # 验证和迁移配置
                result = {}
                for key in SMART_OPS_OPTIONS.keys():
                    if key not in smart_ops:
                        # 缺失配置项，使用默认值
                        result[key] = {
                            "enabled": True,
                            "supported_types": DEFAULT_SUPPORTED_TYPES.get(key, ALL_FILE_TYPES)
                        }
                        print(f"[DEBUG] [StatusBar] 补充缺失配置项: {key}")
                    else:
                        op_config = smart_ops[key]
                        # 兼容旧格式：如果直接是 bool，转换为新格式
                        if isinstance(op_config, bool):
                            result[key] = {
                                "enabled": op_config,
                                "supported_types": DEFAULT_SUPPORTED_TYPES.get(key, ALL_FILE_TYPES)
                            }
                            print(f"[DEBUG] [StatusBar] 迁移旧配置格式: {key}")
                        elif isinstance(op_config, dict):
                            # 新格式：确保包含所有字段
                            result[key] = {
                                "enabled": op_config.get("enabled", True),
                                "supported_types": op_config.get("supported_types", DEFAULT_SUPPORTED_TYPES.get(key, ALL_FILE_TYPES))
                            }
                        else:
                            # 未知格式，使用默认值
                            result[key] = {
                                "enabled": True,
                                "supported_types": DEFAULT_SUPPORTED_TYPES.get(key, ALL_FILE_TYPES)
                            }
                            print(f"[WARN] [StatusBar] 未知配置格式: {key}, 使用默认值")
                
                # 保存迁移后的配置
                if result != smart_ops:
                    self._save_smart_ops_config(result)
                    print(f"[DEBUG] [StatusBar] 配置已迁移并保存")
                
                print(f"[DEBUG] [StatusBar] ✓ 配置加载成功")
                return result
        except Exception as e:
            print(f"[ERROR] [StatusBar] 加载配置失败: {e}")
        
        # 使用默认配置
        default = self._get_default_smart_ops_config()
        print(f"[DEBUG] [StatusBar] 使用默认配置")
        return default
    
    def _get_default_smart_ops_config(self):
        """获取默认的智能操作配置"""
        return {
            key: {
                "enabled": True,
                "supported_types": DEFAULT_SUPPORTED_TYPES.get(key, ALL_FILE_TYPES)
            }
            for key in SMART_OPS_OPTIONS.keys()
        }
    
    def _is_op_enabled(self, key: str) -> bool:
        """检查操作是否启用"""
        op_config = self.enabled_ops.get(key, {})
        if isinstance(op_config, bool):
            return op_config
        return op_config.get("enabled", True)
    
    def _get_op_supported_types(self, key: str) -> list:
        """获取操作支持的文件类型"""
        op_config = self.enabled_ops.get(key, {})
        if isinstance(op_config, bool):
            return DEFAULT_SUPPORTED_TYPES.get(key, ALL_FILE_TYPES)
        return op_config.get("supported_types", DEFAULT_SUPPORTED_TYPES.get(key, ALL_FILE_TYPES))
    
    def _load_smart_ops_order(self):
        """
        加载智能操作顺序配置
        
        Returns:
            list: 选项 key 的顺序列表
        """
        print("[DEBUG] [StatusBar] 加载智能操作顺序配置...")
        try:
            if CONFIG_PATH.exists():
                data = load_config(str(CONFIG_PATH)) or {}
                raw_order = data.get('smart_ops_order', [])
                order = [k for k in raw_order if k in SMART_OPS_OPTIONS]
                print(f"[DEBUG] [StatusBar] 从配置文件读取顺序: {order}")
                
                # 验证顺序完整性（确保所有选项都在顺序列表中）
                all_keys = set(SMART_OPS_OPTIONS.keys())
                order_keys = set(order)
                
                # 如果顺序为空或不完整，使用默认顺序
                if not order or all_keys != order_keys:
                    default_order = list(SMART_OPS_OPTIONS.keys())
                    if order:
                        # 保留现有顺序，补充缺失的项
                        missing = all_keys - order_keys
                        default_order = order + list(missing)
                    self._save_smart_ops_order(default_order)
                    print(f"[DEBUG] [StatusBar] 顺序配置不完整，使用默认顺序: {default_order}")
                    return default_order
                
                print(f"[DEBUG] [StatusBar] ✓ 顺序配置加载成功: {order}")
                return order
        except Exception as e:
            print(f"[ERROR] [StatusBar] 加载顺序配置失败: {e}")
        
        # 默认顺序：按照 SMART_OPS_OPTIONS 的定义顺序
        default_order = list(SMART_OPS_OPTIONS.keys())
        print(f"[DEBUG] [StatusBar] 使用默认顺序: {default_order}")
        return default_order
    
    def _detect_file_type(self, file_path: str) -> str:
        """
        检测单个文件的类型
        
        Args:
            file_path: 文件路径
            
            Returns:
            str: 文件类型键（archive, markdown, image, text, code, pdf, document, other）
        """
        print(f"[DEBUG] [StatusBar] 检测文件类型: {file_path}")
        try:
            path = Path(file_path)
            ext = path.suffix.lower()
            
            # 检查所有文件类型（除了 other）
            for type_key, type_info in FILE_TYPES.items():
                if type_key == "other":
                    continue
                if ext in type_info["extensions"]:
                    print(f"[DEBUG] [StatusBar] 检测到文件类型: {type_key} (扩展名: {ext})")
                    return type_key
            
            # 如果没有匹配，返回 other
            print(f"[DEBUG] [StatusBar] 未匹配到特定类型，返回 other (扩展名: {ext})")
            return "other"
        except Exception as e:
            print(f"[ERROR] [StatusBar] 检测文件类型失败: {e}")
            return "other"
    
    def _get_file_types(self, file_paths: list) -> set:
        """
        获取文件列表的所有类型（去重）
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            set: 文件类型集合
        """
        print(f"[DEBUG] [StatusBar] 获取文件类型集合，文件数量: {len(file_paths)}")
        types = set()
        for file_path in file_paths:
            file_type = self._detect_file_type(file_path)
            types.add(file_type)
        print(f"[DEBUG] [StatusBar] 文件类型集合: {types}")
        return types
    
    def _save_smart_ops_order(self, order):
        """
        保存智能操作顺序配置
        
        注意：配置文件已与许可证文件分离，只包含配置相关字段
        
        Args:
            order: 选项 key 的顺序列表
        """
        print(f"[DEBUG] [StatusBar] 保存智能操作顺序配置: {order}")
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取现有配置（只包含配置相关字段）
            data = {}
            if CONFIG_PATH.exists():
                data = load_config(str(CONFIG_PATH)) or {}
            
            # 更新顺序配置
            data['smart_ops_order'] = order
            write_config(data, str(CONFIG_PATH))
            print(f"[DEBUG] [StatusBar] ✓ 顺序配置保存成功，共 {len(order)} 个选项")
        except Exception as e:
            print(f"[ERROR] [StatusBar] 保存顺序配置失败: {e}")
    
    def _save_smart_ops_config(self, smart_ops):
        """
        保存智能操作配置（新格式：包含 enabled 和 supported_types）
        
        按照流程图设计：配置保存后立即生效
        注意：配置文件已与许可证文件分离，只包含配置相关字段
        
        Args:
            smart_ops: 智能操作配置字典，格式为 {key: {"enabled": bool, "supported_types": list}}
        """
        print(f"[DEBUG] [StatusBar] 保存智能操作配置")
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            print(f"[DEBUG] [StatusBar] 配置文件路径: {CONFIG_PATH}")
            
            # 读取现有配置（只包含配置相关字段）
            data = {}
            if CONFIG_PATH.exists():
                data = load_config(str(CONFIG_PATH)) or {}
                print(f"[DEBUG] [StatusBar] 读取现有配置: {list(data.keys())}")
            
            # 更新配置相关字段
            data['smart_ops'] = smart_ops
            # 同时保存顺序配置（如果存在）
            if hasattr(self, 'ops_order') and self.ops_order:
                data['smart_ops_order'] = self.ops_order
            write_config(data, str(CONFIG_PATH))
            print(f"[DEBUG] [StatusBar] ✓ 配置保存成功，共 {len(smart_ops)} 个选项")
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
    
    def _show_alert_common(self, title, msg, buttons=None, with_input=False, input_placeholder="", alert_style=0):
        """
        通用弹窗方法，统一处理窗口层级、强制显示等逻辑
        
        Args:
            title: 弹窗标题
            msg: 弹窗消息内容
            buttons: 按钮列表，如果为 None 则使用默认按钮 ["确定"]
            with_input: 是否显示输入框
            input_placeholder: 输入框占位符文本
            alert_style: 弹窗样式（0=信息，1=警告，2=错误）
            
        Returns:
            如果 with_input=True，返回 (button_index, input_value)
            否则返回 button_index（1000=第一个按钮，1001=第二个按钮，以此类推）
        """
        from AppKit import NSAlert, NSTextField, NSApp
        print(f"[DEBUG] [StatusBar] 显示弹窗 - title={title}, with_input={with_input}")
        
        # 【步骤 1】设置应用激活策略和激活应用
        NSApp.setActivationPolicy_(0)  # NSApplicationActivationPolicyRegular
        NSApp.activateIgnoringOtherApps_(True)
        print("[DEBUG] [StatusBar] 应用已激活")
        
        # 【步骤 1.5】如果有输入框，确保应用有 Edit 菜单（支持 ⌘+C/⌘+V）
        if with_input:
            _setup_edit_menu(NSApp)
        
        # 【步骤 2】创建弹窗
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(msg)
        alert.setAlertStyle_(alert_style)
        
        # 【步骤 3】添加按钮
        if buttons is None:
            buttons = ["确定"]
        for btn_title in buttons:
            alert.addButtonWithTitle_(btn_title)
        print(f"[DEBUG] [StatusBar] 已添加 {len(buttons)} 个按钮")
        
        # 【步骤 4】添加输入框（如果需要）
        field = None
        if with_input:
            alert.addButtonWithTitle_("取消")
            field = NSTextField.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(250, 24)))
            field.setPlaceholderString_(input_placeholder)
            field.setEditable_(True)
            field.setSelectable_(True)
            field.setBezeled_(True)
            field.setDrawsBackground_(True)
            alert.setAccessoryView_(field)
            print(f"[DEBUG] [StatusBar] 已添加输入框，占位符={input_placeholder}")
        
        # 【步骤 5】设置窗口层级（确保显示在最前面，但不影响默认居中位置）
        window = alert.window()
        if window:
            # 设置窗口层级为浮在最前面
            window.setLevel_(NSFloatingWindowLevel)
            # 设置窗口集合行为
            collection_behavior = (NSWindowCollectionBehaviorCanJoinAllSpaces | 
                                  NSWindowCollectionBehaviorFullScreenAuxiliary)
            window.setCollectionBehavior_(collection_behavior)
            print("[DEBUG] [StatusBar] 窗口层级已设置（显示在最前面）")
            
            # 如果有输入框，设置为第一响应者（在 runModal 之前设置）
            if with_input and field:
                window.makeFirstResponder_(field)
        
        # 【步骤 6】显示弹窗（runModal 会自动居中显示）
        print("[DEBUG] [StatusBar] 显示弹窗（模态，自动居中）")
        result = alert.runModal()
        print(f"[DEBUG] [StatusBar] 弹窗关闭，返回结果={result}")
        
        # 【步骤 7】恢复应用激活策略
        NSApp.setActivationPolicy_(2)  # NSApplicationActivationPolicyAccessory
        print("[DEBUG] [StatusBar] 应用激活策略已恢复")
        
        # 【步骤 8】返回结果
        if with_input and field:
            input_value = field.stringValue().strip() if result == 1000 else ""
            print(f"[DEBUG] [StatusBar] 输入框值={input_value}")
            return (result == 1000, input_value)
        # 返回按钮索引（1000=第一个按钮，1001=第二个按钮，以此类推）
        return result
    
    def setup_menu(self):
        """
        设置菜单
        
        按照流程图设计构建完整的菜单结构
        """
        print("[DEBUG] [StatusBar] 开始设置菜单...")
        from .permission import check_accessibility
        
        menu = NSMenu.alloc().init()
        
        # 【步骤 1】功能区
        print("[DEBUG] [StatusBar] 添加功能区...")
        self.files_header = _add_menu_item(menu, self, "无待移动文件", enabled=False)
        _add_menu_item(menu, self, "清空列表", "clearCut:")
        
        # 【步骤 2】文件智能操作子菜单（根据配置动态构建）
        print("[DEBUG] [StatusBar] 构建文件智能操作子菜单...")
        self.smart_ops_menu = self._build_smart_ops_menu()
        
        # 主菜单项：使用简洁的标题
        smart_ops_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("文件智能操作", None, "")
        smart_ops_item.setSubmenu_(self.smart_ops_menu)
        menu.addItem_(smart_ops_item)
        print("[DEBUG] [StatusBar] ✓ 文件智能操作子菜单已添加")
        
        # 【步骤 3】配置选项子菜单（按照流程图：与文件智能操作平级）
        print("[DEBUG] [StatusBar] 构建配置选项子菜单...")
        self.config_menu = self._build_config_menu()
        
        # 主菜单项：使用简洁的标题
        config_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("配置选项", None, "")
        config_item.setSubmenu_(self.config_menu)
        menu.addItem_(config_item)
        print("[DEBUG] [StatusBar] ✓ 配置选项子菜单已添加")
        
        menu.addItem_(NSMenuItem.separatorItem())
        
        # 【步骤 4】系统设置
        print("[DEBUG] [StatusBar] 添加系统设置区域...")
        perm_ok = check_accessibility()
        if perm_ok:
            _add_menu_item(menu, self, "已获得系统权限", enabled=False)
        else:
            _add_menu_item(menu, self, "未获得系统权限 (点击授权)", "checkPermission:")
        
        menu.addItem_(NSMenuItem.separatorItem())
        
        # 【步骤 5】关于和退出
        print("[DEBUG] [StatusBar] 添加关于和退出...")
        _add_menu_item(menu, self, "关于", "showAbout:")
        _add_menu_item(menu, self, "退出", "quit:", "q")
        
        self.menu = menu
        self.status_item.setMenu_(menu)
        print("[DEBUG] [StatusBar] ✓ 菜单设置完成")
    
    def _build_smart_ops_menu(self, files: list = None):
        """
        根据配置构建智能操作菜单（支持根据文件类型过滤）
        
        按照流程图设计：
        1. 说明项
        2. 操作选项（根据配置和文件类型显示，按照配置顺序）
        
        Args:
            files: 文件路径列表，如果提供则根据文件类型过滤操作
        """
        print(f"[DEBUG] [StatusBar] 构建智能操作菜单... (文件数量: {len(files) if files else 0})")
        menu = NSMenu.alloc().init()
        
        # 【步骤 1】添加说明项（禁用状态，仅用于提示）
        _add_menu_item(menu, self, "💡 重复 ⌘+X 时自动显示", enabled=False)
        menu.addItem_(NSMenuItem.separatorItem())
        print("[DEBUG] [StatusBar] 已添加说明项")
        
        # 【步骤 2】检测文件类型（如果提供了文件列表）
        file_types = None
        if files:
            file_types = self._get_file_types(files)
            print(f"[DEBUG] [StatusBar] 检测到文件类型: {file_types}")
        
        # 【步骤 3】根据配置和顺序添加操作选项（按照流程图：操作选项根据配置和文件类型显示）
        order = getattr(self, 'ops_order', list(SMART_OPS_OPTIONS.keys()))
        print(f"[DEBUG] [StatusBar] 使用顺序: {order}")
        
        enabled_count = 0
        for key in order:
            if key not in SMART_OPS_OPTIONS:
                continue
            
            # 检查操作是否启用
            if not self._is_op_enabled(key):
                print(f"[DEBUG] [StatusBar] 操作已禁用: {key}")
                continue
            
            # 如果提供了文件列表，检查文件类型是否匹配
            if files and file_types:
                supported_types = set(self._get_op_supported_types(key))
                # 检查文件类型是否与操作支持的类型有交集
                if not (file_types & supported_types):
                    print(f"[DEBUG] [StatusBar] 文件类型不匹配，跳过操作: {key} (文件类型: {file_types}, 支持类型: {supported_types})")
                    continue
            
            # 添加操作选项
            option = SMART_OPS_OPTIONS[key]
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
        2. 配置选项（子菜单，点击不关闭主菜单，支持排序）
        """
        print("[DEBUG] [StatusBar] 构建配置选项菜单...")
        menu = NSMenu.alloc().init()
        
        # 【步骤 1】添加配置标题（禁用状态）
        _add_menu_item(menu, self, "⚙️ 配置显示项", enabled=False)
        print("[DEBUG] [StatusBar] 已添加配置标题")
        
        # 【步骤 2】按照保存的顺序为每个选项创建子菜单
        order = getattr(self, 'ops_order', list(SMART_OPS_OPTIONS.keys()))
        print(f"[DEBUG] [StatusBar] 使用顺序: {order}")
        
        for idx, key in enumerate(order):
            if key not in SMART_OPS_OPTIONS:
                print(f"[WARN] [StatusBar] 跳过无效的配置项: {key}")
                continue
            
            option = SMART_OPS_OPTIONS[key]
            is_enabled = self._is_op_enabled(key)
            
            # 为每个配置项创建子菜单（点击不关闭主菜单）
            submenu = NSMenu.alloc().init()
            
            # 子菜单项1：启用/禁用（复选框）
            toggle_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "启用/禁用", "toggleSmartOp:", ""
            )
            toggle_item.setTarget_(self)
            toggle_item.setRepresentedObject_(key)
            toggle_item.setState_(1 if is_enabled else 0)
            submenu.addItem_(toggle_item)
            
            # 子菜单项2：支持的文件类型（新增）
            file_types_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "支持的文件类型", None, ""
            )
            file_types_item.setSubmenu_(self._build_file_types_menu(key))
            submenu.addItem_(file_types_item)
            
            # 子菜单项2：上移（如果不是第一个）
            if idx > 0:
                move_up_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    "↑ 上移", "moveConfigUp:", ""
                )
                move_up_item.setTarget_(self)
                move_up_item.setRepresentedObject_(key)
                submenu.addItem_(move_up_item)
            
            # 子菜单项3：下移（如果不是最后一个）
            if idx < len(order) - 1:
                move_down_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    "↓ 下移", "moveConfigDown:", ""
                )
                move_down_item.setTarget_(self)
                move_down_item.setRepresentedObject_(key)
                submenu.addItem_(move_down_item)
            
            # 创建主菜单项（带子菜单）
            # 标题显示复选框状态：☑ 或 ☐
            checkbox = "☑" if is_enabled else "☐"
            main_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"{checkbox} {option['title']}", None, ""
            )
            main_item.setSubmenu_(submenu)
            menu.addItem_(main_item)
            print(f"[DEBUG] [StatusBar] 已添加配置项: {option['title']} (状态={'启用' if is_enabled else '禁用'})")
        
        # 【步骤 3】添加分隔线与编辑配置文件
        menu.addItem_(NSMenuItem.separatorItem())
        _add_menu_item(menu, self, "📝 编辑配置文件", "openConfigFile:")
        print("[DEBUG] [StatusBar] 已添加编辑配置文件选项")
        
        print(f"[DEBUG] [StatusBar] ✓ 配置选项菜单构建完成")
        return menu
    
    def _build_file_types_menu(self, operation_key: str) -> NSMenu:
        """
        构建文件类型选择菜单
        
        Args:
            operation_key: 操作键（compress, decompress, md_to_html, copy_paths）
            
        Returns:
            NSMenu: 文件类型选择菜单
        """
        print(f"[DEBUG] [StatusBar] 构建文件类型选择菜单: {operation_key}")
        menu = NSMenu.alloc().init()
        
        # 获取当前操作支持的文件类型
        supported_types = self._get_op_supported_types(operation_key)
        print(f"[DEBUG] [StatusBar] 当前支持的文件类型: {supported_types}")
        
        # 添加全选/全不选快捷操作
        all_selected = set(supported_types) == set(ALL_FILE_TYPES)
        select_all_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "全选" if not all_selected else "全不选", "toggleAllFileTypes:", ""
        )
        select_all_item.setTarget_(self)
        select_all_item.setRepresentedObject_(operation_key)
        menu.addItem_(select_all_item)
        menu.addItem_(NSMenuItem.separatorItem())
        
        # 添加每个文件类型选项
        for type_key in ALL_FILE_TYPES:
            type_info = FILE_TYPES[type_key]
            is_supported = type_key in supported_types
            
            type_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"{'☑' if is_supported else '☐'} {type_info['name']}", "toggleFileType:", ""
            )
            type_item.setTarget_(self)
            # 使用 representedObject 存储 (operation_key, type_key) 元组
            type_item.setRepresentedObject_({"operation": operation_key, "type": type_key})
            type_item.setState_(1 if is_supported else 0)
            menu.addItem_(type_item)
        
        print(f"[DEBUG] [StatusBar] ✓ 文件类型选择菜单构建完成")
        return menu
    
    @objc.IBAction
    def toggleFileType_(self, sender):
        """切换文件类型支持状态"""
        data = sender.representedObject()
        if not data or not isinstance(data, dict):
            print(f"[ERROR] [StatusBar] 无法获取操作和类型信息")
            return
        
        operation_key = data.get("operation")
        type_key = data.get("type")
        
        if not operation_key or not type_key:
            print(f"[ERROR] [StatusBar] 操作或类型信息不完整")
            return
        
        print(f"[DEBUG] [StatusBar] 切换文件类型支持: {operation_key} - {type_key}")
        
        # 获取当前支持的文件类型
        supported_types = self._get_op_supported_types(operation_key)
        
        # 切换状态
        if type_key in supported_types:
            supported_types = [t for t in supported_types if t != type_key]
        else:
            supported_types = list(supported_types) + [type_key]
        
        # 更新配置
        op_config = self.enabled_ops.get(operation_key, {})
        if isinstance(op_config, bool):
            # 旧格式，转换为新格式
            self.enabled_ops[operation_key] = {
                "enabled": op_config,
                "supported_types": supported_types
            }
        else:
            # 新格式，更新 supported_types
            self.enabled_ops[operation_key] = {
                "enabled": op_config.get("enabled", True),
                "supported_types": supported_types
            }
        
        # 保存配置
        self._save_smart_ops_config(self.enabled_ops)
        
        # 重建菜单
        self._rebuild_menus()
        
        print(f"[DEBUG] [StatusBar] ✓ 文件类型支持已更新: {operation_key} - {supported_types}")
    
    @objc.IBAction
    def toggleAllFileTypes_(self, sender):
        """全选/全不选文件类型"""
        operation_key = sender.representedObject()
        if not operation_key:
            print(f"[ERROR] [StatusBar] 无法获取操作信息")
            return
        
        print(f"[DEBUG] [StatusBar] 全选/全不选文件类型: {operation_key}")
        
        # 获取当前支持的文件类型
        supported_types = self._get_op_supported_types(operation_key)
        all_selected = set(supported_types) == set(ALL_FILE_TYPES)
        
        # 切换状态
        if all_selected:
            # 全不选
            new_supported_types = []
        else:
            # 全选
            new_supported_types = ALL_FILE_TYPES.copy()
        
        # 更新配置
        op_config = self.enabled_ops.get(operation_key, {})
        if isinstance(op_config, bool):
            # 旧格式，转换为新格式
            self.enabled_ops[operation_key] = {
                "enabled": op_config,
                "supported_types": new_supported_types
            }
        else:
            # 新格式，更新 supported_types
            self.enabled_ops[operation_key] = {
                "enabled": op_config.get("enabled", True),
                "supported_types": new_supported_types
            }
        
        # 保存配置
        self._save_smart_ops_config(self.enabled_ops)
        
        # 重建菜单
        self._rebuild_menus()
        
        print(f"[DEBUG] [StatusBar] ✓ 文件类型支持已更新: {operation_key} - {new_supported_types}")
    
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
        current_state = self._is_op_enabled(key)
        new_state = not current_state
        
        # 更新配置（保持 supported_types）
        op_config = self.enabled_ops.get(key, {})
        if isinstance(op_config, bool):
            # 旧格式，转换为新格式
            self.enabled_ops[key] = {
                "enabled": new_state,
                "supported_types": DEFAULT_SUPPORTED_TYPES.get(key, ALL_FILE_TYPES)
            }
        else:
            # 新格式，只更新 enabled
            self.enabled_ops[key] = {
                "enabled": new_state,
                "supported_types": op_config.get("supported_types", DEFAULT_SUPPORTED_TYPES.get(key, ALL_FILE_TYPES))
            }
        
        print(f"[DEBUG] [StatusBar] 状态切换: {current_state} -> {new_state}")
        
        # 【步骤 2】保存配置
        self._save_smart_ops_config(self.enabled_ops)
        
        # 【步骤 3】更新菜单项状态
        sender.setState_(1 if new_state else 0)
        
        # 【步骤 4】重新构建菜单（更新显示的操作项和配置项）
        print("[DEBUG] [StatusBar] 重新构建菜单以更新显示的操作项和配置项...")
        self._rebuild_menus()
        
        status = "已启用" if new_state else "已禁用"
        print(f"[DEBUG] [StatusBar] ✓ {SMART_OPS_OPTIONS[key]['title']} {status}")
    
    @objc.IBAction
    def moveConfigUp_(self, sender):
        """
        上移配置项
        
        按照流程图设计：调整配置选项的显示顺序
        """
        key = sender.representedObject()
        if not key:
            print(f"[ERROR] [StatusBar] 无法获取配置项 key")
            return
        
        print(f"[DEBUG] [StatusBar] 上移配置项: {key}")
        order = getattr(self, 'ops_order', list(SMART_OPS_OPTIONS.keys()))
        
        # 查找当前项的位置
        try:
            idx = order.index(key)
            if idx == 0:
                print(f"[DEBUG] [StatusBar] 已经是第一个，无法上移")
                return
            
            # 与上一个交换位置
            order[idx], order[idx - 1] = order[idx - 1], order[idx]
            self.ops_order = order
            print(f"[DEBUG] [StatusBar] 上移成功，新顺序: {order}")
            
            # 保存顺序配置
            self._save_smart_ops_order(order)
            
            # 重新构建菜单
            self._rebuild_menus()
            
            option_title = SMART_OPS_OPTIONS[key]['title']
            print(f"[DEBUG] [StatusBar] ✓ {option_title} 已上移")
        except ValueError:
            print(f"[ERROR] [StatusBar] 配置项 {key} 不在顺序列表中")
    
    @objc.IBAction
    def moveConfigDown_(self, sender):
        """
        下移配置项
        
        按照流程图设计：调整配置选项的显示顺序
        """
        key = sender.representedObject()
        if not key:
            print(f"[ERROR] [StatusBar] 无法获取配置项 key")
            return
        
        print(f"[DEBUG] [StatusBar] 下移配置项: {key}")
        order = getattr(self, 'ops_order', list(SMART_OPS_OPTIONS.keys()))
        
        # 查找当前项的位置
        try:
            idx = order.index(key)
            if idx == len(order) - 1:
                print(f"[DEBUG] [StatusBar] 已经是最后一个，无法下移")
                return
            
            # 与下一个交换位置
            order[idx], order[idx + 1] = order[idx + 1], order[idx]
            self.ops_order = order
            print(f"[DEBUG] [StatusBar] 下移成功，新顺序: {order}")
            
            # 保存顺序配置
            self._save_smart_ops_order(order)
            
            # 重新构建菜单
            self._rebuild_menus()
            
            option_title = SMART_OPS_OPTIONS[key]['title']
            print(f"[DEBUG] [StatusBar] ✓ {option_title} 已下移")
        except ValueError:
            print(f"[ERROR] [StatusBar] 配置项 {key} 不在顺序列表中")
    
    def _rebuild_menus(self):
        """
        重新构建菜单（配置顺序变化后调用）
        """
        print("[DEBUG] [StatusBar] 重新构建菜单...")
        
        # 重新构建两个子菜单
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
        
        print("[DEBUG] [StatusBar] ✓ 菜单重建完成")
    
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
        
        # 【步骤 2】根据文件列表动态构建智能操作菜单（根据文件类型过滤）
        smart_ops_menu = self._build_smart_ops_menu(files)
        print(f"[DEBUG] [StatusBar] 已根据文件类型构建智能操作菜单")
        
        # 【步骤 3】获取状态栏按钮
        button = self.status_item.button()
        if not button:
            print("[ERROR] [StatusBar] 无法获取状态栏按钮，菜单显示失败")
            return
        
        # 【步骤 4】临时替换菜单为智能操作菜单
        original_menu = self.status_item.menu()
        self.status_item.setMenu_(smart_ops_menu)
        print("[DEBUG] [StatusBar] 已临时替换菜单")
        
        # 【步骤 5】获取按钮位置并显示菜单
        frame = button.frame()
        point = NSPoint(frame.origin.x, frame.origin.y - frame.size.height)
        print(f"[DEBUG] [StatusBar] 菜单显示位置: ({point.x}, {point.y})")
        
        # 使用 popUpMenuPositioningItem 显示菜单，支持键盘导航
        # 按照流程图：支持键盘上下键选择，回车确认，ESC 取消
        smart_ops_menu.popUpMenuPositioningItem_atLocation_inView_(
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
            success, msg, output_path = compress_execute(files)
            self.send_notification("✅ 压缩成功" if success else "❌ 压缩失败", msg)
            return success, msg
        
        self._execute_smart_operation("压缩文件", _compress)
    
    @objc.IBAction
    def smartDecompress_(self, sender):
        """解压缩文件"""
        def _decompress(files):
            all_success = True
            for archive_path in files:
                success, msg, output_dir = decompress_execute(archive_path)
                self.send_notification("✅ 解压成功" if success else "❌ 解压失败", msg)
                if not success:
                    all_success = False
            return all_success, "解压完成"
        
        self._execute_smart_operation("解压缩文件", _decompress)
    
    @objc.IBAction
    def smartMdToHtml_(self, sender):
        """MD 转 HTML"""
        def _md_to_html(files):
            all_success = True
            for md_path in files:
                if not md_path.lower().endswith(('.md', '.markdown')):
                    self.send_notification("⚠️ 跳过", f"{Path(md_path).name} 不是 Markdown 文件")
                    continue
                success, msg, output_path = md_to_html_execute(md_path)
                self.send_notification("✅ 转换成功" if success else "❌ 转换失败", msg)
                if not success:
                    all_success = False
            return all_success, "转换完成"
        
        self._execute_smart_operation("MD 转 HTML", _md_to_html)
    
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
    def smartOpenTerminal_(self, sender):
        """打开终端并切换到选中文件的上一级目录"""
        def _open_terminal(files):
            success, msg, _ = open_terminal_execute(files)
            if success:
                self.send_notification("✅ 已打开终端", msg)
            else:
                self.send_notification("❌ 打开失败", msg)
            return success, msg
        
        self._execute_smart_operation("打开终端", _open_terminal)
    
    @objc.IBAction
    def smartPdfEditor_(self, sender):
        """打开 PDF24 工具网页进行 PDF、Word 等文档转换"""
        def _pdf_editor(files):
            success, msg, _ = pdf_editor_execute(files)
            if success:
                self.send_notification("✅ 已打开文档转换工具", msg)
            else:
                self.send_notification("❌ 打开失败", msg)
            return success, msg
        
        self._execute_smart_operation("PDF WORD 等在线免费转化工具", _pdf_editor)
    
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
    def openConfigFile_(self, sender):
        """
        打开配置文件进行编辑
        
        使用系统默认编辑器打开配置文件，方便用户直接编辑
        """
        print("[DEBUG] [StatusBar] 打开配置文件进行编辑...")
        try:
            import subprocess
            
            # 确保配置文件存在
            if not CONFIG_PATH.exists():
                CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
                default_config = {
                    'smart_ops': {key: True for key in SMART_OPS_OPTIONS.keys()},
                    'smart_ops_order': list(SMART_OPS_OPTIONS.keys())
                }
                write_config(default_config, str(CONFIG_PATH))
                print(f"[DEBUG] [StatusBar] 创建默认配置文件: {CONFIG_PATH}")
            
            # 使用系统默认编辑器打开文件
            # macOS 使用 'open -t' 命令打开文件，-t 表示使用默认文本编辑器
            result = subprocess.run(['open', '-t', str(CONFIG_PATH)], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"[DEBUG] [StatusBar] ✓ 配置文件已打开: {CONFIG_PATH}")
                self.send_notification(
                    "📝 配置文件已打开",
                    f"路径: {CONFIG_PATH}",
                )
            else:
                print(f"[ERROR] [StatusBar] 打开配置文件失败: {result.stderr}")
                self.send_notification("❌ 打开失败", "无法打开配置文件，请检查文件权限")
        except Exception as e:
            print(f"[ERROR] [StatusBar] 打开配置文件时出错: {e}")
            self.send_notification("❌ 打开失败", f"错误: {str(e)}")
    
    @objc.IBAction
    def showAbout_(self, sender):
        """显示关于对话框"""
        from AppKit import NSWorkspace, NSURL
        print("[DEBUG] [StatusBar] showAbout_() - 显示关于对话框")
        
        about_text = (
            "Mac 文件剪切移动工具\n\n"
            "• ⌘+X 剪切\n• ⌘+V 移动\n\n"
            "版本: 1.0.0\n作者: Cedar 🐱\n微信: z858998813\n\n"
            "完全免费、开源使用（CC BY-NC 4.0）"
        )
        
        # 使用通用方法显示对话框
        response = self._show_alert_common(
            "✂️ CommondX", 
            about_text, 
            buttons=["访问官网", "关闭"],
            with_input=False,
            alert_style=0
        )
        
        # 处理按钮点击
        # NSAlertFirstButtonReturn = 1000, NSAlertSecondButtonReturn = 1001
        if response == 1000:  # 访问官网
            website_url = "https://github.com/zhangs-cedar/mac-commondX"
            NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(website_url))
            print(f"[DEBUG] [StatusBar] 打开官网: {website_url}")
    
    @objc.IBAction
    def quit_(self, sender):
        NSApplication.sharedApplication().terminate_(None)
    
    def send_notification(self, title, msg):
        """
        发送通知（系统通知或弹窗）
        
        优先使用系统通知，如果失败则使用弹窗提示
        """
        import time
        print(f"[DEBUG] [StatusBar] send_notification called - location=status_bar.py:send_notification, title={title}, msg={msg[:50]}, timestamp={int(time.time() * 1000)}")
        
        center = NSUserNotificationCenter.defaultUserNotificationCenter()
        
        print(f"[DEBUG] [StatusBar] NSUserNotificationCenter check - location=status_bar.py:send_notification, center_exists={center is not None}, timestamp={int(time.time() * 1000)}")
        
        notification_sent = False
        if center:
            try:
                n = NSUserNotification.alloc().init()
                n.setTitle_(title)
                n.setInformativeText_(msg)
                center.deliverNotification_(n)
                notification_sent = True
                
                print(f"[DEBUG] [StatusBar] NSUserNotification delivered - location=status_bar.py:send_notification, success=True, timestamp={int(time.time() * 1000)}")
            except Exception as e:
                print(f"[DEBUG] [StatusBar] NSUserNotification delivery failed - location=status_bar.py:send_notification, error={str(e)}, timestamp={int(time.time() * 1000)}")
                print(f"[ERROR] [StatusBar] 发送通知失败: {e}")
        
        # 如果系统通知失败或不可用，使用弹窗提示
        if not notification_sent:
            print(f"[DEBUG] [StatusBar] Falling back to alert dialog - location=status_bar.py:send_notification, title={title}, timestamp={int(time.time() * 1000)}")
            self._show_alert_dialog(title, msg)
    
    def _show_alert_dialog(self, title, msg):
        """
        显示弹窗提示（简单提示，只有一个确定按钮）
        
        Args:
            title: 标题
            msg: 消息内容
        """
        print(f"[DEBUG] [StatusBar] _show_alert_dialog() - title={title}")
        # 使用通用方法
        self._show_alert_common(title, msg, buttons=["确定"], with_input=False, alert_style=0)
