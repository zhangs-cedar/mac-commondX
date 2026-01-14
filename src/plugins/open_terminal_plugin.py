#!/usr/bin/env python3
"""
打开终端插件

打开 Terminal 应用，并切换到选中文件的上一级目录。
"""

from pathlib import Path
from cedar.utils import print
from ..utils import run_script, escape_path


def execute(files: list) -> tuple:
    """
    打开终端并切换到选中文件的上一级目录
    
    Args:
        files: 文件路径列表
        
    Returns:
        tuple: (success: bool, message: str, None)
    """
    print(f"[DEBUG] [OpenTerminalPlugin] 开始打开终端，文件数量={len(files) if files else 0}")
    try:
        if not files:
            print("[ERROR] [OpenTerminalPlugin] 没有选中文件")
            return False, "没有选中文件", None
        
        # 获取第一个文件的上一级目录（多个文件时使用第一个文件的目录）
        first_file = Path(files[0])
        if not first_file.exists():
            print(f"[ERROR] [OpenTerminalPlugin] 文件不存在: {first_file}")
            return False, "文件不存在", None
        
        # 获取上一级目录
        parent_dir = first_file.parent
        parent_dir_path = str(parent_dir.absolute())
        print(f"[DEBUG] [OpenTerminalPlugin] 目标目录: {parent_dir_path}")
        
        # 转义路径中的特殊字符
        escaped_path = escape_path(parent_dir_path)
        
        # 使用 AppleScript 打开 Terminal 并切换到目录
        script = f'''
        tell application "Terminal"
            activate
            do script "cd \\"{escaped_path}\\""
        end tell
        '''
        
        result = run_script(script, timeout=10)
        
        # AppleScript 执行成功（Terminal 打开可能没有输出）
        if result is not None or result == "":
            count = len(files)
            msg = f"已在终端打开目录" if count == 1 else f"已在终端打开目录（基于第一个文件）"
            print(f"[DEBUG] [OpenTerminalPlugin] ✓ 终端已打开，目录: {parent_dir_path}")
            return True, msg, None
        else:
            print(f"[ERROR] [OpenTerminalPlugin] 打开终端失败")
            return False, "打开终端失败", None
    
    except Exception as e:
        print(f"[ERROR] [OpenTerminalPlugin] 打开终端失败: {e}")
        return False, f"打开终端失败：{str(e)}", None
