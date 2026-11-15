import sys
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox
)

from config.settings import config
from core.safety import safety, logger
from core.tts_engine import tts
from core.brain import brain, ActionPlan
from automation.orchestrator import orchestrator
from gui.hud_visualizer import ArcReactorHUD
from gui.heygem_avatar import HeyGemAvatarWidget
from gui.system_tray import SystemTrayManager
from gui.settings_dialog import SettingsDialog

BASE_DIR = Path(__file__).resolve().parent.parent


class BrainWorker(QThread):
    """Off-thread brain planner — prevents GUI freeze during Gemini API calls."""
    plan_ready = Signal(object)   # emits ActionPlan
    error = Signal(str)

    def __init__(self, command: str, parent=None):
        super().__init__(parent)
        self._command = command

    def run(self):
        try:
            plan = brain.plan_command(self._command)
            self.plan_ready.emit(plan)
        except Exception as e:
            logger.error(f"[BrainWorker] Planning error: {e}")
            self.error.emit(str(e))


class GuiSignals(QObject):
    """Thread-safe Qt signal dispatcher."""
    audio_level = Signal(float)
    transcript_received = Signal(str)
    state_changed = Signal(bool)
    step_updated = Signal(int, dict, str)
    tts_state = Signal(bool)
    plan_ready = Signal(object)
    planning_started = Signal(str)

