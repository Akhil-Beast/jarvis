import math
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient
from PySide6.QtWidgets import QWidget

class ArcReactorHUD(QWidget):
    """Custom high-performance animated Arc-Reactor HUD visualizer widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        
        self.rotation_angle = 0.0
        self.audio_level = 0.0       # 0.0 to 1.0
        self.smoothed_level = 0.0
        self.state = "STANDBY"       # "STANDBY", "LISTENING", "SPEAKING", "STOPPED"

        # 60 FPS animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(16)

    def set_state(self, state: str):
        self.state = state
        self.update()

    def set_audio_level(self, level: float):
        self.audio_level = max(0.0, min(1.0, level))

    def _update_animation(self):
        # Rotate outer and inner rings
        self.rotation_angle = (self.rotation_angle + 1.2) % 360.0
        # Smooth audio bounce
        self.smoothed_level += (self.audio_level - self.smoothed_level) * 0.25
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        center_x = w / 2.0
        center_y = h / 2.0
        base_radius = min(w, h) * 0.38

        # Color palette by state
        if self.state == "STOPPED":
            primary_color = QColor(239, 68, 68)      # Red
            glow_color = QColor(239, 68, 68, 80)
        elif self.state == "SPEAKING":
            primary_color = QColor(59, 130, 246)     # Blue
            glow_color = QColor(59, 130, 246, 90)
        elif self.state == "LISTENING":
            primary_color = QColor(0, 255, 220)      # Neon Cyan
            glow_color = QColor(0, 255, 220, 120)
        elif self.state == "THINKING":
            primary_color = QColor(251, 191, 36)     # Amber / thinking
            glow_color = QColor(251, 191, 36, 100)
        else: # STANDBY
            primary_color = QColor(0, 180, 230)      # Electric Cyan
            glow_color = QColor(0, 180, 230, 60)

        # Reactive pulse radius
        pulse = self.smoothed_level * 18.0
        r_outer = base_radius + pulse
        r_mid = base_radius * 0.72 + (pulse * 0.6)
        r_inner = base_radius * 0.42 + (pulse * 0.3)

        # 1. Background radial glow
        gradient = QRadialGradient(center_x, center_y, r_outer * 1.2)
        gradient.setColorAt(0.0, glow_color)
        gradient.setColorAt(0.7, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 20))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(center_x - r_outer * 1.2, center_y - r_outer * 1.2, r_outer * 2.4, r_outer * 2.4))

        # 2. Outer Segmented Ring
        pen_outer = QPen(primary_color, 2.5)
        painter.setPen(pen_outer)
        painter.setBrush(Qt.NoBrush)
        
        # 8 segmented circular arcs
        for i in range(8):
            start_angle = (i * 45 + self.rotation_angle) * 16
            span_angle = 30 * 16
            painter.drawArc(QRectF(center_x - r_outer, center_y - r_outer, r_outer * 2, r_outer * 2), int(start_angle), int(span_angle))

        # 3. Middle Reverse-Rotating Ring with Orbiting Nodes
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(-self.rotation_angle * 1.5)
        
        pen_mid = QPen(QColor(primary_color.red(), primary_color.green(), primary_color.blue(), 160), 1.5, Qt.DashLine)
        painter.setPen(pen_mid)
        painter.drawEllipse(QRectF(-r_mid, -r_mid, r_mid * 2, r_mid * 2))

        # 4 Orbiting Dots
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(primary_color))
        for angle_deg in [0, 90, 180, 270]:
            rad = math.radians(angle_deg)
            nx = r_mid * math.cos(rad)
            ny = r_mid * math.sin(rad)
            painter.drawEllipse(QRectF(nx - 4, ny - 4, 8, 8))
        painter.restore()

        # 4. Glowing Core
        core_grad = QRadialGradient(center_x, center_y, r_inner)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 240))
        core_grad.setColorAt(0.5, primary_color)
        core_grad.setColorAt(1.0, QColor(primary_color.red(), primary_color.green(), primary_color.blue(), 40))
        painter.setBrush(QBrush(core_grad))
        painter.setPen(QPen(primary_color, 1.5))
        painter.drawEllipse(QRectF(center_x - r_inner, center_y - r_inner, r_inner * 2, r_inner * 2))
