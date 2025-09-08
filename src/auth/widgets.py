from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QFont
from PyQt6.QtCore import Qt, QRectF, QEvent

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
