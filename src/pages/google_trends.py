import sys
import time
import pandas as pd
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QPushButton, QLabel, QTableWidget, QTableWidgetItem, 
    QCompleter, QHeaderView
)
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
import os
from dotenv import load_dotenv
import numpy as np

# Load API key from .env file
load_dotenv()
SERPAPI_KEY = os.getenv('SERPAPI_KEY')
if not SERPAPI_KEY:
    raise ValueError("SERPAPI_KEY not found in .env file. Please set it up.")

# Custom Navigation Toolbar to exclude "Edit Axis" and "Configure Subplots"
class CustomNavigationToolbar(NavigationToolbar):
    # Define the toolbar buttons to include (excluding Subplots and Edit Axis)
    toolitems = [
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to previous view', 'back', 'back'),
        ('Forward', 'Forward to next view', 'forward', 'forward'),
        ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
        ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
    ]

    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)

class PageWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Google Trends Analysis")
        self.resize(1200, 800)
        
        # Updated stylesheet to match the image's dark theme with improved responsiveness
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0F172A;
            }
            QLabel {
                color: #F1F5F9;
                font-family: Arial;
                font-size: 16px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #1E293B;
                border: 2px solid #334155;
                border-radius: 6px;
                padding: 10px;
                color: #F1F5F9;
                font-size: 14px;
            }
            QLineEdit::placeholder {
                color: #94A3B8;
            }
            QLineEdit:focus {
                border: 2px solid #0EA5E9;
            }
            QPushButton {
                background-color: #0EA5E9;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #38BDF8;
            }
            QPushButton:pressed {
                background-color: #0284C7;
            }
            QTableWidget {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                gridline-color: #475569;
                color: #F1F5F9;
                font-size: 14px;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QHeaderView::section {
                background-color: #334155;
                padding: 12px;
                border: 1px solid #334155;
                color: #F1F5F9;
                font-weight: bold;
            }
            QFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
            }
            QToolBar {
                background-color: #1E293B;
                border: none;
            }
            QToolBar QToolButton {
                color: #FFFFFF;
                background-color: #0EA5E9;
                border-radius: 4px;
                padding: 4px;
            }
            QToolBar QToolButton:hover {
                background-color: #38BDF8;
            }
        """)
        
        # Central widget and main layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)  # Increased margins for better spacing
        
        # Left layout for search and chart
        left_layout = QVBoxLayout()
        left_layout.setSpacing(12)
        
        # Title
        title_label = QLabel("Google Trends Analysis")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; padding: 15px;")
        left_layout.addWidget(title_label)
        
        # Top search bar layout
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Enter stock ticker (e.g., HDFCBANK)")
        self.search_btn = QPushButton("Fetch Trends")
        self.search_btn.clicked.connect(self.search_stock)
        search_layout.addWidget(self.search_edit, 3)  # Stretch factor for responsiveness
        search_layout.addWidget(self.search_btn, 1)
        left_layout.addLayout(search_layout)
        
        # Chart frame and canvas
        chart_frame = QWidget()
        chart_layout = QVBoxLayout(chart_frame)
        self.figure = plt.Figure(facecolor='#1E293B')
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas, 1)  # Stretch factor for chart
        self.toolbar = CustomNavigationToolbar(self.canvas, self)  # Use custom toolbar
        chart_layout.addWidget(self.toolbar)
        left_layout.addWidget(chart_frame)
        
        # Right side for interest rate table
        right_layout = QVBoxLayout()
        table_label = QLabel("Interest Over Time")
        table_label.setStyleSheet("padding: 15px;")
        right_layout.addWidget(table_label)
        self.interest_table = QTableWidget()
        self.interest_table.setColumnCount(3)  # Updated to 3 columns
        self.interest_table.setHorizontalHeaderLabels(["Sr No.", "Date", "Interest Index"])  # Added Sr No.
        self.interest_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.interest_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Make table read-only
        self.interest_table.verticalHeader().setVisible(False)
        right_layout.addWidget(self.interest_table)
        
        # Add to main layout with stretch factors for responsiveness
        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_layout, 2)  # Adjusted stretch for balance
        
        # Fetch tickers for autocomplete
        self.tickers = self.get_tickers()
        if self.tickers:
            completer = QCompleter(self.tickers)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.search_edit.setCompleter(completer)
        
        # Initial empty table
        self.interest_table.setRowCount(0)

    def get_tickers(self):
        tickers = []
        cache_file_nse = "nse_tickers.csv"
        cache_file_bse = "bse_tickers.xlsx"
        
        # Fetch NSE tickers with fallback
        if os.path.exists(cache_file_nse):
            try:
                df_nse = pd.read_csv(cache_file_nse)
                tickers.extend(df_nse['SYMBOL'].tolist())
            except Exception as e:
                print(f"Error reading cached NSE tickers: {e}")
        else:
            try:
                nse_url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
                headers = {'User-Agent': 'Mozilla/5.0'}
                df_nse = pd.read_csv(nse_url, storage_options={'headers': headers})
                tickers.extend(df_nse['SYMBOL'].tolist())
                df_nse.to_csv(cache_file_nse, index=False)
            except Exception as e:
                print(f"Error fetching NSE tickers: {e}")
                tickers.extend(['RELIANCE', 'TCS'])  # Minimal fallback

        # Fetch BSE tickers with fallback
        if os.path.exists(cache_file_bse):
            try:
                df_bse = pd.read_excel(cache_file_bse, engine='openpyxl')
                if 'SCRIP CODE' in df_bse.columns:
                    tickers.extend(df_bse['SCRIP CODE'].astype(str).tolist())
            except Exception as e:
                print(f"Error reading cached BSE tickers: {e}")
        else:
            try:
                bse_url = "https://www.bseindia.com/downloads1/eligible.xls"
                headers = {'User-Agent': 'Mozilla/5.0'}
                df_bse = pd.read_excel(bse_url, engine='openpyxl', storage_options={'headers': headers})
                if 'SCRIP CODE' in df_bse.columns:
                    tickers.extend(df_bse['SCRIP CODE'].astype(str).tolist())
                df_bse.to_excel(cache_file_bse, index=False)
            except Exception as e:
                print(f"Error fetching BSE tickers: {e}")
                tickers.extend(['HDFCBANK', 'INFY'])  # Minimal fallback

        return sorted(set(tickers))  # Unique and sorted

    def search_stock(self):
        ticker = self.search_edit.text().strip().upper()
        if not ticker:
            self.show_error("Please enter a stock ticker.")
            return
        
        keyword = f"{ticker} share price"
        try:
            params = {
                'engine': 'google_trends',
                'q': keyword,
                'data_type': 'TIMESERIES',
                'date': 'today 5-y',
                'geo': 'IN',
                'api_key': SERPAPI_KEY  # Use the variable instead of string
            }
            response = requests.get('https://serpapi.com/search', params=params, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            data = response.json()
            
            if 'interest_over_time' in data and 'timeline_data' in data['interest_over_time']:
                timeline = data['interest_over_time']['timeline_data']
                dates = [item['date'] for item in timeline]
                values = []
                for item in timeline:
                    if item['values'] and len(item['values']) > 0:
                        val = item['values'][0].get('value', 'N/A')
                        values.append(float(val) if val != 'N/A' else 0)
                    else:
                        values.append(0)
                
                # Update chart
                self.ax.clear()
                self.ax.plot(dates, values, color='#0EA5E9', linewidth=2)
                
                num_points = len(dates)
                if num_points > 0:
                    tick_indices = np.linspace(0, num_points - 1, 3, dtype=int)
                    tick_dates = [dates[i] for i in tick_indices]
                    self.ax.set_xticks(tick_indices)
                    self.ax.set_xticklabels(tick_dates, rotation=45)
                
                self.ax.set_title(f"Interest Over Time for {ticker}", color='#F1F5F9', fontsize=16)
                self.ax.set_xlabel("Date", color='#F1F5F9', fontsize=14)
                self.ax.set_ylabel("Interest Index", color='#F1F5F9', fontsize=14)
                self.ax.set_facecolor('#1E293B')
                self.ax.tick_params(axis='x', colors='#F1F5F9')
                self.ax.tick_params(axis='y', colors='#F1F5F9')
                self.ax.grid(True, color='#475569', linestyle='-', alpha=0.2)
                self.ax.spines['top'].set_visible(False)
                self.ax.spines['right'].set_visible(False)
                self.ax.spines['left'].set_color('#475569')
                self.ax.spines['bottom'].set_color('#475569')
                self.figure.tight_layout()
                self.canvas.draw()
                
                # Update table with serial numbers
                self.interest_table.setRowCount(len(timeline))
                for i, (date, value) in enumerate(zip(dates, values)):
                    sr_no_item = QTableWidgetItem(str(i + 1))  # Serial number starts from 1
                    sr_no_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    date_item = QTableWidgetItem(str(date))
                    date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    value_item = QTableWidgetItem(str(value))
                    value_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self.interest_table.setItem(i, 0, sr_no_item)  # Sr No. column
                    self.interest_table.setItem(i, 1, date_item)   # Date column
                    self.interest_table.setItem(i, 2, value_item)  # Interest Index column
                self.interest_table.resizeColumnsToContents()
            else:
                self.show_error(f"No trend data available for {ticker}.")
            
            time.sleep(2)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                self.show_error("Rate limit exceeded. Please try again later.")
            elif e.response.status_code == 401:
                self.show_error("Invalid API key. Check your .env file.")
            else:
                self.show_error(f"Error fetching trends: {e}")
        except Exception as e:
            self.show_error(f"Error loading trends for {ticker}: {e}")

    def show_error(self, message):
        self.ax.clear()
        self.ax.text(0.5, 0.5, message, horizontalalignment='center', verticalalignment='center', color='#EF4444', transform=self.ax.transAxes)
        self.ax.set_facecolor('#1E293B')
        self.canvas.draw()
        self.interest_table.setRowCount(1)
        sr_no_item = QTableWidgetItem("1")  # Serial number for error row
        sr_no_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        message_item = QTableWidgetItem(message)
        message_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        na_item = QTableWidgetItem("N/A")
        na_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.interest_table.setItem(0, 0, sr_no_item)   # Sr No. column
        self.interest_table.setItem(0, 1, message_item) # Date column
        self.interest_table.setItem(0, 2, na_item)      # Interest Index column

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Application failed to start: {e}")
        sys.exit(1)