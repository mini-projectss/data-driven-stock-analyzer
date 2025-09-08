from PyQt6.QtWidgets import QPushButton, QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QFont, QBrush, QPixmap,QLinearGradient
from PyQt6.QtCore import Qt, QRectF, QEvent

import os

class RoundedButton(QPushButton):
    def __init__(self, text, bg_color, fg_color, hover_color, parent=None):
        super().__init__(text, parent)
        self.bg_color = QColor(bg_color)
        self.fg_color = QColor(fg_color)
        self.hover_color = QColor(hover_color)
        self.current_bg = self.bg_color
        self.radius = 15
        self.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(160, 45)
        self.setStyleSheet("border: none;")
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            self.current_bg = self.hover_color
            self.update()
            self.setStyleSheet("color: black; border: none;")
        elif event.type() == QEvent.Type.Leave:
            self.current_bg = self.bg_color
            self.update()
            self.setStyleSheet(f"color: white; border: none;")
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), self.radius, self.radius)

        painter.fillPath(path, self.current_bg)
        painter.setPen(self.fg_color if self.current_bg == self.bg_color else QColor("black"))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())

class LoadingPage(QWidget):
    def __init__(self, message="Loading..."):
        super().__init__()
        self.setWindowTitle("Loading")
        self.resize(600, 400)
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # 🔧 FIXED PATH
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        assets_path = os.path.join(project_root, "assets")

        logo_path = os.path.join(assets_path, "logo1.png")

        # Load logo
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.logo_label.setPixmap(pixmap)
            else:
                self.logo_label.setText("⚠️ Logo failed to load.")
        else:
            self.logo_label.setText("⚠️ Logo not found.")

        # App name
        title_label = QLabel("ApexAlytics")
        title_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #eeeeee;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Loading message
        self.message_label = QLabel(message)
        self.message_label.setFont(QFont("Segoe UI", 16))
        self.message_label.setStyleSheet("color: #eeeeee;")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add widgets to layout
        layout.addWidget(self.logo_label)
        layout.addWidget(title_label)
        layout.addWidget(self.message_label)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0.0, QColor("#0f2027"))
        gradient.setColorAt(0.5, QColor("#203a43"))
        gradient.setColorAt(1.0, QColor("#2c5364"))

        painter.fillRect(0, 0, w, h, QBrush(gradient))