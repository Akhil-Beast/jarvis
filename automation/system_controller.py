import os
import time
import subprocess
from datetime import datetime
from pathlib import Path
from core.safety import logger

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    HAS_PYAUTOGUI = False

class SystemController:
    """Controls OS-level Windows functions: volume, media, screenshots, file navigation."""

    @staticmethod
    def adjust_volume(direction: str = "up", steps: int = 5):
        """direction: 'up', 'down', or 'mute'"""
        if not HAS_PYAUTOGUI or pyautogui is None:
            return
        key = "volumeup" if direction == "up" else ("volumedown" if direction == "down" else "volumemute")
        count = 1 if direction == "mute" else steps
        logger.info(f"[System] Volume {direction} ({count} steps)")
        for _ in range(count):
            pyautogui.press(key)
            time.sleep(0.02)

    @staticmethod
    def take_screenshot(save_dir: Path | None = None) -> str:
        """Captures full screen and saves to desktop or designated directory."""
        if save_dir is None:
            save_dir = Path.home() / "Desktop"
        save_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = save_dir / f"screenshot_{timestamp}.png"
        
        if HAS_PYAUTOGUI and pyautogui is not None:
            try:
                screenshot = pyautogui.screenshot()
                screenshot.save(filepath)
                logger.info(f"[System] Screenshot saved: {filepath}")
                return str(filepath)
            except Exception as e:
                logger.warning(f"[System] Screenshot capture notice: {e}")
        return ""

    @staticmethod
    def open_folder(folder_path: str = ""):
        """Opens File Explorer to a specific path or user's home folder."""
        path = folder_path.strip()
        if not path:
            path = str(Path.home())
        elif path.lower() in ["downloads", "desktop", "documents", "pictures", "videos"]:
            path = str(Path.home() / path.capitalize())

        try:
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
            logger.info(f"[System] Opened folder: {path}")
        except Exception as e:
            logger.error(f"[System] Failed to open folder '{path}': {e}")

    @staticmethod
    def search_in_explorer(query: str):
        """Focuses explorer and triggers search bar navigation."""
        if not HAS_PYAUTOGUI or pyautogui is None:
            return
        logger.info(f"[System] Initiating Windows Explorer search: '{query}'")
        pyautogui.hotkey("ctrl", "e")
        time.sleep(0.1)
        pyautogui.write(query, interval=0.02)
        pyautogui.press("enter")

    @staticmethod
    def lock_workstation():
        """Locks the Windows computer workstation immediately."""
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            logger.info("[System] Workstation locked.")
        except Exception as e:
            logger.error(f"[System] Failed to lock workstation: {e}")

system_controller = SystemController()
