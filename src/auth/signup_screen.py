import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QFrame, QStackedWidget, QMessageBox
)
from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QFont, QBrush, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal
from auth.widgets import RoundedButton, KeyboardNavigationMixin

import  pyrebase
import firebase_admin
from firebase_admin import credentials, firestore

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
# Firebase Admin SDK (for Firestore)
if not firebase_admin._apps:
    # Use your service account key (download from Firebase Console)
    cred = credentials.Certificate(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "serviceAccountKey.json"
        )
    )
    firebase_admin.initialize_app(cred)

db = firestore.client()

class SignupPage(QWidget, KeyboardNavigationMixin):
    navigate_to_login = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sign Up - ApexAlytics")
        self.resize(800, 600)
        self.setMinimumSize(400, 300)
        self.logo = None
        self.load_logo()
        self.init_ui()
        self.focusable_widgets = [
            self.username_input,
            self.email_input,
            self.password_input,
            self.confirm_password_input,
            self.signup_button,
            self.back_button
        ]
        self.init_keyboard_navigation()

    def load_logo(self):
        # The script is in src/auth, so we go up 3 levels to the project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logo_path = os.path.join(project_root, "assets", "logo1.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                # Scaled to a suitable size for the signup card
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

        title = QLabel("Create Account")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: white; background: transparent;")
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

        # --- Add Logo ---
        if self.logo:
            logo_label = QLabel()
            logo_label.setPixmap(self.logo)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setStyleSheet("background: transparent;")
            layout.addWidget(logo_label)
        
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
            uid = user['localId']
            db.collection("users").document(uid).set({"username": username, "email": email})
            QMessageBox.information(self, "Signup Successful", "Your account has been created!")
            self.navigate_to_login.emit()
        except Exception as e:
            QMessageBox.critical(self, "Signup Failed", str(e))


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
            