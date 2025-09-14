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

# Load API key from .env file
load_dotenv()
SERPAPI_KEY = os.getenv('SERPAPI_KEY')
if not SERPAPI_KEY:
    raise ValueError("SERPAPI_KEY not found in .env file. Please set it up.")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Google Trends Analysis")
        self.resize(1200, 800)
        
        # Enhanced dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #2E2E2E, stop: 1 #1A1A1A);
            }
            QLabel {
                color: #FFFFFF;
                font-family: Arial;
                font-size: 16px;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #3E3E3E;
                border: 2px solid #4E4E4E;
                border-radius: 5px;
                padding: 8px;
                color: #FFFFFF;
                font-size: 14px;
            }
            QPushButton {
                background-color: #007BFF;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QTableWidget {
                background-color: #3E3E3E;
                border: 2px solid #4E4E4E;
                border-radius: 5px;
                gridline-color: #4E4E4E;
                color: #FFFFFF;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 5px;
                border: 1px solid #4E4E4E;
            }
            QHeaderView::section {
                background-color: #4E4E4E;
                padding: 8px;
                border: 1px solid #4E4E4E;
                color: #FFFFFF;
                font-weight: bold;
            }
            QFrame {
                background-color: #3E3E3E;
                border: 2px solid #4E4E4E;
                border-radius: 5px;
            }
        """)
        
        # Central widget and main layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        
        # Left layout for search and chart
        left_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Google Trends Analysis")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title_label)
        
        # Top search bar layout
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Enter stock ticker (e.g., HDFCBANK)")
        self.search_btn = QPushButton("Fetch Trends")
        self.search_btn.clicked.connect(self.search_stock)
        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.search_btn)
        left_layout.addLayout(search_layout)
        
        # Chart frame and canvas
        chart_frame = QWidget()
        chart_layout = QVBoxLayout(chart_frame)
        self.figure = plt.Figure(facecolor='#3E3E3E')
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        self.toolbar = NavigationToolbar(self.canvas, self)
        chart_layout.addWidget(self.toolbar)
        left_layout.addWidget(chart_frame)
        
        # Right side for interest rate table
        right_layout = QVBoxLayout()
        table_label = QLabel("Interest Over Time")
        right_layout.addWidget(table_label)
        self.interest_table = QTableWidget()
        self.interest_table.setColumnCount(2)
        self.interest_table.setHorizontalHeaderLabels(["Date", "Interest Index"])
        self.interest_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_layout.addWidget(self.interest_table)
        
        # Add to main layout with stretch factors for responsiveness
        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_layout, 1)
        
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
                'api_key': SERPAPI_KEY
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
                self.ax.plot(dates, values, color='#1E90FF', linewidth=1.5)
                self.ax.set_title(f"Interest Over Time for {ticker}", color='#FFFFFF', fontsize=14)
                self.ax.set_xlabel("Date", color='#FFFFFF', fontsize=12)
                self.ax.set_ylabel("Interest Index", color='#FFFFFF', fontsize=12)
                self.ax.set_facecolor('#000000')
                self.ax.tick_params(axis='x', colors='#FFFFFF', rotation=45)
                self.ax.tick_params(axis='y', colors='#FFFFFF')
                self.ax.grid(True, color='#333333', linestyle='-', alpha=0.3)
                self.ax.spines['top'].set_visible(False)
                self.ax.spines['right'].set_visible(False)
                self.ax.spines['left'].set_color('#333333')
                self.ax.spines['bottom'].set_color('#333333')
                self.figure.tight_layout()
                self.canvas.draw()
                
                # Update table
                self.interest_table.setRowCount(len(timeline))
                for i, (date, value) in enumerate(zip(dates, values)):
                    self.interest_table.setItem(i, 0, QTableWidgetItem(str(date)))
                    self.interest_table.setItem(i, 1, QTableWidgetItem(str(value)))
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
        self.ax.text(0.5, 0.5, message, horizontalalignment='center', verticalalignment='center', color='#FF0000', transform=self.ax.transAxes)
        self.ax.set_facecolor('#000000')
        self.canvas.draw()
        self.interest_table.setRowCount(1)
        self.interest_table.setItem(0, 0, QTableWidgetItem(message))
        self.interest_table.setItem(0, 1, QTableWidgetItem("N/A"))

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Application failed to start: {e}")
        sys.exit(1)