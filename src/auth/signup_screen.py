from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QFrame ,QMessageBox
)
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QFont, QBrush
from PyQt6.QtCore import Qt
from PyQt6.QtCore import pyqtSignal
from auth.widgets import RoundedButton 
from auth.login_screen import LoginPage
import pyrebase

firebase_config = {
    "apiKey": "AIzaSyCMxdihdCyXTl_OZ3aDZ84LX0sM_no7jWw",
    "authDomain": "data-driven-stock-analyzer.appspot.com",
    "databaseURL": "https://data-driven-stock-analyzer.firebaseio.com",
    "projectId": "data-driven-stock-analyzer",
    "storageBucket": "data-driven-stock-analyzer.firebasestorage.app",
    "messagingSenderId": "206028689023",
    "appId": "1:206028689023:web:5c36ab2b9aa30266b0794a",
    "measurementId": "G-W5V8X55W49"
}
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

class SignupPage(QWidget):
    signup_success = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign Up - ApexAlytics")
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

        title = QLabel("Create Account")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setStyleSheet(self.input_style())

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.email_input.setStyleSheet(self.input_style())

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(self.input_style())

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm Password")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setStyleSheet(self.input_style())

        self.signup_button = RoundedButton(
            "Sign Up", bg_color="#32cd32", fg_color="white", hover_color="#7ef87e"
        )
        self.signup_button.clicked.connect(self.handle_signup)

        self.back_button = RoundedButton(
            "Back", bg_color="#555555", fg_color="white", hover_color="#777777"
        )
        self.back_button.clicked.connect(self.handle_back)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        buttons_layout.addWidget(self.back_button)
        buttons_layout.addWidget(self.signup_button)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.addWidget(title)
        layout.addWidget(self.username_input)
        layout.addWidget(self.email_input)
        layout.addWidget(self.password_input)
        layout.addWidget(self.confirm_password_input)
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
                border: 2px solid #32cd32;
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

    def handle_signup(self):
        username = self.username_input.text()
        email = self.email_input.text()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()

        if len(password) < 6:
            QMessageBox.warning(self, "Signup Error", "Password must be at least 6 characters!")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "Signup Error", "Passwords do not match!")
            return

        try:
            user = auth.create_user_with_email_and_password(email, password)
            QMessageBox.information(self, "Signup Successful", "Your account has been created!")
            self.close()  # Close signup window
            self.signup_success.emit()
        except Exception as e:
            QMessageBox.critical(self, "Signup Failed", str(e))


    def handle_back(self):
        self.close()  # This will close the signup window and return control to the main window
