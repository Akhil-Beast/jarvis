import sys
import os
import threading
import time
import urllib.request

# Safeguard standard streams for windowed / background runtimes
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from core.voice_listener import VoiceListener
from core.hotkey_manager import HotkeyManager
from core.safety import logger
from gui.main_window import MainWindow

BASE_DIR = Path(__file__).resolve().parent


def ensure_local_server():
    """Starts the local JARVIS web server daemon on port 10000 if not already running."""
    try:
        urllib.request.urlopen("http://127.0.0.1:10000/health", timeout=1)
        logger.info("[Main] Local JARVIS server is already online on port 10000.")
        return
    except Exception:
        pass

    logger.info("[Main] Starting embedded local JARVIS server on port 10000...")
    import uvicorn
    from server import app

    def _run_server():
        cfg = uvicorn.Config(app, host="127.0.0.1", port=10000, log_level="warning")
        server = uvicorn.Server(cfg)
        server.run()

    t = threading.Thread(target=_run_server, daemon=True)
    t.start()

    # Wait briefly for server to bind
    for _ in range(30):
        try:
            urllib.request.urlopen("http://127.0.0.1:10000/health", timeout=0.5)
            logger.info("[Main] Local JARVIS server online and ready.")
            break
        except Exception:
            time.sleep(0.15)


def main():
    # Single instance enforcement via Windows named mutex
    try:
        import win32event, win32api, winerror
        _mutex = win32event.CreateMutex(None, False, "Global\\JARVIS_Voice_Assistant_SingleInstance_Mutex")
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            logger.warning("[Main] Another instance of JARVIS is already running. Focusing existing instance.")
            from automation.window_manager import window_manager
            window_manager.focus_window("JARVIS")
            sys.exit(0)
    except Exception as e:
        logger.debug(f"[Main] Single instance mutex check notice: {e}")

    # Ensure local server is started first
    ensure_local_server()

    logger.info("Initializing JARVIS Desktop Assistant (Web HUD Mode)...")
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS Voice Assistant")
    app.setQuitOnLastWindowClosed(False)

    icon_path = BASE_DIR / "assets" / "icon_active.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Initialize Core Engines
    voice_listener = VoiceListener()
    hotkey_manager = HotkeyManager()

    # Initialize Main GUI Window (hosts the exact same Web HUD)
    window = MainWindow(voice_listener, hotkey_manager)

    # Wire hotkey callbacks to Qt signals (thread-safe queued invocation)
    hotkey_manager.toggle_callback = lambda: window.signals.toggle_requested.emit()
    hotkey_manager.stop_callback = lambda: window.signals.emergency_stop_triggered.emit()

    # Start Background Workers
    voice_listener.start()
    hotkey_manager.start()

    # Show Window unless --minimized argument was passed
    if "--minimized" not in sys.argv:
        window.show()
    else:
        logger.info("Starting minimized to system tray.")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
