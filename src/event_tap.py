#!/usr/bin/env python3
"""
全局快捷键监听 - Quartz Event Tap

【事件捕获机制说明】
Event Tap 是 macOS 提供的系统级事件拦截机制，可以捕获所有键盘和鼠标事件。
当用户按下键盘时，系统会先调用我们的 _callback 函数，我们可以：
1. 检查事件是否符合条件（如 Cmd+X）
2. 如果符合，执行我们的逻辑并返回 None（吞掉事件，阻止系统默认行为）
3. 如果不符合，返回原事件（放行事件，让系统正常处理）

【页面触发说明】
"页面触发"指的是 Finder 窗口成为活动窗口（前台应用）。
只有当 Finder 是当前活动应用时，我们才处理 Cmd+X 事件。
"""

import Quartz
from Quartz import (
    CGEventTapCreate, CGEventTapEnable, CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource, CFRunLoopGetCurrent, CGEventMaskBit,
    kCGSessionEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
    kCGEventKeyDown, CGEventGetIntegerValueField, kCGKeyboardEventKeycode
)
from AppKit import NSWorkspace
from cedar.utils import print
from .license_manager import license_manager

# 键码与修饰键
KEY_X, KEY_V = 7, 9
CMD, SHIFT, OPT = Quartz.kCGEventFlagMaskCommand, Quartz.kCGEventFlagMaskShift, Quartz.kCGEventFlagMaskAlternate
FINDER_ID = "com.apple.finder"


