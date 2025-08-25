#!/usr/bin/env python3
# main_app.py
# Main app: reusable sidebar + stacked pages
# Expects page modules in src/pages/*.py exposing a QWidget subclass named Page / DashboardPage / PageWidget / MainWidget.

import sys
import importlib
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QSizePolicy, QSpacerItem
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

PAGE_MODULES = [
    ("Dashboard", "dashboard"),
    ("Portfolio", "portfolio"),
    ("Prediction", "prediction"),
    ("News_Sentiment", "news_sentiment"),
    ("Political Trading", "political_trading"),
    ("Google Trends", "google_trends"),
    ("Profile", "profile"),
]

# helper: try importing src.pages.<module> then pages.<module>, then plain <module>
def import_page_class(basename: str):
    candidates = [
        f"src.pages.{basename}",
        f"pages.{basename}",
        basename
    ]
    class_names = ("Page", "DashboardPage", "PageWidget", "MainWidget")
    for modname in candidates:
        try:
            mod = importlib.import_module(modname)
        except Exception:
            continue
        # try class names
        for cname in class_names:
            cls = getattr(mod, cname, None)
            if cls is not None:
                return cls
        # fallback: find any QWidget subclass in module
        import inspect
        for obj_name in dir(mod):
            obj = getattr(mod, obj_name)
            try:
                if inspect.isclass(obj) and issubclass(obj, QWidget):
                    return obj
            except Exception:
                continue
    return None

# simple placeholder page when a real page is missing
class BlankPage(QWidget):
    def __init__(self, title: str = "Blank Page"):
        super().__init__()
        layout = QVBoxLayout(self)
        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #E6EEF6;")
        sub = QLabel("This page is a placeholder. Put page code in src/pages/<module>.py")
        sub.setStyleSheet("color: #AFC3D8;")
        layout.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(sub, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addStretch()

# small reusable sidebar (kept minimal; you can move to src/widgets/sidebar.py if desired)
class Sidebar(QFrame):
    def __init__(self, menu_items):
        super().__init__()
        self.setFixedWidth(220)
        self.setStyleSheet("background: #0F1215;")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16,16,16,16)
        self.layout.setSpacing(10)

        title = QLabel("Apex Analytics")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #EAF2FF;")
        self.layout.addWidget(title)

        self.layout.addSpacing(6)
        menu_label = QLabel("MENU")
        menu_label.setStyleSheet("color:#9aa4b6; font-size:10px;")
        self.layout.addWidget(menu_label)

        self.menu_buttons = []
        for name in menu_items:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setStyleSheet(self._button_style(False))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.layout.addWidget(btn)
            self.menu_buttons.append(btn)

        self.layout.addItem(QSpacerItem(20,20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        acc_label = QLabel("ACCOUNT")
        acc_label.setStyleSheet("color:#9aa4b6; font-size:10px;")
        self.layout.addWidget(acc_label)
        for t in ("Profile","Settings"):
            b = QPushButton(t)
            b.setFixedHeight(36)
            b.setStyleSheet(self._button_style(False))
            self.layout.addWidget(b)

        self.layout.addStretch()
        # theme placeholder
        theme = QLabel("Dark Mode")
        theme.setStyleSheet("color:#C4CEDA;")
        self.layout.addWidget(theme, alignment=Qt.AlignmentFlag.AlignLeft)

    def _button_style(self, selected: bool):
        if selected:
            return ("QPushButton{background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1F7A7A, stop:1 #2AA6A6);"
                    "color:#F5FFFF; border-radius:8px; font-weight:600; text-align:left; padding-left:12px;}")
        else:
            return ("QPushButton{background:transparent; color:#D6DBE0; border-radius:8px; text-align:left; padding-left:12px;}"
                    "QPushButton:hover{background:#1C1E22;}")

    def set_selected_index(self, idx: int):
        for i, b in enumerate(self.menu_buttons):
            b.setChecked(i==idx)
            b.setStyleSheet(self._button_style(i==idx))

# main window that holds sidebar + stacked pages
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apex Analytics")
        self.resize(1360, 820)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        # build sidebar
        page_titles = [t for t,m in PAGE_MODULES]
        self.sidebar = Sidebar(page_titles)
        layout.addWidget(self.sidebar)

        # stacked widget
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        # import pages (or fallback blanks)
        self.pages = []
        for title, modname in PAGE_MODULES:
            cls = import_page_class(modname)
            if cls:
                try:
                    widget = cls()
                except Exception:
                    # constructor required args or failed -> placeholder
                    widget = BlankPage(f"{title} (module found, couldn't instantiate)")
            else:
                widget = BlankPage(title)
            self.pages.append(widget)
            self.stack.addWidget(widget)

        # wire up sidebar buttons
        for i, btn in enumerate(self.sidebar.menu_buttons):
            btn.clicked.connect(lambda checked, idx=i: self.change_page(idx))

        # initial selection
        self.change_page(0)

    def change_page(self, index:int):
        self.stack.setCurrentIndex(index)
        self.sidebar.set_selected_index(index)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # a minimal global dark-ish style
    app.setStyleSheet("""
        QMainWindow{background:#0B0D0E; color:#E6EEF6;}
        QLabel{color:#DDE8F5;}
    """)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
