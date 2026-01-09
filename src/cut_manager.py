#!/usr/bin/env python3
"""剪切管理器"""

import subprocess
from pathlib import Path
from cedar.utils import print


def _run_script(script: str, timeout: int = 5) -> str:
    """执行 AppleScript，返回输出"""
    try:
        r = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=timeout)
        print(f"[DEBUG] AppleScript returncode={r.returncode}")
        print(f"[DEBUG] stdout: {r.stdout[:200] if r.stdout else '(empty)'}")
        if r.stderr:
            print(f"[DEBUG] stderr: {r.stderr[:200]}")
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception as e:
        print(f"AppleScript 执行失败: {e}")
        return ""


def _escape(path: str) -> str:
    """转义路径中的特殊字符"""
    return path.replace('\\', '\\\\').replace('"', '\\"')


class CutManager:
    """剪切管理器"""
    
    def __init__(self, on_state_change=None):
        self.cut_files = []
        self.on_state_change = on_state_change
        self.last_selection = None  # 上一次选择的文件列表
        self.same_selection_count = 0  # 连续相同选择的次数
    
    @property
    def has_cut_files(self) -> bool:
        return bool(self.cut_files)
    
    @property
    def count(self) -> int:
        return len(self.cut_files)
    
    def get_finder_selection(self) -> list:
        """获取 Finder 选中的文件"""
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
        print("[DEBUG] 获取 Finder 选中文件...")
        output = _run_script(script)
        print(f"[DEBUG] 原始输出: '{output}'")
        if output:
            result = [p.strip() for p in output.split(', ') if p.strip()]
        else:
            result = []
        print(f"[DEBUG] 解析结果: {result}")
        return result
    
    def get_finder_current_folder(self) -> str:
        """获取 Finder 当前文件夹"""
        script = '''tell application "Finder"
            try
                return POSIX path of (insertion location as alias)
            on error
                try
                    if (count of windows) = 0 then return POSIX path of (path to desktop)
                    return POSIX path of (target of front window as alias)
                on error
                    return POSIX path of (path to desktop)
                end try
            end try
        end tell'''
        return _run_script(script)
    
    def _is_same_selection(self, current: list, last: list) -> bool:
        """判断两次选择是否相同（使用集合比较，忽略顺序）"""
        if not current or not last:
            return False
        return set(current) == set(last)
    
    def cut(self) -> tuple:
        """
        剪切选中的文件
        
        Returns:
            tuple: (success: bool, should_show_dialog: bool)
                - success: 是否成功剪切
                - should_show_dialog: 是否应该显示智能操作弹窗（连续两次相同选择）
        """
        files = self.get_finder_selection()
        if not files:
            print("未选中文件")
            self.last_selection = None
            self.same_selection_count = 0
            return False, False
        
        valid = [f for f in files if Path(f).exists()]
        if not valid:
            print("文件不存在")
            self.last_selection = None
            self.same_selection_count = 0
            return False, False
        
        # 比较当前选择和上一次选择
        if self._is_same_selection(valid, self.last_selection):
            self.same_selection_count += 1
        else:
            # 选择不同，重置计数
            self.same_selection_count = 1
        
        # 更新上一次选择
        self.last_selection = valid.copy()
        
        # 判断是否应该显示弹窗（连续两次相同选择）
        should_show_dialog = self.same_selection_count == 2
        
        # 如果是第二次相同选择，不执行剪切，只返回应该显示弹窗的标志
        if should_show_dialog:
            print(f"连续两次选择相同文件，触发智能操作")
            return True, True
        
        # 第三次及以后相同选择，保持静默
        if self.same_selection_count > 2:
            print(f"连续 {self.same_selection_count} 次选择相同文件，保持静默")
            return True, False
        
        # 第一次选择，执行剪切
        self.cut_files = valid
        print(f"已剪切 {len(valid)} 个文件")
        self._notify()
        return True, False
    
    def paste(self) -> tuple:
        """粘贴（移动）文件"""
        if not self.cut_files:
            return False, "没有待移动文件"
        
        target = self.get_finder_current_folder()
        if not target or not Path(target).exists():
            return False, "目标文件夹无效"
        
        files_str = ", ".join(f'POSIX file "{_escape(f)}"' for f in self.cut_files)
        script = f'''tell application "Finder"
            try
                move {{{files_str}}} to POSIX file "{_escape(target)}"
                return "OK"
            on error e
                return "Error: " & e
            end try
        end tell'''
        
        output = _run_script(script, timeout=30)
        if output == "OK":
            cnt = len(self.cut_files)
            self.cut_files = []
            self._notify()
            return True, f"已移动 {cnt} 个文件"
        return False, f"移动失败: {output}"
    
    def clear(self):
        """清空剪切列表"""
        self.cut_files = []
        self._notify()
        print("已清空")
    
    def _notify(self):
        if self.on_state_change:
            self.on_state_change(self.cut_files)