class MainWindow(QMainWindow):
    """Modern Desktop HUD Interface for JARVIS Voice Control Assistant."""

    def __init__(self, voice_listener, hotkey_manager):
        super().__init__()
        self.voice_listener = voice_listener
        self.hotkey_manager = hotkey_manager

        self.signals = GuiSignals()
        self._connect_signals()

        self.setWindowTitle("JARVIS // Windows Voice Automation Assistant")
        self.resize(780, 680)
        self.setMinimumSize(600, 500)
        self.setWindowIcon(QIcon(str(BASE_DIR / "assets" / "icon_active.png")))

        self._apply_theme()
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

    def _connect_signals(self):
        self.signals.audio_level.connect(self._on_audio_level)
        self.signals.transcript_received.connect(self._on_transcript_received)
        self.signals.state_changed.connect(self._on_state_changed)
        self.signals.step_updated.connect(self._on_step_updated)
        self.signals.tts_state.connect(self._on_tts_state)

        # Wire voice listener callbacks to Qt signals
        self.voice_listener.on_level = lambda lvl: self.signals.audio_level.emit(lvl)
        self.voice_listener.on_transcript = lambda txt: self.signals.transcript_received.emit(txt)
        self.voice_listener.on_state_change = lambda act: self.signals.state_changed.emit(act)
        tts.register_state_callback(lambda spk: self.signals.tts_state.emit(spk))
        orchestrator.on_step_update = lambda idx, stp, stat: self.signals.step_updated.emit(idx, stp, stat)

    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b0f19;
            }
            QWidget {
                color: #e2e8f0;
                font-family: 'Segoe UI', 'Roboto', sans-serif;
            }
            QFrame#card {
                background-color: #121826;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
            QPushButton#btnToggleActive {
                background-color: #0284c7;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px 20px;
                border: 1px solid #38bdf8;
            }
            QPushButton#btnToggleActive:hover {
                background-color: #0369a1;
            }
            QPushButton#btnToggleInactive {
                background-color: #334155;
                color: #94a3b8;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px 20px;
                border: 1px solid #475569;
            }
            QPushButton#btnToggleInactive:hover {
                background-color: #475569;
                color: #f1f5f9;
            }
            QPushButton#btnStop {
                background-color: #dc2626;
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px 18px;
                border: 1px solid #f87171;
            }
            QPushButton#btnStop:hover {
                background-color: #b91c1c;
            }
            QPushButton#btnSecondary {
                background-color: #1e293b;
                color: #cbd5e1;
                font-size: 12px;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 6px 14px;
            }
            QPushButton#btnSecondary:hover {
                background-color: #334155;
                color: #ffffff;
            }
            QTableWidget {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 6px;
                gridline-color: #1e293b;
                color: #e2e8f0;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)

    def _build_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # 1. Top Header Bar
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("J.A.R.V.I.S. // DESKTOP AUTOMATION")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8; letter-spacing: 1px;")
        self.lbl_status = QLabel("● SYSTEM STANDBY (Press Ctrl+Alt+Space to Activate)")
        self.lbl_status.setStyleSheet("font-size: 12px; color: #94a3b8;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(self.lbl_status)
        header.addLayout(title_box)

        header.addStretch()

        # Master Toggle Button
        self.btn_toggle = QPushButton("ACTIVATE LISTENING")
        self.btn_toggle.setObjectName("btnToggleInactive")
        self.btn_toggle.clicked.connect(self.toggle_assistant)
        header.addWidget(self.btn_toggle)

        # Emergency Stop Button
        self.btn_stop = QPushButton("🛑 EMERGENCY STOP")
        self.btn_stop.setObjectName("btnStop")
        self.btn_stop.clicked.connect(self.emergency_stop)
        header.addWidget(self.btn_stop)

        layout.addLayout(header)

        # 2. Central Arc-Reactor & HeyGem Digital Avatar Visualizer
        center_card = QFrame()
        center_card.setObjectName("card")
        center_layout = QVBoxLayout(center_card)
        center_layout.setContentsMargins(12, 10, 12, 12)
        center_layout.setAlignment(Qt.AlignCenter)

        visual_container = QHBoxLayout()
        visual_container.setAlignment(Qt.AlignCenter)

        self.hud = ArcReactorHUD()
        visual_container.addWidget(self.hud)

        self.avatar = HeyGemAvatarWidget()
        visual_container.addWidget(self.avatar)

        center_layout.addLayout(visual_container)

        self.lbl_transcript = QLabel("Say 'Hey Assistant' or 'Jarvis' to execute commands...")
        self.lbl_transcript.setAlignment(Qt.AlignCenter)
        self.lbl_transcript.setStyleSheet("""
            font-size: 14px;
            color: #38bdf8;
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 6px;
            padding: 8px 16px;
            min-height: 24px;
        """)
        center_layout.addWidget(self.lbl_transcript)
        layout.addWidget(center_card, stretch=2)

        # 3. Action Execution Pipeline Table
        pipeline_card = QFrame()
        pipeline_card.setObjectName("card")
        pipe_layout = QVBoxLayout(pipeline_card)
        pipe_layout.setContentsMargins(12, 10, 12, 10)

        pipe_header = QHBoxLayout()
        lbl_pipe_title = QLabel("AUTOMATION PIPELINE EXECUTION")
        lbl_pipe_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #94a3b8;")
        pipe_header.addWidget(lbl_pipe_title)
        pipe_header.addStretch()

        btn_vision = QPushButton("👁 Inspect Screen")
        btn_vision.setObjectName("btnSecondary")
        btn_vision.setToolTip("Take a screenshot and use Gemini Vision to see what is on the screen")
        btn_vision.clicked.connect(lambda: self._on_transcript_received("what is on my screen"))
        pipe_header.addWidget(btn_vision)

        btn_apks = QPushButton("📱 Find APKs")
        btn_apks.setObjectName("btnSecondary")
        btn_apks.setToolTip("Scan Desktop, Downloads, and Phone for APK files")
        btn_apks.clicked.connect(lambda: self._on_transcript_received("find all apks"))
        pipe_header.addWidget(btn_apks)

        btn_clear = QPushButton("Clear")
        btn_clear.setObjectName("btnSecondary")
        btn_clear.clicked.connect(self._clear_table)
        pipe_header.addWidget(btn_clear)
        pipe_layout.addLayout(pipe_header)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Step", "Action & Parameters", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        pipe_layout.addWidget(self.table)

        layout.addWidget(pipeline_card, stretch=3)

        # 4. Bottom Footer Toolbar
        footer = QHBoxLayout()
        lbl_hint = QLabel("Shortcuts: [Ctrl+Alt+Space] Toggle | [Esc] Emergency Abort")
        lbl_hint.setStyleSheet("font-size: 11px; color: #64748b;")
        footer.addWidget(lbl_hint)
        footer.addStretch()

        btn_settings = QPushButton("⚙ Settings")
        btn_settings.setObjectName("btnSecondary")
        btn_settings.clicked.connect(self.open_settings)
        footer.addWidget(btn_settings)

        btn_tray = QPushButton("Minimize to Tray")
        btn_tray.setObjectName("btnSecondary")
        btn_tray.clicked.connect(self.hide)
        footer.addWidget(btn_tray)

        layout.addLayout(footer)

    def toggle_assistant(self):
        active = self.voice_listener.toggle()

    def emergency_stop(self):
        safety.trigger_emergency_stop()
        self.hud.set_state("STOPPED")
        self.avatar.set_state("STANDBY")
        self.lbl_status.setText("🛑 EMERGENCY STOP TRIGGERED (Tasks Halted)")
        self.lbl_status.setStyleSheet("font-size: 12px; color: #ef4444; font-weight: bold;")
        tts.speak("Emergency stop engaged.", interrupt=True)

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def _on_state_changed(self, is_active: bool):
        self.tray_manager.set_active_state(is_active)
        if is_active:
            self.btn_toggle.setText("DEACTIVATE ASSISTANT")
            self.btn_toggle.setObjectName("btnToggleActive")
            self.lbl_status.setText("● ONLINE & LISTENING (Speak voice commands)")
            self.lbl_status.setStyleSheet("font-size: 12px; color: #38bdf8; font-weight: bold;")
            self.hud.set_state("LISTENING")
            self.avatar.set_state("LISTENING")
            tts.speak("Online, sir.")
        else:
            self.btn_toggle.setText("ACTIVATE LISTENING")
            self.btn_toggle.setObjectName("btnToggleInactive")
            self.lbl_status.setText("● SYSTEM STANDBY (Press Ctrl+Alt+Space to Activate)")
            self.lbl_status.setStyleSheet("font-size: 12px; color: #94a3b8;")
            self.hud.set_state("STANDBY")
            self.avatar.set_state("STANDBY")
        self.btn_toggle.setStyle(self.btn_toggle.style())

    def _on_audio_level(self, level: float):
        self.hud.set_audio_level(level)
        self.avatar.set_audio_level(level)

    def _on_tts_state(self, is_speaking: bool):
        if is_speaking:
            self.hud.set_state("SPEAKING")
            self.avatar.set_state("SPEAKING")
        else:
            if self.voice_listener.is_active:
                self.hud.set_state("LISTENING")
                self.avatar.set_state("LISTENING")
            else:
                self.hud.set_state("STANDBY")
                self.avatar.set_state("STANDBY")

    def _on_transcript_received(self, text: str):
        self.lbl_transcript.setText(f"You said: \"{text}\"")
        self.lbl_status.setText(f"🧠 Planning: '{text}'…")
        self.hud.set_state("THINKING")
        self.avatar.set_state("THINKING")

        # Spawn off-thread worker — prevents GUI freeze during Gemini API calls
        self._brain_worker = BrainWorker(text)
        self._brain_worker.plan_ready.connect(self._on_plan_ready)
        self._brain_worker.error.connect(self._on_plan_error)
        self._brain_worker.start()

    def _on_plan_ready(self, plan: ActionPlan):
        """Receives the ActionPlan on the main thread after BrainWorker finishes."""
        # Restore UI state
        if self.voice_listener.is_active:
            self.hud.set_state("LISTENING")
            self.avatar.set_state("LISTENING")
            self.lbl_status.setText("● ONLINE & LISTENING (Speak voice commands)")
            self.lbl_status.setStyleSheet("font-size: 12px; color: #38bdf8; font-weight: bold;")
        else:
            self.hud.set_state("STANDBY")
            self.avatar.set_state("STANDBY")

        # Populate execution table
        self.table.setRowCount(len(plan.steps))
        for row, step in enumerate(plan.steps):
            self.table.setItem(row, 0, QTableWidgetItem(f"#{row + 1}"))
            action_desc = f"{step.get('action')}: { {k: v for k, v in step.items() if k != 'action'} }"
            self.table.setItem(row, 1, QTableWidgetItem(action_desc))
            self.table.setItem(row, 2, QTableWidgetItem("⏳ PENDING"))

        # Execute plan in background orchestrator thread
        orchestrator.execute_plan_async(plan)

    def _on_plan_error(self, error_msg: str):
        """Handles brain planning errors gracefully."""
        self.lbl_status.setText(f"⚠ Planning error — retrying with fallback")
        self.lbl_status.setStyleSheet("font-size: 12px; color: #f59e0b;")
        logger.error(f"[MainWindow] BrainWorker error: {error_msg}")
        tts.speak("I encountered an error planning that command, sir.")

    def _on_step_updated(self, index: int, step: dict, status: str):
        if 0 <= index < self.table.rowCount():
            icon_map = {
                "RUNNING": "⚡ RUNNING",
                "SUCCESS": "✓ DONE",
                "FAILED": "✗ FAILED",
                "ABORTED": "🛑 STOPPED"
            }
            item = QTableWidgetItem(icon_map.get(status, status))
            if status == "SUCCESS":
                item.setForeground(Qt.green)
            elif status in ["FAILED", "ABORTED"]:
                item.setForeground(Qt.red)
            elif status == "RUNNING":
                item.setForeground(Qt.cyan)
            self.table.setItem(index, 2, item)

    def _clear_table(self):
        self.table.setRowCount(0)

    def _confirm_destructive_action(self, action_description: str) -> bool:
        """Pops up confirmation dialog on UI thread."""
        ret = QMessageBox.question(
            self,
            "Security Confirmation Required",
            f"JARVIS is about to execute a potentially destructive action:\n\n{action_description}\n\nDo you authorize this?",
            QMessageBox.Yes | QMessageBox.No
        )
        return ret == QMessageBox.Yes

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