class EventTap:
    """
    全局快捷键监听器
    
    按照流程图顺序处理事件：
    1. 捕获键盘事件
    2. 检查是否为 Cmd+X
    3. 检查是否为 Finder 窗口
    4. 检查许可证
    5. 调用 on_cut 或 on_paste
    """
    
    def __init__(self, on_cut=None, on_paste=None, on_license_invalid=None):
        """
        初始化事件监听器
        
        Args:
            on_cut: Cmd+X 时的回调函数
            on_paste: Cmd+V 时的回调函数
            on_license_invalid: 许可证无效时的回调函数（用于显示激活提示）
        """
        self.on_cut = on_cut
        self.on_paste = on_paste
        self.on_license_invalid = on_license_invalid
        self.tap = None
        self.running = False
    
    def _is_finder_active(self) -> bool:
        """
        检查 Finder 是否为前台应用（活动窗口）
        
        【页面触发说明】
        这个方法检查当前"活动窗口"是否是 Finder。
        活动窗口就是用户当前正在使用的窗口，也就是"前台应用"。
        只有当 Finder 是活动窗口时，我们才处理 Cmd+X 事件。
        """
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        is_finder = app and app.bundleIdentifier() == FINDER_ID
        print(f"[2] [EventTap] 检查是否为 Finder 窗口 - 结果: {is_finder}")
        return is_finder
    
    def _callback(self, proxy, event_type, event, refcon):
        """
        事件回调函数
        
        【事件捕获说明】
        这是 Event Tap 的核心回调函数。每当系统有键盘事件时，都会先调用这个函数。
        我们可以在这里拦截事件，决定是"吞掉"（返回 None）还是"放行"（返回 event）。
        """
        # #region agent log - 在函数最开始就记录，确保即使出错也能看到
        import json, time
        try:
            with open('/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run2",
                    "hypothesisId": "D",
                    "location": "event_tap.py:_callback",
                    "message": "Event Tap 回调被调用（函数入口）",
                    "data": {"event_type": event_type, "timestamp": time.time()},
                    "timestamp": int(time.time() * 1000)
                }) + '\n')
        except Exception as e:
            print(f"[DEBUG LOG ERROR] {e}")
        # #endregion
        
        # 【关键修复】每次回调时都确保 Event Tap 已启用
        # 这样可以自动恢复被系统禁用的 Event Tap
        if self.running and self.tap:
            try:
                CGEventTapEnable(self.tap, True)
            except:
                pass  # 如果失败，继续执行，至少记录了这个事件
        
        try:
            # 【步骤 1】捕获键盘事件
            print(f"[1] [EventTap] 捕获键盘事件 - event_type={event_type}")
            
            # 只处理按键按下事件，忽略其他事件（如按键释放）
            if event_type != kCGEventKeyDown:
                print(f"[1] [EventTap] 非按键按下事件，放行 - event_type={event_type}")
                return event
            
            # 【步骤 2】检查是否为 Cmd+X 或 Cmd+V
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            print(f"[2] [EventTap] 检查按键 - keycode={keycode} (X=7, V=9)")
            
            if keycode not in (KEY_X, KEY_V):
                print(f"[2] [EventTap] 不是 X 或 V 键，放行事件")
                return event
            
            # 检查修饰键（必须按下 Cmd，不能同时按下 Shift 或 Option）
            flags = Quartz.CGEventGetFlags(event)
            has_cmd = bool(flags & CMD)
            has_shift = bool(flags & SHIFT)
            has_opt = bool(flags & OPT)
            print(f"[2] [EventTap] 检查修饰键 - Cmd={has_cmd}, Shift={has_shift}, Option={has_opt}")
            
            if not has_cmd or has_shift or has_opt:
                print(f"[2] [EventTap] 修饰键不符合要求，放行事件")
                return event
            
            print(f"[2] [EventTap] ✓ 确认为 Cmd+X 或 Cmd+V")
            
            # 【步骤 3】检查是否为 Finder 窗口
            is_finder = self._is_finder_active()
            # #region agent log
            import json, time
            try:
                with open('/Users/zhangsong/Desktop/code/cedar_dev/mac-commondX/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run2",
                        "hypothesisId": "B",
                        "location": "event_tap.py:_callback",
                        "message": "Finder 检查结果",
                        "data": {"is_finder": is_finder, "keycode": keycode, "timestamp": time.time()},
                        "timestamp": int(time.time() * 1000)
                    }) + '\n')
            except: pass
            # #endregion
            if not is_finder:
                print(f"[3] [EventTap] 不是 Finder 窗口，放行事件")
                return event
            
            print(f"[3] [EventTap] ✓ 确认为 Finder 窗口")
            
            # 【步骤 4】检查许可证（按照流程图，在确认 Finder 后立即检查）
            print(f"[4] [EventTap] 检查许可证...")
            if not license_manager.is_valid():
                print(f"[4] [EventTap] ✗ 许可证无效，显示激活提示")
                # 调用回调函数显示激活提示（由 app.py 传入）
                if self.on_license_invalid:
                    self.on_license_invalid()
                # 放行事件，让系统正常处理（不吞掉事件）
                return event
            
            print(f"[4] [EventTap] ✓ 许可证有效")
            
            # 【步骤 5】调用对应的处理函数
            handler = self.on_cut if keycode == KEY_X else self.on_paste
            if handler:
                print(f"[5] [EventTap] 调用处理函数 - {'on_cut' if keycode == KEY_X else 'on_paste'}")
                if handler():
                    print(f"[5] [EventTap] 处理函数返回 True，吞掉事件（阻止系统默认行为）")
                    return None  # 吞掉事件，阻止系统默认的剪切/粘贴行为
                else:
                    print(f"[5] [EventTap] 处理函数返回 False，放行事件")
            else:
                print(f"[5] [EventTap] 未设置处理函数，放行事件")
                
        except Exception as e:
            print(f"[ERROR] [EventTap] 事件回调错误: {e}")
            import traceback
            print(traceback.format_exc())
        
        return event
    
    def start(self) -> bool:
        """
        启动事件监听
        
        【工作原理】
        1. 创建 Event Tap，注册回调函数
        2. 将 Event Tap 添加到系统的运行循环中
        3. 启用 Event Tap，开始捕获事件
        
        注意：需要用户在"系统设置 > 隐私与安全性 > 辅助功能"中授权。
        """
        if self.running:
            print("[EventTap] 已在运行，跳过启动")
            return True
        
        print("[EventTap] 正在创建 Event Tap...")
        self.tap = CGEventTapCreate(
            kCGSessionEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
            CGEventMaskBit(kCGEventKeyDown), self._callback, None
        )
        if not self.tap:
            print("[ERROR] [EventTap] 无法创建 Event Tap，检查辅助功能权限")
            return False
        
        print("[EventTap] Event Tap 创建成功，添加到运行循环...")
        source = CFMachPortCreateRunLoopSource(None, self.tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, Quartz.kCFRunLoopCommonModes)
        CGEventTapEnable(self.tap, True)
        
        self.running = True
        print("[EventTap] ✓ Event Tap 已启动，开始监听键盘事件")
        return True
    
    def ensure_enabled(self):
        """
        确保 Event Tap 已启用
        
        【问题说明】
        macOS 在显示模态对话框时可能会自动禁用 Event Tap。
        这个方法检查 Event Tap 是否仍然启用，如果没有则重新启用。
        如果重新启用失败，则完全重新创建 Event Tap。
        """
        if not self.running:
            print("[EventTap] Event Tap 未运行，无法确保启用")
            return False
        
        # 如果 tap 对象不存在，需要重新创建
        if not self.tap:
            print("[EventTap] Event Tap 对象不存在，重新创建...")
            return self._recreate_tap()
        
        # 尝试重新启用 Event Tap
        try:
            CGEventTapEnable(self.tap, True)
            print("[EventTap] ✓ Event Tap 已重新启用")
            return True
        except Exception as e:
            print(f"[EventTap] 重新启用 Event Tap 失败: {e}，尝试重新创建...")
            return self._recreate_tap()
    
    def _recreate_tap(self):
        """
        重新创建 Event Tap
        
        当 Event Tap 被系统禁用且无法恢复时，完全重新创建它。
        """
        print("[EventTap] 开始重新创建 Event Tap...")
        
        # 先停止旧的（如果存在）
        if self.tap:
            try:
                CGEventTapEnable(self.tap, False)
            except:
                pass
            self.tap = None
        
        # 重新创建
        self.tap = CGEventTapCreate(
            kCGSessionEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
            CGEventMaskBit(kCGEventKeyDown), self._callback, None
        )
        if not self.tap:
            print("[ERROR] [EventTap] 无法重新创建 Event Tap，检查辅助功能权限")
            self.running = False
            return False
        
        # 重新添加到运行循环
        source = CFMachPortCreateRunLoopSource(None, self.tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, Quartz.kCFRunLoopCommonModes)
        CGEventTapEnable(self.tap, True)
        
        print("[EventTap] ✓ Event Tap 已重新创建并启用")
        return True
    
    def stop(self):
        """停止事件监听"""
        if self.tap:
            print("[EventTap] 正在停止 Event Tap...")
            CGEventTapEnable(self.tap, False)
            self.tap = None
        self.running = False
        print("[EventTap] ✓ Event Tap 已停止")
