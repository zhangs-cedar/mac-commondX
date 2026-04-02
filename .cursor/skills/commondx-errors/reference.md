# CommondX AI 错误模式 — 参考全文

本文件为错误模式库的**正文来源**；增删模式时请同时更新本文件与 [SKILL.md](SKILL.md) 中的检查清单（若适用）。

## 代码规范

- **PATTERN-001**: 路径处理  
  - **特征**: 使用 `+ '/'` 或 `+ '\\'` 拼接路径，或使用 `os.path.join()`  
  - **修正**: 使用 `pathlib.Path` 对象  
  - **示例**: `Path.home() / "Library/Application Support/App"`

- **PATTERN-002**: 类型提示简化  
  - **特征**: 使用 `Optional[str] = None` 等复杂类型提示  
  - **修正**: 简化为 `str = None`（项目 Python 3.8 约束下按 `.cursorrules`）  
  - **示例**: `def func(file: str = None) -> str:`

- **PATTERN-007**: 代码优化  
  - **特征**: 重复代码块、调试日志、深层嵌套条件、未用导入  
  - **修正**: 提取公共函数、删除调试日志、简化条件、清理导入  

## macOS 开发

- **PATTERN-003**: 通知 vs 弹窗  
  - **特征**: 用 `NSUserNotificationCenter` 展示重要信息  
  - **修正**: 重要信息用 `NSAlert`；通知仅后台提醒  

- **PATTERN-004**: 打包后路径  
  - **特征**: 用 `__file__` 定位可写配置  
  - **修正**: bundle 内只读；用户数据放 `~/Library/Application Support/`  

- **PATTERN-005**: Finder 检测  
  - **特征**: `target of front window` 取目标路径  
  - **修正**: 使用 `insertion location` 获取插入位置  

- **PATTERN-006**: 权限管理  
  - **特征**: 每次打包后需重新授权  
  - **修正**: 打包脚本可加 `tccutil reset Accessibility` 清除旧记录  

- **PATTERN-011**: PyObjC 命名冲突  
  - **特征**: NSObject 子类中 `_xxx` 被误认为 ObjC 访问器  
  - **修正**: 辅助方法提到类外为普通函数  

- **PATTERN-012**: AppleScript 格式敏感  
  - **特征**: 简化后返回空结果  
  - **修正**: 保持原始格式；先 `set` 再 `repeat`；三引号字符串后要有换行  

- **PATTERN-016**: Event Tap 恢复  
  - **特征**: 模态对话框后 Event Tap 停止  
  - **修正**: 五层防护（不激活应用、立即恢复、延迟恢复、回调恢复、重新创建）  

- **PATTERN-017**: NSAlert 输入框无法粘贴  
  - **特征**: NSTextField 不响应 ⌘+V  
  - **原因**: 缺少标准 Edit 菜单；快捷键经菜单路由到第一响应者  
  - **修正**: 创建标准应用菜单栏，含 Edit：`cut:`, `copy:`, `paste:`, `selectAll:`  
  - **参考**: `test/test_alert_input.py`  

```python
def setup_edit_menu(app):
    menubar = NSMenu.alloc().init()
    edit_menu = NSMenu.alloc().initWithTitle_("Edit")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Cut", "cut:", "x")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Copy", "copy:", "c")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Paste", "paste:", "v")
    edit_menu.addItemWithTitle_action_keyEquivalent_("Select All", "selectAll:", "a")
    app.setMainMenu_(menubar)
```

## 重构陷阱

- **PATTERN-013**: 函数返回值 — 必须接收 `obj = func(obj, ...)`  
- **PATTERN-014**: 导入语句 — 重构后验证 import 完整  
- **PATTERN-015**: 状态重置 — 「取消」保持状态；仅成功路径重置  

## Event Tap 五层防护（展开）

1. 弹窗时不 `activateIgnoringOtherApps`，Finder 保持活动  
2. 弹窗关闭后立即恢复 Tap  
3. 多次延迟恢复（50 / 100 / 200 ms）  
4. 回调入口检查并自动恢复  
5. 失败则完全重建 Tap  

## NSAlert 粘贴问题（展开）

**错误做法**: 用 `NSWindowDidBecomeKeyNotification`、NSTimer、手写粘贴。  
**正确做法**: 标准 Edit 菜单 + 系统路由。
