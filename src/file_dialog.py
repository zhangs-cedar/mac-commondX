#!/usr/bin/env python3
"""文件操作对话框"""

from AppKit import (
    NSAlert, NSTextView, NSScrollView, NSApp, NSFont,
    NSSize, NSRect, NSPoint
)


def show_file_operations_dialog(files):
    """
    显示文件操作弹窗（可扩展）
    
    Args:
        files: 文件路径列表
        
    Returns:
        bool: True 表示用户点击了"复制路径"，False 表示取消
    """
    NSApp.setActivationPolicy_(0)
    NSApp.activateIgnoringOtherApps_(True)
    
    alert = NSAlert.alloc().init()
    alert.setMessageText_("文件智能操作")
    
    # 显示最多5个路径
    MAX_DISPLAY = 5
    display_files = files[:MAX_DISPLAY]
    total_count = len(files)
    
    # 构建显示文本
    paths_text = "\n".join(display_files)
    if total_count > MAX_DISPLAY:
        paths_text += f"\n\n... 还有 {total_count - MAX_DISPLAY} 个文件"
    
    alert.setInformativeText_(f"已选中 {total_count} 个文件/文件夹")
    
    # 创建可滚动的文本视图
    scroll_view = NSScrollView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(500, 200)))
    text_view = NSTextView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(480, 0)))
    text_view.setString_(paths_text)
    text_view.setFont_(NSFont.monospacedSystemFontOfSize_weight_(11, 0))
    text_view.setEditable_(False)
    text_view.setSelectable_(True)
    text_view.setDrawsBackground_(True)
    text_view.setVerticallyResizable_(True)
    text_view.setHorizontallyResizable_(False)
    text_view.textContainer().setContainerSize_(NSSize(480, 1e7))
    text_view.textContainer().setWidthTracksTextView_(True)
    
    # 根据内容调整文本视图高度
    text_view.sizeToFit()
    content_height = text_view.frame().size.height
    if content_height > 200:
        content_height = 200
    
    text_view.setFrame_(NSRect(NSPoint(0, 0), NSSize(480, content_height)))
    
    scroll_view.setDocumentView_(text_view)
    scroll_view.setHasVerticalScroller_(True)
    scroll_view.setAutohidesScrollers_(True)
    scroll_view.setBorderType_(1)  # NSBezelBorder
    
    alert.setAccessoryView_(scroll_view)
    
    # 添加操作按钮（可扩展）
    alert.addButtonWithTitle_("复制路径")
    alert.addButtonWithTitle_("取消")
    
    result = alert.runModal()
    NSApp.setActivationPolicy_(2)
    
    # 返回操作结果：1000=复制路径, 1001=取消
    return result == 1000
