from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QFont
from PyQt6.QtCore import (
    Qt, QRectF, QEvent, pyqtProperty, QPropertyAnimation, QEasingCurve
)

class RoundedButton(QPushButton):
    def __init__(self, text, bg_color, fg_color, hover_color, parent=None):
        super().__init__(text, parent)
        # Store original colors
        self._bg_color = QColor(bg_color)
        self._fg_color = QColor(fg_color)
        self._hover_color = QColor(hover_color)
        
        # This will be the property we animate
        self._current_bg_for_anim = self._bg_color

        self.radius = 15
        self.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(160, 45)
        
        # Set initial style using the QColor's name
        self.setStyleSheet(f"color: {self._fg_color.name()}; border: none;")
        self.installEventFilter(self)

        # Setup animation for the background color
        self.animation = QPropertyAnimation(self, b"animatedBackgroundColor")
        self.animation.setDuration(300) # Duration in milliseconds
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(QColor)
    def animatedBackgroundColor(self):
        """ Property getter for the animated background color. """
        return self._current_bg_for_anim

    @animatedBackgroundColor.setter
    def animatedBackgroundColor(self, color):
        """ Property setter that QPropertyAnimation will use. """
        self._current_bg_for_anim = color
        self.update() # Trigger a repaint for each frame of the animation

    def eventFilter(self, obj, event):
        """ Filter events to detect mouse hover. """
        if event.type() == QEvent.Type.Enter:
            self.animation.setEndValue(self._hover_color)
            self.animation.start()
            # Change text color immediately on hover
            self.setStyleSheet("color: black; border: none;") 
        elif event.type() == QEvent.Type.Leave:
            self.animation.setEndValue(self._bg_color)
            self.animation.start()
            # Change text color back immediately
            self.setStyleSheet(f"color: {self._fg_color.name()}; border: none;")
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        """ Custom paint event to draw the rounded rectangle. """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), self.radius, self.radius)

        # Use the animated property for the background fill
        painter.fillPath(path, self._current_bg_for_anim)

        # Let the stylesheet handle the text color, so we just draw the text
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())