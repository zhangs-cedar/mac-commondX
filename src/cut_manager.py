#!/usr/bin/env python3
"""
剪切管理器

【状态跟踪机制说明】
这个类负责跟踪用户的选择状态，判断是否应该显示智能操作弹窗。

核心逻辑：
1. 记录上一次选择的文件列表（last_selection）
2. 每次 cut() 时，比较当前选择和上一次选择
3. 如果选择相同 → 返回 (True, True)，触发智能操作弹窗
4. 如果选择不同 → 执行剪切，更新 cut_files，返回 (True, False)

【选择比较机制】
使用 set() 比较文件列表，忽略顺序。例如：
- ["file1", "file2"] 和 ["file2", "file1"] 被视为相同
- 空列表 [] 和 None 被视为相同（都是空选择）
"""

from pathlib import Path
from cedar.utils import print
from .utils import run_script, escape_path


class CutManager:
    """
    剪切管理器
    
    负责：
    1. 获取 Finder 选中的文件
    2. 跟踪选择状态（比较当前选择和上一次选择）
    3. 执行剪切操作（更新 cut_files）
    4. 执行粘贴操作（移动文件）
    """
    
    def __init__(self, on_state_change=None):
        self.cut_files = []  # 已剪切的文件列表（用于粘贴）
        self.on_state_change = on_state_change  # 状态变化回调
        self.last_selection = None  # 上一次选择的文件列表（用于判断是否显示弹窗）
    
    @property
    def has_cut_files(self) -> bool:
        return bool(self.cut_files)
    
    @property
    def count(self) -> int:
        return len(self.cut_files)
    
    def get_finder_selection(self) -> list:
        """
        获取 Finder 当前选中的文件列表
        
        使用 AppleScript 与 Finder 通信，获取用户选中的文件路径。
        如果没有选中文件，返回空列表 []。
        """
        print("[6.1] [CutManager] 获取 Finder 选中文件...")
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
        output = run_script(script)
        if output:
            result = [p.strip() for p in output.split(', ') if p.strip()]
        else:
            result = []
        print(f"[6.1] [CutManager] 获取到 {len(result)} 个文件: {result}")
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
        return run_script(script)
    
    def _is_same_selection(self, current: list, last: list) -> bool:
        """
        判断两次选择是否相同
        
        【选择比较机制】
        使用 set() 比较文件列表，忽略顺序。例如：
        - ["file1", "file2"] 和 ["file2", "file1"] → 相同
        - [] 和 None → 相同（都视为空选择）
        - ["file1"] 和 ["file2"] → 不同
        
        Args:
            current: 当前选择的文件列表
            last: 上一次选择的文件列表（可能是 None）
            
        Returns:
            bool: 如果选择相同返回 True，否则返回 False
        """
        # 空列表和 None 都视为空选择
        if not current and not last:
            print("[6.2] [CutManager] 选择比较: 都是空选择，视为相同")
            return True
        if not current or not last:
            print(f"[6.2] [CutManager] 选择比较: 一个为空一个不为空，不同")
            return False
        
        is_same = set(current) == set(last)
        print(f"[6.2] [CutManager] 选择比较: current={set(current)}, last={set(last)}, 结果={is_same}")
        return is_same
    
    def cut(self) -> tuple:
        """
        处理文件选择（按照流程图逻辑）
        
        【工作流程】
        1. 获取 Finder 选中的文件
        2. 比较当前选择和上一次选择
        3. 更新 last_selection（记录当前选择）
        4. 如果没有文件 → 返回 (False, False)
        5. 如果选择相同 → 返回 (True, True)，触发智能操作弹窗
        6. 如果选择不同 → 执行剪切，更新 cut_files，返回 (True, False)
        
        Returns:
            tuple: (success: bool, should_show_dialog: bool)
                - success: 是否成功处理（有文件且有效）
                - should_show_dialog: 是否应该显示智能操作弹窗（选择与上次相同）
        """
        print("[6] [CutManager] cut() 开始处理文件选择")
        
        # 【步骤 6.1】获取 Finder 选中的文件
        files = self.get_finder_selection()
        
        # 如果没有选中文件，记录空列表
        if not files:
            files = []
        
        # 【步骤 6.2】比较当前选择和上一次选择
        print(f"[6.2] [CutManager] 比较选择 - current={files}, last={self.last_selection}")
        is_same = self._is_same_selection(files, self.last_selection)
        
        # 【步骤 6.3】更新 last_selection（记录当前选择，不管文件是否存在）
        old_last_selection = self.last_selection
        self.last_selection = files.copy() if files else []
        print(f"[6.3] [CutManager] 更新 last_selection: {old_last_selection} -> {self.last_selection}")
        
        # 【步骤 6.4】如果没有文件，不执行任何操作
        if not files:
            print("[6.4] [CutManager] 未选中文件，返回 (False, False)")
            return False, False
        
        # 【步骤 6.5】验证文件是否存在（只在执行剪切时验证，弹窗时不需要验证）
        valid = [f for f in files if Path(f).exists()]
        if not valid:
            print("[6.5] [CutManager] 文件不存在，返回 (False, False)")
            return False, False
        
        # 【步骤 6.6】如果选择相同，触发智能操作弹窗
        if is_same:
            print("[6.6] [CutManager] 选择与上次相同，触发智能操作弹窗")
            print("[6.6] [CutManager] 返回 (True, True)")
            return True, True
        
        # 【步骤 6.7】选择不同，执行剪切操作
        print("[6.7] [CutManager] 选择不同，执行剪切操作")
        self.cut_files = valid
        print(f"[6.7] [CutManager] 更新 cut_files: {len(valid)} 个文件")
        # #region agent log
        import json, time
        try:
            with open('/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run2",
                    "hypothesisId": "F",
                    "location": "cut_manager.py:cut",
                    "message": "执行剪切操作，更新 cut_files",
                    "data": {"cut_files_count": len(valid), "cut_files": valid, "timestamp": time.time()},
                    "timestamp": int(time.time() * 1000)
                }) + '\n')
        except: pass
        # #endregion
        self._notify()
        print("[6.7] [CutManager] 返回 (True, False)")
        return True, False
    
    def paste(self) -> tuple:
        """粘贴（移动）文件"""
        if not self.cut_files:
            return False, "没有待移动文件"
        
        target = self.get_finder_current_folder()
        if not target or not Path(target).exists():
            return False, "目标文件夹无效"
        
        files_str = ", ".join(f'POSIX file "{escape_path(f)}"' for f in self.cut_files)
        script = f'''tell application "Finder"
            try
                move {{{files_str}}} to POSIX file "{escape_path(target)}"
                return "OK"
            on error e
                return "Error: " & e
            end try
        end tell'''
        
        output = run_script(script, timeout=30)
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
