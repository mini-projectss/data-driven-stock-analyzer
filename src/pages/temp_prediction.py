#!/usr/bin/env python3
# Apex Analytics - Prediction Page
# This page provides stock prediction visualizations and data.

import sys
import os
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QFrame, QHeaderView, QRadioButton, QDateEdit, QCompleter
)
from PyQt6.QtGui import QFont, QPainter, QColor, QLinearGradient, QBrush
from PyQt6.QtCore import Qt, QDate
import matplotlib
matplotlib.use('qtagg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates

# --- Configuration: Relative paths to data folders ---
DATA_PATH = 'data'
HISTORICAL_PATH = os.path.join(DATA_PATH, 'historical')
PREDICTIONS_PATH = os.path.join(DATA_PATH, 'predictions')

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

# ---------------------------------- Main Application -----------------------------------
class PredictionPage(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apex Analytics - Stock Prediction")
        self.setGeometry(100, 100, 1400, 1000)

        self.central_widget = GradientWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(20)

        self._load_ticker_data()
        self._create_header()
        self._create_search_and_graph_section()
        self._create_screener_section()
        self._apply_styles()

        self.search_button.clicked.connect(self._on_search_clicked)
        self.search_input.returnPressed.connect(self._on_search_clicked)
        self.filter_button.clicked.connect(self._on_filter_clicked)

    # --- UI Creation Methods (Your Original Code) ---
    def _create_header(self):
        header_label = QLabel("Data Driven Stock Analyzer")
        header_label.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("color: #FFFFFF; text-shadow: 0 0 10px rgba(0, 194, 184, 0.7);")
        self.main_layout.addWidget(header_label)

    def _create_search_and_graph_section(self):
        top_section_container = QFrame()
        top_section_container.setObjectName("container")
        top_section_layout = QVBoxLayout(top_section_container)
        top_section_layout.setSpacing(15)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter stock ticker (e.g., 3MINDIA or RELIANCE)")
        
        completer = QCompleter(self.clean_ticker_list)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.search_input.setCompleter(completer)
        
        # --- CHANGE: Added exchange filter to search bar ---
        self.search_nse_radio = QRadioButton("NSE")
        self.search_bse_radio = QRadioButton("BSE")
        self.search_nse_radio.setChecked(True)

        self.search_button = QPushButton("Analyze")
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_nse_radio)
        search_layout.addWidget(self.search_bse_radio)
        search_layout.addWidget(self.search_button)
        top_section_layout.addLayout(search_layout)

        self.status_label = QLabel("Enter a ticker and click Analyze to view predictions.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_section_layout.addWidget(self.status_label)
        
        graph_details_layout = QHBoxLayout()
        
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        graph_details_layout.addWidget(self.canvas, 2)

        details_container = QFrame()
        details_container.setObjectName("detailsContainer")
        details_v_layout = QVBoxLayout(details_container)
        
        self.lgbm_details_label = QLabel("LGBM Predictions will appear here.")
        self.prophet_details_label = QLabel("Prophet Predictions will appear here.")
        
        details_v_layout.addWidget(QLabel("<b>LGBM Model (Next 7 Days)</b>"))
        details_v_layout.addWidget(self.lgbm_details_label)
        details_v_layout.addStretch()
        details_v_layout.addWidget(QLabel("<b>Prophet Model (Next 7 Days)</b>"))
        details_v_layout.addWidget(self.prophet_details_label)

        graph_details_layout.addWidget(details_container, 1)

        top_section_layout.addLayout(graph_details_layout)
        self.main_layout.addWidget(top_section_container)
        
        self._create_initial_graph()

    def _create_screener_section(self):
        screener_container = QFrame()
        screener_container.setObjectName("container")
        screener_layout = QVBoxLayout(screener_container)
        
        screener_title = QLabel("Market Screener")
        screener_title.setFont(QFont("Inter", 18, QFont.Weight.DemiBold)) # FIX: Was SemiBold
        screener_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        screener_layout.addWidget(screener_title)

        filter_layout = QHBoxLayout()
        self.bse_radio = QRadioButton("BSE")
        self.nse_radio = QRadioButton("NSE")
        self.nse_radio.setChecked(True)
        self.date_filter = QDateEdit(QDate.currentDate())
        self.model_combo = QComboBox()
        self.model_combo.addItems(["LGBM", "Prophet"])
        self.trend_combo = QComboBox()
        self.trend_combo.addItems(["Advances", "Declines"])
        self.filter_button = QPushButton("Filter Results")

        filter_layout.addWidget(QLabel("Exchange:"))
        filter_layout.addWidget(self.bse_radio)
        filter_layout.addWidget(self.nse_radio)
        filter_layout.addStretch()
        filter_layout.addWidget(QLabel("Date:"))
        filter_layout.addWidget(self.date_filter)
        filter_layout.addStretch()
        filter_layout.addWidget(QLabel("Model:"))
        filter_layout.addWidget(self.model_combo)
        filter_layout.addStretch()
        filter_layout.addWidget(QLabel("Trend:"))
        filter_layout.addWidget(self.trend_combo)
        filter_layout.addStretch()
        filter_layout.addWidget(self.filter_button)
        screener_layout.addLayout(filter_layout)

        self.results_table = QTableWidget()
        screener_layout.addWidget(self.results_table)
        self.main_layout.addWidget(screener_container)
        
        self._initialize_table()

    # --- LOGIC INTEGRATION: All data handling and plotting functions ---

    def _load_ticker_data(self):
        self.ticker_map = {}
        self.clean_ticker_list = []
        try:
            with open('tickersbse.txt', 'r') as f:
                for line in f:
                    ticker = line.strip()
                    clean_name = ticker.replace('.BO', '')
                    self.ticker_map[f"{clean_name}_BSE"] = ticker
            with open('tickersnse.txt', 'r') as f:
                for line in f:
                    ticker = line.strip()
                    clean_name = ticker.replace('.NS', '')
                    if f"{clean_name}_BSE" not in self.ticker_map:
                         self.clean_ticker_list.append(clean_name)
                    self.ticker_map[f"{clean_name}_NSE"] = ticker
            # Create a unique sorted list for the completer
            self.clean_ticker_list = sorted(list(set(self.clean_ticker_list + [k.split('_')[0] for k in self.ticker_map.keys()])))

        except Exception as e:
            print(f"Could not load ticker files: {e}")

    def _on_search_clicked(self):
        clean_ticker = self.search_input.text().strip().upper()
        if not clean_ticker:
            self.status_label.setText("<b style='color:#FF6B6B;'>Please enter a ticker.</b>")
            return

        exchange = "BSE" if self.search_bse_radio.isChecked() else "NSE"
        ticker_key = f"{clean_ticker}_{exchange}"
        ticker = self.ticker_map.get(ticker_key)

        if not ticker:
            self.status_label.setText(f"<b style='color:#FF6B6B;'>Ticker '{clean_ticker}' not found on {exchange}.</b>")
            return

        filename_ticker = ticker.replace('.', '_')
        pred_file = os.path.join(PREDICTIONS_PATH, f'{filename_ticker}_prediction.csv')
        hist_file = os.path.join(HISTORICAL_PATH, exchange, f'{filename_ticker}.csv')

        if not os.path.exists(pred_file) or not os.path.exists(hist_file):
            self.status_label.setText(f"<b style='color:#FF6B6B;'>Data not found for ticker: {ticker}</b>")
            self._create_initial_graph()
            self.lgbm_details_label.setText("N/A")
            self.prophet_details_label.setText("N/A")
            return

        self.status_label.setText(f"Displaying results for <b style='color:#00C2B8;'>{ticker}</b>")
        try:
            pred_df = pd.read_csv(pred_file, parse_dates=['Date'])
            hist_df = pd.read_csv(hist_file, parse_dates=['Date'])
            self._plot_real_data(hist_df, pred_df)
            self._populate_details(pred_df)
        except Exception as e:
            self.status_label.setText(f"<b style='color:#FF6B6B;'>Error loading data for {ticker}: {e}</b>")

    def _on_filter_clicked(self):
        exchange = "BSE" if self.bse_radio.isChecked() else "NSE"
        selected_date_str = self.date_filter.date().toString("yyyy-MM-dd")
        model = self.model_combo.currentText()
        trend = self.trend_combo.currentText()
        
        ticker_file = 'tickersbse.txt' if exchange == 'BSE' else 'tickersnse.txt'
        try:
            with open(ticker_file, 'r') as f:
                tickers = [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            self._populate_table([], error_message=f"{ticker_file} not found.")
            return

        results = []
        for ticker in tickers:
            filename = ticker.replace('.', '_') + '_prediction.csv'
            pred_file = os.path.join(PREDICTIONS_PATH, filename)
            if not os.path.exists(pred_file):
                continue
            
            try:
                df = pd.read_csv(pred_file, parse_dates=['Date'])
                day_data = df[df['Date'].dt.strftime('%Y-%m-%d') == selected_date_str]
                
                if not day_data.empty:
                    row = day_data.iloc[0]
                    open_price = row[f'{model}_Open']
                    close_price = row[f'{model}_Close']
                    is_advance = close_price > open_price
                    
                    if (trend == "Advances" and is_advance) or (trend == "Declines" and not is_advance):
                        results.append([
                            ticker.split('.')[0], f"{open_price:.2f}", f"{row[f'{model}_High']:.2f}",
                            f"{row[f'{model}_Low']:.2f}", f"{row[f'{model}_Close']:.2f}"
                        ])
            except Exception:
                continue
        
        self._populate_table(results)
        
    def _plot_real_data(self, hist_df, pred_df):
        hist_data = hist_df.tail(7)
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        ax.plot(hist_data['Date'], hist_data['Close'], color='#E0E0E0', linewidth=2, label='Historical Close', marker='o', markersize=5)
        ax.plot(pred_df['Date'], pred_df['Prophet_Close'], color='#A020F0', linewidth=2, linestyle='--', label='Prophet Prediction')
        ax.plot(pred_df['Date'], pred_df['LGBM_Close'], color='#FFA500', linewidth=2, linestyle='--', label='LGBM Prediction')
        
        self._style_plot(ax)
        self.figure.autofmt_xdate(rotation=30, ha='right')
        self.figure.tight_layout(pad=2.5)
        self.canvas.draw()
        
    def _populate_details(self, pred_df):
        lgbm_html = "<table width='100%' style='font-size: 13px;'>"
        prophet_html = "<table width='100%' style='font-size: 13px;'>"
        for _, row in pred_df.iterrows():
            date_str = row['Date'].strftime('%b %d')
            lgbm_html += f"<tr><td><b>{date_str}</b></td><td><span style='color:#FFA500;'>O:{row['LGBM_Open']:.2f} H:{row['LGBM_High']:.2f} L:{row['LGBM_Low']:.2f} C:{row['LGBM_Close']:.2f}</span></td></tr>"
            prophet_html += f"<tr><td><b>{date_str}</b></td><td><span style='color:#A020F0;'>O:{row['Prophet_Open']:.2f} H:{row['Prophet_High']:.2f} L:{row['Prophet_Low']:.2f} C:{row['Prophet_Close']:.2f}</span></td></tr>"
        lgbm_html += "</table>"
        prophet_html += "</table>"
        self.lgbm_details_label.setText(lgbm_html)
        self.prophet_details_label.setText(prophet_html)

    def _populate_table(self, data, error_message=None):
        self.results_table.clear()
        self.results_table.setSortingEnabled(False)
        if error_message:
            self.results_table.setRowCount(1)
            self.results_table.setColumnCount(1)
            self.results_table.setHorizontalHeaderLabels(["Error"])
            self.results_table.setItem(0, 0, QTableWidgetItem(error_message))
            self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            return

        if not data:
            self.results_table.setRowCount(1)
            self.results_table.setColumnCount(1)
            self.results_table.setHorizontalHeaderLabels(["Result"])
            self.results_table.setItem(0, 0, QTableWidgetItem("No stocks found matching the criteria."))
            self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            return
            
        headers = ["Ticker", "Open", "High", "Low", "Close"]
        self.results_table.setRowCount(len(data))
        self.results_table.setColumnCount(len(headers))
        self.results_table.setHorizontalHeaderLabels(headers)
        
        for r_idx, row in enumerate(data):
            for c_idx, item in enumerate(row):
                self.results_table.setItem(r_idx, c_idx, QTableWidgetItem(item))
        
        self.results_table.setSortingEnabled(True)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)

    # --- Initial State & Styling Methods (Your Original Code) ---
    def _create_initial_graph(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Prediction Graph Appears Here',
                horizontalalignment='center', verticalalignment='center',
                fontsize=14, color='#8899A9', transform=ax.transAxes)
        self._style_plot(ax)
        self.canvas.draw()

    def _initialize_table(self):
        self._populate_table([], error_message="Select filters and click 'Filter Results' to see data.")

    def _style_plot(self, ax):
        self.figure.patch.set_facecolor('#1B2026')
        ax.set_facecolor('#1B2026')
        ax.spines['bottom'].set_color('#5A6B7F')
        ax.spines['top'].set_color('#1B2026')
        ax.spines['right'].set_color('#1B2026')
        ax.spines['left'].set_color('#5A6B7F')
        ax.tick_params(axis='x', colors='#DDE8F5', labelsize=10)
        ax.tick_params(axis='y', colors='#DDE8F5', labelsize=10)
        ax.yaxis.label.set_color('#DDE8F5')
        ax.xaxis.label.set_color('#DDE8F5')
        ax.grid(color='#2B323A', linestyle='--', linewidth=0.5)
        legend = ax.legend()
        if legend:
            legend.get_frame().set_facecolor('#2B323A')
            legend.get_frame().set_edgecolor('#5A6B7F')
            for text in legend.get_texts():
                text.set_color('#DDE8F5')

    def _apply_styles(self):
        self.setStyleSheet(self._base_style() + self._container_style() + self._button_style() +
                           self._input_style() + self._table_style() + self._scrollbar_style())

    def _base_style(self): return "QWidget { color: #DDE8F5; font-family: 'Inter', sans-serif; font-size: 14px; }"
    def _container_style(self): return "QFrame#container, QFrame#detailsContainer { background-color: #1B2026; border-radius: 12px; border: 1px solid #2B323A; padding: 15px; }"
    def _button_style(self): return "QPushButton { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00A7A7, stop:1 #00C2B8); color: #0B1116; font-weight: 700; border: none; padding: 10px 20px; border-radius: 8px; } QPushButton:hover { background-color: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00B8B8, stop:1 #00D3C9); } QPushButton:pressed { background-color: #009696; }"
    def _input_style(self): return "QLineEdit, QComboBox, QDateEdit { background-color: #0B1116; border: 1px solid #2B323A; padding: 10px; border-radius: 8px; } QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border-color: #00A7A7; }"
    def _table_style(self): return "QTableWidget { background-color: #0B1116; border: 1px solid #2B323A; gridline-color: #2B323A; } QHeaderView::section { background-color: #1B2026; color: #DDE8F5; padding: 8px; border: 1px solid #2B323A; font-weight: 600; }"
    def _scrollbar_style(self): return "QScrollBar:vertical, QScrollBar:horizontal { border: none; background: transparent; width: 10px; height: 10px; margin: 0px; } QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #4a5568; min-height: 20px; min-width: 20px; border-radius: 5px; } QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: #718096; }"

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PredictionPage()
    window.show()
    sys.exit(app.exec())