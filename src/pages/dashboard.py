#!/usr/bin/env python3
# dashboard.py -- fixed parsing, responsive layout, search + completer, date-range fixes

import sys, os, glob, random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QCheckBox, QFrame, QMessageBox, QCompleter, QHeaderView, QSizePolicy
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('qtagg')  # or 'QT_QTAGG' depending on your system
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import numpy as np

# ---------- Utility functions ----------
def safe_read_csv(path):
    """
    Read CSV robustly:
    - parse Date if available, else try first column
    - coerce numeric OHLCV columns (remove thousands separators)
    - return DataFrame with DatetimeIndex and numeric columns
    """
    df = pd.read_csv(path, dtype=str)  # read all as string first to handle weird formats
    # Normalize column names to expected lower-case mapping
    cols_lower = {c.lower(): c for c in df.columns}
    # Try to find a date column
    date_col = None
    for candidate in ('date', 'timestamp', 'dt'):
        if candidate in cols_lower:
            date_col = cols_lower[candidate]
            break
    if date_col is None:
        # fallback: first column
        date_col = df.columns[0] if len(df.columns) > 0 else None

    if date_col is not None:
        # parse datetimes
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce', infer_datetime_format=True)
        if df[date_col].isna().all():
            # If parse failed entirely, raise
            raise ValueError(f"Could not parse any dates in CSV ({path}) from column '{date_col}'")
        df = df.set_index(date_col)
    else:
        raise ValueError(f"No date column detected in {path}")

    # Standardize OHLCV names
    rename_map = {}
    for k, v in cols_lower.items():
        if k in ('open', 'o'): rename_map[v] = 'Open'
        if k in ('high', 'h'): rename_map[v] = 'High'
        if k in ('low', 'l'): rename_map[v] = 'Low'
        if k in ('close', 'c', 'adj close', 'adjclose'): rename_map[v] = 'Close'
        if k in ('volume', 'v', 'vol', 'totaltradequantity'): rename_map[v] = 'Volume'
    if rename_map:
        df = df.rename(columns=rename_map)

    # Ensure columns exist
    for required in ['Open','High','Low','Close','Volume']:
        if required not in df.columns:
            df[required] = pd.NA

    # Coerce numeric: remove commas and convert
    for col in ['Open','High','Low','Close','Volume']:
        df[col] = df[col].astype(str).str.replace(',', '', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(subset=['Close'])  # must have close to plot
    df = df.sort_index()
    return df

# ---------- Dashboard UI ----------
class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apex Analytics")
        self.resize(1280, 820)
        self._load_tickers()
        self._build_ui()
        self.apply_dark_theme()
        # initialize with a random ticker from BSE (if exists) or simulated
        self.full_df = None
        self.update_chart_data()  # load random / simulated
        self.update_top_values(self.table_combo.currentText())

    def _load_tickers(self):
        """Scan data/historical/NSE and BSE for CSV filenames (without extension)."""
        self.tickers = {'NSE': [], 'BSE': []}
        for exch in ('NSE', 'BSE'):
            folder = os.path.join('data', 'historical', exch)
            if os.path.isdir(folder):
                for f in sorted(os.listdir(folder)):
                    if f.lower().endswith('.csv'):
                        self.tickers[exch].append(os.path.splitext(f)[0])

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14,14,14,14)
        sidebar_layout.setSpacing(12)

        title = QLabel("Apex Analytics")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #EAF2FF")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        sidebar_layout.addWidget(title)

        sidebar_layout.addSpacing(6)
        menu_label = QLabel("MENU")
        menu_label.setStyleSheet("color: #9aa4b6; font-size:10px;")
        sidebar_layout.addWidget(menu_label)

        # menu buttons
        self.menu_buttons = []
        names = ["Dashboard", "Portfolio", "Prediction", "News & Sentiment", "Political Trading", "Google Trends"]
        for i, name in enumerate(names):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(40)
            btn.setFont(QFont("Segoe UI", 10))
            btn.clicked.connect(lambda checked, idx=i: self._select_menu(idx))
            btn.setStyleSheet(self._sidebar_button_style(False))
            sidebar_layout.addWidget(btn)
            self.menu_buttons.append(btn)
        self._select_menu(0)  # select dashboard

        sidebar_layout.addStretch()
        # Account section
        account_label = QLabel("ACCOUNT")
        account_label.setStyleSheet("color: #9aa4b6; font-size:10px;")
        sidebar_layout.addWidget(account_label)
        for t in ("Profile", "Settings"):
            b = QPushButton(t)
            b.setFixedHeight(36)
            b.setFont(QFont("Segoe UI", 10))
            b.setStyleSheet(self._sidebar_button_style(False))
            sidebar_layout.addWidget(b)

        sidebar_layout.addStretch()
        # Theme toggle
        self.theme_toggle = QCheckBox("Dark Mode")
        self.theme_toggle.setChecked(True)
        self.theme_toggle.stateChanged.connect(self._on_theme_toggle)
        sidebar_layout.addWidget(self.theme_toggle)

        main_layout.addWidget(sidebar)

        # Main content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14,14,14,14)
        content_layout.setSpacing(12)

        header_h = QHBoxLayout()
        title_lbl = QLabel("Dashboard")
        title_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_h.addWidget(title_lbl, alignment=Qt.AlignmentFlag.AlignLeft)

        # Search bar and exchange selector
        search_h = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search ticker/company")
        self.search_input.returnPressed.connect(self.on_search)
        self.search_input.setFixedHeight(34)
        search_h.addWidget(self.search_input)

        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(['NSE','BSE'])
        self.exchange_combo.currentTextChanged.connect(self._update_completer)
        self.exchange_combo.setFixedWidth(80)
        search_h.addWidget(self.exchange_combo)
        header_h.addLayout(search_h)
        content_layout.addLayout(header_h)

        # Build completer initially
        self.completer = QCompleter(self.tickers.get(self.exchange_combo.currentText(), []))
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_input.setCompleter(self.completer)

        # Indices small charts row
        indices_frame = QFrame()
        indices_frame.setObjectName('indices_frame')
        indices_layout = QHBoxLayout(indices_frame)
        indices_layout.setSpacing(10)
        indices_layout.setContentsMargins(0,0,0,0)

        example_indices = ["NIFTY 50","S&P 500","DJIA","NASDAQ","GOLD","Oil"]
        for name in example_indices:
            f = QFrame()
            f.setStyleSheet("background: #2b2b2b; border-radius:8px;")
            f.setFixedHeight(80)
            fl = QVBoxLayout(f)
            lbl = QLabel(name)
            lbl.setFont(QFont("Segoe UI", 9))
            lbl.setStyleSheet("color:#cfeaff;")
            fl.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignLeft)
            # tiny plot
            fig = Figure(figsize=(1.6,0.6), dpi=80)
            ax = fig.add_subplot()
            data = np.random.randn(20).cumsum()
            ax.plot(data, color='#6ff0e1')
            ax.axis('off')
            canv = FigureCanvas(fig)
            fl.addWidget(canv)
            indices_layout.addWidget(f)
        content_layout.addWidget(indices_frame)

        # Main chart container (rounded)
        chart_container = QFrame()
        chart_container.setObjectName('chart_container')
        chart_container.setStyleSheet("background: #17181A; border-radius: 10px;")
        chart_container.setMinimumHeight(340)
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(12,12,12,12)
        chart_layout.setSpacing(8)

        # Recent buttons (rounded)
        recent_h = QHBoxLayout()
        recent_h.setSpacing(10)
        self.recent_buttons = []
        for i in range(5):
            b = QPushButton(f"R{i+1}")
            b.setFixedSize(56,56)
            b.setStyleSheet("border-radius:28px; background:#2d2f33; color:#fff;")
            recent_h.addWidget(b)
            self.recent_buttons.append(b)
        chart_layout.addLayout(recent_h)

        # Range buttons
        range_h = QHBoxLayout()
        range_h.setSpacing(8)
        self.range_buttons = []
        ranges = ["1d","5d","1m","6m","1y","5y"]
        for r in ranges:
            btn = QPushButton(r)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setStyleSheet("border-radius:6px; padding:2px 8px;")
            btn.clicked.connect(lambda chk, rr=r: self.update_chart_range(rr))
            self.range_buttons.append(btn)
            range_h.addWidget(btn)
        chart_layout.addLayout(range_h)

        # Chart canvas (matplotlib)
        self.chart_fig = Figure(figsize=(8,3), dpi=100)
        self.chart_ax = self.chart_fig.add_subplot()
        self.chart_canvas = FigureCanvas(self.chart_fig)
        chart_layout.addWidget(self.chart_canvas)

        content_layout.addWidget(chart_container)

        # Bottom row: left table (top values) + right watchlist
        bottom_h = QHBoxLayout()
        bottom_h.setSpacing(12)

        # Left frame with rounded corners (table)
        left_frame = QFrame()
        left_frame.setStyleSheet("background:#171819; border-radius:10px;")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(8,8,8,8)
        left_layout.setSpacing(8)

        filter_h = QHBoxLayout()
        filter_label = QLabel("Filter:")
        filter_label.setFont(QFont("Segoe UI",9))
        filter_h.addWidget(filter_label)
        self.table_combo = QComboBox()
        self.table_combo.addItems(['BSE','NSE'])
        self.table_combo.currentTextChanged.connect(self.update_top_values)
        filter_h.addWidget(self.table_combo)
        filter_h.addStretch()
        left_layout.addLayout(filter_h)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Instrument","Volume","High","Low"])
        # make stretchable and responsive
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(self.table)

        bottom_h.addWidget(left_frame, 3)  # give it more space

        # Right watchlist placeholder
        right_frame = QFrame()
        right_frame.setStyleSheet("background:#171819; border-radius:10px;")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(8,8,8,8)
        wlbl = QLabel("Watchlist")
        wlbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        right_layout.addWidget(wlbl, alignment=Qt.AlignmentFlag.AlignTop)
        bottom_h.addWidget(right_frame, 1)

        content_layout.addLayout(bottom_h)

        main_layout.addWidget(content, 1)  # content gets expanding space

        # store widgets for later use
        self.left_table_frame = left_frame
        self.chart_container = chart_container

    # ---------- Styles ----------
    def _sidebar_button_style(self, selected: bool):
        if selected:
            return ("QPushButton { background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,"
                    "stop:0 #2e6b6b, stop:1 #1e7a7a); color: white; border-radius: 8px; }")
        else:
            return ("QPushButton { background: transparent; color: #d6dbe0; border-radius: 8px; text-align:left; padding-left:10px; }"
                    "QPushButton:hover { background:#222426; }")

    def _select_menu(self, index):
        for i, btn in enumerate(self.menu_buttons):
            selected = (i == index)
            btn.setChecked(selected)
            btn.setStyleSheet(self._sidebar_button_style(selected))

    def _on_theme_toggle(self, state):
        self.apply_dark_theme() if state==Qt.CheckState.Checked.value else self.apply_light_theme()

    def apply_dark_theme(self):
        dark = """
        QMainWindow{ background:#121213; color:#e6eef6; }
        QLabel{ color:#dbe9f7; }
        QLineEdit, QComboBox { background:#1e1f21; color:#e6eef6; border:1px solid #2b2b2b; border-radius:6px; padding:4px; }
        QPushButton { background: #2b2b2b; color:#e6eef6; border: none; }
        QTableWidget { background: #121315; color:#e6eef6; border: none; }
        """
        self.setStyleSheet(dark)

    def apply_light_theme(self):
        light = """
        QMainWindow{ background:#f4f6f8; color:#111; }
        """
        self.setStyleSheet(light)

    # ---------- Completer / Search ----------
    def _update_completer(self, exch):
        lst = self.tickers.get(exch, [])
        if not isinstance(self.completer, QCompleter):
            self.completer = QCompleter(lst)
            self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.search_input.setCompleter(self.completer)
        else:
            self.completer.model().setStringList(lst)

    def on_search(self):
        ticker = self.search_input.text().strip()
        exch = self.exchange_combo.currentText()
        if not ticker:
            QMessageBox.information(self, "Search", "Type a ticker and press Enter")
            return
        # attempt to load CSV for ticker
        path = os.path.join('data','historical', exch, f"{ticker}.csv")
        if not os.path.exists(path):
            QMessageBox.warning(self, "Not found", f"Ticker file not found: {path}")
            return
        try:
            df = safe_read_csv(path)
            self.full_df = df
            self.plot_ohlc(self.full_df)
        except Exception as e:
            QMessageBox.critical(self, "CSV load error", f"Failed to load '{path}':\n{e}")

    # ---------- Chart handling ----------
    def update_chart_data(self, ticker=None, exchange='BSE'):
        # if ticker provided, try to load; else pick random from BSE or NSE. If nothing, simulate
        df = None
        if ticker:
            p = os.path.join('data','historical', exchange, f"{ticker}.csv")
            if os.path.exists(p):
                try:
                    df = safe_read_csv(p)
                except Exception as e:
                    QMessageBox.warning(self, "CSV", f"Failed to load {p}: {e}")
                    df = None
        else:
            # pick random from BSE then NSE
            for exch in ('BSE','NSE'):
                if self.tickers.get(exch):
                    r = random.choice(self.tickers[exch])
                    try:
                        df = safe_read_csv(os.path.join('data','historical', exch, f"{r}.csv"))
                        break
                    except Exception:
                        df = None
            # if still None, simulate simple data
        if df is None or df.empty:
            # simulate some OHLC-like series (for display)
            dates = pd.date_range(end=pd.Timestamp.today(), periods=120, freq='B')
            prices = 100 + np.cumsum(np.random.randn(len(dates)))
            df = pd.DataFrame(index=dates)
            df['Open'] = prices + np.random.randn(len(dates)) * 0.5
            df['Close'] = prices + np.random.randn(len(dates)) * 0.5
            df['High'] = np.maximum(df['Open'], df['Close']) + np.abs(np.random.randn(len(dates)))
            df['Low'] = np.minimum(df['Open'], df['Close']) - np.abs(np.random.randn(len(dates)))
            df['Volume'] = (np.random.rand(len(dates)) * 10000).astype(int)
        self.full_df = df
        self.plot_ohlc(self.full_df)

    def plot_ohlc(self, df):
        self.chart_ax.clear()
        if df is None or df.empty:
            self.chart_canvas.draw()
            return
        # ensure df index is datetime
        df = df.sort_index()
        # get numeric columns guaranteed by safe_read_csv
        # plot candlestick-like bars (simple)
        width = 0.8
        xs = df.index
        opens = pd.to_numeric(df['Open'], errors='coerce')
        closes = pd.to_numeric(df['Close'], errors='coerce')
        highs = pd.to_numeric(df['High'], errors='coerce')
        lows = pd.to_numeric(df['Low'], errors='coerce')
        # decide up/down
        up_mask = closes >= opens
        down_mask = ~up_mask
        # draw vertical lines (high-low)
        self.chart_ax.vlines(xs, lows, highs, color='silver', linewidth=0.8)
        # draw rectangles (open-close)
        self.chart_ax.bar(xs[up_mask], (closes - opens)[up_mask], bottom=opens[up_mask], width=width, color='#1db954', edgecolor='#1db954')
        self.chart_ax.bar(xs[down_mask], (closes - opens)[down_mask], bottom=opens[down_mask], width=width, color='#e84d4d', edgecolor='#e84d4d')
        self.chart_ax.set_ylabel("Price")
        self.chart_ax.grid(axis='y', linestyle=':', alpha=0.2)
        # format x ticks nicely
        self.chart_fig.autofmt_xdate()
        self.chart_canvas.draw()

    # ---------- Range button logic ----------
    def update_chart_range(self, label):
        # uncheck others and check this
        for b in self.range_buttons:
            b.setChecked(b.text() == label)
        if self.full_df is None or self.full_df.empty:
            return
        df = self.full_df
        now = pd.Timestamp.now()
        if label == '1d':
            new_df = df.last('1D') if '1D' in pd.tseries.frequencies.get_freq_aliases() else df.iloc[-1:]
        elif label == '5d':
            cutoff = now - pd.Timedelta(days=7)
            new_df = df.loc[df.index >= cutoff]
        elif label == '1m':
            cutoff = now - pd.Timedelta(days=30)
            new_df = df.loc[df.index >= cutoff]
        elif label == '6m':
            cutoff = now - pd.Timedelta(days=182)
            new_df = df.loc[df.index >= cutoff]
        elif label == '1y':
            cutoff = now - pd.Timedelta(days=365)
            new_df = df.loc[df.index >= cutoff]
        elif label == '5y':
            cutoff = now - pd.Timedelta(days=1825)
            new_df = df.loc[df.index >= cutoff]
        else:
            new_df = df
        if new_df.empty:
            QMessageBox.information(self, "Range", "No data available for selected range")
            return
        self.plot_ohlc(new_df)

    # ---------- Top values table ----------
    def update_top_values(self, exchange):
        # list of tickers for this exchange
        tickers_list = self.tickers.get(exchange, [])
        n = len(tickers_list)
        # safety: show up to 500 rows but small preview
        self.table.setRowCount(min(n, 800))
        for i, ticker in enumerate(tickers_list[:800]):
            path = os.path.join('data','historical', exchange, f"{ticker}.csv")
            vol = ""
            high = ""
            low = ""
            if os.path.exists(path):
                try:
                    df = pd.read_csv(path)
                    # try to get last row values robustly
                    if 'Close' in df.columns or 'High' in df.columns:
                        last_row = df.iloc[-1]
                        vol = str(last_row.get('Volume', last_row.get('TOTALTRADEQUANTITY', "")))
                        high = str(last_row.get('High', last_row.get('HIGH', "")))
                        low = str(last_row.get('Low', last_row.get('LOW', "")))
                except Exception:
                    pass
            self.table.setItem(i, 0, QTableWidgetItem(ticker))
            self.table.setItem(i, 1, QTableWidgetItem(vol))
            self.table.setItem(i, 2, QTableWidgetItem(high))
            self.table.setItem(i, 3, QTableWidgetItem(low))

# ---------- run ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = DashboardWindow()
    w.show()
    sys.exit(app.exec())
