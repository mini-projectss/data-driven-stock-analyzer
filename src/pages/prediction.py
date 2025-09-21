#!/usr/bin/env python3
# Apex Analytics - Prediction Page
# Design mock-up based on Figma prompt and dashboard.py styles.
# This page is a QWidget intended to be loaded by main_page.py
#
# v4: Final fix for transparent tab pane background.

import sys
import os
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QFrame, QHeaderView, QSizePolicy, QAbstractItemView, QTabWidget,
    QSpacerItem, QCheckBox
)
from PyQt6.QtGui import QFont, QPainter, QColor, QLinearGradient, QBrush
from PyQt6.QtCore import Qt, QSize
import matplotlib
matplotlib.use('qtagg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ---------------------------- Custom Gradient Background Widget ----------------------------
# (Copied from dashboard.py for style consistency)
class GradientWidget(QWidget):
    """A widget with a rich, cool-toned diagonal gradient background."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        # Same rich gradient as the dashboard/login
        top_left_color = QColor("#0f0c29")
        middle_color = QColor("#302b63")
        bottom_right_color = QColor("#24243e")

        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0.0, top_left_color)
        gradient.setColorAt(0.5, middle_color)
        gradient.setColorAt(1.0, bottom_right_color)

        painter.fillRect(self.rect(), QBrush(gradient))
        super().paintEvent(event)

# ---------------------------- Main Prediction Page Widget ----------------------------
class PredictionPage(GradientWidget):
    """
    Main prediction page, inheriting from GradientWidget for the background.
    This class will be found and loaded by main_page.py's importer.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Title
        title = QLabel("Prediction & Analysis Platform")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #EAF2FF; background:transparent;")
        main_layout.addWidget(title)

        # --- Main Tab Widget ---
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(self._get_tab_bar_style())
        
        # --- Create each tab ---
        self.analyze_tab = self._create_analyze_tab()
        self.screener_tab = self._create_screener_tab()
        self.watchlist_tab = self._create_watchlist_tab()
        
        # --- Add tabs ---
        self.tab_widget.addTab(self.analyze_tab, "Analyze")
        self.tab_widget.addTab(self.screener_tab, "Market Screener")
        self.tab_widget.addTab(self.watchlist_tab, "Watchlist")
        
        main_layout.addWidget(self.tab_widget)
        
        # Set initial chart plot
        self._plot_dummy_prediction_chart()
        self._set_dummy_table_data(self.analyze_table)
        self._set_dummy_table_data(self.screener_table, 20)
        self._set_dummy_table_data(self.watchlist_table, 3)

    # ---------------------------- Tab Creation Methods ----------------------------
    
    def _create_analyze_tab(self):
        """Creates the 'Analyze' tab content."""
        tab_widget = QWidget()
        # Note: Individual stylesheet is removed from here, now handled globally by _get_tab_bar_style
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 10, 0, 0)
        tab_layout.setSpacing(12)

        # --- 1. Controls Bar ---
        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        controls_frame.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px; padding: 10px;")
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setSpacing(10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search BSE/NSE Ticker...")
        self.search_input.setFixedHeight(36)
        self.search_input.setStyleSheet(self._search_bar_style())
        controls_layout.addWidget(self.search_input, 2) 

        controls_layout.addWidget(self._create_filter_pill("Exchange:", ["BSE", "NSE"]))
        controls_layout.addWidget(self._create_filter_pill("Time Range:", ["Days (7D)", "Hours (24H)", "Minutes (1H)"]))

        analyze_btn = QPushButton("Analyze Symbol")
        analyze_btn.setFixedHeight(36)
        analyze_btn.setStyleSheet(self._pill_button_style_accent()) 
        analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_layout.addWidget(analyze_btn)
        
        tab_layout.addWidget(controls_frame)

        # --- 2. Content Area (Chart + Table) ---
        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)
        
        # --- 2a. Left Side (Chart) ---
        chart_card = QFrame()
        chart_card.setFrameShape(QFrame.Shape.StyledPanel)
        chart_card.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px;")
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(12, 12, 12, 12)
        
        self.chart_fig = Figure(figsize=(8, 3), dpi=100)
        self.chart_fig.patch.set_alpha(0.0)
        self.chart_ax = self.chart_fig.add_subplot()
        self.chart_canvas = FigureCanvas(self.chart_fig)
        self.chart_canvas.setStyleSheet("background: transparent;")
        chart_layout.addWidget(self.chart_canvas)
        
        content_layout.addWidget(chart_card, 3) 

        # --- 2b. Right Side (Data Table) ---
        table_card = QFrame()
        table_card.setFrameShape(QFrame.Shape.StyledPanel)
        table_card.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px;")
        table_card.setMinimumWidth(350) 
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(12, 12, 12, 12)
        table_layout.setSpacing(10)

        toggle_layout = QHBoxLayout()
        self.hist_fut_switch = QCheckBox("Historical")
        self.hist_fut_switch.setStyleSheet(self._slider_switch_style())
        self.hist_fut_switch.toggled.connect(self._on_hist_fut_toggled)
        toggle_layout.addWidget(self.hist_fut_switch)
        toggle_layout.addStretch()
        table_layout.addLayout(toggle_layout)
        
        self.analyze_table = QTableWidget()
        self.analyze_table.setColumnCount(5)
        self.analyze_table.setHorizontalHeaderLabels(["Time", "Open", "High", "Low", "Close"])
        self.analyze_table.setStyleSheet(self._table_style())
        self.analyze_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.analyze_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table_layout.addWidget(self.analyze_table)
        
        content_layout.addWidget(table_card, 2) 
        
        tab_layout.addLayout(content_layout)
        
        return tab_widget

    def _create_screener_tab(self):
        """Creates the 'Market Screener' tab content."""
        tab_widget = QWidget()
        # Note: Individual stylesheet is removed from here, now handled globally by _get_tab_bar_style
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 10, 0, 0)
        tab_layout.setSpacing(12)
        
        # --- 1. Controls Bar ---
        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        controls_frame.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px; padding: 10px;")
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setSpacing(10)
        
        controls_layout.addWidget(self._create_filter_pill("Exchange:", ["BSE", "NSE", "All"]))
        controls_layout.addWidget(self._create_filter_pill("Model:", ["Prophet", "LightGBM"]))
        controls_layout.addWidget(self._create_filter_pill("Date:", ["Sep 22", "Sep 23", "Sep 24", "Sep 25"]))
        controls_layout.addWidget(self._create_filter_pill("Trend:", ["All", "Advances", "Declines"]))
        controls_layout.addStretch()
        
        tab_layout.addWidget(controls_frame)
        
        # --- 2. Content (Table) ---
        table_card = QFrame()
        table_card.setFrameShape(QFrame.Shape.StyledPanel)
        table_card.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px;")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(12, 12, 12, 12)
        
        self.screener_table = QTableWidget()
        self.screener_table.setColumnCount(6)
        self.screener_table.setHorizontalHeaderLabels(["Stock", "Date", "Open", "High", "Low", "Close"])
        self.screener_table.setStyleSheet(self._table_style())
        self.screener_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.screener_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.screener_table.setSortingEnabled(True)
        table_layout.addWidget(self.screener_table)
        
        tab_layout.addWidget(table_card)
        
        return tab_widget

    def _create_watchlist_tab(self):
        """Creates the 'Watchlist' tab content."""
        tab_widget = QWidget()
        # Note: Individual stylesheet is removed from here, now handled globally by _get_tab_bar_style
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 10, 0, 0)
        tab_layout.setSpacing(12)

        # --- 1. Controls Bar ---
        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        controls_frame.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px; padding: 10px;")
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setSpacing(10)

        controls_layout.addWidget(self._create_filter_pill("Model:", ["LightGBM", "Prophet"]))
        controls_layout.addWidget(self._create_filter_pill("Date:", ["Sep 24", "Sep 25", "Sep 26"]))
        
        watchlist_count = QLabel("+ 1 stocks in watchlist")
        watchlist_count.setStyleSheet("background: transparent; color: #9aa4b6; font-size: 11px;")
        controls_layout.addWidget(watchlist_count)
        controls_layout.addStretch()
        
        tab_layout.addWidget(controls_frame)
        
        # --- 2. Content (Table) ---
        table_card = QFrame()
        table_card.setFrameShape(QFrame.Shape.StyledPanel)
        table_card.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px;")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(12, 12, 12, 12)
        
        self.watchlist_table = QTableWidget()
        self.watchlist_table.setColumnCount(6)
        self.watchlist_table.setHorizontalHeaderLabels(["Stock", "Date", "Open", "High", "Low", "Close"])
        self.watchlist_table.setStyleSheet(self._table_style())
        self.watchlist_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.watchlist_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.watchlist_table.setSortingEnabled(True)
        table_layout.addWidget(self.watchlist_table)
        
        tab_layout.addWidget(table_card)
        
        return tab_widget

    def _create_filter_pill(self, label_text, combo_items):
        """Helper to create the Label + ComboBox filter pills from the image."""
        pill_widget = QWidget()
        pill_layout = QHBoxLayout(pill_widget)
        pill_layout.setContentsMargins(0,0,0,0)
        pill_layout.setSpacing(5)
        
        label = QLabel(label_text)
        label.setStyleSheet("background: transparent; color: #9aa4b6; font-size: 11px;")
        pill_layout.addWidget(label)
        
        combo = QComboBox()
        combo.addItems(combo_items)
        combo.setStyleSheet(self._combo_style())
        pill_layout.addWidget(combo)
        
        return pill_widget
        
    def _on_hist_fut_toggled(self, checked):
        if checked:
            self.hist_fut_switch.setText("Future")
        else:
            self.hist_fut_switch.setText("Historical")
        
    # ---------------------------- Dummy Data and Plotting ----------------------------

    def _plot_dummy_prediction_chart(self):
        """Plots a dummy chart matching the style of the user's image."""
        self.chart_ax.clear()
        self._style_axes_dark(self.chart_ax)
        
        self.chart_ax.set_title(
            "Price Prediction Chart", 
            color="#EAF2FF", 
            fontsize=14, 
            pad=10
        )
        
        t_hist = np.arange(0, 20)
        y_hist = 100 + np.cumsum(np.random.randn(20) * 0.5)
        
        last_val = y_hist[-1]
        t_future = np.arange(19, 30)
        
        y_prophet = last_val + np.cumsum(np.random.randn(11) * 0.3)
        y_prophet_drift = y_prophet + np.linspace(0, 1.5, 11)
        
        y_lgbm = last_val + np.cumsum(np.random.randn(11) * 0.3)
        y_lgbm_drift = y_lgbm + np.linspace(0, -1, 11)
        
        self.chart_ax.plot(t_hist, y_hist, color='white', linestyle='-', linewidth=2, label='Historical')
        self.chart_ax.plot(t_future, y_prophet_drift, color='#A855F7', linestyle='--', linewidth=2, label='Prophet')
        self.chart_ax.plot(t_future, y_lgbm_drift, color='#F97316', linestyle='--', linewidth=2, label='LightGBM')
        
        legend = self.chart_fig.legend(
            loc='lower center', 
            ncol=3, 
            frameon=False, 
            labelcolor='white'
        )
        for text in legend.get_texts():
            text.set_fontsize(10)

        self.chart_fig.tight_layout()
        self.chart_canvas.draw()

    def _set_dummy_table_data(self, table_widget, num_rows=5):
        """Populates a table with dummy data."""
        table_widget.setRowCount(num_rows)
        dummy_stocks = ["ICICIBANK", "KOTAKBANK", "TCS", "RELIANCE", "HDFCBANK", "INFY"]
        
        for i in range(num_rows):
            stock = np.random.choice(dummy_stocks)
            date = f"2025-09-{22+i}"
            o = f"₹{1400 + np.random.rand()*100:.2f}"
            h = f"₹{1500 + np.random.rand()*100:.2f}"
            l = f"₹{1300 + np.random.rand()*100:.2f}"
            c = f"₹{1450 + np.random.rand()*100:.2f}"
            
            data_row = [stock, date, o, h, l, c]
            
            if table_widget.columnCount() == 5:
                data_row = [f"15:{30+i}:00", o, h, l, c]
            
            for j, item_text in enumerate(data_row):
                item = QTableWidgetItem(item_text)
                if j > 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
                
                if item_text.startswith("₹"):
                    if "High" in table_widget.horizontalHeaderItem(j).text():
                        item.setForeground(QColor("#20C997"))
                    elif "Low" in table_widget.horizontalHeaderItem(j).text():
                        item.setForeground(QColor("#E35D6A"))
                        
                table_widget.setItem(i, j, item)

    # ---------------------------- Style Methods (from dashboard.py) ----------------------------

    def _slider_switch_style(self):
        """Returns the QSS for a modern slider switch (styled QCheckBox)."""
        return """
            QCheckBox {
                spacing: 10px;
                color: #DDE8F5;
                font-weight: 600;
                font-size: 10pt;
            }
            QCheckBox::indicator {
                width: 44px;
                height: 24px;
                background-color: #3B4652;
                border-radius: 12px;
                border: 1px solid #2B323A;
            }
            QCheckBox::indicator:unchecked:hover {
                background-color: #4a5568;
            }
            QCheckBox::indicator:checked {
                background-color: #33C4B9;
                border: 1px solid #2AA6A6;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #2AA6A6;
            }
            QCheckBox::indicator::handle {
                width: 20px;
                height: 20px;
                background-color: white;
                border-radius: 10px;
                margin: 2px;
            }
            QCheckBox::indicator::handle:unchecked {
                margin-left: 2px;
            }
            QCheckBox::indicator::handle:checked {
                margin-left: 22px; 
            }
        """

    def _get_tab_bar_style(self):
        """Returns the QSS for the main tab bar, matching the image."""
        return """
        QTabWidget::pane {
            border: 0;
            background: transparent;
        }
        QTabBar::tab {
            background: transparent;
            color: #9aa4b6;
            font-size: 14px;
            font-weight: 600;
            padding: 10px 15px;
            margin-right: 10px;
            border: none;
        }
        QTabBar::tab:hover {
            color: #FFFFFF;
        }
        QTabBar::tab:selected {
            color: #FFFFFF;
            border-bottom: 3px solid #33C4B9;
        }
        /* 🔑 Force tab page widgets to stay transparent */
        QTabWidget::tab-bar {
            alignment: left;
        }
        QWidget { 
            background: transparent;
        }
    """


    def _search_bar_style(self):
        """Style for the main search bar, from dashboard.py."""
        return """
            QLineEdit {
                background-color: #1B2026; color: #DDE8F5; border: 1px solid #2B323A;
                border-radius: 18px; padding: 0px 15px; font-size: 11pt;
            }
            QLineEdit:hover { border: 1px solid #3B4652; }
            QLineEdit:focus { border: 1px solid #33C4B9; }
        """

    def _pill_button_style_accent(self):
        """A modern style for the main 'Analyze' button."""
        return """
            QPushButton {
                background-color: #33C4B9;
                color: #0A0D10;
                border-radius: 18px;
                padding: 5px 15px;
                font-weight: bold;
                font-size: 10pt;
                border: none;
            }
            QPushButton:hover {
                background-color: #2AA6A6;
            }
            QPushButton:pressed {
                background-color: #1F7A7A;
            }
        """
    
    def _style_axes_dark(self, ax):
        ax.set_facecolor("none")
        ax.tick_params(axis='x', colors="#CCD6E4")
        ax.tick_params(axis='y', colors="#CCD6E4")
        for s in ax.spines.values():
            s.set_color("#2C2F34")
        ax.grid(axis='y', linestyle=':', color="#2A2E33", alpha=0.35)

    def _range_button_style(self):
        return ("QPushButton{background:#1B2026; color:#DDE8F5; border:1px solid #2B323A; border-radius:10px; padding:6px 8px;}"
                "QPushButton:hover{background:#232A31;}"
                "QPushButton:checked{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00A7A7, stop:1 #00C2B8);"
                "color:#0B1116; font-weight:700; border:0px;}")

    def _combo_style(self):
        return ("""
        QComboBox {
            background-color: #1B2026; color: #DDE8F5; border: 1px solid #2B323A;
            border-radius: 10px; padding: 6px 25px 6px 10px; font-weight: 600;
        }
        QComboBox:hover { border: 1px solid #33C4B9; }
        QComboBox::drop-down {
            subcontrol-origin: padding; subcontrol-position: top right;
            width: 22px; border-left-width: 1px; border-left-color: #2B323A;
            border-left-style: solid; border-top-right-radius: 9px; border-bottom-right-radius: 9px;
        }
        QComboBox::down-arrow { image: url(assets/down-arrow.png); width: 10px; height: 10px; }
        QComboBox QAbstractItemView {
            background: #15181B; color: #E8F2FF; border: 1px solid #3B4652;
            border-radius: 8px; selection-background-color: #1F7A7A;
            padding: 4px; outline: 0px;
        }
        """)

    def _table_style(self):
        return (f"""
        QTableWidget {{
            background: transparent; color: #E6EEF6; border: none;
            gridline-color: #2B323A;
            selection-background-color: rgba(42, 166, 166, 0.3);
            alternate-background-color: rgba(255, 255, 255, 0.02);
        }}
        QTableWidget::item {{ 
            padding: 6px 8px; 
            border-bottom: 1px solid #2B323A; 
            border-right: 1px solid #2B323A;
        }}
        QTableWidget::item:selected {{ color: #F5FFFF; }}
        QHeaderView::section {{
            background-color: transparent; color: #9aa4b6;
            font-weight: 600; border: none; padding: 8px;
            border-bottom: 2px solid #33C4B9;
        }}
        QTableCornerButton::section {{ background-color: transparent; border: none; }}
        {self._scrollbar_style()}
        """)

    def _scrollbar_style(self):
        return """
            QScrollBar:vertical {
                border: none; background: transparent; width: 10px; margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #4a5568; min-height: 20px; border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover { background: #718096; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
            QScrollBar:horizontal {
                border: none; background: transparent; height: 10px; margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #4a5568; min-width: 20px; border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover { background: #718096; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
        """

# ---------------------------- Standalone Run (for testing) ----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    win = QMainWindow()
    win.setWindowTitle("Apex Analytics - Prediction Page Test")
    win.resize(1360, 820)
    
    win.setStyleSheet("background:#0A0C0E;")
    
    prediction_page = PredictionPage()
    
    win.setCentralWidget(prediction_page)
    
    win.show()
    sys.exit(app.exec())
