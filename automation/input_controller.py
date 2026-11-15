import time
from core.safety import logger, safety

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    HAS_PYAUTOGUI = False

try:
    import pyperclip
    HAS_PYPERCLIP = True
except Exception:
    pyperclip = None
    HAS_PYPERCLIP = False

class InputController:
    """Provides low-level keyboard and mouse simulation with clipboard acceleration."""

    @staticmethod
    def type_text(text: str, press_enter: bool = False, use_clipboard: bool = True):
        """Types text cleanly. Uses clipboard paste by default for speed and Unicode reliability."""
        if safety.is_aborted or not HAS_PYAUTOGUI or pyautogui is None:
            return

        logger.info(f"[Input] Typing text (length={len(text)}, enter={press_enter})")
        if use_clipboard and HAS_PYPERCLIP and pyperclip is not None:
            old_clip = ""
            try:
                old_clip = pyperclip.paste()
            except Exception:
                pass

            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.08)

            # Restore original clipboard
            try:
                if old_clip:
                    pyperclip.copy(old_clip)
            except Exception:
                pass
        else:
            pyautogui.write(text, interval=0.01)

        if press_enter:
            time.sleep(0.05)
            pyautogui.press("enter")

    @staticmethod
    def press_key(key: str):
        if safety.is_aborted or not HAS_PYAUTOGUI or pyautogui is None:
            return
        logger.info(f"[Input] Pressing key: {key}")
        pyautogui.press(key)

    @staticmethod
    def hotkey(*keys):
        if safety.is_aborted or not HAS_PYAUTOGUI or pyautogui is None:
            return
        logger.info(f"[Input] Sending hotkey: {'+'.join(keys)}")
        pyautogui.hotkey(*keys)

    @staticmethod
    def click(x: int | None = None, y: int | None = None, clicks: int = 1, button: str = "left"):
        if safety.is_aborted or not HAS_PYAUTOGUI or pyautogui is None:
            return
        if x is not None and y is not None:
            pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        else:
            pyautogui.click(clicks=clicks, button=button)

    @staticmethod
    def scroll(clicks: int = -300):
        if safety.is_aborted or not HAS_PYAUTOGUI or pyautogui is None:
            return
        logger.info(f"[Input] Scrolling: {clicks}")
        pyautogui.scroll(clicks)

    @staticmethod
    def select_all_and_copy() -> str:
        if not HAS_PYAUTOGUI or pyautogui is None:
            return ""
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.05)
        try:
            if HAS_PYPERCLIP and pyperclip is not None:
                return pyperclip.paste()
        except Exception:
            pass
        return ""

input_controller = InputController()
