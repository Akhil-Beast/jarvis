import pyaudio
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QCheckBox,
    QComboBox, QSpinBox, QSlider, QPushButton, QTabWidget, QWidget, QMessageBox
)
from PySide6.QtCore import Qt
from config.settings import settings_manager, config


def _get_input_devices():
    """Return list of (index, name) for all audio input devices."""
    devices = [(-1, "System Default")]
    try:
        pa = pyaudio.PyAudio()
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                devices.append((i, f"[{i}] {info['name'][:55]}"))
        pa.terminate()
    except Exception:
        pass
    # Special text-mode entry
    devices.append((-99, "[-99] Text Input Mode (no mic needed — debug)"))
    return devices


class SettingsDialog(QDialog):
    """Configuration dialog for Assistant settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JARVIS Settings & AI Configuration")
        self.resize(560, 520)
        self.setStyleSheet("""
            QDialog { background-color: #0d1117; color: #c9d1d9; }
            QTabWidget::pane { border: 1px solid #30363d; background-color: #161b22; }
            QTabBar::tab { background-color: #21262d; color: #8b949e; padding: 8px 16px; margin-right: 4px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background-color: #161b22; color: #58a6ff; font-weight: bold; }
            QLabel { color: #c9d1d9; font-size: 13px; }
            QLineEdit, QComboBox, QSpinBox { background-color: #0d1117; color: #f0f6fc; border: 1px solid #30363d; border-radius: 4px; padding: 6px; }
            QLineEdit:focus { border: 1px solid #58a6ff; }
            QPushButton { background-color: #238636; color: white; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #2ea043; }
            QPushButton#btnCancel { background-color: #21262d; color: #c9d1d9; }
            QPushButton#btnCancel:hover { background-color: #30363d; }
            QCheckBox { color: #c9d1d9; font-size: 13px; }
        """)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # ---------------------------------------------------------------- #
        # Tab 1: Voice & Triggers                                           #
        # ---------------------------------------------------------------- #
        tab_voice = QWidget()
        l_voice = QVBoxLayout(tab_voice)

        l_voice.addWidget(QLabel("Primary Wake Word:"))
        self.txt_wake = QLineEdit(config.wake_word)
        l_voice.addWidget(self.txt_wake)

        l_voice.addWidget(QLabel("Secondary Wake Word:"))
        self.txt_wake2 = QLineEdit(config.wake_word_secondary)
        l_voice.addWidget(self.txt_wake2)

        self.chk_continuous = QCheckBox("Continuous Listening (process all voice while Active)")
        self.chk_continuous.setChecked(config.continuous_listening)
        l_voice.addWidget(self.chk_continuous)

        self.chk_startup = QCheckBox("Start automatically with Windows")
        self.chk_startup.setChecked(config.start_with_windows)
        l_voice.addWidget(self.chk_startup)

        l_voice.addWidget(QLabel("Speech Rate (words per minute):"))
        self.spin_rate = QSpinBox()
        self.spin_rate.setRange(100, 350)
        self.spin_rate.setValue(config.speech_rate)
        l_voice.addWidget(self.spin_rate)

        # ---- Microphone Device ----
        l_voice.addWidget(QLabel("Microphone Input Device:"))
        self.cmb_mic = QComboBox()
        self._mic_devices = _get_input_devices()
        for idx, name in self._mic_devices:
            self.cmb_mic.addItem(name, idx)
        # Select current
        current_idx = config.mic_device_index
        for i, (idx, _) in enumerate(self._mic_devices):
            if idx == current_idx:
                self.cmb_mic.setCurrentIndex(i)
                break
        l_voice.addWidget(self.cmb_mic)
        l_voice.addWidget(QLabel("  ↑ If mic shows no signal, try each device. Run scratch/mic_test.py to find the best one."))

        # ---- Energy Threshold ----
        l_voice.addWidget(QLabel("Mic Energy Threshold (300–2000 typical):"))
        self.spin_energy = QSpinBox()
        self.spin_energy.setRange(50, 5000)
        self.spin_energy.setValue(config.audio_energy_threshold)
        l_voice.addWidget(self.spin_energy)

        self.chk_dynamic = QCheckBox("Dynamic energy threshold (auto-adjusts to ambient noise)")
        self.chk_dynamic.setChecked(config.dynamic_energy_threshold)
        l_voice.addWidget(self.chk_dynamic)

        l_voice.addStretch()
        self.tabs.addTab(tab_voice, "Triggers & Speech")

        # ---------------------------------------------------------------- #
        # Tab 2: AI Brain                                                    #
        # ---------------------------------------------------------------- #
        tab_brain = QWidget()
        l_brain = QVBoxLayout(tab_brain)

        l_brain.addWidget(QLabel("Primary AI Brain Provider:"))
        self.cmb_provider = QComboBox()
        self.cmb_provider.addItems(["auto", "gemini", "openai", "local_rules"])
        self.cmb_provider.setCurrentText(config.ai_provider)
        l_brain.addWidget(self.cmb_provider)

        l_brain.addWidget(QLabel("Google Gemini API Key (optional):"))
        self.txt_gemini = QLineEdit(config.gemini_api_key)
        self.txt_gemini.setEchoMode(QLineEdit.Password)
        l_brain.addWidget(self.txt_gemini)

        l_brain.addWidget(QLabel("OpenAI API Key (optional):"))
        self.txt_openai = QLineEdit(config.openai_api_key)
        self.txt_openai.setEchoMode(QLineEdit.Password)
        l_brain.addWidget(self.txt_openai)

        l_brain.addWidget(QLabel("ElevenLabs API Key (optional — movie voice):"))
        self.txt_eleven = QLineEdit(config.elevenlabs_api_key)
        self.txt_eleven.setEchoMode(QLineEdit.Password)
        l_brain.addWidget(self.txt_eleven)

        l_brain.addStretch()
        self.tabs.addTab(tab_brain, "AI & Cloud Keys")

        layout.addWidget(self.tabs)

        # ---- Save / Cancel ----
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save Settings")
        btn_save.clicked.connect(self._save_settings)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def _save_settings(self):
        config.wake_word = self.txt_wake.text().strip()
        config.wake_word_secondary = self.txt_wake2.text().strip()
        config.continuous_listening = self.chk_continuous.isChecked()
        config.speech_rate = self.spin_rate.value()
        config.ai_provider = self.cmb_provider.currentText()
        config.gemini_api_key = self.txt_gemini.text().strip()
        config.openai_api_key = self.txt_openai.text().strip()
        config.elevenlabs_api_key = self.txt_eleven.text().strip()

        # Mic settings
        config.mic_device_index = self.cmb_mic.currentData()
        config.audio_energy_threshold = self.spin_energy.value()
        config.dynamic_energy_threshold = self.chk_dynamic.isChecked()

        # Windows startup registry
        if config.start_with_windows != self.chk_startup.isChecked():
            settings_manager.set_start_with_windows(self.chk_startup.isChecked())

        settings_manager.save(config)
        QMessageBox.information(
            self, "Settings Saved",
            "JARVIS configuration updated.\nRestart the assistant for microphone changes to take effect."
        )
        self.accept()
