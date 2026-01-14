#!/usr/bin/env python3
"""
全局快捷键监听 - Quartz Event Tap

修复说明：
1. 确保 ⌘+C 事件被捕获后立即返回原事件（return event），不干扰系统剪贴板写入。
2. 增加了对 Event Tap 被系统意外禁用时的自动恢复逻辑（_recreate_tap）。
3. 严格区分 Finder 逻辑（X/V）与全局逻辑（C）。
"""

import time
import Quartz
from Quartz import (
    CGEventTapCreate, CGEventTapEnable, CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource, CFRunLoopGetCurrent, CGEventMaskBit,
    kCGSessionEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
    kCGEventKeyDown, CGEventGetIntegerValueField, kCGKeyboardEventKeycode,
    kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput
)
from AppKit import NSWorkspace
from cedar.utils import print
from .license_manager import license_manager

# 键码定义
KEY_X = 7
KEY_C = 8
KEY_V = 9
CMD = Quartz.kCGEventFlagMaskCommand
# 排除掉 Shift 和 Option，只识别纯 ⌘+Key
EXCLUDE_FLAGS = Quartz.kCGEventFlagMaskShift | Quartz.kCGEventFlagMaskAlternate

class EventTap:
    """全局快捷键监听器"""
    
    def __init__(self, on_cut=None, on_paste=None, on_copy=None, on_license_invalid=None):
        self.on_cut = on_cut
        self.on_paste = on_paste
        self.on_copy = on_copy
        self.on_license_invalid = on_license_invalid
        self.tap = None
        self.running = False

    def _is_finder_active(self) -> bool:
        """检查 Finder 是否为当前活跃窗口"""
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return app and app.bundleIdentifier() == "com.apple.finder"

    def _callback(self, proxy, event_type, event, refcon):
        """Event Tap 回调函数"""
        # 处理 Tap 被系统自动禁用的情况
        if event_type == kCGEventTapDisabledByTimeout or event_type == kCGEventTapDisabledByUserInput:
            print(f"[EventTap] Tap 被禁用 (type: {event_type})，尝试重启...")
            if self.tap:
                CGEventTapEnable(self.tap, True)
            return event

        if event_type != kCGEventKeyDown:
            return event

        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
        flags = Quartz.CGEventGetFlags(event)

        # 1. 必须包含 Command 键
        # 2. 不能包含 Shift 或 Option (排除 ⌘+Shift+C 等组合键)
        if not (flags & CMD) or (flags & EXCLUDE_FLAGS):
            return event

        # --- 处理 ⌘+C (全局监听) ---
        if keycode == KEY_C:
            if self.on_copy:
                # 触发 app.py 中的异步检查逻辑
                self.on_copy()
            # 关键：必须返回原 event，让系统执行真正的复制动作
            return event

        # --- 处理 ⌘+X 和 ⌘+V (仅在 Finder 中生效) ---
        if keycode in (KEY_X, KEY_V):
            if not self._is_finder_active():
                return event
            
            # 权限/许可证检查
            if not license_manager.is_valid():
                print("[EventTap] 许可证无效，忽略操作")
                if self.on_license_invalid:
                    self.on_license_invalid()
                return event
            
            # 执行回调
            handler = self.on_cut if keycode == KEY_X else self.on_paste
            if handler and handler():
                # 如果回调返回 True，表示我们成功处理了文件移动
                # 返回 None 以“吞掉”该事件，防止 Finder 执行默认的“剪切/粘贴文本”动作
                return None
        
        return event

    def start(self) -> bool:
        """启动事件监听"""
        print("[EventTap] 正在创建 Event Tap...")
        
        # 监听按下事件
        mask = CGEventMaskBit(kCGEventKeyDown)
        
        self.tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            mask,
            self._callback,
            None
        )

        if not self.tap:
            print("[ERROR] 无法创建 Event Tap。请确保已授予辅助功能 (Accessibility) 权限。")
            return False

        # 将 Tap 添加到当前的 RunLoop 中
        source = CFMachPortCreateRunLoopSource(None, self.tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, Quartz.kCFRunLoopCommonModes)
        
        # 启用 Tap
        CGEventTapEnable(self.tap, True)
        self.running = True
        print("[EventTap] ✓ 启动成功")
        return True

    def _recreate_tap(self):
        """当 Tap 崩溃或失效时重新创建"""
        print("[EventTap] 尝试重新初始化...")
        if self.tap:
            Quartz.CFRelease(self.tap)
        return self.start()

    def stop(self):
        """停止监听"""
        if self.tap:
            print("[EventTap] 停止监听")
            CGEventTapEnable(self.tap, False)
            # 在某些环境下可能需要手动从 RunLoop 移除，这里简写
        self.running = False