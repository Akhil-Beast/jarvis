import time
import pyautogui
import pyperclip
from core.safety import logger, safety

# PyAutoGUI safety configuration
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

class InputController:
    """Provides low-level keyboard and mouse simulation with clipboard acceleration."""

    @staticmethod
    def type_text(text: str, press_enter: bool = False, use_clipboard: bool = True):
        """Types text cleanly. Uses clipboard paste by default for speed and Unicode reliability."""
        if safety.is_aborted:
            return

        logger.info(f"[Input] Typing text (length={len(text)}, enter={press_enter})")
        if use_clipboard:
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
        if safety.is_aborted:
            return
        logger.info(f"[Input] Pressing key: {key}")
        pyautogui.press(key)

    @staticmethod
    def hotkey(*keys):
        if safety.is_aborted:
            return
        logger.info(f"[Input] Sending hotkey: {'+'.join(keys)}")
        pyautogui.hotkey(*keys)

    @staticmethod
    def click(x: int | None = None, y: int | None = None, clicks: int = 1, button: str = "left"):
        if safety.is_aborted:
            return
        if x is not None and y is not None:
            pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        else:
            pyautogui.click(clicks=clicks, button=button)

    @staticmethod
    def scroll(clicks: int):
        if safety.is_aborted:
            return
        logger.info(f"[Input] Scrolling: {clicks}")
        pyautogui.scroll(clicks)

    @staticmethod
    def select_all_and_copy() -> str:
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.05)
        try:
            return pyperclip.paste()
        except Exception:
            return ""

input_controller = InputController()
