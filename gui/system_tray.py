from pathlib import Path
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from core.safety import logger

BASE_DIR = Path(__file__).resolve().parent.parent

class SystemTrayManager:
    """Manages system tray presence, status icon toggles, and context menu."""

    def __init__(self, main_window, on_toggle=None, on_stop=None, on_settings=None):
        self.main_window = main_window
        self.on_toggle = on_toggle
        self.on_stop = on_stop
        self.on_settings = on_settings

        self.icon_active = QIcon(str(BASE_DIR / "assets" / "icon_active.png"))
        self.icon_inactive = QIcon(str(BASE_DIR / "assets" / "icon_inactive.png"))

        self.tray_icon = QSystemTrayIcon(self.icon_inactive, main_window)
        self.tray_icon.setToolTip("JARVIS - Windows Voice Assistant [OFF]")

        # Context Menu
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu { background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d; }
            QMenu::item:selected { background-color: #1f6feb; color: white; }
        """)

        act_show = QAction("Open JARVIS HUD", self.menu)
        act_show.triggered.connect(self._show_window)
        self.menu.addAction(act_show)

        self.act_toggle = QAction("Toggle Listening (Ctrl+Alt+Space)", self.menu)
        if self.on_toggle:
            self.act_toggle.triggered.connect(self.on_toggle)
        self.menu.addAction(self.act_toggle)

        act_stop = QAction("Emergency Stop (Esc)", self.menu)
        if self.on_stop:
            act_stop.triggered.connect(self.on_stop)
        self.menu.addAction(act_stop)

        self.menu.addSeparator()

        act_settings = QAction("Settings...", self.menu)
        if self.on_settings:
            act_settings.triggered.connect(self.on_settings)
        self.menu.addAction(act_settings)

        self.menu.addSeparator()

        act_exit = QAction("Exit JARVIS", self.menu)
        act_exit.triggered.connect(self.main_window.close_application)
        self.menu.addAction(act_exit)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def set_active_state(self, is_active: bool):
        if is_active:
            self.tray_icon.setIcon(self.icon_active)
            self.tray_icon.setToolTip("JARVIS - Windows Voice Assistant [ACTIVE]")
            self.act_toggle.setText("Deactivate Assistant")
            self.show_notification("JARVIS Online", "Voice recognition and Windows automation is active.")
        else:
            self.tray_icon.setIcon(self.icon_inactive)
            self.tray_icon.setToolTip("JARVIS - Windows Voice Assistant [STANDBY]")
            self.act_toggle.setText("Activate Assistant")
            self.show_notification("JARVIS Standby", "Assistant is paused.")

    def show_notification(self, title: str, message: str):
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 2000)

    def _show_window(self):
        self.main_window.show()
        self.main_window.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()
