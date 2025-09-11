#!/usr/bin/env python3
# Apex Analytics - Dashboard (dynamic chips, extra ranges, modern filter combo)
# Updated: left navigation bar removed; index fetch runs in background (non-blocking)
# Requirements: yfinance, pandas, numpy, PyQt6, matplotlib, pytz

import sys
import os
import random
import warnings
import logging
from typing import Optional
from datetime import datetime
import pytz  # For timezone-aware clock

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QCheckBox, QFrame, QMessageBox, QCompleter, QHeaderView, QSizePolicy,
    QScrollArea, QAbstractItemView
)
from PyQt6.QtGui import QFont, QPainter, QColor, QLinearGradient, QBrush
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QRunnable, QThreadPool
import matplotlib
matplotlib.use('qtagg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
import numpy as np

# yfinance for live updates
try:
    import yfinance as yf
except Exception:
    yf = None  # code will gracefully fall back to simulated data

# Silence noisy yfinance warnings/logging that spam the console.
logging.getLogger("yfinance").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*possibly delisted.*", category=Warning)

# ---------------------------- Custom Gradient Background Widget ----------------------------
class GradientWidget(QWidget):
    """A widget with a rich, cool-toned diagonal gradient background."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Same rich gradient as the login/signup pages
        top_left_color = QColor("#0f0c29")
        middle_color = QColor("#302b63")
        bottom_right_color = QColor("#24243e")

        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0.0, top_left_color)
        gradient.setColorAt(0.5, middle_color)
        gradient.setColorAt(1.0, bottom_right_color)

        painter.fillRect(self.rect(), QBrush(gradient))
        super().paintEvent(event)

# ---------------------------- Helpers ----------------------------
SUFFIXES = (".BO", "_BO", ".NS", "_NS", "-EQ", "-BE", "-BZ")

def clean_ticker(name: str) -> str:
    """Return a pretty display ticker without exchange suffixes."""
    if not name:
        return name
    n = name.upper()
    for s in SUFFIXES:
        if n.endswith(s):
            n = n[: -len(s)]
    return n

def safe_read_csv(path: str) -> pd.DataFrame:
    """Robust CSV reader returning DateTime-indexed OHLCV data if possible."""
    df = pd.read_csv(path, dtype=str, low_memory=False)
    if df.empty:
        return pd.DataFrame()

    cols_lower = {c.lower(): c for c in df.columns}
    date_col = None
    for cand in ("date", "timestamp", "time", "datetime"):
        if cand in cols_lower:
            date_col = cols_lower[cand]
            break
    if date_col is None:
        date_col = df.columns[0]

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    if df[date_col].isna().all():
        raise ValueError(f"Could not parse dates in '{os.path.basename(path)}'")

    df = df.set_index(date_col).sort_index()

    rename = {}
    for low, orig in cols_lower.items():
        if low in ("open", "o"): rename[orig] = "Open"
        if low in ("high", "h"): rename[orig] = "High"
        if low in ("low", "l"):  rename[orig] = "Low"
        if low in ("close", "c", "adj close", "adjclose"): rename[orig] = "Close"
        if low in ("volume","v","vol","totaltradequantity","totaltradedqty"):
            rename[orig] = "Volume"
    df = df.rename(columns=rename)

    for col in ["Open","High","Low","Close","Volume"]:
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = df[col].astype(str).str.replace(",", "", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Close"])
    return df

# ---------------------------- Background worker for indices ----------------------------
class IndexFetchSignals(QObject):
    finished = pyqtSignal(dict)  # payload: { symbol_str : pandas.Series }

class IndexFetcher(QRunnable):
    """
    QRunnable that fetches a small history for a list of symbols (indices).
    Emits a dict mapping symbol->pandas.Series (index timestamps -> close values)
    """
    def __init__(self, indices_conf):
        super().__init__()
        self.indices_conf = indices_conf
        self.signals = IndexFetchSignals()

    def run(self):
        results = {}
        for conf in self.indices_conf:
            sym = conf.get("symbol")
            series = self._fetch_index_series(sym, period="7d", interval="60m")
            if series is None or len(series) == 0:
                series = self._simulate_series()
            results[sym] = series
        self.signals.finished.emit(results)

    def _simulate_series(self, points=24):
        x = np.arange(points)
        y = np.cumsum(np.random.randn(points)) + 100
        idx = pd.date_range(end=pd.Timestamp.now(), periods=len(x), freq='h')
        return pd.Series(y, index=idx)

    def _fetch_index_series(self, symbol: str, period="7d", interval="60m"):
        if yf is None:
            return self._simulate_series()
        try:
            ticker = yf.Ticker(symbol)
            fetch_period = "2d" if "INR" in symbol or "VIX" in symbol else period
            fetch_interval = "15m" if "INR" in symbol or "VIX" in symbol else interval
            hist = ticker.history(period=fetch_period, interval=fetch_interval, actions=False)
            if hist is None or hist.empty:
                hist = ticker.history(period="30d", interval="1d", actions=False)
            if hist is None or hist.empty:
                return pd.Series(dtype=float)
            closes = hist["Close"].dropna()
            if len(closes) > 48:
                closes = closes.iloc[-48:]
            return closes
        except Exception:
            return pd.Series(dtype=float)

# ---------------------------- Main Window (Dashboard Page) ----------------------------
class DashboardWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # data maps
        self.tickers = {"NSE": [], "BSE": []}
        self.display_map = {"NSE": {}, "BSE": {}}   # display -> file ticker
        self._load_tickers()

        self.indices_conf = [
            # For mini-charts
            {"label":"NIFTY 50", "symbol":"^NSEI"},
            {"label":"SENSEX",   "symbol":"^BSESN"},
            {"label":"NIFTY Bank", "symbol":"^NSEBANK"},
            {"label":"NIFTY Midcap 100", "symbol":"^CNXMDCP100"},
            {"label":"NIFTY Smallcap 100", "symbol":"^CNXSML100"},
            {"label":"Gold", "symbol":"GOLDBEES.NS"},
            # For header pills
            {"label":"USDINR", "symbol":"INR=X"},
            {"label":"INDIA VIX", "symbol":"^INDIAVIX"}
        ]

        self.threadpool = QThreadPool()
        self._indices_fetch_in_progress = False
        self._sim_tick_counter = 0
        self._build_ui()
        self.chips = []
        self.full_df = None

        initial_added = False
        for exch in ("BSE", "NSE"):
            if self.tickers.get(exch):
                file_t = random.choice(self.tickers[exch])
                display = clean_ticker(file_t)
                self._add_chip(display, exch, file_t, select=True)
                try:
                    df = safe_read_csv(os.path.join("data", "historical", exch, f"{file_t.replace('.', '_')}.csv"))
                    self.full_df = df
                    self.plot_ohlc(self.full_df)
                except Exception:
                    self.update_chart_data()
                initial_added = True
                break
        if not initial_added:
            self.update_chart_data()

        self.update_top_values(self.table_combo.currentText())
        self._setup_index_canvases()
        self.index_timer = QTimer(self)
        self.index_timer.timeout.connect(self._schedule_index_fetch)
        self.index_timer.start(10_000)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_header_indicators)
        self.status_timer.start(1000)

    def _load_tickers(self):
        for exch in ("NSE", "BSE"):
            folder = os.path.join("data", "historical", exch)
            if not os.path.isdir(folder):
                continue
            for f in sorted(os.listdir(folder)):
                if not f.lower().endswith(".csv"):
                    continue
                file_ticker = os.path.splitext(f)[0].replace('_', '.')
                display = clean_ticker(file_ticker)
                self.tickers[exch].append(file_ticker)
                self.display_map[exch][display] = file_ticker

    def _build_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0,0,0,0)
        
        main_scroll_area = QScrollArea()
        main_scroll_area.setWidgetResizable(True)
        main_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        main_scroll_area.setStyleSheet(self._scrollbar_style())
        page_layout.addWidget(main_scroll_area)

        content_bg = GradientWidget()
        main_scroll_area.setWidget(content_bg)

        cl = QVBoxLayout(content_bg)
        cl.setContentsMargins(16,16,16,16)
        cl.setSpacing(12)
        
        content_bg.setMinimumWidth(1200)
        content_bg.setMinimumHeight(800)

        # header line
        header = QHBoxLayout()
        header.setSpacing(10)

        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("Search ticker/company")
        self.search_input.setMinimumWidth(400)
        self.search_input.setFixedHeight(36); self.search_input.returnPressed.connect(self.on_search)
        search_style = """
            QLineEdit {
                background-color: #1B2026; color: #DDE8F5; border: 1px solid #2B323A;
                border-radius: 18px; padding: 0px 15px;
            }
            QLineEdit:hover { border: 1px solid #3B4652; }
            QLineEdit:focus { border: 1px solid #33C4B9; }
        """
        self.search_input.setStyleSheet(search_style)
        header.addWidget(self.search_input)

        self.search_button = QPushButton("Search")
        self.search_button.setFixedHeight(36)
        self.search_button.setFixedWidth(100)
        self.search_button.setStyleSheet(self._pill_button_style())
        self.search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_button.clicked.connect(self.on_search)
        header.addWidget(self.search_button)

        self.exchange_combo = QComboBox(); self.exchange_combo.addItems(["NSE","BSE"])
        self.exchange_combo.setFixedWidth(110); self.exchange_combo.currentTextChanged.connect(self._update_completer)
        self.exchange_combo.setStyleSheet(self._combo_style())
        header.addWidget(self.exchange_combo)
        
        pills_container = QWidget()
        pills_layout = QHBoxLayout(pills_container)
        pills_layout.setContentsMargins(0,0,0,0)
        pills_layout.setSpacing(10)
        
        self.clock_label = QLabel("--:--:-- IST")
        self.market_status_label = QLabel("⚫ MARKET CLOSED")
        self.breadth_label = QLabel("A/D --/--")
        self.usdinr_label = QLabel("USD/INR --.----")
        self.vix_label = QLabel("India VIX --")

        pill_widgets = [self.clock_label, self.market_status_label, self.breadth_label, self.usdinr_label, self.vix_label]
        for pill in pill_widgets:
            pill.setFixedHeight(36)
            pill.setStyleSheet(self._pill_style("#1B2026", "#DDE8F5"))
            pills_layout.addWidget(pill)
        
        header.addWidget(pills_container)
        header.addStretch(1) 
        cl.addLayout(header)

        self.completer = QCompleter(sorted(self.display_map[self.exchange_combo.currentText()].keys()))
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_input.setCompleter(self.completer)

        # Index charts
        idx_frame = QFrame(); idx_layout = QHBoxLayout(idx_frame)
        idx_layout.setSpacing(10); idx_layout.setContentsMargins(0,0,0,0)
        self.indices_widgets = []
        for conf in self.indices_conf:
            if conf['symbol'] in ["INR=X", "^INDIAVIX"]: continue
            nm = conf["label"]
            c = QFrame(); c.setStyleSheet("background:rgba(25, 27, 30, 0.85); border-radius:10px;")
            c.setMinimumWidth(180)
            v = QVBoxLayout(c); v.setContentsMargins(10,8,10,8)

            header_h = QHBoxLayout()
            lbl = QLabel(nm); lbl.setStyleSheet("color:#cfeaff; font-size:11px; background:transparent;")
            lbl.setFont(QFont("Inter, Segoe UI", 9)); header_h.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignLeft)

            val_lbl = QLabel("—"); val_lbl.setStyleSheet("color:#9fb3c8; font-weight:600; background:transparent;")
            val_lbl.setFont(QFont("Inter, Segoe UI", 9)); header_h.addStretch(); header_h.addWidget(val_lbl, alignment=Qt.AlignmentFlag.AlignRight)
            v.addLayout(header_h)

            fig = Figure(figsize=(1.7,0.7), dpi=100); fig.patch.set_alpha(0.0)
            ax = fig.add_subplot(); ax.set_facecolor("none")
            for spine in ax.spines.values(): spine.set_visible(False)
            ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
            canvas = FigureCanvas(fig); canvas.setStyleSheet("background: transparent;")
            v.addWidget(canvas); idx_layout.addWidget(c)
            self.indices_widgets.append({
                "frame": c, "ax": ax, "canvas": canvas, "label": nm,
                "symbol": conf["symbol"], "value_label": val_lbl
            })
        cl.addWidget(idx_frame)

        # main chart card
        chart_card = QFrame()
        chart_card.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px;")
        chart_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        ch = QVBoxLayout(chart_card); ch.setContentsMargins(12,12,12,12); ch.setSpacing(10)

        self.chips_scroll = QScrollArea()
        self.chips_scroll.setWidgetResizable(True)
        self.chips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.chips_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chips_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chips_scroll.setStyleSheet(self._scrollbar_style())
        self.chips_container = QWidget()
        self.chips_hlayout = QHBoxLayout(self.chips_container)
        self.chips_hlayout.setContentsMargins(0,0,0,0)
        self.chips_hlayout.setSpacing(8)
        self.chips_container.setLayout(self.chips_hlayout)
        self.chips_scroll.setWidget(self.chips_container)
        ch.addWidget(self.chips_scroll)

        ranges = ["1d","5d","1m","6m","1y","2y","3y","5y"]
        rb = QHBoxLayout(); rb.setSpacing(8)
        self.range_buttons = []
        for r in ranges:
            btn = QPushButton(r)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumWidth(56)
            btn.setFixedHeight(34)
            btn.setStyleSheet(self._range_button_style())
            btn.clicked.connect(lambda _c, rr=r: self.update_chart_range(rr))
            self.range_buttons.append(btn)
            rb.addWidget(btn)
        ch.addLayout(rb)

        self.chart_fig = Figure(figsize=(8,3), dpi=100)
        self.chart_fig.patch.set_alpha(0.0)
        self.chart_ax = self.chart_fig.add_subplot()
        self._style_axes_dark(self.chart_ax)
        self.chart_canvas = FigureCanvas(self.chart_fig)
        self.chart_canvas.setStyleSheet("background: transparent;")
        ch.addWidget(self.chart_canvas)
        cl.addWidget(chart_card)

        # bottom row: table + watchlist
        bottom = QHBoxLayout(); bottom.setSpacing(12)
        left = QFrame(); left.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px;")
        ll = QVBoxLayout(left); ll.setContentsMargins(10,10,10,10)
        fl = QHBoxLayout()
        flab = QLabel("Filter:"); flab.setStyleSheet("color:#9fb3c8; font-size:11px; background:transparent;"); fl.addWidget(flab)
        self.table_combo = QComboBox(); self.table_combo.addItems(["BSE","NSE"])
        self.table_combo.currentTextChanged.connect(self.update_top_values)
        self.table_combo.setFixedWidth(110)
        self.table_combo.setStyleSheet(self._combo_style())
        fl.addWidget(self.table_combo); fl.addStretch()
        ll.addLayout(fl)

        self.table = QTableWidget(); self.table.setColumnCount(4)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(["Instrument","Volume","High","Low"])
        hh = self.table.horizontalHeader(); hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setStyleSheet(self._table_style())
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        ll.addWidget(self.table)
        bottom.addWidget(left, 3)

        right = QFrame(); right.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px;")
        rl = QVBoxLayout(right); rl.setContentsMargins(10,10,10,10)
        wl = QLabel("Watchlist"); wl.setFont(QFont("Inter, Segoe UI", 12, QFont.Weight.Bold))
        wl.setStyleSheet("background: transparent;")
        rl.addWidget(wl, alignment=Qt.AlignmentFlag.AlignTop)
        bottom.addWidget(right, 1)
        cl.addLayout(bottom)
    
    def _update_header_indicators(self):
        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)
        self.clock_label.setText(now_ist.strftime('%H:%M:%S IST'))

        is_weekday = now_ist.weekday() < 5
        is_market_time = now_ist.time() >= datetime.strptime("09:15", "%H:%M").time() and \
                         now_ist.time() <= datetime.strptime("15:30", "%H:%M").time()

        if is_weekday and is_market_time:
            self.market_status_label.setText("🟢 MARKET OPEN")
            self.market_status_label.setStyleSheet(self._pill_style("#14453d", "#20C997"))
        else:
            self.market_status_label.setText("🔴 MARKET CLOSED")
            self.market_status_label.setStyleSheet(self._pill_style("#4d222a", "#E35D6A"))

        self._sim_tick_counter += 1
        if self._sim_tick_counter % 5 == 0:
            exch = self.exchange_combo.currentText()
            if exch == "BSE":
                adv = random.randint(1500, 2500)
                dec = random.randint(1000, 2000)
            else:
                adv = random.randint(800, 1500)
                dec = random.randint(400, 1000)
            self.breadth_label.setText(f"A/D {adv}▲ / {dec}▼")

    # ---------------------------- Styles ----------------------------
    def _pill_button_style(self):
        """A modern style for the new Search button, matching other pills."""
        # --- FIX 1: Search button style updated to match pills ---
        return """
            QPushButton {
                background-color: #1B2026;
                color: #DDE8F5;
                border-radius: 18px;
                padding: 5px 15px;
                font-weight: bold;
                font-size: 10pt;
                border: none;
            }
            QPushButton:hover {
                background-color: #2b323a;
            }
            QPushButton:pressed {
                background-color: #1a202c;
            }
        """

    def _scrollbar_style(self):
        """A modern, minimalistic scrollbar style."""
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

    def _pill_style(self, bg_color, text_color):
        return f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 18px;
                padding: 5px 15px;
                font-weight: bold;
                font-size: 10pt;
            }}
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
            border-radius: 10px; padding: 8px 30px 8px 12px; font-weight: 600;
        }
        QComboBox:hover { border: 1px solid #33C4B9; }
        QComboBox::drop-down {
            subcontrol-origin: padding; subcontrol-position: top right;
            width: 28px; border-left-width: 1px; border-left-color: #2B323A;
            border-left-style: solid; border-top-right-radius: 9px; border-bottom-right-radius: 9px;
        }
        QComboBox::down-arrow { width: 14px; height: 14px; }
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
        QTableWidget::item { padding: 4px 8px; border-bottom: 1px solid #2B323A; }
        QTableWidget::item:selected { color: #F5FFFF; }
        QHeaderView::section {
            background-color: transparent; color: #9aa4b6;
            font-weight: 600; border: none; padding: 8px;
            border-bottom: 2px solid #33C4B9;
        }
        QTableCornerButton::section { background-color: transparent; border: none; }
        QScrollBar:vertical, QScrollBar:horizontal {
            border: none;
            background: transparent;
            width: 10px;
            height: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background: #4a5568;
            min-height: 20px;
            min-width: 20px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
            background: #718096;
        }
        """)

    def _chip_style(self):
        return ("QPushButton{background:#1B2026; color:#DCE8F6; border:1px solid #2B323A; border-radius:14px; padding:6px 14px;}"
                "QPushButton:hover{background:#232A31;}"
                "QPushButton:checked{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2AA6A6, stop:1 #33C4B9);"
                "color:#0A0D10; border:0px; font-weight:700;}")

    def _update_completer(self, exch):
        display_list = sorted(self.display_map.get(exch, {}).keys())
        if not hasattr(self, "completer") or self.completer is None:
            self.completer = QCompleter(display_list)
            self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.search_input.setCompleter(self.completer)
        else:
            self.completer.model().setStringList(display_list)

    def _resolve_to_file_ticker(self, typed: str, exch: str) -> Optional[str]:
        if not typed: return None
        typed_clean = clean_ticker(typed.strip().upper())
        m = self.display_map.get(exch, {})
        if typed_clean in m: return m[typed_clean]
        for disp, file_tick in m.items():
            if disp.startswith(typed_clean) or typed_clean in disp:
                return file_tick
        if typed.upper() in self.tickers.get(exch, []): return typed.upper()
        return None

    def on_search(self):
        exch = self.exchange_combo.currentText()
        typed = self.search_input.text()
        file_ticker = self._resolve_to_file_ticker(typed, exch)
        if not file_ticker:
            QMessageBox.warning(self, "Not found", f"No ticker found for '{typed}' in {exch}")
            return
        
        path = os.path.join("data","historical",exch,f"{file_ticker.replace('.','_')}.csv")
        if not os.path.exists(path):
            QMessageBox.warning(self, "File missing", f"Ticker file not found:\n{path}")
            return
        try:
            df = safe_read_csv(path)
            self.full_df = df
            self.plot_ohlc(self.full_df)
            self._add_chip(clean_ticker(file_ticker), exch, file_ticker, select=True)
        except Exception as e:
            QMessageBox.critical(self, "CSV error", f"{e}")

    def _add_chip(self, display: str, exch: str, file_ticker: str, select: bool = False):
        existing_chips = [chip_data[0] for chip_data in self.chips]
        if display in existing_chips:
            for d, e, f, btn_ref in self.chips:
                is_target = (d == display)
                btn_ref.setChecked(is_target)
            return

        btn = QPushButton(display)
        btn.setCheckable(True)
        btn.setStyleSheet(self._chip_style())
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        def on_click(checked, dt=display, ex=exch, ft=file_ticker, btn_ref=btn):
            for w in self.chips_container.findChildren(QPushButton):
                if w is not btn_ref:
                    w.setChecked(False)
            btn_ref.setChecked(True)
            self.exchange_combo.setCurrentText(ex)
            self.search_input.setText(dt)
            self.on_search()
        btn.clicked.connect(on_click)
        self.chips_hlayout.addWidget(btn)
        self.chips.append((display, exch, file_ticker, btn))
        if select:
            for _,_,_,w in self.chips:
                w.setChecked(False)
            btn.setChecked(True)
        self.chips_scroll.horizontalScrollBar().setValue(self.chips_scroll.horizontalScrollBar().maximum())

    def update_chart_data(self, ticker: Optional[str] = None, exchange: str = "BSE"):
        df = None
        if ticker:
            p = os.path.join("data","historical",exchange,f"{ticker.replace('.','_')}.csv")
            if os.path.exists(p):
                try: df = safe_read_csv(p)
                except Exception: df = None
        else:
            for exch in ("BSE","NSE"):
                if self.tickers.get(exch):
                    file_ticker = random.choice(self.tickers[exch])
                    try:
                        df = safe_read_csv(os.path.join("data","historical",exch,f"{file_ticker.replace('.','_')}.csv"))
                        self._add_chip(clean_ticker(file_ticker), exch, file_ticker, select=False)
                        break
                    except Exception: df = None
        if df is None or df.empty:
            dates = pd.date_range(end=pd.Timestamp.today(), periods=160, freq="B")
            prices = 100 + np.cumsum(np.random.randn(len(dates)))
            df = pd.DataFrame(index=dates)
            df["Open"] = prices + np.random.randn(len(dates))*0.5
            df["Close"] = prices + np.random.randn(len(dates))*0.5
            df["High"]  = np.maximum(df["Open"], df["Close"]) + np.abs(np.random.randn(len(dates)))
            df["Low"]   = np.minimum(df["Open"], df["Close"]) - np.abs(np.random.randn(len(dates)))
            df["Volume"]= (np.random.rand(len(dates))*10000).astype(int)
        self.full_df = df
        self.plot_ohlc(self.full_df)

    def plot_ohlc(self, df: pd.DataFrame):
        self.chart_ax.clear()
        self._style_axes_dark(self.chart_ax)
        if df is None or df.empty:
            self.chart_canvas.draw(); return
        df = df.sort_index()
        xs = df.index
        o, c, h, l = [pd.to_numeric(df[col], errors="coerce") for col in ["Open","Close","High","Low"]]
        up = c >= o; down = ~up
        self.chart_ax.vlines(xs, l, h, color="#7B8794", linewidth=0.7, alpha=0.7)
        self.chart_ax.bar(xs[up], (c-o)[up], bottom=o[up], width=0.8, color="#20C997", edgecolor="#20C997")
        self.chart_ax.bar(xs[down],(c-o)[down],bottom=o[down],width=0.8, color="#E35D6A", edgecolor="#E35D6A")
        self.chart_ax.set_ylabel("Price", color="#CCD6E4")
        self.chart_fig.autofmt_xdate()
        self.chart_canvas.draw()

    def update_chart_range(self, label: str):
        for b in self.range_buttons: b.setChecked(b.text() == label)
        if self.full_df is None or self.full_df.empty: return
        df = self.full_df
        
        periods_in_trading_days = {"1d":1, "5d":5, "1m":22, "6m":126, "1y":252, "2y":504, "3y":756, "5y":1260}
        
        if label in periods_in_trading_days:
            num_rows = periods_in_trading_days[label]
            new_df = df.iloc[-num_rows:]
        else: 
            new_df = df
            
        if new_df.empty:
            QMessageBox.information(self, "Range", "No data for selected range"); return
        self.plot_ohlc(new_df)

    def update_top_values(self, exchange: str):
        files = self.tickers.get(exchange, [])
        rows = min(len(files), 800)
        self.table.setRowCount(rows)
        for i, file_ticker in enumerate(files[:rows]):
            disp = clean_ticker(file_ticker)
            vol = high = low = ""
            path = os.path.join("data","historical",exchange,f"{file_ticker.replace('.','_')}.csv")
            
            if os.path.exists(path) and os.path.getsize(path) > 50:
                try:
                    with open(path, 'rb') as f:
                        header_line = f.readline().decode().strip()
                        header = [h.lower() for h in header_line.split(',')]
                        
                        f.seek(-1024, os.SEEK_END)
                        last_line = f.readlines()[-1].decode().strip()

                    if last_line:
                        last_values = last_line.split(',')
                        
                        vol_idx = header.index("volume") if "volume" in header else header.index("totaltradequantity")
                        high_idx = header.index("high")
                        low_idx = header.index("low")
                        
                        vol = last_values[vol_idx]
                        high = last_values[high_idx]
                        low = last_values[low_idx]
                except Exception:
                    pass
            
            for j, val in enumerate([disp, vol, high, low]):
                item = QTableWidgetItem(val)
                self.table.setItem(i, j, item)

    def _setup_index_canvases(self):
        for w in self.indices_widgets:
            ax = w["ax"]; ax.clear(); ax.set_facecolor("none")
            ax.plot([], []);
            for s in ax.spines.values(): s.set_visible(False)
            ax.tick_params(left=False,bottom=False,labelleft=False,labelbottom=False)
            w["canvas"].draw()

    def _schedule_index_fetch(self):
        if self._indices_fetch_in_progress: return
        self._indices_fetch_in_progress = True
        worker = IndexFetcher(self.indices_conf)
        worker.signals.finished.connect(self._on_indices_fetched)
        self.threadpool.start(worker)

    def _on_indices_fetched(self, results: dict):
        usdinr_series = results.get("INR=X")
        if usdinr_series is not None and not usdinr_series.empty:
            last_val = usdinr_series.iloc[-1]
            self.usdinr_label.setText(f"USD/INR {last_val:.4f}")

        vix_series = results.get("^INDIAVIX")
        if vix_series is not None and not vix_series.empty:
            last_val = vix_series.iloc[-1]
            self.vix_label.setText(f"India VIX {last_val:.2f}")

        for w in self.indices_widgets:
            sym = w["symbol"]
            series = results.get(sym)
            if series is None or len(series) == 0:
                ax = w["ax"]; ax.clear(); ax.set_facecolor("none")
                for s in ax.spines.values(): s.set_visible(False)
                ax.tick_params(left=False,bottom=False,labelleft=False,labelbottom=False)
                w["value_label"].setText("—"); w["value_label"].setStyleSheet("color:#9fb3c8; font-weight:600; background:transparent;")
                w["canvas"].draw(); continue
            
            color = "#9fb3c8"
            try:
                if len(series) >= 2:
                    last, prev = float(series.iloc[-1]), float(series.iloc[-2])
                    diff = last - prev; pct = (diff / prev * 100) if prev != 0 else 0.0
                    color = "#5FE1C2" if diff >= 0 else "#FF6B6B"
                    arrow = "▲" if diff >= 0 else "▼"
                    val_str = f"{last:,.0f}" if abs(last) >= 1000 else f"{last:,.2f}"
                    text = f"{val_str} {arrow} {pct:+.2f}%"
                    w["value_label"].setText(text); w["value_label"].setStyleSheet(f"color:{color}; font-weight:600; background:transparent;")
                else:
                    last = float(series.iloc[-1]); val_str = f"{last:,.2f}"
                    w["value_label"].setText(val_str); w["value_label"].setStyleSheet("color:#9fb3c8; font-weight:600; background:transparent;")
                    color = "#5FE1C2"
            except Exception:
                w["value_label"].setText("—"); w["value_label"].setStyleSheet("color:#9fb3c8; font-weight:600; background:transparent;")

            ax = w["ax"]; ax.clear(); ax.set_facecolor("none")
            for s in ax.spines.values(): s.set_visible(False)
            ax.tick_params(left=False,bottom=False,labelleft=False,labelbottom=False)
            ax.plot(series.index, series.values, color=color, linewidth=2)
            w["canvas"].draw()
        self._indices_fetch_in_progress = False

# ---------------------------- run ----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.setWindowTitle("Apex Analytics - Dashboard")
    win.resize(1360, 840)
    dashboard_page = DashboardWindow()
    win.setCentralWidget(dashboard_page)
    win.show()
    sys.exit(app.exec())

