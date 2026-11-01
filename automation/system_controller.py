import os
import time
import subprocess
from datetime import datetime
from pathlib import Path
import pyautogui
from core.safety import logger

class SystemController:
    """Controls OS-level Windows functions: volume, media, screenshots, file navigation."""

    @staticmethod
    def adjust_volume(direction: str = "up", steps: int = 5):
        """direction: 'up', 'down', or 'mute'"""
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
        
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        logger.info(f"[System] Screenshot saved: {filepath}")
        return str(filepath)

    @staticmethod
    def open_folder(folder_path: str = ""):
        """Opens File Explorer to a specific path or user's home folder."""
        path = folder_path.strip()
        if not path:
            path = str(Path.home())
        elif path.lower() in ["downloads", "desktop", "documents", "pictures", "videos"]:
            path = str(Path.home() / path.capitalize())

        logger.info(f"[System] Opening folder in Explorer: {path}")
        subprocess.Popen(f'explorer.exe "{path}"', shell=True)

    @staticmethod
    def search_in_explorer(query: str):
        """Opens File Explorer and focuses the search box with query."""
        subprocess.Popen("explorer.exe", shell=True)
        time.sleep(0.8)
        pyautogui.hotkey("ctrl", "e")
        time.sleep(0.1)
        pyautogui.write(query, interval=0.02)
        pyautogui.press("enter")

    @staticmethod
    def lock_workstation():
        logger.info("[System] Locking Windows workstation.")
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)

system_controller = SystemController()
