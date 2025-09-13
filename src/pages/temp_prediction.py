#!/usr/bin/env python3
# Apex Analytics - Prediction Page
# This page provides stock prediction visualizations and data.

import sys
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,

    QFrame, QHeaderView, QSizePolicy, QScrollArea, QAbstractItemView, QTabWidget
)
from PyQt6.QtGui import QFont, QPainter, QColor, QLinearGradient, QBrush
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('qtagg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ---------------------------- Custom Gradient Background Widget ----------------------------
class GradientWidget(QWidget):
    """A widget with a rich, cool-toned diagonal gradient background."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
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
class PredictionPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)

        # Main scroll area for resizability
        main_scroll_area = QScrollArea()
        main_scroll_area.setWidgetResizable(True)
        main_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        main_scroll_area.setStyleSheet(self._scrollbar_style())
        page_layout.addWidget(main_scroll_area)

        # Gradient background
        content_bg = GradientWidget()
        main_scroll_area.setWidget(content_bg)

        # Main content layout
        content_layout = QVBoxLayout(content_bg)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)
        
        # --- 1. First Tab: Prediction Graph ---
        tab1_frame = self._create_main_frame()
        tab1_layout = QVBoxLayout(tab1_frame)
        tab1_layout.setSpacing(12)
        
        # Search and filter bar
        search_bar_layout = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search for a stock to predict (e.g., RELIANCE)")
        search_input.setFixedHeight(38)
        search_input.setStyleSheet(self._search_bar_style())
        search_bar_layout.addWidget(search_input, 1) # Give more stretch factor to search

        exchange_combo_1 = QComboBox()
        exchange_combo_1.addItems(["NSE", "BSE"])
        exchange_combo_1.setStyleSheet(self._combo_style())
        search_bar_layout.addWidget(exchange_combo_1)
        tab1_layout.addLayout(search_bar_layout)
        
        # Prediction Graph
        self.chart_fig = Figure(figsize=(8, 3), dpi=100)
        self.chart_fig.patch.set_alpha(0.0)
        self.chart_ax = self.chart_fig.add_subplot()
        self.chart_canvas = FigureCanvas(self.chart_fig)
        self.chart_canvas.setStyleSheet("background: transparent;")
        self._plot_prediction_graph() # Plot dummy data
        tab1_layout.addWidget(self.chart_canvas)

        # LSTM/Prophet Details Tabs
        details_tabs = QTabWidget()
        details_tabs.setStyleSheet(self._tab_widget_style())
        
        lstm_tab = QWidget()
        prophet_tab = QWidget()
        
        details_tabs.addTab(lstm_tab, "LSTM Model Details")
        details_tabs.addTab(prophet_tab, "Prophet Model Details")
        
        self._setup_details_tab(lstm_tab, self._generate_dummy_table_data(7))
        self._setup_details_tab(prophet_tab, self._generate_dummy_table_data(7))
        
        tab1_layout.addWidget(details_tabs)
        content_layout.addWidget(tab1_frame)

        # --- 2. Second Tab: Market Prediction List ---
        tab2_frame = self._create_main_frame()
        tab2_layout = QVBoxLayout(tab2_frame)
        tab2_layout.setSpacing(12)

        # Filters for the market list
        market_filters_layout = QHBoxLayout()
        market_filters_layout.setSpacing(10)
        market_filters_layout.addWidget(QLabel("Filters:"))
        
        exchange_combo_2 = QComboBox(); exchange_combo_2.addItems(["Exchange", "BSE", "NSE"])
        date_combo = QComboBox(); date_combo.addItems(["Date", "2025-09-15", "2025-09-16"])
        model_combo = QComboBox(); model_combo.addItems(["Model", "LSTM", "Prophet"])
        type_combo = QComboBox(); type_combo.addItems(["Type", "Advances", "Declines"])
        
        for combo in [exchange_combo_2, date_combo, model_combo, type_combo]:
            combo.setStyleSheet(self._combo_style())
            market_filters_layout.addWidget(combo)
            
        market_filters_layout.addStretch()
        
        show_results_btn = QPushButton("Show Results")
        show_results_btn.setFixedHeight(38)
        show_results_btn.setStyleSheet(self._pill_button_style())
        show_results_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        market_filters_layout.addWidget(show_results_btn)
        
        tab2_layout.addLayout(market_filters_layout)

        # Market Prediction Table
        market_table = self._create_styled_table(["Stock", "Date", "Time", "Open", "High", "Low", "Close", "Volume"])
        self._populate_dummy_main_table(market_table, 20)
        tab2_layout.addWidget(market_table)
        content_layout.addWidget(tab2_frame)
        
        # --- 3. Third Tab: Watchlist ---
        tab3_frame = self._create_main_frame()
        tab3_layout = QVBoxLayout(tab3_frame)
        tab3_layout.setSpacing(12)
        
        watchlist_label = QLabel("Model-Based Watchlist")
        watchlist_label.setFont(QFont("Inter, Segoe UI", 14, QFont.Weight.Bold))
        watchlist_label.setStyleSheet("background: transparent; color: #EAF2FF;")
        tab3_layout.addWidget(watchlist_label)
        
        watchlist_table = self._create_styled_table(["Stock", "Date", "Time", "Open", "High", "Low", "Close", "Volume"])
        self._populate_dummy_main_table(watchlist_table, 5) # Smaller list for watchlist
        tab3_layout.addWidget(watchlist_table)
        content_layout.addWidget(tab3_frame)
        
        content_layout.addStretch(1)

    # ---------------------------- UI Creation Helpers ----------------------------

    def _create_main_frame(self):
        """Creates a styled QFrame that acts as a container for each tab section."""
        frame = QFrame()
        frame.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px;")
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return frame

    def _setup_details_tab(self, tab_widget, data):
        """Configures the layout and table for the LSTM/Prophet details tabs."""
        layout = QVBoxLayout(tab_widget)
        layout.setContentsMargins(0,0,0,0)
        table = self._create_styled_table(["Date", "Open", "High", "Low", "Close", "Volume"])
        table.setAlternatingRowColors(False) # A bit cleaner for small tables
        
        table.setRowCount(len(data))
        for row_idx, row_data in enumerate(data):
            for col_idx, cell_data in enumerate(row_data):
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(cell_data)))
        layout.addWidget(table)

    def _create_styled_table(self, headers):
        """Creates a QTableWidget with the standard dark theme."""
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setStyleSheet(self._table_style())
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        return table

    # ---------------------------- Dummy Data and Plotting ----------------------------

    def _plot_prediction_graph(self):
        """Generates and plots dummy data for the prediction graph."""
        self._style_axes_dark(self.chart_ax)
        
        # Generate date ranges
        today = pd.Timestamp.now()
        past_dates = pd.to_datetime(pd.date_range(end=today, periods=8, freq='D'))[:-1]
        future_dates = pd.to_datetime(pd.date_range(start=today, periods=8, freq='D'))[1:]

        # Generate data
        past_actual = 100 + np.cumsum(np.random.randn(7) * 2)
        last_actual_point = past_actual[-1]
        
        future_lstm = last_actual_point + np.cumsum(np.random.randn(7) * 2.5)
        future_prophet = last_actual_point + np.cumsum(np.random.randn(7) * 2.2)

        # Plotting
        self.chart_ax.plot(past_dates, past_actual, marker='o', linestyle='-', color='#33C4B9', label='Actual Past Data')
        
        # Connect last actual point to first prediction point
        self.chart_ax.plot([past_dates[-1], future_dates[0]], [last_actual_point, future_lstm[0]],
                           linestyle='--', color='#FFA500')
        self.chart_ax.plot([past_dates[-1], future_dates[0]], [last_actual_point, future_prophet[0]],
                           linestyle='--', color='#8A2BE2')
                           
        self.chart_ax.plot(future_dates, future_lstm, marker='o', linestyle='--', color='#FFA500', label='LSTM Prediction')
        self.chart_ax.plot(future_dates, future_prophet, marker='o', linestyle='--', color='#8A2BE2', label='Prophet Prediction')
        
        self.chart_ax.set_ylabel("Stock Price", color="#CCD6E4")
        self.chart_ax.legend(labelcolor="#DDE8F5", facecolor="#1B2026", edgecolor="#2B323A")
        self.chart_fig.autofmt_xdate()
        self.chart_canvas.draw()

    def _generate_dummy_table_data(self, num_rows):
        """Generates dummy data for the details tables."""
        data = []
        start_date = pd.Timestamp.now().date()
        for i in range(num_rows):
            date = start_date + pd.Timedelta(days=i)
            o = round(100 + i*0.5 + np.random.rand(), 2)
            c = round(o + np.random.uniform(-2, 2), 2)
            h = round(max(o, c) + np.random.rand(), 2)
            l = round(min(o, c) - np.random.rand(), 2)
            v = np.random.randint(100000, 5000000)
            data.append([date.strftime('%Y-%m-%d'), o, h, l, c, f"{v:,}"])
        return data
        
    def _populate_dummy_main_table(self, table, num_rows):
        """Populates the larger market and watchlist tables with dummy data."""
        stocks = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BAJFINANCE", "HINDUNILVR"]
        table.setRowCount(num_rows)
        for i in range(num_rows):
            stock = np.random.choice(stocks)
            date = (pd.Timestamp.now().date() - pd.Timedelta(days=np.random.randint(0,5))).strftime('%Y-%m-%d')
            time = "15:30:00"
            o = round(np.random.uniform(500, 3000), 2)
            c = round(o + np.random.uniform(-50, 50), 2)
            h = round(max(o, c) + np.random.uniform(0, 20), 2)
            l = round(min(o, c) - np.random.uniform(0, 20), 2)
            v = f"{np.random.randint(50000, 2000000):,}"
            
            row_data = [stock, date, time, str(o), str(h), str(l), str(c), v]
            for j, val in enumerate(row_data):
                table.setItem(i, j, QTableWidgetItem(val))

    # ---------------------------- Styles (Copied from dashboard.py) ----------------------------

    def _style_axes_dark(self, ax):
        ax.clear()
        ax.set_facecolor("none")
        ax.tick_params(axis='x', colors="#CCD6E4")
        ax.tick_params(axis='y', colors="#CCD6E4")
        for s in ax.spines.values(): s.set_color("#2C2F34")
        ax.grid(True, which='both', axis='y', linestyle=':', color="#2A2E33", alpha=0.7)

    def _search_bar_style(self):
        return """
            QLineEdit {
                background-color: #1B2026; color: #DDE8F5; border: 1px solid #2B323A;
                border-radius: 18px; padding: 0px 15px; font-size: 11pt;
            }
            QLineEdit:hover { border: 1px solid #3B4652; }
            QLineEdit:focus { border: 1px solid #33C4B9; }
        """

    def _pill_button_style(self):
        return """
            QPushButton {
                background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00A7A7, stop:1 #00C2B8);
                color: #0B1116; border-radius: 18px; padding: 5px 20px;
                font-weight: bold; font-size: 10pt; border: none;
            }
            QPushButton:hover { background-color: #232A31; }
            QPushButton:pressed { background-color: #1a202c; }
        """
        
    def _combo_style(self):
        return ("""
        QComboBox {
            background-color: #1B2026; color: #DDE8F5; border: 1px solid #2B323A;
            border-radius: 10px; padding: 8px 30px 8px 12px; font-weight: 600;
        }
        QComboBox:hover { border: 1px solid #33C4B9; }
        QComboBox::drop-down {
            subcontrol-origin: padding; subcontrol-position: top right;
            width: 28px; border-left-width: 1px; border-left-color: #2B323A;
            border-left-style: solid; border-top-right-radius: 9px; border-bottom-right-radius: 9px;
        }
        QComboBox::down-arrow { image: url(none); } /* Hide default arrow */
        QComboBox QAbstractItemView {
            background: #15181B; color: #E8F2FF; border: 1px solid #3B4652;
            border-radius: 8px; selection-background-color: #1F7A7A;
            padding: 4px; outline: 0px;
        }
        """)

    def _table_style(self):
        return ("""
        QTableWidget {
            background: transparent; color: #E6EEF6; border: none;
            gridline-color: #2B323A;
            selection-background-color: rgba(42, 166, 166, 0.3);
            alternate-background-color: rgba(255, 255, 255, 0.02);
        }
        QTableWidget::item { padding: 8px; border-bottom: 1px solid #2B323A; }
        QTableWidget::item:selected { color: #F5FFFF; }
        QHeaderView::section {
            background-color: transparent; color: #9aa4b6;
            font-weight: 600; border: none; padding: 10px 8px;
            border-bottom: 2px solid #33C4B9;
        }
        """)
        
    def _tab_widget_style(self):
        return """
        QTabWidget::pane {
            border: 1px solid #2B323A;
            border-radius: 8px;
            margin-top: -1px;
        }
        QTabBar::tab {
            background: #1B2026;
            color: #DDE8F5;
            border: 1px solid #2B323A;
            border-bottom: none;
            padding: 10px 25px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }
        QTabBar::tab:hover {
            background: #232A31;
        }
        QTabBar::tab:selected {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00A7A7, stop:1 #00C2B8);
            color: #0B1116;
            font-weight: 700;
        }
        """

    def _scrollbar_style(self):
        return """
            QScrollBar:vertical, QScrollBar:horizontal {
                border: none; background: transparent; width: 10px; height: 10px; margin: 0px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #4a5568; min-height: 20px; min-width: 20px; border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #718096; }
        """

# ---------------------------- For Standalone Testing ----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.setWindowTitle("Apex Analytics - Prediction Page")
    win.resize(1200, 900)
    prediction_page = PredictionPage()
    win.setCentralWidget(prediction_page)
    win.show()
    sys.exit(app.exec())