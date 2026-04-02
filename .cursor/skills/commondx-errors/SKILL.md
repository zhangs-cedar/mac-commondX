---
name: commondx-errors
description: >-
  Applies CommondX / macOS PyObjC pitfall patterns from the project error log:
  pathlib-only paths, NSAlert vs notifications, bundle vs Application Support paths,
  Event Tap recovery after modal dialogs, NSAlert text field paste via Edit menu,
  AppleScript and PyObjC naming. Use when editing mac-commondX, menu bar apps,
  Quartz Event Tap, NSAlert, PyInstaller packaging, or accessibility scripts.
---

# CommondX 错误模式 Skill

## When to use

- Touching `src/status_bar.py`, `src/event_tap.py`, plugins, AppleScript, `tools/build_dmg.sh`, `init.sh`, or TCC / Accessibility.
- User mentions: notification vs alert, Event Tap dead after dialog, modal, packaged app paths, `__file__` for config, Finder integration, paste in alert field.

## Pre-flight checklist (do this before shipping a change)

1. **Paths** — `pathlib.Path` only; no `os.path.join` or string `+ '/'` (PATTERN-001).
2. **Critical UX** — use `NSAlert` for must-see messages; `NSUserNotification` only for low-priority background hints (PATTERN-003).
3. **Packaged app** — writable user data under `~/Library/Application Support/<App>/`; do not treat bundle resources via `__file__` as writable config (PATTERN-004).
4. **PyObjC** — avoid `_method` names on `NSObject` subclasses for helpers; use module-level functions (PATTERN-011).
5. **Modal + Event Tap** — after any modal UI, apply the **five-layer Tap recovery** (below).
6. **Paste in NSAlert fields** — app must have a real **Edit** menu with `cut:`, `copy:`, `paste:`, `selectAll:` (PATTERN-017); menu bar may be hidden but menu must exist.

## Event Tap — five-layer recovery (summary)

Showing a modal dialog can disable the tap. After the dialog closes:

1. Do **not** call `activateIgnoringOtherApps` for the alert path; keep Finder key.
2. Re-enable the tap **immediately** when the dialog ends (e.g. `CGEventTapEnable(tap, True)` or project helper).
3. **Delayed** re-enable (e.g. 50 ms, 100 ms, 200 ms) so the system leaves modal state.
4. At the **start of the tap callback**, detect disabled tap and re-enable.
5. If still broken, **tear down and recreate** the tap.

Details and context: [reference.md](reference.md).

## NSAlert + standard shortcuts

Standard ⌘C / ⌘V / ⌘X / ⌘A are routed through the **menu system**. `NSTextField` implements the actions, but without menu items the shortcuts do not fire.

- Build a minimal menubar with an **Edit** submenu and the four items above, then `setMainMenu_`.
- Avoid fake fixes: notification observers, timers, or hand-rolled paste for this.

Minimal pattern (Python / PyObjC): see [reference.md](reference.md).

## Refactor discipline

- **Return values** — if a function returns a new object, assign it: `obj = f(obj, ...)` (PATTERN-013).
- **Imports** — after moves/splits, verify every symbol still imports (PATTERN-014).
- **Cancel** — user cancel must **not** reset tracking state; reset only after successful operations (PATTERN-015).

## Full pattern index

Numbered patterns (001–017), Finder/AppleScript notes, and expanded notes: [reference.md](reference.md).
