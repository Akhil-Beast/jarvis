"""
automation/handy_injector.py — Direct Foreground Text & Keystroke Injection
Inspired by cjpais/Handy (https://github.com/cjpais/Handy)

Provides:
- Direct typing into whichever application window currently has focus
- Clipboard-based fast insertion (preserves user's original clipboard)
- Keystroke synthesis for hotkeys and commands
"""
import time
from core.safety import logger
from automation.input_controller import input_controller
from automation.window_manager import window_manager

try:
    import pyperclip
    HAS_PYPERCLIP = True
except Exception:
    pyperclip = None
    HAS_PYPERCLIP = False


class HandyInjector:
    """Injects dictated text and keystrokes directly into the active foreground window,
    matching the core UX pattern of Handy (https://github.com/cjpais/Handy)."""

    def __init__(self):
        pass

    def inject_text(self, text: str, press_enter: bool = False, restore_clipboard: bool = True):
        """Pastes or types text directly into the foreground window.
        Uses clipboard injection for instant zero-latency pasting, then restores the clipboard."""
        if not text:
            return

        active_title = window_manager.get_active_window_title()
        logger.info(f"[HandyInjector] Injecting text into active window '{active_title}': '{text[:40]}...'")

        old_clipboard = ""
        if restore_clipboard:
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                old_clipboard = ""

        try:
            # Clipboard injection is instant (100x faster than simulated keystrokes for long paragraphs)
            pyperclip.copy(text)
            time.sleep(0.05)
            input_controller.hotkey("ctrl", "v")
            time.sleep(0.05)

            if press_enter:
                input_controller.press_key("enter")
        finally:
            if restore_clipboard:
                try:
                    time.sleep(0.1)
                    pyperclip.copy(old_clipboard)
                except Exception:
                    pass

    def inject_keystrokes(self, text: str):
        """Simulates raw keystroke typing (for apps that block clipboard paste, like some secure terminals)."""
        input_controller.type_text(text, press_enter=False)


handy_injector = HandyInjector()
