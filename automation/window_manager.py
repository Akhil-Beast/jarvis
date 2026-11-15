import time
from core.safety import logger

try:
    import win32gui
    import win32con
    import win32process
    HAS_WIN32 = True
except ImportError:
    win32gui = None
    win32con = None
    win32process = None
    HAS_WIN32 = False

class WindowManager:
    """Manages active Windows top-level windows, focusing, snapping, and closing."""

    @staticmethod
    def get_open_windows() -> list[dict]:
        """Returns a list of visible user application windows."""
        if not HAS_WIN32 or win32gui is None:
            return []

        windows = []

        def enum_handler(hwnd, extra):
            try:
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
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_handler, None)
        except Exception as e:
            logger.debug(f"[WindowManager] EnumWindows notice: {e}")
        return windows

    @staticmethod
    def focus_window(title_or_keyword: str) -> bool:
        """Brings the matching window to foreground forcefully without GUI deadlocks."""
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
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            # Force restore if minimized
            win32gui.ShowWindow(match_hwnd, win32con.SW_RESTORE)

            # Safe Win32 foreground attach — avoids synthetic Alt key pulses that trigger
            # modal menu loops or deadlock low-level keyboard hooks
            cur_thread = kernel32.GetCurrentThreadId()
            fg_hwnd = user32.GetForegroundWindow()
            if fg_hwnd and fg_hwnd != match_hwnd:
                fg_pid = ctypes.c_ulong()
                fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, ctypes.byref(fg_pid))
                if fg_thread != cur_thread:
                    user32.AttachThreadInput(cur_thread, fg_thread, True)
                    user32.SetForegroundWindow(match_hwnd)
                    user32.BringWindowToTop(match_hwnd)
                    user32.AttachThreadInput(cur_thread, fg_thread, False)
                else:
                    user32.SetForegroundWindow(match_hwnd)
                    user32.BringWindowToTop(match_hwnd)
            else:
                user32.SetForegroundWindow(match_hwnd)
                user32.BringWindowToTop(match_hwnd)

            time.sleep(0.08)
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
        if not HAS_WIN32 or win32gui is None:
            return
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        except Exception:
            pass

    @staticmethod
    def get_active_window_title() -> str:
        """Returns the title of the currently active (foreground) window."""
        if not HAS_WIN32 or win32gui is None:
            return ""
        try:
            hwnd = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(hwnd) if hwnd else ""
        except Exception:
            return ""

window_manager = WindowManager()
