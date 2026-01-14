#!/usr/bin/env python3
"""
工具函数模块

提供各模块共用的工具函数，遵循 DRY 原则，提高代码复用性。
"""
import subprocess
from cedar.utils import print


def run_script(script: str, timeout: int = 5) -> str:
    """
    执行 AppleScript，返回输出
    
    Args:
        script: AppleScript 脚本内容
        timeout: 超时时间（秒），默认 5 秒
        
    Returns:
        str: 脚本输出，如果执行失败返回空字符串
    """
    print(f"[DEBUG] [Utils] 执行 AppleScript，timeout={timeout}")
    try:
        r = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=timeout)
        print(f"[DEBUG] [Utils] AppleScript returncode={r.returncode}")
        print(f"[DEBUG] [Utils] stdout: {r.stdout[:200] if r.stdout else '(empty)'}")
        if r.stderr:
            print(f"[DEBUG] [Utils] stderr: {r.stderr[:200]}")
        result = r.stdout.strip() if r.returncode == 0 else ""
        print(f"[DEBUG] [Utils] AppleScript 执行完成，返回结果长度={len(result)}")
        return result
    except Exception as e:
        print(f"[ERROR] [Utils] AppleScript 执行失败: {e}")
        return ""


def escape_path(path: str) -> str:
    """
    转义路径中的特殊字符
    
    用于 AppleScript 中处理包含特殊字符的路径。
    
    Args:
        path: 需要转义的路径字符串
        
    Returns:
        str: 转义后的路径字符串
    """
    print(f"[DEBUG] [Utils] 转义路径: {path}")
    escaped = path.replace('\\', '\\\\').replace('"', '\\"')
    print(f"[DEBUG] [Utils] 转义后: {escaped}")
    return escaped


def copy_to_clipboard(text: str):
    """
    复制文本到剪贴板
    
    Args:
        text: 要复制的文本内容
    """
    print(f"[DEBUG] [Utils] 复制到剪贴板，文本长度={len(text)}")
    from AppKit import NSPasteboard, NSStringPboardType
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, NSStringPboardType)
    print(f"[DEBUG] [Utils] ✓ 已复制到剪贴板")


def get_clipboard_content() -> str:
    """
    读取剪贴板内容
    
    Returns:
        str: 剪贴板文本内容，如果读取失败返回空字符串
    """
    print(f"[DEBUG] [Utils] 读取剪贴板内容...")
    try:
        from AppKit import NSPasteboard, NSStringPboardType
        pb = NSPasteboard.generalPasteboard()
        content = pb.stringForType_(NSStringPboardType)
        if content:
            print(f"[DEBUG] [Utils] ✓ 剪贴板内容已读取，长度={len(content)}")
            return content
        else:
            print(f"[DEBUG] [Utils] 剪贴板内容为空")
            return ""
    except Exception as e:
        print(f"[ERROR] [Utils] 读取剪贴板失败: {e}")
        return ""






