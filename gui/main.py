import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QFont, QBrush, QPixmap, QPainterPath
from PyQt6.QtCore import Qt, QRectF

from widgets import RoundedButton


class ApexAlyticsApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ApexAlytics")
        self.resize(800, 600)
        self.setMinimumSize(400, 300)
        self.logo = None
        self.load_logo()
        self.init_ui()

    def load_logo(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "assets", "logo1.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.logo = pixmap

    def init_ui(self):
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

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(20)

        self.logo_label = QLabel()
        if self.logo:
            self.logo_label.setPixmap(self.logo)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("ApexAlytics")
        self.title_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #eeeeee;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.footer_label = QLabel("Empowering insights, beautifully.")
        self.footer_label.setFont(QFont("Segoe UI", 10))
        self.footer_label.setStyleSheet("color: #aaaaaa;")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(self.logo_label, stretch=0)
        main_layout.addSpacing(20)
        main_layout.addWidget(self.title_label)
        main_layout.addLayout(buttons_layout)
        main_layout.addSpacing(20)
        main_layout.addWidget(self.footer_label)

        self.setLayout(main_layout)

    def open_login(self):
        from login_screen import LoginPage
        self.login_window = LoginPage()
        self.login_window.show()

    def open_signup(self):
        from signup_screen import SignupPage
        self.signup_window = SignupPage()
        self.signup_window.show()


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        top_color = QColor("#0f2027")
        middle_color = QColor("#203a43")
        bottom_color = QColor("#2c5364")

        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0.0, top_color)
        gradient.setColorAt(0.5, middle_color)
        gradient.setColorAt(1.0, bottom_color)

        painter.fillRect(0, 0, w, h, QBrush(gradient))

def main():
    app = QApplication(sys.argv)
    window = ApexAlyticsApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
