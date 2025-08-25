# src/pages/portfolio.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

class Page(QWidget):               # or name it PortfolioPage
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("Portfolio")
        title.setFont(QFont("Segoe UI", 18))
        title.setStyleSheet("color:#E6EEF6;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(QLabel("This is the portfolio page (placeholder)."))
        layout.addStretch()
