import sys
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QMainWindow, QPushButton, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QStackedWidget
from PyQt6.QtCore import Qt
# Matplotlib imports for embedding
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import random

class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        # Create a Matplotlib canvas to embed a chart
        canvas = FigureCanvas(Figure(figsize=(5,3)))
        layout.addWidget(canvas)
        ax = canvas.figure.subplots()
        # Generate random stock-like data for demonstration
        dates = list(range(1, 51))
        prices = [100 + random.uniform(-5, 5) for _ in dates]
        ax.plot(dates, prices, color='teal', marker='o')
        ax.set_title("Sample Stock Price")
        ax.set_xlabel("Time")
        ax.set_ylabel("Price")
        # Stretch layout
        layout.addStretch()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stock Dashboard")
        self.resize(800, 600)
        # Main container widget
        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        # Navigation bar
        nav_bar = QWidget()
        nav_bar.setFixedHeight(50)
        nav_bar.setStyleSheet("""
            background-color: #2E3B55;
            border-bottom: 2px solid #1F2A40;
        """)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(10, 5, 10, 5)
        nav_layout.setSpacing(20)
        btn_dashboard = QPushButton("Dashboard")
        btn_page2 = QPushButton("Page 2")
        btn_page3 = QPushButton("Page 3")
        for btn in (btn_dashboard, btn_page2, btn_page3):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                color: #FFFFFF;
                background-color: #3C4A6B;
                border: none;
                padding: 8px 16px;
                border-radius: 12px;
            """)
            btn_layout = nav_layout.addWidget(btn)
        main_layout.addWidget(nav_bar)

        # Stacked widget for pages
        self.stacked = QStackedWidget()
        # Create pages
        page1 = DashboardPage()
        page2 = QLabel("Page 2 Content (Placeholder)")
        page2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page3 = QLabel("Page 3 Content (Placeholder)")
        page3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stacked.addWidget(page1)
        self.stacked.addWidget(page2)
        self.stacked.addWidget(page3)
        main_layout.addWidget(self.stacked)

        # Connect buttons to change pages
        btn_dashboard.clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        btn_page2.clicked.connect(lambda: self.stacked.setCurrentIndex(1))
        btn_page3.clicked.connect(lambda: self.stacked.setCurrentIndex(2))

        # Example styling for rounded main window (if frameless) -- optional
        self.setStyleSheet("QMainWindow { border-radius: 10px; }")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # Optional: Remove window frame and enable translucency for custom shape
    # main = MainWindow()
    # main.setWindowFlag(Qt.WindowType.FramelessWindowHint)
    # main.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    main = MainWindow()
    main.show()
    sys.exit(app.exec())
