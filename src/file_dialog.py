#!/usr/bin/env python3
"""
文件操作对话框

【模态对话框说明】
模态对话框（Modal Dialog）是一种特殊的窗口，它会：
1. 阻塞当前线程，直到用户关闭对话框
2. runModal() 方法会一直等待，直到用户点击按钮
3. 用户点击按钮后，runModal() 返回按钮的返回值
4. 在 runModal() 返回之前，代码不会继续执行

这就是为什么在 app.py 中，show_file_operations_dialog() 调用后，
代码会"暂停"，直到用户选择操作。
"""

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
    显示文件智能操作弹窗
    
    【模态对话框工作原理】
    1. 创建 NSAlert 对象
    2. 添加按钮（复制路径、压缩/解压、取消）
    3. 调用 runModal() - 这会阻塞代码执行，直到用户点击按钮
    4. runModal() 返回按钮的返回值（1000=第一个按钮，1001=第二个按钮，等等）
    5. 根据返回值判断用户选择的操作
    
    Args:
        files: 文件路径列表
        
    Returns:
        tuple: (action: str, alert: NSAlert)
            - action: 操作类型 "copy"、"compress"、"decompress" 或 None（取消）
            - alert: 弹窗引用（虽然弹窗已关闭，但保留引用以便统一处理）
    """
    from cedar.utils import print
    
    print("[7.2] [FileDialog] show_file_operations_dialog() 开始创建弹窗")
    print(f"[7.2] [FileDialog] 文件列表: {len(files)} 个文件")
    
    # 【关键修复】不激活应用，避免影响 Event Tap
    # 只临时改变激活策略，不强制激活应用
    # 这样弹窗仍然可以显示，但不会让应用成为活动窗口，Finder 保持为活动窗口
    original_policy = NSApp.activationPolicy()
    if original_policy == 2:  # NSApplicationActivationPolicyAccessory
        NSApp.setActivationPolicy_(0)  # NSApplicationActivationPolicyRegular
    # 不调用 activateIgnoringOtherApps，保持 Finder 为活动窗口
    
    alert = NSAlert.alloc().init()
    alert.setMessageText_("文件智能操作")
    
    # 统计文件类型
    total_count = len(files)
    archive_count = sum(1 for f in files if _is_archive_file(f))
    has_regular_files = any(not _is_archive_file(f) for f in files)
    print(f"[7.2] [FileDialog] 文件统计 - 总数={total_count}, 压缩文件={archive_count}, 有普通文件={has_regular_files}")
    
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
    
    # 【步骤 7.2.1】智能添加操作按钮
    # 始终显示"复制路径"按钮（第一个按钮，返回值 1000）
    alert.addButtonWithTitle_("复制路径")
    print("[7.2.1] [FileDialog] 添加按钮: 复制路径")
    
    # 根据文件类型智能显示第二个按钮
    has_action_button = False
    action_type = None
    if archive_count > 0 and archive_count == total_count:
        # 全部是压缩文件，显示解压按钮
        alert.addButtonWithTitle_("智能解压")
        has_action_button = True
        action_type = "decompress"
        print("[7.2.1] [FileDialog] 添加按钮: 智能解压（全部是压缩文件）")
    elif has_regular_files:
        # 有普通文件/文件夹，显示压缩按钮
        alert.addButtonWithTitle_("压缩为 ZIP")
        has_action_button = True
        action_type = "compress"
        print("[7.2.1] [FileDialog] 添加按钮: 压缩为 ZIP（有普通文件）")
    
    # 取消按钮（最后一个按钮）
    alert.addButtonWithTitle_("取消")
    print("[7.2.1] [FileDialog] 添加按钮: 取消")
    print(f"[7.2.1] [FileDialog] 按钮配置完成 - has_action_button={has_action_button}, action_type={action_type}")
    
    # 【步骤 7.2.2】显示弹窗（runModal 是阻塞的）
    # 【重要】runModal() 会阻塞代码执行，直到用户点击按钮
    # 用户点击按钮后，runModal() 返回按钮的返回值：
    # - 1000 = 第一个按钮（复制路径）
    # - 1001 = 第二个按钮（压缩/解压，如果存在）或取消
    # - 1002 = 第三个按钮（取消，如果有第二个按钮）
    print("[7.2.2] [FileDialog] 调用 runModal() - 代码将在此处暂停，等待用户操作...")
    result = alert.runModal()
    print(f"[7.2.2] [FileDialog] runModal() 返回 - result={result}（用户已选择）")
    
    # 恢复应用策略
    NSApp.setActivationPolicy_(original_policy)
    
    # 【关键修复】由于没有激活应用，Finder 应该仍然是活动窗口
    # 验证一下确保 Finder 是活动窗口
    from AppKit import NSWorkspace
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    is_finder = app and app.bundleIdentifier() == "com.apple.finder"
    if not is_finder:
        print(f"[7.2.2] [FileDialog] 警告：Finder 不是活动窗口，当前应用: {app.bundleIdentifier() if app else None}")
        # 如果 Finder 不是活动窗口，尝试恢复（虽然理论上不应该发生）
        import subprocess
        try:
            subprocess.run(['osascript', '-e', 'tell application "Finder" to activate'], 
                          timeout=2, capture_output=True)
            print("[7.2.2] [FileDialog] ✓ Finder 已恢复为活动窗口")
        except Exception as e:
            print(f"[7.2.2] [FileDialog] ✗ 恢复 Finder 失败: {e}")
    else:
        print("[7.2.2] [FileDialog] ✓ Finder 仍然是活动窗口（未激活应用）")
    
    # 【关键修复】弹窗关闭后，确保 Event Tap 仍然启用
    # macOS 在显示模态对话框时可能会自动禁用 Event Tap
    # 需要在弹窗关闭后重新启用
    print("[7.2.2] [FileDialog] 确保 Event Tap 已启用...")
    # 注意：这里无法直接访问 event_tap 实例，需要在 app.py 中处理
    
    # 【步骤 7.2.3】根据返回值判断用户选择的操作
    if result == 1000:
        action = "copy"
        print("[7.2.3] [FileDialog] 用户选择: 复制路径")
    elif result == 1001 and has_action_button:
        action = action_type
        print(f"[7.2.3] [FileDialog] 用户选择: {action_type}")
    else:
        action = None
        print("[7.2.3] [FileDialog] 用户选择: 取消")
    
    print(f"[7.2] [FileDialog] 弹窗处理完成，返回 action={action}")
    return action, alert
