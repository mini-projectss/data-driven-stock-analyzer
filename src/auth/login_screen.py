import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QFrame, QStackedWidget
)
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QFont, QBrush, QPixmap
from PyQt6.QtCore import Qt

from auth.widgets import RoundedButton


class LoginPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login - ApexAlytics")
        self.resize(800, 600)
        self.setMinimumSize(400, 300)
        self.logo = None
        self.load_logo()
        self.init_ui()

    def load_logo(self):
        # The script is in src/auth, so we go up 3 levels to the project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logo_path = os.path.join(project_root, "assets", "logo1.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                # Scaled to a suitable size for the login card
                pixmap = pixmap.scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.logo = pixmap

    def init_ui(self):
        self.card = QFrame()
        self.card.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 0.9);
                border-radius: 15px;
                padding: 30px;
            }
        """)
        self.card.setFixedWidth(400)

        title = QLabel("Login")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background: transparent;")
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
        forgot_label.setStyleSheet("background: transparent;")

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
        
        # --- Add Logo ---
        if self.logo:
            logo_label = QLabel()
            logo_label.setPixmap(self.logo)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setStyleSheet("background: transparent;")
            layout.addWidget(logo_label)

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

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        print(f"Attempted login with:\nUsername: {username}\nPassword: {password}")
        # Add your login logic here

    def _find_ancestor_stack(self):
        ancestor = self.parent()
        while ancestor is not None:
            if isinstance(ancestor, QStackedWidget):
                return ancestor
            ancestor = ancestor.parent()
        return None

    def handle_back(self):
        stack = self._find_ancestor_stack()
        if stack is not None:
            stack.setCurrentIndex(0)
        else:
            self.close()