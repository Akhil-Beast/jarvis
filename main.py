import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from core.voice_listener import VoiceListener
from core.hotkey_manager import HotkeyManager
from core.safety import logger
from gui.main_window import MainWindow

BASE_DIR = Path(__file__).resolve().parent

def main():
    logger.info("Initializing JARVIS Desktop Automation Assistant...")
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS Voice Assistant")
    app.setQuitOnLastWindowClosed(False)

    icon_path = BASE_DIR / "assets" / "icon_active.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Initialize Core Engines
    voice_listener = VoiceListener()
    hotkey_manager = HotkeyManager()

    # Initialize Main GUI Window
    window = MainWindow(voice_listener, hotkey_manager)

    # Wire hotkey callbacks to UI actions
    hotkey_manager.toggle_callback = window.toggle_assistant
    hotkey_manager.stop_callback = window.emergency_stop

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
