#!/usr/bin/env python3
"""文件操作对话框"""

import os
from pathlib import Path
from AppKit import (
    NSAlert, NSTextView, NSScrollView, NSApp, NSFont, NSColor,
    NSSize, NSRect, NSPoint
)


def _is_directory(path):
    """判断是否为文件夹"""
    try:
        return os.path.isdir(path)
    except:
        return False


def _is_archive_file(path):
    """判断是否为压缩文件"""
    if _is_directory(path):
        return False
    ext = Path(path).suffix.lower()
    archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tgz', '.tar.gz', '.tar.bz2'}
    return ext in archive_extensions or any(path.lower().endswith(ext) for ext in archive_extensions)


def _format_paths_list(files):
    """格式化路径列表，每行一个路径"""
    lines = []
    for path in files:
        if _is_directory(path):
            lines.append(f"📁 {path}")
        else:
            lines.append(f"📄 {path}")
    return "\n".join(lines)


def show_file_operations_dialog(files):
    """
    显示文件操作弹窗
    
    Args:
        files: 文件路径列表
        
    Returns:
        tuple: (action: str, alert: NSAlert)
            - action: 操作类型 "copy"、"compress"、"decompress" 或 None（取消）
            - alert: 弹窗引用
    """
    from cedar.utils import print
    
    print("[DEBUG] show_file_operations_dialog() 进入")
    print(f"[DEBUG] show_file_operations_dialog() 文件列表: {files}")
    
    NSApp.setActivationPolicy_(0)
    NSApp.activateIgnoringOtherApps_(True)
    
    alert = NSAlert.alloc().init()
    alert.setMessageText_("文件智能操作")
    
    # 统计信息
    total_count = len(files)
    archive_count = sum(1 for f in files if _is_archive_file(f))
    has_regular_files = any(not _is_archive_file(f) for f in files)
    print(f"[DEBUG] show_file_operations_dialog() 统计: total={total_count}, archive={archive_count}, has_regular={has_regular_files}")
    
    # 构建提示文本
    if total_count == 1:
        info_text = f"已选中 1 个项目"
    else:
        info_text = f"已选中 {total_count} 个项目"
    
    alert.setInformativeText_(info_text)
    
    # 创建可滚动的文本视图
    scroll_view = NSScrollView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(600, 200)))
    text_view = NSTextView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(580, 0)))
    
    # 格式化路径列表
    paths_text = _format_paths_list(files)
    text_view.setString_(paths_text)
    text_view.setFont_(NSFont.monospacedSystemFontOfSize_weight_(11, 0))
    text_view.setEditable_(False)
    text_view.setSelectable_(True)
    text_view.setDrawsBackground_(True)
    text_view.setVerticallyResizable_(True)
    text_view.setHorizontallyResizable_(False)
    text_view.textContainer().setContainerSize_(NSSize(580, 1e7))
    text_view.textContainer().setWidthTracksTextView_(True)
    
    # 根据内容调整文本视图高度
    text_view.sizeToFit()
    content_height = text_view.frame().size.height
    if content_height > 200:
        content_height = 200
    
    text_view.setFrame_(NSRect(NSPoint(0, 0), NSSize(580, content_height)))
    
    scroll_view.setDocumentView_(text_view)
    scroll_view.setHasVerticalScroller_(True)
    scroll_view.setAutohidesScrollers_(True)
    scroll_view.setBorderType_(1)  # NSBezelBorder
    
    alert.setAccessoryView_(scroll_view)
    
    # 智能添加操作按钮
    # 始终显示"复制路径"
    alert.addButtonWithTitle_("复制路径")
    
    # 根据选中项显示压缩或解压按钮
    has_action_button = False
    action_type = None
    if archive_count > 0 and archive_count == total_count:
        # 全部是压缩文件，显示解压按钮
        alert.addButtonWithTitle_("智能解压")
        has_action_button = True
        action_type = "decompress"
        print("[DEBUG] show_file_operations_dialog() 添加解压按钮")
    elif has_regular_files:
        # 有普通文件/文件夹，显示压缩按钮
        alert.addButtonWithTitle_("压缩为 ZIP")
        has_action_button = True
        action_type = "compress"
        print("[DEBUG] show_file_operations_dialog() 添加压缩按钮")
    
    # 取消按钮
    alert.addButtonWithTitle_("取消")
    print(f"[DEBUG] show_file_operations_dialog() 按钮配置: has_action_button={has_action_button}, action_type={action_type}")
    
    # 在调用 runModal() 之前返回 alert 引用，以便外部可以关闭它
    # 注意：runModal() 是阻塞的，返回时弹窗已关闭
    print("[DEBUG] show_file_operations_dialog() 准备显示弹窗 (runModal)")
    result = alert.runModal()
    print(f"[DEBUG] show_file_operations_dialog() 弹窗返回: result={result}")
    NSApp.setActivationPolicy_(2)
    
    # 返回操作类型和弹窗引用（虽然弹窗已关闭，但保留引用以便统一处理）
    # 按钮顺序：复制路径(1000), 压缩/解压(1001 如果存在), 取消(1001 或 1002)
    if result == 1000:
        action = "copy"
        print("[DEBUG] show_file_operations_dialog() 用户选择: 复制路径")
    elif result == 1001 and has_action_button:
        action = action_type
        print(f"[DEBUG] show_file_operations_dialog() 用户选择: {action_type}")
    else:
        action = None
        print("[DEBUG] show_file_operations_dialog() 用户选择: 取消")
    
    print(f"[DEBUG] show_file_operations_dialog() 返回: action={action}, alert={alert}")
    print("[DEBUG] show_file_operations_dialog() 退出")
    return action, alert
