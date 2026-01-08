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
        str: 操作类型 "copy"、"compress"、"decompress" 或 None（取消）
    """
    NSApp.setActivationPolicy_(0)
    NSApp.activateIgnoringOtherApps_(True)
    
    alert = NSAlert.alloc().init()
    alert.setMessageText_("文件智能操作")
    
    # 统计信息
    total_count = len(files)
    archive_count = sum(1 for f in files if _is_archive_file(f))
    has_regular_files = any(not _is_archive_file(f) for f in files)
    
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
    elif has_regular_files:
        # 有普通文件/文件夹，显示压缩按钮
        alert.addButtonWithTitle_("压缩为 ZIP")
        has_action_button = True
        action_type = "compress"
    
    # 取消按钮
    alert.addButtonWithTitle_("取消")
    
    result = alert.runModal()
    NSApp.setActivationPolicy_(2)
    
    # 返回操作类型
    # 按钮顺序：复制路径(1000), 压缩/解压(1001 如果存在), 取消(1001 或 1002)
    if result == 1000:
        return "copy"
    elif result == 1001 and has_action_button:
        return action_type
    else:
        return None
