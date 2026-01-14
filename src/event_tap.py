import Quartz
from AppKit import NSEvent, NSKeyDownMask, NSCommandKeyMask
from cedar.utils import print
import time

class EventTap:
    def __init__(self, on_cut=None, on_paste=None, on_copy=None, on_license_invalid=None):
        self.on_cut = on_cut
        self.on_paste = on_paste
        self.on_copy = on_copy
        self.on_license_invalid = on_license_invalid
        self.tap = None
        self.run_loop_source = None
        
        # 新增：物理按键防抖记录
        self._last_c_time = 0
        self._last_x_time = 0
        self._last_v_time = 0

    def _callback(self, proxy, event_type, event, refcon):
        if event_type == Quartz.kCGEventKeyDown:
            flags = Quartz.CGEventGetFlags(event)
            # 检查是否按下了 Command 键
            if flags & Quartz.kCGEventFlagMaskCommand:
                keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGEventFieldKeyboardEventKeycode)
                
                # 定义键码
                KEY_X = 7
                KEY_C = 8
                KEY_V = 9
                
                now = time.time()
                debounce_interval = 0.2  # 200ms 内不重复处理物理按键

                # 处理 ⌘+X
                if keycode == KEY_X:
                    if now - self._last_x_time < debounce_interval:
                        return event
                    self._last_x_time = now
                    if self.on_cut:
                        self.on_cut()
                    return event

                # 处理 ⌘+C (核心优化点)
                elif keycode == KEY_C:
                    if now - self._last_c_time < debounce_interval:
                        return event
                    self._last_c_time = now
                    if self.on_copy:
                        # 延迟一小会儿执行，确保系统剪贴板已经写入了最新的内容
                        self.on_copy()
                    return event

                # 处理 ⌘+V
                elif keycode == KEY_V:
                    if now - self._last_v_time < debounce_interval:
                        return event
                    self._last_v_time = now
                    if self.on_paste:
                        if self.on_paste():
                            return None
                    return event

        return event

    def start(self):
        mask = (1 << Quartz.kCGEventKeyDown)
        self.tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            mask,
            self._callback,
            None
        )

        if not self.tap:
            print("无法创建 EventTap")
            return False

        self.run_loop_source = Quartz.CFRunLoopAddSource(
            Quartz.CFRunLoopGetCurrent(),
            Quartz.CFMachPortCreateRunLoopSource(None, self.tap, 0),
            Quartz.kCFRunLoopCommonModes
        )
        Quartz.CGEventTapEnable(self.tap, True)
        return True

    def stop(self):
        if self.tap:
            Quartz.CGEventTapEnable(self.tap, False)
            Quartz.CFRunLoopRemoveSource(
                Quartz.CFRunLoopGetCurrent(),
                self.run_loop_source,
                Quartz.kCFRunLoopCommonModes
            )
            self.tap = None