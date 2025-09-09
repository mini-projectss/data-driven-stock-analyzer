import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QHBoxLayout, QVBoxLayout, QStackedWidget
)
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QFont, QBrush, QPixmap
from PyQt6.QtCore import Qt

from pages.main_page import MainWindow
from auth.widgets import RoundedButton


class ApexAlyticsApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ApexAlytics")
        self.resize(800, 600)
        self.setMinimumSize(400, 300)
        self.logo = None
        self.main_window = None
        self.load_logo()
        self.init_ui()

    def load_logo(self):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(project_root, "assets", "logo1.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.logo = pixmap

    def init_ui(self):
        # Create stacked widget to host landing + other pages in same window
        self.stack = QStackedWidget()
        # Create landing widget (container) and populate it with current landing UI
        self.landing_widget = QWidget()
        landing_layout = QVBoxLayout()
        landing_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        landing_layout.setSpacing(20)

        # Logo
        self.logo_label = QLabel()
        if self.logo:
            self.logo_label.setPixmap(self.logo)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title
        self.title_label = QLabel("ApexAlytics")
        self.title_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #eeeeee;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Buttons (use RoundedButton from widgets)
        self.login_button = RoundedButton(
            "Login", bg_color="#1e90ff", fg_color="white", hover_color="#63b3ff"
        )
        self.signup_button = RoundedButton(
            "Sign Up", bg_color="#32cd32", fg_color="white", hover_color="#7ef87e"
        )

        self.login_button.clicked.connect(self.open_login)
        self.signup_button.clicked.connect(self.open_signup)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)
        buttons_layout.addWidget(self.login_button)
        buttons_layout.addWidget(self.signup_button)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Footer
        self.footer_label = QLabel("Empowering insights, beautifully.")
        self.footer_label.setFont(QFont("Segoe UI", 10))
        self.footer_label.setStyleSheet("color: #aaaaaa;")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Assemble landing layout
        landing_layout.addWidget(self.logo_label, stretch=0)
        landing_layout.addSpacing(20)
        landing_layout.addWidget(self.title_label)
        landing_layout.addLayout(buttons_layout)
        landing_layout.addSpacing(20)
        landing_layout.addWidget(self.footer_label)

        self.landing_widget.setLayout(landing_layout)

        # Add landing to stack as index 0
        self.stack.addWidget(self.landing_widget)

        # Main layout of this window contains the stacked widget
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

        # Keep references to pages if added later
        self.login_page = None
        self.signup_page = None

    def open_login(self):
        from auth.login_screen import LoginPage

        if self.login_page is None:
            self.login_page = LoginPage(parent=self.stack)
            self.login_page.login_successful.connect(self.handle_login_success)
            self.stack.addWidget(self.login_page)

        self.stack.setCurrentWidget(self.login_page)

    def open_signup(self):
        from auth.signup_screen import SignupPage

        if self.signup_page is None:
            self.signup_page = SignupPage(parent=self.stack)
            self.signup_page.navigate_to_login.connect(self.handle_navigate_to_login)
            self.stack.addWidget(self.signup_page)
        self.stack.setCurrentWidget(self.signup_page)

    def handle_navigate_to_login(self):
        self.open_login()

    def handle_login_success(self):
        if self.main_window is None:
            self.main_window = MainWindow()
            self.stack.addWidget(self.main_window)
        self.stack.setCurrentWidget(self.main_window)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # A rich, dark purple/blue gradient for a more modern feel
        top_left_color = QColor("#0f0c29")
        middle_color = QColor("#302b63")
        bottom_right_color = QColor("#24243e")

        # Use a diagonal gradient for a more dynamic background
        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0.0, top_left_color)
        gradient.setColorAt(0.5, middle_color)
        gradient.setColorAt(1.0, bottom_right_color)

        painter.fillRect(self.rect(), QBrush(gradient))


def main():
    app = QApplication(sys.argv)
    window = ApexAlyticsApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()