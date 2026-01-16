#!/usr/bin/env python3
"""
工具函数模块

提供各模块共用的工具函数，遵循 DRY 原则，提高代码复用性。
"""
import subprocess
import sys
from pathlib import Path
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


def get_resource_path(relative_path: str, base_file: str = None) -> Path:
    """
    获取资源文件路径（支持开发环境和打包后环境）
    
    自动检测运行环境：
    - 开发环境：使用 base_file 的父目录作为基准路径
    - 打包后：使用 sys._MEIPASS 作为基准路径，保持打包时的目录结构
    
    Args:
        relative_path: 相对于基准路径的资源文件路径，如 "assets/mermaid.min.js"
        base_file: 调用者的 __file__ 路径，如果为 None 则自动检测（使用调用栈）
        
    Returns:
        Path: 资源文件的完整路径
        
    Examples:
        # 在插件中使用（推荐）
        mermaid_path = get_resource_path("assets/mermaid.min.js", __file__)
        
        # 自动检测调用者位置
        mermaid_path = get_resource_path("assets/mermaid.min.js")
    """
    print(f"[DEBUG] [Utils] 获取资源路径: {relative_path}")
    
    # 如果没有指定 base_file，尝试从调用栈获取
    if base_file is None:
        import inspect
        try:
            frame = inspect.currentframe().f_back
            base_file = frame.f_globals.get('__file__')
            if base_file:
                print(f"[DEBUG] [Utils] 自动检测到调用者文件: {base_file}")
        except:
            pass
    
    # PyInstaller 打包后，资源文件在 sys._MEIPASS 目录
    if hasattr(sys, '_MEIPASS'):
        # 打包后：根据 base_file 判断资源位置
        # 如果 base_file 包含 'plugins'，说明是插件资源，使用 src/plugins/ 结构
        if base_file and 'plugins' in str(base_file):
            # 保持打包时的目录结构：sys._MEIPASS/src/plugins/
            base_path = Path(sys._MEIPASS) / "src" / "plugins"
        else:
            # 其他情况，使用 sys._MEIPASS 作为根目录
            base_path = Path(sys._MEIPASS)
        print(f"[DEBUG] [Utils] 打包环境，sys._MEIPASS={sys._MEIPASS}, base_path={base_path}")
    else:
        # 开发环境：使用 base_file 的父目录
        if base_file:
            base_path = Path(base_file).parent
        else:
            # 如果无法确定，使用当前工作目录
            base_path = Path.cwd()
        print(f"[DEBUG] [Utils] 开发环境，base_path={base_path}")
    
    resource_path = base_path / relative_path
    print(f"[DEBUG] [Utils] 资源路径: {resource_path}, 存在: {resource_path.exists()}")
    return resource_path






