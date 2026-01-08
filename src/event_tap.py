#!/usr/bin/env python3
"""全局快捷键监听 - Quartz Event Tap"""

import Quartz
from Quartz import (
    CGEventTapCreate, CGEventTapEnable, CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource, CFRunLoopGetCurrent, CGEventMaskBit,
    kCGSessionEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
    kCGEventKeyDown, CGEventGetIntegerValueField, kCGKeyboardEventKeycode
)
from AppKit import NSWorkspace
from cedar.utils import print

# 键码与修饰键
KEY_X, KEY_V = 7, 9
CMD, SHIFT, OPT = Quartz.kCGEventFlagMaskCommand, Quartz.kCGEventFlagMaskShift, Quartz.kCGEventFlagMaskAlternate
FINDER_ID = "com.apple.finder"


class EventTap:
    """全局快捷键监听器"""
    
    def __init__(self, on_cut=None, on_paste=None):
        self.on_cut = on_cut
        self.on_paste = on_paste
        self.tap = None
        self.running = False
    
    def _is_finder_active(self) -> bool:
        """检查 Finder 是否为前台应用"""
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return app and app.bundleIdentifier() == FINDER_ID
    
    def _callback(self, proxy, event_type, event, refcon):
        """事件回调"""
        try:
            if event_type != kCGEventKeyDown:
                return event
            
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            if keycode not in (KEY_X, KEY_V):
                return event
            
            flags = Quartz.CGEventGetFlags(event)
            if not (flags & CMD) or (flags & SHIFT) or (flags & OPT):
                return event
            
            if not self._is_finder_active():
                return event
            
            handler = self.on_cut if keycode == KEY_X else self.on_paste
            if handler and handler():
                return None  # 吞掉事件
        except Exception as e:
            print(f"Event callback error: {e}")
        return event
    
    def start(self) -> bool:
        """启动监听"""
        if self.running:
            return True
        
        self.tap = CGEventTapCreate(
            kCGSessionEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
            CGEventMaskBit(kCGEventKeyDown), self._callback, None
        )
        if not self.tap:
            print("无法创建 Event Tap，检查辅助功能权限")
            return False
        
        source = CFMachPortCreateRunLoopSource(None, self.tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, Quartz.kCFRunLoopCommonModes)
        CGEventTapEnable(self.tap, True)
        
        self.running = True
        print("Event Tap 已启动")
        return True
    
    def stop(self):
        """停止监听"""
        if self.tap:
            CGEventTapEnable(self.tap, False)
            self.tap = None
        self.running = False
        print("Event Tap 已停止")
