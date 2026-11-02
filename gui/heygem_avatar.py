"""
gui/heygem_avatar.py — Digital Human Avatar Visualizer
Inspired by suifeng9203/HeyGem.ai (https://github.com/suifeng9203/HeyGem.ai)

Provides:
- Real-time animated AI digital human companion in PySide6
- Lip sync and speech expression reacting to audio levels
- Seamless sidecar mode alongside the Arc Reactor HUD
"""
import math
import random
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QFont
from PySide6.QtWidgets import QWidget


class HeyGemAvatarWidget(QWidget):
    """Interactive visual digital human avatar based on HeyGem architecture."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.state = "STANDBY"   # "STANDBY", "LISTENING", "SPEAKING", "EXECUTING"
        self.audio_level = 0.0
        self._mouth_open = 0.0
        self._eye_blink = 0.0
        self._pulse = 0.0
        self._blink_counter = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_step)
        self.timer.start(16)  # ~60 fps

    def set_state(self, state: str):
        self.state = state
        self.update()

    def set_audio_level(self, level: float):
        self.audio_level = max(0.0, min(1.0, level))

    def _animate_step(self):
        self._pulse += 0.05

        # Blinking logic
        self._blink_counter += 1
        if self._blink_counter > 180:  # Every ~3 seconds
            if self._blink_counter < 192:
                self._eye_blink = math.sin((self._blink_counter - 180) / 12.0 * math.pi)
            else:
                self._blink_counter = random.randint(0, 60)
                self._eye_blink = 0.0

        # Mouth movement reacts to audio level or speech state
        if self.state == "SPEAKING":
            target_mouth = 0.3 + 0.7 * abs(math.sin(self._pulse * 4.0)) * max(0.2, self.audio_level)
            self._mouth_open += (target_mouth - self._mouth_open) * 0.3
        else:
            self._mouth_open += (0.0 - self._mouth_open) * 0.2

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        size = min(w, h) * 0.85
        r = size / 2

        # 1. Background glow
        glow_color = QColor(14, 165, 233, 40) if self.state in ["LISTENING", "SPEAKING"] else QColor(71, 85, 105, 30)
        painter.setBrush(QBrush(glow_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - r - 10, cy - r - 10, (r + 10) * 2, (r + 10) * 2))

        # 2. Outer holographic boundary ring
        ring_color = QColor(56, 189, 248) if self.state == "SPEAKING" else (
            QColor(34, 197, 94) if self.state == "LISTENING" else QColor(100, 116, 139)
        )
        pen = QPen(ring_color, 2.5)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(15, 23, 42, 220)))
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # 3. Avatar Face Silhouette (Stylized Digital Human Face)
        face_r = r * 0.65
        face_rect = QRectF(cx - face_r, cy - face_r * 1.15, face_r * 2, face_r * 2.3)
        face_grad = QLinearGradient(cx, cy - face_r, cx, cy + face_r)
        face_grad.setColorAt(0.0, QColor(30, 41, 59))
        face_grad.setColorAt(1.0, QColor(15, 23, 42))
        painter.setBrush(QBrush(face_grad))
        painter.setPen(QPen(QColor(56, 189, 248, 120), 1.5))
        painter.drawRoundedRect(face_rect, face_r * 0.8, face_r * 1.1)

        # 4. Eyes (Digital visor / glowing iris with blinking)
        eye_y = cy - face_r * 0.2
        eye_w = face_r * 0.35
        eye_h = max(2.0, face_r * 0.18 * (1.0 - self._eye_blink))

        eye_color = QColor(56, 189, 248) if self.state != "STANDBY" else QColor(148, 163, 184)
        painter.setBrush(QBrush(eye_color))
        painter.setPen(Qt.NoPen)

        # Left & Right Eye
        painter.drawRoundedRect(QRectF(cx - face_r * 0.55, eye_y - eye_h / 2, eye_w, eye_h), 4, 4)
        painter.drawRoundedRect(QRectF(cx + face_r * 0.20, eye_y - eye_h / 2, eye_w, eye_h), 4, 4)

        # 5. HeyGem Talking Mouth / Audio Lip Sync
        mouth_y = cy + face_r * 0.45
        mouth_w = face_r * 0.5
        mouth_h = max(3.0, face_r * 0.35 * self._mouth_open)
        painter.setBrush(QBrush(QColor(244, 63, 94, 200) if self.state == "SPEAKING" else QColor(51, 65, 85)))
        painter.setPen(QPen(QColor(56, 189, 248, 180), 1.5))
        painter.drawRoundedRect(QRectF(cx - mouth_w / 2, mouth_y - mouth_h / 2, mouth_w, mouth_h), 6, 6)

        # 6. Status Label
        painter.setPen(QPen(QColor(148, 163, 184)))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        label_text = f"HEYGEM AI // {self.state}"
        painter.drawText(QRectF(0, h - 25, w, 20), Qt.AlignCenter, label_text)
