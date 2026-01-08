#!/usr/bin/env python3
"""剪切管理器 - 管理剪切文件列表和状态"""

import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Callable
from cedar.utils import print


class CutManager:
    """剪切管理器"""
    
    def __init__(self, on_state_change: Optional[Callable] = None):
        self.cut_files: List[str] = []  # 待移动的文件列表
        self.on_state_change = on_state_change  # 状态变化回调
    
    @property
    def has_cut_files(self) -> bool:
        """是否有待移动的文件"""
        return len(self.cut_files) > 0
    
    @property
    def count(self) -> int:
        """待移动文件数量"""
        return len(self.cut_files)
    
    def get_finder_selection(self) -> List[str]:
        """获取 Finder 当前选中的文件"""
        script = '''
        tell application "Finder"
            set selectedItems to selection
            set pathList to {}
            repeat with itemRef in selectedItems
                set itemPath to POSIX path of (itemRef as alias)
                copy itemPath to end of pathList
            end repeat
            return pathList
        end tell
        '''
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                # 解析返回的路径列表
                paths = result.stdout.strip()
                if paths:
                    # AppleScript 返回格式: path1, path2, ...
                    return [p.strip() for p in paths.split(', ') if p.strip()]
        except Exception as e:
            print(f"获取 Finder 选中文件失败: {e}")
        return []
    
    def get_finder_current_folder(self) -> str:
        """获取 Finder 当前打开的文件夹路径（支持桌面）"""
        script = '''
        tell application "Finder"
            try
                -- 没有打开窗口时，默认为桌面
                if (count of windows) = 0 then
                    return POSIX path of (path to desktop)
                end if
                set frontWindow to front window
                -- 检测桌面窗口
                if name of frontWindow is "桌面" or name of frontWindow is "Desktop" then
                    return POSIX path of (path to desktop)
                end if
                return POSIX path of (target of frontWindow as alias)
            on error
                return POSIX path of (path to desktop)
            end try
        end tell
        '''
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            print(f"获取当前文件夹失败: {e}")
        return ""
    
    def cut(self) -> bool:
        """执行剪切操作 - 记录选中的文件"""
        files = self.get_finder_selection()
        if not files:
            print("未选中任何文件")
            return False
            
        # 验证文件存在
        valid_files = [f for f in files if Path(f).exists()]
        if valid_files:
            self.cut_files = valid_files
            print(f"已剪切 {len(valid_files)} 个文件")
            self._notify_state_change()
            return True
        
        print("选中的文件不存在")
        return False
    
    def paste(self) -> Tuple[bool, str]:
        """执行粘贴操作 - 移动文件到目标位置 (使用 Finder 原生移动)"""
        print(f"[CutManager] Starting paste. Cut files: {self.cut_files}")
        if not self.cut_files:
            print("[CutManager] No files to move")
            return False, "没有待移动的文件"
        
        target_folder = self.get_finder_current_folder()
        print(f"[CutManager] Target folder: {target_folder}")
        if not target_folder:
            print("[CutManager] Could not get target folder")
            return False, "无法获取目标文件夹"
            
        if not Path(target_folder).exists():
             print("[CutManager] Target folder does not exist")
             return False, "目标文件夹不存在"

        # 构造 AppleScript
        def escape_path(path):
            return path.replace('\\', '\\\\').replace('"', '\\"')

        files_list = [f'POSIX file "{escape_path(f)}"' for f in self.cut_files]
        files_str = ", ".join(files_list)
        
        script = f'''
        tell application "Finder"
            try
                set sourceFiles to {{{files_str}}}
                set targetFolder to POSIX file "{escape_path(target_folder)}"
                move sourceFiles to targetFolder
                return "OK"
            on error errMsg number errNum
                return "Error: " & errMsg
            end try
        end tell
        '''
        
        print(f"[CutManager] Running AppleScript to move files...")
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, text=True, timeout=30
            )
            
            output = result.stdout.strip()
            print(f"[CutManager] AppleScript result: {output}")
            
            if output == "OK":
                count = len(self.cut_files)
                self.cut_files = []
                self._notify_state_change()
                return True, f"已移动 {count} 个文件"
            else:
                print(f"[CutManager] Move failed: {output}")
                return False, f"移动失败: {output}"
                
        except Exception as e:
            print(f"[CutManager] Exception during move: {e}")
            return False, f"执行出错: {str(e)}"
    
    def clear(self):
        """清空剪切列表"""
        self.cut_files = []
        self._notify_state_change()
        print("已清空剪切列表")
    
    def _notify_state_change(self):
        """通知状态变化"""
        if self.on_state_change:
            self.on_state_change(self.cut_files)
