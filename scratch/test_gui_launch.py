"""
scratch/test_gui_launch.py
Verify that MainWindow and QApplication start, pump events, and exit cleanly without freeze.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from core.voice_listener import VoiceListener
from core.hotkey_manager import HotkeyManager
from gui.main_window import MainWindow

def test_gui():
    print("Initializing GUI application...")
    app = QApplication(sys.argv)
    
    voice_listener = VoiceListener()
    hotkey_manager = HotkeyManager()
    
    window = MainWindow(voice_listener, hotkey_manager)
    window.show()
    
    # Check that events pump smoothly and close after 2 seconds
    def on_timeout():
        print("GUI pumped messages cleanly without freeze! Exiting test...")
        window.close_application()
        app.quit()
        
    QTimer.singleShot(2000, on_timeout)
    app.exec()
    print("GUI launch test passed!")

if __name__ == "__main__":
    test_gui()
