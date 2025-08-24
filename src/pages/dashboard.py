#!/usr/bin/env python3
# dashboard.py - corrected, recent-search buttons, range fixes, robust CSV parsing

import sys, os, glob, random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QCheckBox, QFrame, QMessageBox, QCompleter, QHeaderView, QSizePolicy
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import matplotlib
matplotlib.use('qtagg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
import datetime

# ---------- Utility functions ----------
def safe_read_csv(path):
    """
    Read CSV robustly:
    - parse Date if available, else try first column
    - coerce numeric OHLCV columns (remove thousands separators)
    - return DataFrame with DatetimeIndex and numeric columns
    """
    df = pd.read_csv(path, dtype=str, low_memory=False)  # read as str to sanitize
    # Normalize column name lookup
    cols_lower = {c.lower(): c for c in df.columns}

    # choose a date column if present
    date_col = None
    for candidate in ('date', 'timestamp', 'time', 'datetime'):
        if candidate in cols_lower:
            date_col = cols_lower[candidate]
            break
    if date_col is None:
        # fallback to first column
        date_col = df.columns[0] if len(df.columns) > 0 else None

    if date_col is None:
        raise ValueError("No date column found")

    # parse datetimes (no infer_datetime_format arg)
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    if df[date_col].isna().all():
        raise ValueError(f"Date parsing failed for column '{date_col}' in {path}")
    df = df.set_index(date_col)

    # Map common OHLC/Volume names to canonical columns
    rename_map = {}
    for lower, orig in cols_lower.items():
        if lower in ('open','o'): rename_map[orig] = 'Open'
        if lower in ('high','h'): rename_map[orig] = 'High'
        if lower in ('low','l'): rename_map[orig] = 'Low'
        if lower in ('close','c','adj close','adjclose'): rename_map[orig] = 'Close'
        if lower in ('volume','v','vol','totaltradequantity','totaltradedqty'): rename_map[orig] = 'Volume'
    if rename_map:
        df = df.rename(columns=rename_map)

    # Ensure required cols exist
    for col in ['Open','High','Low','Close','Volume']:
        if col not in df.columns:
            df[col] = pd.NA

    # sanitize numeric columns: remove commas and convert
    for col in ['Open','High','Low','Close','Volume']:
        df[col] = df[col].astype(str).str.replace(',', '', regex=False)
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # drop rows without Close
    df = df.dropna(subset=['Close'])
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
        # recent searches (list of tuples (ticker, exchange)) - newest first
        self.recent = []
        self.full_df = None
        self.update_chart_data()     # initial random/simulated load
        self.update_top_values(self.table_combo.currentText())

    def _load_tickers(self):
        self.tickers = {'NSE': [], 'BSE': []}
        for exch in ('NSE','BSE'):
            folder = os.path.join('data','historical', exch)
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
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14,14,14,14)
        sidebar_layout.setSpacing(10)

        title = QLabel("Apex Analytics")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #EAF2FF")
        sidebar_layout.addWidget(title)

        sidebar_layout.addSpacing(6)
        menu_label = QLabel("MENU")
        menu_label.setStyleSheet("color: #9aa4b6; font-size:10px;")
        sidebar_layout.addWidget(menu_label)

        # menu buttons rounded
        self.menu_buttons = []
        names = ["Dashboard","Portfolio","Prediction","News & Sentiment","Political Trading","Google Trends"]
        for i, name in enumerate(names):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setFont(QFont("Segoe UI", 10))
            btn.clicked.connect(lambda checked, idx=i: self._select_menu(idx))
            btn.setStyleSheet(self._sidebar_button_style(False))
            sidebar_layout.addWidget(btn)
            self.menu_buttons.append(btn)
        self._select_menu(0)  # default

        sidebar_layout.addStretch()
        acc_lbl = QLabel("ACCOUNT")
        acc_lbl.setStyleSheet("color: #9aa4b6; font-size:10px;")
        sidebar_layout.addWidget(acc_lbl)
        for t in ("Profile","Settings"):
            b = QPushButton(t)
            b.setFixedHeight(36)
            b.setFont(QFont("Segoe UI", 10))
            b.setStyleSheet(self._sidebar_button_style(False))
            sidebar_layout.addWidget(b)
        sidebar_layout.addStretch()

        # theme toggle
        self.theme_toggle = QCheckBox("Dark Mode")
        self.theme_toggle.setChecked(True)
        self.theme_toggle.stateChanged.connect(self._on_theme_toggle)
        sidebar_layout.addWidget(self.theme_toggle)

        main_layout.addWidget(sidebar)

        # Main content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14,14,14,14)
        content_layout.setSpacing(12)

        # Header + search
        header = QHBoxLayout()
        hdr_lbl = QLabel("Dashboard")
        hdr_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.addWidget(hdr_lbl, alignment=Qt.AlignmentFlag.AlignLeft)

        # search + exchange selector
        search_h = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search ticker/company")
        self.search_input.returnPressed.connect(self.on_search)
        self.search_input.setFixedHeight(34)
        search_h.addWidget(self.search_input)

        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(['NSE','BSE'])
        self.exchange_combo.setFixedWidth(80)
        self.exchange_combo.currentTextChanged.connect(self._update_completer)
        search_h.addWidget(self.exchange_combo)
        header.addLayout(search_h)
        content_layout.addLayout(header)

        # completer
        self.completer = QCompleter(self.tickers.get(self.exchange_combo.currentText(), []))
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_input.setCompleter(self.completer)

        # indices row (simulated)
        indices_frame = QFrame()
        indices_layout = QHBoxLayout(indices_frame)
        indices_layout.setSpacing(10)
        example_indices = ["NIFTY 50","S&P 500","DJIA","NASDAQ","GOLD","Oil"]
        for name in example_indices:
            f = QFrame()
            f.setStyleSheet("background: #2b2b2b; border-radius:8px;")
            f.setFixedHeight(80)
            fl = QVBoxLayout(f)
            lbl = QLabel(name); lbl.setFont(QFont("Segoe UI",9)); lbl.setStyleSheet("color:#cfeaff;")
            fl.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignLeft)
            # small plot
            fig = Figure(figsize=(1.6,0.6), dpi=80)
            ax = fig.add_subplot()
            data = np.random.randn(20).cumsum()
            ax.plot(data, color='#6ff0e1')
            ax.axis('off')
            canv = FigureCanvas(fig)
            fl.addWidget(canv)
            indices_layout.addWidget(f)
        content_layout.addWidget(indices_frame)

        # chart container
        chart_container = QFrame()
        chart_container.setStyleSheet("background: #17181A; border-radius: 10px;")
        chart_container.setMinimumHeight(360)
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(12,12,12,12)
        chart_layout.setSpacing(8)

        # recent buttons (wired)
        recent_h = QHBoxLayout()
        self.recent_buttons = []
        for i in range(5):
            b = QPushButton("—")
            b.setFixedSize(56,56)
            b.setStyleSheet("border-radius:28px; background:#2d2f33; color:#fff;")
            b.clicked.connect(lambda _, idx=i: self._on_recent_click(idx))
            recent_h.addWidget(b)
            self.recent_buttons.append(b)
        chart_layout.addLayout(recent_h)

        # range buttons
        range_h = QHBoxLayout()
        self.range_buttons = []
        ranges = ["1d","5d","1m","6m","1y","5y"]
        for r in ranges:
            btn = QPushButton(r)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setStyleSheet("border-radius:6px; padding:2px 8px;")
            btn.clicked.connect(lambda _, rr=r: self.update_chart_range(rr))
            self.range_buttons.append(btn)
            range_h.addWidget(btn)
        chart_layout.addLayout(range_h)

        # chart canvas
        self.chart_fig = Figure(figsize=(8,3), dpi=100)
        self.chart_ax = self.chart_fig.add_subplot()
        self.chart_canvas = FigureCanvas(self.chart_fig)
        chart_layout.addWidget(self.chart_canvas)
        content_layout.addWidget(chart_container)

        # bottom row
        bottom_h = QHBoxLayout()
        left_frame = QFrame()
        left_frame.setStyleSheet("background:#171819; border-radius:10px;")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(8,8,8,8)

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

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Instrument","Volume","High","Low"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_layout.addWidget(self.table)
        bottom_h.addWidget(left_frame, 3)

        right_frame = QFrame()
        right_frame.setStyleSheet("background:#171819; border-radius:10px;")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(8,8,8,8)
        wlbl = QLabel("Watchlist")
        wlbl.setFont(QFont("Segoe UI",12, QFont.Weight.Bold))
        right_layout.addWidget(wlbl, alignment=Qt.AlignmentFlag.AlignTop)
        bottom_h.addWidget(right_frame, 1)

        content_layout.addLayout(bottom_h)
        main_layout.addWidget(content, 1)

        # store UI refs
        self.left_table_frame = left_frame
        self.chart_container = chart_container

    # ---------- styling helpers ----------
    def _sidebar_button_style(self, selected: bool):
        if selected:
            return ("QPushButton { background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,"
                    "stop:0 #2e6b6b, stop:1 #1e7a7a); color: white; border-radius: 8px; }")
        else:
            return ("QPushButton { background: transparent; color: #d6dbe0; border-radius: 8px; text-align:left; padding-left:10px; }"
                    "QPushButton:hover { background:#222426; }")

    def _select_menu(self, index):
        for i, btn in enumerate(self.menu_buttons):
            sel = (i == index)
            btn.setChecked(sel)
            btn.setStyleSheet(self._sidebar_button_style(sel))

    def _on_theme_toggle(self, state):
        self.apply_dark_theme() if state == Qt.CheckState.Checked.value else self.apply_light_theme()

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
        self.setStyleSheet("QMainWindow{ background:#f4f6f8; color:#111; }")

    # ---------- completer / search ----------
    def _update_completer(self, exch):
        lst = self.tickers.get(exch, [])
        if not hasattr(self, 'completer') or self.completer is None:
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
        path = os.path.join('data','historical', exch, f"{ticker}.csv")
        if not os.path.exists(path):
            QMessageBox.warning(self, "Not found", f"Ticker file not found: {path}")
            return
        try:
            df = safe_read_csv(path)
            self.full_df = df
            self.plot_ohlc(self.full_df)
            # update recent list
            self._add_recent(ticker, exch)
        except Exception as e:
            QMessageBox.critical(self, "CSV load error", f"Failed to load '{path}':\n{e}")

    # ---------- recent handling ----------
    def _add_recent(self, ticker, exch):
        # add to front, unique, keep length 5
        item = (ticker, exch)
        if item in self.recent:
            self.recent.remove(item)
        self.recent.insert(0, item)
        self.recent = self.recent[:5]
        # update button labels
        for i, b in enumerate(self.recent_buttons):
            if i < len(self.recent):
                t, e = self.recent[i]
                b.setText(t)
            else:
                b.setText("—")

    def _on_recent_click(self, idx):
        if idx < len(self.recent):
            ticker, exch = self.recent[idx]
            self.exchange_combo.setCurrentText(exch)
            self.search_input.setText(ticker)
            self.on_search()

    # ---------- chart logic ----------
    def update_chart_data(self, ticker=None, exchange='BSE'):
        df = None
        if ticker:
            p = os.path.join('data','historical', exchange, f"{ticker}.csv")
            if os.path.exists(p):
                try:
                    df = safe_read_csv(p)
                except Exception:
                    df = None
        else:
            # pick random ticker (BSE then NSE) or simulate
            for exch in ('BSE','NSE'):
                if self.tickers.get(exch):
                    r = random.choice(self.tickers[exch])
                    try:
                        df = safe_read_csv(os.path.join('data','historical', exch, f"{r}.csv"))
                        break
                    except Exception:
                        df = None
        if df is None or df.empty:
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
        df = df.sort_index()
        xs = df.index
        opens = pd.to_numeric(df['Open'], errors='coerce')
        closes = pd.to_numeric(df['Close'], errors='coerce')
        highs = pd.to_numeric(df['High'], errors='coerce')
        lows = pd.to_numeric(df['Low'], errors='coerce')
        up_mask = closes >= opens
        down_mask = ~up_mask
        # draw wicks
        self.chart_ax.vlines(xs, lows, highs, color='silver', linewidth=0.8)
        # draw bodies
        self.chart_ax.bar(xs[up_mask], (closes - opens)[up_mask], bottom=opens[up_mask], width=0.8, color='#1db954', edgecolor='#1db954')
        self.chart_ax.bar(xs[down_mask], (closes - opens)[down_mask], bottom=opens[down_mask], width=0.8, color='#e84d4d', edgecolor='#e84d4d')
        self.chart_ax.set_ylabel("Price")
        self.chart_ax.grid(axis='y', linestyle=':', alpha=0.2)
        self.chart_fig.autofmt_xdate()
        self.chart_canvas.draw()

    # ---------- range handling (no deprecated pandas API) ----------
    def update_chart_range(self, label):
        # toggle selected
        for b in self.range_buttons:
            b.setChecked(b.text() == label)
        if self.full_df is None or self.full_df.empty:
            return
        df = self.full_df
        now = pd.Timestamp.now()
        if label == '1d':
            # last available row (most recent trading day)
            new_df = df.iloc[-1:]
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

    # ---------- top-values table ----------
    def update_top_values(self, exchange):
        tickers_list = self.tickers.get(exchange, [])
        n = len(tickers_list)
        rows = min(n, 800)
        self.table.setRowCount(rows)
        for i, ticker in enumerate(tickers_list[:rows]):
            path = os.path.join('data','historical', exchange, f"{ticker}.csv")
            vol = ""; high = ""; low = ""
            if os.path.exists(path):
                try:
                    df = pd.read_csv(path, low_memory=False)
                    if not df.empty:
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
