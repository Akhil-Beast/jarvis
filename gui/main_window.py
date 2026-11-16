"""
gui/main_window.py — Modern Futuristic Web HUD Window for JARVIS Desktop
Embeds the exact same futuristic Cyberpunk / Iron Man HUD as Render Web
using PySide6 QWebEngineView with native Windows integration.

Features:
- 100% Identical UI to Render Web (Arc Reactor, Thought Card, Chat Stream, App Deck, Input Bar)
- Full Local Desktop Execution (opens real Windows apps, moves mouse, hotkeys)
- Hands-Free Speech Recognition Bridge (routes mic transcript directly into HUD)
- Hardware Global Hotkey support (Ctrl+Alt+Space to focus/toggle, Esc to abort)
- Automatic Microphone Permission granting for Web Speech API
- Native System Tray integration (minimize to tray, background listening)
"""
import sys
import json
import urllib.request
import threading
import time
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QObject, QUrl, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QMessageBox
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings

from config.settings import config
from core.safety import safety, logger
from core.tts_engine import tts
from automation.orchestrator import orchestrator
from gui.system_tray import SystemTrayManager

BASE_DIR = Path(__file__).resolve().parent.parent


class JarvisWebPage(QWebEnginePage):
    """Custom WebEnginePage that automatically grants microphone and media permissions."""

    def __init__(self, profile=None, parent=None):
        if profile:
            super().__init__(profile, parent)
        else:
            super().__init__(parent)
        self.featurePermissionRequested.connect(self._on_feature_permission_requested)

    def _on_feature_permission_requested(self, security_origin, feature):
        # Auto-grant microphone and media stream access
        logger.info(f"[HUD/Page] Granting permission for feature {feature} from {security_origin.toString()}")
        self.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionGrantedByUser)


class GuiSignals(QObject):
    """Thread-safe Qt signal dispatcher."""
    audio_level = Signal(float)
    transcript_received = Signal(str)
    state_changed = Signal(bool)
    step_updated = Signal(int, dict, str)
    tts_state = Signal(bool)
    emergency_stop_triggered = Signal()
    toggle_requested = Signal()


class MainWindow(QMainWindow):
    """
    Futuristic Native Desktop Window for JARVIS.
    Hosts the exact same responsive Web HUD as Render Web, powered by QWebEngineView.
    """

    def __init__(self, voice_listener, hotkey_manager):
        super().__init__()
        self.voice_listener = voice_listener
        self.hotkey_manager = hotkey_manager

        self.signals = GuiSignals()
        self._connect_signals()

        self.setWindowTitle("J.A.R.V.I.S. // Autonomous Desktop Assistant")
        self.resize(1020, 840)
        self.setMinimumSize(700, 600)
        self.setStyleSheet("background-color: #070b14;")

        icon_path = BASE_DIR / "assets" / "icon_active.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()

        # Initialize System Tray
        self.tray_manager = SystemTrayManager(
            self,
            on_toggle=self.toggle_assistant,
            on_stop=self.emergency_stop,
            on_settings=self.open_settings
        )

        # Wire up safety confirmation dialog
        safety.set_confirmation_handler(self._confirm_destructive_action)

    def _build_ui(self):
        container = QWidget(self)
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Initialize QWebEngineView with custom page
        self.web_view = QWebEngineView(container)
        
        # Configure Profile & Permissions
        profile = QWebEngineProfile.defaultProfile()
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)

        self.web_page = JarvisWebPage(profile, self.web_view)
        self.web_view.setPage(self.web_page)
        layout.addWidget(self.web_view)

        # Connect load finished to announce ready
        self.web_view.loadFinished.connect(self._on_web_loaded)

        # Load local server URL
        local_url = "http://127.0.0.1:10000/"
        logger.info(f"[MainWindow] Loading Futuristic Web HUD from {local_url}...")
        self.web_view.setUrl(QUrl(local_url))

    def _on_web_loaded(self, ok: bool):
        if ok:
            logger.info("[MainWindow] Web HUD rendered successfully in native window.")
        else:
            logger.warning("[MainWindow] Failed to load local Web HUD. Retrying in 2 seconds...")
            QTimer.singleShot(2000, lambda: self.web_view.setUrl(QUrl("http://127.0.0.1:10000/")))

    def _connect_signals(self):
        self.signals.transcript_received.connect(self._on_transcript_received)
        self.signals.emergency_stop_triggered.connect(self.emergency_stop)
        self.signals.toggle_requested.connect(self.toggle_assistant)

        # Wire voice listener callbacks to Qt signals
        self.voice_listener.on_transcript = lambda txt: self.signals.transcript_received.emit(txt)
        tts.register_state_callback(lambda spk: self.signals.tts_state.emit(spk))

    def _on_transcript_received(self, text: str):
        """Transfers hands-free voice speech directly into the Web HUD command processor."""
        if not text or not text.strip():
            return
        logger.info(f"[MainWindow] Hands-free voice detected: '{text}' -> injecting into Web HUD.")
        # Execute JavaScript sendCommand in the web view
        js = f"if (typeof sendCommand === 'function') {{ sendCommand({json.dumps(text.strip())}); }}"
        self.web_view.page().runJavaScript(js)

    def toggle_assistant(self):
        """Toggles window visibility and brings to foreground on hotkey press."""
        if self.isVisible() and not self.isMinimized() and self.isActiveWindow():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()
            self.raise_()

    def emergency_stop(self):
        """Halts all automation immediately."""
        logger.warning("[MainWindow] Emergency stop triggered!")
        safety.trigger_emergency_stop()
        tts.speak("Automation stopped.", interrupt=True)
        # Inform Web HUD of stop
        self.web_view.page().runJavaScript("if (typeof appendMessage === 'function') { appendMessage('jarvis', 'Emergency Stop: Automation halted.'); }")

    def open_settings(self):
        try:
            from gui.settings_dialog import SettingsDialog
            dlg = SettingsDialog(self)
            dlg.exec()
        except Exception as e:
            logger.warning(f"[MainWindow] Settings dialog notice: {e}")

    def _confirm_destructive_action(self, action_description: str) -> bool:
        """Pops up confirmation dialog safely on UI thread."""
        try:
            from PySide6.QtCore import QThread
            if QThread.currentThread() != self.thread():
                logger.warning(f"[MainWindow] Background confirmation for: {action_description}")
                return False
            ret = QMessageBox.question(
                self,
                "Security Confirmation Required",
                f"JARVIS is about to execute a potentially destructive action:\n\n{action_description}\n\nDo you authorize this?",
                QMessageBox.Yes | QMessageBox.No
            )
            return ret == QMessageBox.Yes
        except Exception as e:
            logger.error(f"[MainWindow] Confirmation error: {e}")
            return False

    def closeEvent(self, event):
        if config.minimize_to_tray_on_close:
            event.ignore()
            self.hide()
            self.tray_manager.show_notification(
                "JARVIS Minimized",
                "Still listening in background. Use Ctrl+Alt+Space or tray icon."
            )
        else:
            self.close_application()

    def close_application(self):
        logger.info("[App] Exiting application...")
        self.voice_listener.stop()
        self.hotkey_manager.stop()
        tts.stop()
        sys.exit(0)
