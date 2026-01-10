#!/usr/bin/env python3
"""
工具函数模块

提供各模块共用的工具函数，遵循 DRY 原则，提高代码复用性。
"""

import os
import subprocess
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


def is_directory(path: str) -> bool:
    """
    判断路径是否为文件夹
    
    Args:
        path: 文件路径
        
    Returns:
        bool: 如果是文件夹返回 True，否则返回 False
    """
    try:
        result = os.path.isdir(path)
        print(f"[DEBUG] [Utils] 判断路径类型: {path} -> {'文件夹' if result else '文件'}")
        return result
    except Exception as e:
        print(f"[ERROR] [Utils] 判断路径类型失败: {e}")
        return False


def is_archive_file(path: str) -> bool:
    """
    判断路径是否为压缩文件
    
    通过检查文件扩展名判断是否为压缩文件。
    
    Args:
        path: 文件路径
        
    Returns:
        bool: 如果是压缩文件返回 True，否则返回 False
    """
    if is_directory(path):
        print(f"[DEBUG] [Utils] 路径是文件夹，不是压缩文件: {path}")
        return False
    
    ext = Path(path).suffix.lower()
    archive_extensions = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tgz', '.tar.gz', '.tar.bz2'}
    result = ext in archive_extensions or any(path.lower().endswith(ext) for ext in archive_extensions)
    print(f"[DEBUG] [Utils] 判断压缩文件: {path} (扩展名={ext}) -> {result}")
    return result


def format_paths_list(files: list) -> str:
    """
    格式化路径列表，每行一个路径，添加图标前缀
    
    文件夹添加 📁 图标，文件添加 📄 图标。
    
    Args:
        files: 文件路径列表
        
    Returns:
        str: 格式化后的路径列表字符串
    """
    print(f"[DEBUG] [Utils] 格式化路径列表，文件数量={len(files)}")
    lines = []
    for path in files:
        if is_directory(path):
            lines.append(f"📁 {path}")
        else:
            lines.append(f"📄 {path}")
    result = "\n".join(lines)
    print(f"[DEBUG] [Utils] 格式化完成，结果长度={len(result)}")
    return result


def detect_archive_type(archive_path: str) -> str:
    """
    检测压缩文件类型
    
    通过检查文件头和扩展名来判断压缩文件类型。
    支持 ZIP、TAR、GZ、BZ2、RAR、7Z 等格式。
    
    Args:
        archive_path: 压缩文件路径
        
    Returns:
        str: 压缩文件类型（'zip'、'tar'、'gz'、'bz2'、'rar'、'7z' 等），如果无法识别返回 None
    """
    print(f"[DEBUG] [Utils] 检测压缩文件类型: {archive_path}")
    path = Path(archive_path)
    ext = path.suffix.lower()
    
    # 检查文件头
    try:
        with open(archive_path, 'rb') as f:
            header = f.read(4)
        
        print(f"[DEBUG] [Utils] 文件头: {header[:4]}")
        
        # ZIP 文件头：PK\x03\x04
        if header[:2] == b'PK':
            print(f"[DEBUG] [Utils] 检测到 ZIP 文件")
            return 'zip'
        
        # TAR 文件头
        if header == b'ustar' or b'ustar' in header:
            print(f"[DEBUG] [Utils] 检测到 TAR 文件")
            return 'tar'
        
        # GZ 文件头：\x1f\x8b
        if header[:2] == b'\x1f\x8b':
            print(f"[DEBUG] [Utils] 检测到 GZ 文件")
            return 'gz'
        
        # RAR 文件头：Rar!
        if header == b'Rar!':
            print(f"[DEBUG] [Utils] 检测到 RAR 文件")
            return 'rar'
        
        # 7Z 文件头：7z\xbc\xaf
        if header[:4] == b'7z\xbc\xaf':
            print(f"[DEBUG] [Utils] 检测到 7Z 文件")
            return '7z'
    except Exception as e:
        print(f"[ERROR] [Utils] 读取文件头失败: {e}")
    
    # 根据扩展名判断
    print(f"[DEBUG] [Utils] 根据扩展名判断: {ext}")
    if ext == '.zip':
        return 'zip'
    elif ext in ['.tar', '.tgz']:
        return 'tar'
    elif ext in ['.gz', '.tar.gz']:
        return 'gz'
    elif ext == '.rar':
        return 'rar'
    elif ext == '.7z':
        return '7z'
    elif ext in ['.bz2', '.tar.bz2']:
        return 'bz2'
    
    print(f"[DEBUG] [Utils] 无法识别压缩文件类型")
    return None
