import time
import win32gui
import win32con
import win32process
from core.safety import logger

class WindowManager:
    """Manages active Windows top-level windows, focusing, snapping, and closing."""

    @staticmethod
    def get_open_windows() -> list[dict]:
        """Returns a list of visible user application windows."""
        windows = []

        def enum_handler(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title:
                    # Filter out system utility windows
                    if title not in ["Program Manager", "Settings", "Windows Input Experience"]:
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            windows.append({"hwnd": hwnd, "title": title, "pid": pid})
                        except Exception:
                            pass

        win32gui.EnumWindows(enum_handler, None)
        return windows

    @staticmethod
    def focus_window(title_or_keyword: str) -> bool:
        """Brings the matching window to foreground forcefully."""
        target = title_or_keyword.lower().strip()
        windows = WindowManager.get_open_windows()
        
        match_hwnd = None
        for w in windows:
            if target in w["title"].lower():
                match_hwnd = w["hwnd"]
                break

        if not match_hwnd:
            logger.warning(f"[WindowManager] No window matching '{title_or_keyword}' found.")
            return False

        try:
            # Force restore if minimized
            win32gui.ShowWindow(match_hwnd, win32con.SW_RESTORE)
            
            # Windows API foreground lock workaround: send Alt key pulse first
            import pyautogui
            pyautogui.press("alt")
            
            win32gui.SetForegroundWindow(match_hwnd)
            time.sleep(0.15)
            logger.info(f"[WindowManager] Focused window (HWND {match_hwnd})")
            return True
        except Exception as e:
            logger.error(f"[WindowManager] Error focusing window: {e}")
            return False

    @staticmethod
    def close_window(title_or_keyword: str = "") -> bool:
        """Closes a specific window by title or the currently active window if omitted."""
        hwnd = None
        if not title_or_keyword:
            hwnd = win32gui.GetForegroundWindow()
        else:
            target = title_or_keyword.lower().strip()
            windows = WindowManager.get_open_windows()
            for w in windows:
                if target in w["title"].lower():
                    hwnd = w["hwnd"]
                    break

        if not hwnd:
            logger.warning("[WindowManager] Target window to close not found.")
            return False

        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            logger.info(f"[WindowManager] Sent WM_CLOSE to HWND {hwnd}")
            return True
        except Exception as e:
            logger.error(f"[WindowManager] Failed to close window: {e}")
            return False

    @staticmethod
    def minimize_all():
        """Minimizes all windows to show desktop."""
        import pyautogui
        pyautogui.hotkey("win", "d")

    @staticmethod
    def maximize_active():
        """Maximizes the currently active window."""
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

    @staticmethod
    def get_active_window_title() -> str:
        """Returns the title of the currently active (foreground) window."""
        hwnd = win32gui.GetForegroundWindow()
        return win32gui.GetWindowText(hwnd) if hwnd else ""

window_manager = WindowManager()
