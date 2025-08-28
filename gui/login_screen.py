from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QFrame
)
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QFont, QBrush
from PyQt6.QtCore import Qt

from widgets import RoundedButton  # Make sure this import is correct


class LoginPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login - ApexAlytics")
        self.resize(800, 600)
        self.setMinimumSize(400, 300)
        self.init_ui()

    def init_ui(self):
        self.card = QFrame()
        self.card.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 15px;
                padding: 30px;
            }
        """)
        self.card.setFixedWidth(400)

        title = QLabel("Login")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username or Email")
        self.username_input.setStyleSheet(self.input_style())

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(self.input_style())

        forgot_label = QLabel("<a href='#' style='color: #aaaaaa;'>Forgot Password?</a>")
        forgot_label.setTextFormat(Qt.TextFormat.RichText)
        forgot_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        forgot_label.setOpenExternalLinks(True)
        forgot_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.login_button = RoundedButton(
            "Login", bg_color="#1e90ff", fg_color="white", hover_color="#63b3ff"
        )
        self.login_button.clicked.connect(self.handle_login)

        self.back_button = RoundedButton(
            "Back", bg_color="#555555", fg_color="white", hover_color="#777777"
        )
        self.back_button.clicked.connect(self.handle_back)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        buttons_layout.addWidget(self.back_button)
        buttons_layout.addWidget(self.login_button)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.addWidget(title)
        layout.addWidget(self.username_input)
        layout.addWidget(self.password_input)
        layout.addWidget(forgot_label)
        layout.addLayout(buttons_layout)

        self.card.setLayout(layout)

        main_layout = QVBoxLayout()
        main_layout.addStretch()
        main_layout.addWidget(self.card, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch()
        main_layout.setContentsMargins(40, 40, 40, 40)

        self.setLayout(main_layout)

    def input_style(self):
        return """
            QLineEdit {
                padding: 10px;
                border: 2px solid #444;
                border-radius: 10px;
                color: white;
                background-color: #2e2e2e;
            }
            QLineEdit:focus {
                border: 2px solid #1e90ff;
            }
        """

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

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        print(f"Attempted login with:\nUsername: {username}\nPassword: {password}")
        # Add your login logic here

    def handle_back(self):
        self.close()  # Closes the login window (adjust as needed)
