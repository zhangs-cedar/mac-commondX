#!/usr/bin/env python3
"""全局快捷键监听模块 - 使用 Quartz Event Tap"""

import Quartz
from Quartz import (
    CGEventTapCreate, CGEventTapEnable, CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource, CFRunLoopGetCurrent, CFRunLoopRun,
    kCGSessionEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
    CGEventMaskBit, kCGEventKeyDown, CGEventGetIntegerValueField,
    kCGKeyboardEventKeycode
)
from Foundation import NSRunLoop, NSDefaultRunLoopMode
from AppKit import NSWorkspace
import threading


# macOS 键码
KEY_X = 7
KEY_V = 9
KEY_C = 8

# 修饰键掩码
CMD_MASK = Quartz.kCGEventFlagMaskCommand
SHIFT_MASK = Quartz.kCGEventFlagMaskShift
OPTION_MASK = Quartz.kCGEventFlagMaskAlternate


class EventTap:
    """全局快捷键监听器"""
    
    def __init__(self, on_cut=None, on_paste=None):
        self.on_cut = on_cut      # Cmd+X 回调
        self.on_paste = on_paste  # Cmd+V 回调
        self.tap = None
        self.running = False
        self._thread = None
    
    def _callback(self, proxy, event_type, event, refcon):
        """事件回调"""
        try:
            if event_type == kCGEventKeyDown:
                keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                flags = Quartz.CGEventGetFlags(event)
                
                # 检查是否按下 Cmd 键（不含其他修饰键）
                cmd_only = (flags & CMD_MASK) and not (flags & OPTION_MASK) and not (flags & SHIFT_MASK)
                
                if cmd_only:
                    # 检查当前应用是否为 Finder
                    ws = NSWorkspace.sharedWorkspace()
                    front_app = ws.frontmostApplication()
                    if not front_app or front_app.bundleIdentifier() != "com.apple.finder":
                        return event

                    handled = False
                    if keycode == KEY_X and self.on_cut:
                        # Cmd+X: 剪切
                        handled = self.on_cut()
                    elif keycode == KEY_V and self.on_paste:
                        # Cmd+V: 粘贴（如果有剪切内容则移动）
                        handled = self.on_paste()
                    
                    if handled:
                        return None
        except Exception as e:
            print(f"Event callback error: {e}")
        
        return event
    
    def start(self):
        """启动事件监听"""
        if self.running:
            return
        
        # 创建事件掩码（只监听键盘按下事件）
        mask = CGEventMaskBit(kCGEventKeyDown)
        
        # 创建事件 tap
        self.tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            mask,
            self._callback,
            None
        )
        
        if not self.tap:
            print("无法创建 Event Tap，请检查辅助功能权限")
            return False
        
        # 添加到运行循环
        source = CFMachPortCreateRunLoopSource(None, self.tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, Quartz.kCFRunLoopCommonModes)
        CGEventTapEnable(self.tap, True)
        
        self.running = True
        print("Event Tap 已启动")
        return True
    
    def stop(self):
        """停止事件监听"""
        if self.tap:
            CGEventTapEnable(self.tap, False)
            self.tap = None
        self.running = False
        print("Event Tap 已停止")


def check_accessibility():
    """检查辅助功能权限"""
    from ApplicationServices import AXIsProcessTrusted
    return AXIsProcessTrusted()


def request_accessibility():
    """请求辅助功能权限"""
    from ApplicationServices import AXIsProcessTrustedWithOptions
    from Foundation import NSDictionary
    
    options = NSDictionary.dictionaryWithObject_forKey_(
        True, "AXTrustedCheckOptionPrompt"
    )
    return AXIsProcessTrustedWithOptions(options)
