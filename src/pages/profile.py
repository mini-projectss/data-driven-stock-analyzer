# src/pages/profile.py
import sys
import os, subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QScrollArea, QFrame, QApplication,QInputDialog,QCompleter
)
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QLinearGradient, QBrush, QPainterPath
)
from PyQt6.QtCore import Qt, QRectF

import firebase_admin
from firebase_admin import credentials, firestore
import yfinance as yf
import pandas as pd

# ---------------------------- Fetch stock symbols ----------------------------
STOCK_SYMBOLS = []
try:
    df_bse = pd.read_csv("ind_bse500list.csv", header=None)
    bse_symbols = df_bse[0].tolist()

    df_nse = pd.read_csv("ind_nse500list.csv", header=None)
    nse_symbols = df_nse[0].tolist()

    # Combine both lists
    STOCK_SYMBOLS = bse_symbols + nse_symbols

except Exception as e:
    print("Failed to load stock symbols:", e)


def get_stock_price(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.history(period="2d")
        if not info.empty:
            current_price = info['Close'][-1]
            prev_close = info['Close'][-2] if len(info) > 1 else current_price
            change_percent = ((current_price - prev_close) / prev_close * 100) if prev_close != 0 else 0
            return current_price, change_percent
    except Exception as e:
        print("Failed to fetch:", symbol, e)
    return None, None

# ---------------------------- Firebase Setup ----------------------------
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()


# ---------------------------- Gradient Background ----------------------------
class GradientWidget(QWidget):
    """Widget with gradient background."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0.0, QColor("#0f0c29"))
        gradient.setColorAt(0.5, QColor("#302b63"))
        gradient.setColorAt(1.0, QColor("#24243e"))

        painter.fillRect(self.rect(), QBrush(gradient))
        super().paintEvent(event)


# ---------------------------- Profile Avatar ----------------------------
class AvatarWidget(QWidget):
    def __init__(self, initials="U", size=100, parent=None):
        super().__init__(parent)
        self.initials = initials
        self.size = size
        self.setFixedSize(size, size)

    def set_initials(self, initials: str):
        self.initials = initials
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(0, 0, self.size, self.size)

        gradient = QLinearGradient(0, 0, self.size, self.size)
        gradient.setColorAt(0.0, QColor("#6c63ff"))
        gradient.setColorAt(1.0, QColor("#302b63"))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)

        path = QPainterPath()
        path.addEllipse(rect)
        painter.fillPath(path, painter.brush())

        painter.setPen(QColor("white"))
        font = QFont("Arial", int(self.size / 3), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.initials)


# ---------------------------- Stock Card Widget ----------------------------
class StockCard(QWidget):
    def __init__(self, uid, symbol, remove_callback, parent=None):
        super().__init__(parent)
        self.uid = uid
        self.symbol = symbol
        self.remove_callback = remove_callback
        self._build_ui()
        self.update_stock_data()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        # Symbol label
        self.symbol_label = QLabel(self.symbol)
        self.symbol_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))

        # Price + Change labels
        self.price_label = QLabel("Loading...")
        self.price_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.change_label = QLabel("")
        self.change_label.setFont(QFont("Arial", 12))

        price_layout = QVBoxLayout()
        price_layout.addWidget(self.price_label, alignment=Qt.AlignmentFlag.AlignRight)
        price_layout.addWidget(self.change_label, alignment=Qt.AlignmentFlag.AlignRight)

        # Remove button
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setStyleSheet("""
            background: #ff4c4c;
            color: #fff;
            border-radius: 8px;
            padding: 5px 10px;
            font-weight: bold;
        """)
        self.remove_btn.clicked.connect(self.remove_stock)

        layout.addWidget(self.symbol_label)
        layout.addStretch()
        layout.addLayout(price_layout)
        layout.addWidget(self.remove_btn)
        self.setStyleSheet("background: #1a1a1a; border-radius: 10px; padding: 5px;")

    def update_stock_data(self):
        def __init__(self, uid, symbol, remove_callback, parent=None):
            super().__init__(parent)
            self.uid = uid
            self.symbol = symbol
            self.remove_callback = remove_callback
            self._build_ui()
            self.update_stock_data()

    def update_stock_data(self):
        price, change = get_stock_price(self.symbol)
        if price is not None:
            self.price_label.setText(f"{price:.2f} ₹")
            self.change_label.setText(f"{change:+.2f}%")
            self.change_label.setStyleSheet(f"color: {'#4caf50' if change>=0 else '#ff4c4c'};")
        else:
            self.price_label.setText("N/A")
            self.change_label.setText("")

    def remove_stock(self):
        if self.remove_callback:
            self.remove_callback(self.symbol, self)

# ---------------------------- Profile Page ----------------------------
class PageWidget(QWidget):
    def __init__(self, uid=None, parent=None):
        super().__init__(parent)
        self.uid = uid
        self.is_editing = False
        self.stock_cards = []
        self._build_ui()
        self.apply_styles()
        if self.uid:
            self.load_user_data()
            self.load_watchlist()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        main_layout.addWidget(scroll)

        bg = GradientWidget()
        scroll.setWidget(bg)

        cl = QVBoxLayout(bg)
        cl.setContentsMargins(50, 40, 50, 40)
        cl.setSpacing(25)

        # Avatar
        self.avatar = AvatarWidget("U", size=100)
        avatar_layout = QHBoxLayout()
        avatar_layout.addStretch()
        avatar_layout.addWidget(self.avatar)
        avatar_layout.addStretch()
        cl.addLayout(avatar_layout)

        title = QLabel("User Profile")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(title)

        # User fields
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setReadOnly(True)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.email_input.setReadOnly(True)

        cl.addWidget(QLabel("Username:"))
        cl.addWidget(self.username_input)
        cl.addWidget(QLabel("Email:"))
        cl.addWidget(self.email_input)

        # Buttons
        btn_layout = QHBoxLayout()
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.toggle_edit)
        self.logout_button = QPushButton("Logout")
        self.logout_button.clicked.connect(self.logout)
        self.logout_button.setStyleSheet("""
            QPushButton {
                background: #ff4c4c;
                color: #fff;
                border-radius: 12px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #cc0000;
            }
        """)
        btn_layout.addWidget(self.edit_button)
        btn_layout.addWidget(self.logout_button)
        cl.addLayout(btn_layout)

        # Add Stock Input with Autocomplete
        input_layout = QHBoxLayout()
        self.stock_input = QLineEdit()
        self.stock_input.setPlaceholderText("Enter stock symbol")
        completer = QCompleter(STOCK_SYMBOLS)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.stock_input.setCompleter(completer)
        input_layout.addWidget(self.stock_input)

        self.add_stock_btn = QPushButton("Add")
        self.add_stock_btn.clicked.connect(self.add_stock_from_input)
        input_layout.addWidget(self.add_stock_btn)
        cl.addLayout(input_layout)

        # Watchlist Heading
        watchlist_label = QLabel("Watchlist")
        watchlist_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        watchlist_label.setStyleSheet("color: #ffffff;")
        cl.addWidget(watchlist_label)

        # Watchlist container
        self.watchlist_container = QWidget()
        self.watchlist_cards_layout = QVBoxLayout(self.watchlist_container)
        self.watchlist_cards_layout.setSpacing(10)
        cl.addWidget(self.watchlist_container)

        cl.addStretch()

    def apply_styles(self):
        self.setStyleSheet("""
            QLabel {
                color: #c0c0c0;
                font-size: 16px;
                font-weight: bold;
            }
            QLineEdit {
                background: #1a1a1a;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 10px;
                font-size: 15px;
            }
            QLineEdit:focus {
                border: 1px solid #6c63ff;
            }
            QPushButton {
                background: #6c63ff;
                color: #fff;
                border-radius: 12px;
                padding: 12px 24px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5852cc;
            }
        """)

    # ---------------- User Data ----------------
    def load_user_data(self):
        if not db or not self.uid:
            return
        try:
            doc = db.collection("users").document(self.uid).get()
            if doc.exists:
                data = doc.to_dict()
                username = data.get("username", "")
                email = data.get("email", "")
                self.username_input.setText(username)
                self.email_input.setText(email)
                initials = (username[:1] if username else email[:1]).upper()
                self.avatar.set_initials(initials)
            else:
                QMessageBox.warning(self, "Error", "No user data found.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load profile: {e}")

    def toggle_edit(self):
        if not self.is_editing:
            self.username_input.setReadOnly(False)
            self.email_input.setReadOnly(True)
            self.edit_button.setText("Save")
            self.is_editing = True
        else:
            self.save_profile()
            self.username_input.setReadOnly(True)
            self.email_input.setReadOnly(True)
            self.edit_button.setText("Edit")
            self.is_editing = False

    def save_profile(self):
        if not self.uid or not db:
            QMessageBox.warning(self, "Error", "Cannot save without user UID or Firestore.")
            return
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "Error", "Username cannot be empty!")
            return
        try:
            db.collection("users").document(self.uid).update({
                "username": username,
            })
            QMessageBox.information(self, "Success", "Profile updated!")
            initials = (username[:1] if username else "").upper()
            self.avatar.set_initials(initials)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def logout(self):
        QMessageBox.information(self, "Logout", "You have been logged out.")
        try:
            main_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
            main_path = os.path.abspath(main_path)
            subprocess.Popen([sys.executable, main_path])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to redirect: {e}")
        QApplication.quit()

    # ---------------- Watchlist ----------------
    def load_watchlist(self):
        if not self.uid:
            return
        try:
            # Clear existing cards
            for card in self.stock_cards:
                card.setParent(None)
            self.stock_cards.clear()

            docs = db.collection("users").document(self.uid).collection("watchlist").stream()
            for doc in docs:
                self.add_stock_card(doc.id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load watchlist: {e}")

    def add_stock_card(self, symbol):
        card = StockCard(self.uid, symbol, remove_callback=self.remove_stock_from_watchlist)
        self.watchlist_cards_layout.addWidget(card)
        self.stock_cards.append(card)

    def add_stock_from_input(self):
        symbol = self.stock_input.text().strip().upper()
        if not symbol:
            return
        try:
            db.collection("users").document(self.uid).collection("watchlist").document(symbol).set({})
            self.add_stock_card(symbol)
            self.stock_input.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add stock: {e}")


    def remove_stock_from_watchlist(self, symbol, card_widget):
        try:
            db.collection("users").document(self.uid).collection("watchlist").document(symbol).delete()
            self.watchlist_cards_layout.removeWidget(card_widget)
            card_widget.setParent(None)
            self.stock_cards.remove(card_widget)
            QMessageBox.information(self, "Removed", f"{symbol} removed from watchlist!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to remove stock: {e}")


# ---------------------------- Alias for main_app.py ----------------------------
Page = PageWidget


# ---------------------------- Standalone Testing ----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    from PyQt6.QtWidgets import QMainWindow
    main_window = QMainWindow()
    main_window.setWindowTitle("Profile Page Test")
    main_window.resize(800, 600)
    page = PageWidget(uid="exampleUID")
    main_window.setCentralWidget(page)
    main_window.show()
    sys.exit(app.exec())
