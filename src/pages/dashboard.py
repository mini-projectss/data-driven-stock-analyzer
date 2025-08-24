#!/usr/bin/env python3
# Apex Analytics - Dashboard (dynamic chips, extra ranges, modern filter combo)
# Added: live yfinance updates for the 6 index mini-charts, refreshed every 10s
# Requirements: yfinance, pandas, numpy, PyQt6, matplotlib

import sys
import os
import random
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QCheckBox, QFrame, QMessageBox, QCompleter, QHeaderView, QSizePolicy,
    QScrollArea
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer
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

# ---------------------------- Main Window ----------------------------
class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apex Analytics")
        self.resize(1360, 840)

        # data maps
        self.tickers = {"NSE": [], "BSE": []}
        self.display_map = {"NSE": {}, "BSE": {}}   # display -> file ticker
        self._load_tickers()

        # index configuration (Yahoo / yfinance symbols)
        # You can change these symbols to other tickers if you prefer
        self.indices_conf = [
            {"label":"NIFTY 50", "symbol":"NIFTY50.NS"},
            {"label":"SENSEX",   "symbol":"^BSESN"},
            {"label":"NIFTY Bank", "symbol":"^NSEBANK"},
            {"label":"NIFTY Midcap 100", "symbol":"NIFTY_MIDCAP_100.NS"},
            {"label":"NIFTY Smallcap 100", "symbol":"SMALLCAP.NS"},
            {"label":"Gold", "symbol":"GOLDBEES.NS"}
        ]

        self._build_ui()
        self.apply_dark_theme()

        # unlimited dynamic chips list (store tuples (display, exch, file_ticker))
        self.chips = []
        self.full_df = None

        # Add one random chip at startup (if any tickers exist)
        initial_added = False
        for exch in ("BSE", "NSE"):
            if self.tickers.get(exch):
                file_t = random.choice(self.tickers[exch])
                display = clean_ticker(file_t)
                self._add_chip(display, exch, file_t, select=True)
                # also load it into chart
                try:
                    df = safe_read_csv(os.path.join("data", "historical", exch, f"{file_t}.csv"))
                    self.full_df = df
                    self.plot_ohlc(self.full_df)
                except Exception:
                    self.update_chart_data()  # fallback simulation
                initial_added = True
                break
        if not initial_added:
            self.update_chart_data()  # simulated series

        self.update_top_values(self.table_combo.currentText())

        # Setup the live index updater (every 10 seconds)
        self._setup_index_canvases()
        self.index_timer = QTimer(self)
        self.index_timer.timeout.connect(self._update_indices_live)
        self.index_timer.start(10_000)  # 10 seconds

    # ------------ Data discovery ------------
    def _load_tickers(self):
        for exch in ("NSE", "BSE"):
            folder = os.path.join("data", "historical", exch)
            if not os.path.isdir(folder):
                continue
            for f in sorted(os.listdir(folder)):
                if not f.lower().endswith(".csv"):
                    continue
                file_ticker = os.path.splitext(f)[0]          # e.g. AFFLE_BO
                display = clean_ticker(file_ticker)           # e.g. AFFLE
                self.tickers[exch].append(file_ticker)
                # NOTE: if collisions happen (same display name twice), last wins.
                self.display_map[exch][display] = file_ticker

    # ------------ UI ------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central); main.setContentsMargins(0,0,0,0); main.setSpacing(0)

        # ---- Sidebar ----
        sidebar = QFrame(); sidebar.setFixedWidth(230)
        sbl = QVBoxLayout(sidebar); sbl.setContentsMargins(16,16,16,16); sbl.setSpacing(10)

        title = QLabel("Apex Analytics")
        title.setFont(QFont("Inter, Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color:#EAF2FF")
        sbl.addWidget(title)

        sbl.addSpacing(4)
        menu_lbl = QLabel("MENU"); menu_lbl.setStyleSheet("color:#9aa4b6; font-size:10px;")
        sbl.addWidget(menu_lbl)

        self.menu_buttons = []
        for i, text in enumerate(["Dashboard","Portfolio","Prediction","News_Sentiment","Political Trading","Google Trends"]):
            b = QPushButton(text.replace("_"," & "))
            b.setCheckable(True); b.setFixedHeight(42); b.setFont(QFont("Inter, Segoe UI", 10))
            b.clicked.connect(lambda _c, idx=i: self._select_menu(idx))
            b.setStyleSheet(self._sidebar_button_style(False))
            sbl.addWidget(b)
            self.menu_buttons.append(b)
        self._select_menu(0)

        sbl.addStretch()
        acc = QLabel("ACCOUNT"); acc.setStyleSheet("color:#9aa4b6; font-size:10px;")
        sbl.addWidget(acc)
        for t in ("Profile","Settings"):
            b = QPushButton(t); b.setFixedHeight(36); b.setFont(QFont("Inter, Segoe UI", 10))
            b.setStyleSheet(self._sidebar_button_style(False)); sbl.addWidget(b)
        sbl.addStretch()

        self.theme_toggle = QCheckBox("Dark Mode"); self.theme_toggle.setChecked(True)
        self.theme_toggle.stateChanged.connect(self._on_theme_toggle); sbl.addWidget(self.theme_toggle)
        main.addWidget(sidebar)

        # ---- Content ----
        content = QWidget(); main.addWidget(content, 1)
        cl = QVBoxLayout(content); cl.setContentsMargins(16,16,16,16); cl.setSpacing(12)

        # header line
        header = QHBoxLayout()
        hdr = QLabel("Dashboard"); hdr.setFont(QFont("Inter, Segoe UI", 18, QFont.Weight.Bold))
        header.addWidget(hdr, alignment=Qt.AlignmentFlag.AlignLeft)

        # Search input
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText("Search ticker/company")
        self.search_input.setFixedHeight(36); self.search_input.returnPressed.connect(self.on_search)
        header.addWidget(self.search_input)

        # Exchange selector (styled like filter)
        self.exchange_combo = QComboBox(); self.exchange_combo.addItems(["NSE","BSE"])
        self.exchange_combo.setFixedWidth(110); self.exchange_combo.currentTextChanged.connect(self._update_completer)
        self.exchange_combo.setStyleSheet(self._combo_style())
        header.addWidget(self.exchange_combo)
        cl.addLayout(header)

        # completer (show *display* names)
        self.completer = QCompleter(sorted(self.display_map[self.exchange_combo.currentText()].keys()))
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.search_input.setCompleter(self.completer)

        # indices mini row (now live-updated)
        idx_frame = QFrame(); idx_layout = QHBoxLayout(idx_frame)
        idx_layout.setSpacing(10); idx_layout.setContentsMargins(0,0,0,0)
        self.indices_widgets = []  # list of dicts {frame, ax, canvas, label, symbol}
        for conf in self.indices_conf:
            nm = conf["label"]
            c = QFrame(); c.setStyleSheet("background:#191B1E; border-radius:10px;")
            v = QVBoxLayout(c); v.setContentsMargins(10,8,10,8)
            lbl = QLabel(nm); lbl.setStyleSheet("color:#cfeaff; font-size:11px;")
            v.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignLeft)

            fig = Figure(figsize=(1.7,0.7), dpi=100)
            fig.patch.set_facecolor("#191B1E")
            ax = fig.add_subplot()
            ax.set_facecolor("#191B1E")
            # initial mini-plot (empty)
            line, = ax.plot([], [], linewidth=2)
            # hide axes ticks & spines
            for spine in ax.spines.values(): spine.set_visible(False)
            ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
            canvas = FigureCanvas(fig)
            v.addWidget(canvas)
            idx_layout.addWidget(c)
            self.indices_widgets.append({"frame": c, "ax": ax, "canvas": canvas, "label": nm, "symbol": conf["symbol"], "line": line})
        cl.addWidget(idx_frame)

        # main chart card
        chart_card = QFrame()
        chart_card.setStyleSheet("background:#0F1215; border-radius:12px;")
        chart_card.setMinimumHeight(380)
        ch = QVBoxLayout(chart_card); ch.setContentsMargins(12,12,12,12); ch.setSpacing(10)

        # ---------- Dynamic chips area ----------
        chips_area = QFrame()
        chips_area.setStyleSheet("background:transparent;")
        chips_layout = QHBoxLayout(chips_area)
        chips_layout.setContentsMargins(0,0,0,0)
        chips_layout.setSpacing(8)

        # Create a scroll area to host unlimited chips horizontally
        self.chips_scroll = QScrollArea()
        self.chips_scroll.setWidgetResizable(True)
        self.chips_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.chips_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chips_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.chips_container = QWidget()
        self.chips_hlayout = QHBoxLayout(self.chips_container)
        self.chips_hlayout.setContentsMargins(0,0,0,0)
        self.chips_hlayout.setSpacing(8)
        self.chips_container.setLayout(self.chips_hlayout)

        self.chips_scroll.setWidget(self.chips_container)
        ch.addWidget(self.chips_scroll)

        # ---------- Range buttons (evenly expanded) ----------
        ranges = ["1d","5d","1m","6m","1y","2y","3y","5y"]
        rb = QHBoxLayout(); rb.setSpacing(8)
        self.range_buttons = []
        for r in ranges:
            btn = QPushButton(r)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # make them expand equally
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setMinimumWidth(56)
            btn.setFixedHeight(34)
            btn.setStyleSheet(self._range_button_style())
            btn.clicked.connect(lambda _c, rr=r: self.update_chart_range(rr))
            self.range_buttons.append(btn)
            rb.addWidget(btn)
        ch.addLayout(rb)

        # matplotlib chart
        self.chart_fig = Figure(figsize=(8,3), dpi=100)
        self.chart_fig.patch.set_facecolor("#0F1215")
        self.chart_ax = self.chart_fig.add_subplot()
        self._style_axes_dark(self.chart_ax)
        self.chart_canvas = FigureCanvas(self.chart_fig)
        ch.addWidget(self.chart_canvas)
        cl.addWidget(chart_card)

        # bottom row: table + watchlist blank
        bottom = QHBoxLayout(); bottom.setSpacing(12)

        left = QFrame(); left.setStyleSheet("background:#0F1215; border-radius:12px;")
        ll = QVBoxLayout(left); ll.setContentsMargins(10,10,10,10)
        fl = QHBoxLayout()
        flab = QLabel("Filter:"); flab.setStyleSheet("color:#9fb3c8; font-size:11px;"); fl.addWidget(flab)
        self.table_combo = QComboBox(); self.table_combo.addItems(["BSE","NSE"])
        self.table_combo.currentTextChanged.connect(self.update_top_values)
        self.table_combo.setFixedWidth(110)
        self.table_combo.setStyleSheet(self._combo_style())
        fl.addWidget(self.table_combo); fl.addStretch()
        ll.addLayout(fl)

        self.table = QTableWidget(); self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Instrument","Volume","High","Low"])
        hh = self.table.horizontalHeader(); hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setStyleSheet(self._table_style())
        ll.addWidget(self.table)
        bottom.addWidget(left, 3)

        right = QFrame(); right.setStyleSheet("background:#0F1215; border-radius:12px;")
        rl = QVBoxLayout(right); rl.setContentsMargins(10,10,10,10)
        wl = QLabel("Watchlist"); wl.setFont(QFont("Inter, Segoe UI", 12, QFont.Weight.Bold))
        rl.addWidget(wl, alignment=Qt.AlignmentFlag.AlignTop)
        bottom.addWidget(right, 1)

        cl.addLayout(bottom)

        # store references
        self.chips_layout = self.chips_hlayout
        self.content_layout = cl

    # ---------------------------- Styles ----------------------------
    def _style_axes_dark(self, ax):
        ax.set_facecolor("#0F1215")
        ax.tick_params(axis='x', colors="#CCD6E4")
        ax.tick_params(axis='y', colors="#CCD6E4")
        for s in ax.spines.values():
            s.set_color("#2C2F34")
        ax.grid(axis='y', linestyle=':', color="#2A2E33", alpha=0.35)

    def _sidebar_button_style(self, selected=False):
        if selected:
            return ("QPushButton{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1F7A7A, stop:1 #2AA6A6);"
                    "color:#F5FFFF; border-radius:10px; font-weight:600;}"
                    "QPushButton:hover{background:#2AA6A6;}")
        else:
            return ("QPushButton{background:transparent; color:#D6DBE0; border-radius:10px; text-align:left; padding-left:12px;}"
                    "QPushButton:hover{background:#1C1E22;}")

    def _range_button_style(self):
        return ("QPushButton{background:#1B2026; color:#DDE8F5; border:1px solid #2B323A; border-radius:10px; padding:6px 8px;}"
                "QPushButton:hover{background:#232A31;}"
                "QPushButton:checked{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00A7A7, stop:1 #00C2B8);"
                "color:#0B1116; font-weight:700; border:0px;}")

    def _combo_style(self):
        return ("""
        QComboBox{background:#15181B; color:#E8F2FF; border:1px solid #2B323A; border-radius:8px; padding:6px 28px 6px 10px;}
        QComboBox:hover{border:1px solid #3B4652;}
        QComboBox::drop-down{width:22px; border:0px;}
        QComboBox QAbstractItemView{background:#0F1215; color:#E8F2FF; selection-background-color:#1F7A7A;}
        """)

    def _table_style(self):
        return ("""
        QTableWidget{background:#0F1215; color:#E6EEF6; border:0px; gridline-color:#2B323A; selection-background-color:#22313B;}
        QHeaderView::section{background:#13171B; color:#AFC3D8; border:0px; padding:6px; border-bottom:1px solid #2B323A;}
        QTableCornerButton::section{background:#13171B; border:0px;}
        """)

    def _chip_style(self):
        return ("QPushButton{background:#1B2026; color:#DCE8F6; border:1px solid #2B323A; border-radius:14px; padding:6px 14px;}"
                "QPushButton:hover{background:#232A31;}"
                "QPushButton:checked{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2AA6A6, stop:1 #33C4B9);"
                "color:#0A0D10; border:0px; font-weight:700;}")

    def _select_menu(self, index):
        for i, b in enumerate(self.menu_buttons):
            b.setChecked(i == index)
            b.setStyleSheet(self._sidebar_button_style(i == index))

    def _on_theme_toggle(self, st):
        # currently only have dark theme; keep hook for future light theme
        self.apply_dark_theme()

    def apply_dark_theme(self):
        self.setStyleSheet("""
        QMainWindow{background:#101214; color:#E6EEF6;}
        QLabel{color:#DDE8F5;}
        QLineEdit{background:#15181B; color:#E8F2FF; border:1px solid #2B323A; border-radius:8px; padding:6px;}
        QLineEdit:focus{border:1px solid #3B4652;}
        QComboBox{color:#E8F2FF;}
        QPushButton{color:#E6EEF6;}
        """)

    # ---------------------------- Completer/Search ----------------------------
    def _update_completer(self, exch):
        display_list = sorted(self.display_map.get(exch, {}).keys())
        if not hasattr(self, "completer") or self.completer is None:
            self.completer = QCompleter(display_list)
            self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.search_input.setCompleter(self.completer)
        else:
            self.completer.model().setStringList(display_list)

    def _resolve_to_file_ticker(self, typed: str, exch: str) -> Optional[str]:
        """Return the file ticker for a typed input (accepts clean names)."""
        if not typed:
            return None
        typed_clean = clean_ticker(typed.strip().upper())
        m = self.display_map.get(exch, {})
        if typed_clean in m:
            return m[typed_clean]
        # fallback partial match
        for disp, file_tick in m.items():
            if disp.startswith(typed_clean) or typed_clean in disp:
                return file_tick
        # last-chance: typed exact file name
        if typed.upper() in self.tickers.get(exch, []):
            return typed.upper()
        return None

    def on_search(self):
        exch = self.exchange_combo.currentText()
        typed = self.search_input.text()
        file_ticker = self._resolve_to_file_ticker(typed, exch)
        if not file_ticker:
            QMessageBox.warning(self, "Not found", f"No ticker found for '{typed}' in {exch}")
            return
        path = os.path.join("data","historical",exch,f"{file_ticker}.csv")
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

    # ---------------------------- Dynamic chips ----------------------------
    def _add_chip(self, display: str, exch: str, file_ticker: str, select: bool = False):
        """Create a new rounded chip button and append to chips bar (unlimited)."""
        btn = QPushButton(display)
        btn.setCheckable(True)
        btn.setStyleSheet(self._chip_style())
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # when clicked, load ticker
        def on_click(checked, dt=display, ex=exch, ft=file_ticker, btn_ref=btn):
            # uncheck other chips
            for w in self.chips_container.findChildren(QPushButton):
                if w is not btn_ref:
                    w.setChecked(False)
            btn_ref.setChecked(True)
            # load the ticker
            self.exchange_combo.setCurrentText(ex)
            self.search_input.setText(dt)
            self.on_search()
        btn.clicked.connect(on_click)

        # append to layout
        self.chips_hlayout.addWidget(btn)
        self.chips.append((display, exch, file_ticker, btn))
        # optionally select it
        if select:
            # uncheck others
            for _,_,_,w in self.chips:
                w.setChecked(False)
            btn.setChecked(True)

        # ensure the new chip is visible in scroll area (scroll to right)
        self.chips_scroll.horizontalScrollBar().setValue(self.chips_scroll.horizontalScrollBar().maximum())

    def _on_recent_click(self, idx):
        # legacy: we don't rely on fixed indexed buttons anymore; kept for compatibility
        if idx < len(self.chips):
            display, exch, file_ticker, btn = self.chips[idx]
            btn.click()

    # ---------------------------- Chart ----------------------------
    def update_chart_data(self, ticker: Optional[str] = None, exchange: str = "BSE"):
        df = None
        if ticker:
            p = os.path.join("data","historical",exchange,f"{ticker}.csv")
            if os.path.exists(p):
                try: df = safe_read_csv(p)
                except Exception: df = None
        else:
            for exch in ("BSE","NSE"):
                if self.tickers.get(exch):
                    file_ticker = random.choice(self.tickers[exch])
                    try:
                        df = safe_read_csv(os.path.join("data","historical",exch,f"{file_ticker}.csv"))
                        self._add_chip(clean_ticker(file_ticker), exch, file_ticker, select=False)
                        break
                    except Exception:
                        df = None
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
        o = pd.to_numeric(df["Open"], errors="coerce")
        c = pd.to_numeric(df["Close"], errors="coerce")
        h = pd.to_numeric(df["High"],  errors="coerce")
        l = pd.to_numeric(df["Low"],   errors="coerce")

        up = c >= o
        down = ~up

        # wicks
        self.chart_ax.vlines(xs, l, h, color="#7B8794", linewidth=0.7, alpha=0.7)
        # bodies
        self.chart_ax.bar(xs[up],   (c-o)[up],   bottom=o[up],   width=0.8, color="#20C997", edgecolor="#20C997")
        self.chart_ax.bar(xs[down], (c-o)[down], bottom=o[down], width=0.8, color="#E35D6A", edgecolor="#E35D6A")

        self.chart_ax.set_ylabel("Price", color="#CCD6E4")
        self.chart_fig.autofmt_xdate()
        self.chart_canvas.draw()

    # ---------------------------- Range ----------------------------
    def update_chart_range(self, label: str):
        for b in self.range_buttons:
            b.setChecked(b.text() == label)
        if self.full_df is None or self.full_df.empty:
            return

        df = self.full_df
        now = pd.Timestamp.now()

        if label == "1d":
            new_df = df.iloc[-1:]
        elif label == "5d":
            new_df = df.loc[df.index >= now - pd.Timedelta(days=7)]
        elif label == "1m":
            new_df = df.loc[df.index >= now - pd.Timedelta(days=31)]
        elif label == "6m":
            new_df = df.loc[df.index >= now - pd.Timedelta(days=186)]
        elif label == "1y":
            new_df = df.loc[df.index >= now - pd.Timedelta(days=365)]
        elif label == "2y":
            new_df = df.loc[df.index >= now - pd.Timedelta(days=730)]
        elif label == "3y":
            new_df = df.loc[df.index >= now - pd.Timedelta(days=1095)]
        elif label == "5y":
            new_df = df.loc[df.index >= now - pd.Timedelta(days=1825)]
        else:
            new_df = df

        if new_df.empty:
            QMessageBox.information(self, "Range", "No data for selected range"); return
        self.plot_ohlc(new_df)

    # ---------------------------- Top values table ----------------------------
    def update_top_values(self, exchange: str):
        files = self.tickers.get(exchange, [])
        rows = min(len(files), 800)
        self.table.setRowCount(rows)

        for i, file_ticker in enumerate(files[:rows]):
            disp = clean_ticker(file_ticker)
            vol = high = low = ""
            path = os.path.join("data","historical",exchange,f"{file_ticker}.csv")
            if os.path.exists(path):
                try:
                    df = pd.read_csv(path, low_memory=False)
                    if not df.empty:
                        last = df.iloc[-1]
                        vol = str(last.get("Volume", last.get("TOTALTRADEQUANTITY","")))
                        high = str(last.get("High", last.get("HIGH","")))
                        low  = str(last.get("Low",  last.get("LOW","")))
                except Exception:
                    pass
            self.table.setItem(i, 0, QTableWidgetItem(disp))
            self.table.setItem(i, 1, QTableWidgetItem(vol))
            self.table.setItem(i, 2, QTableWidgetItem(high))
            self.table.setItem(i, 3, QTableWidgetItem(low))

    # ---------------------------- Index canvases & live update ----------------------------
    def _setup_index_canvases(self):
        """
        Initialize axes/line objects for the mini-index charts (created earlier in _build_ui).
        We keep a reference to the widget list in self.indices_widgets (populated in _build_ui)
        """
        # Ensure each has a visible initial small line
        for w in self.indices_widgets:
            ax = w["ax"]
            ax.clear()
            ax.set_facecolor("#191B1E")
            # break grid/labels for mini look
            ax.plot([], [])
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
            w["canvas"].draw()

    def _fetch_index_series(self, symbol: str, period="7d", interval="60m"):
        """
        Try to fetch series via yfinance. Return pandas Series of closes indexed by timestamp.
        period/interval chosen small for mini charts. If yfinance not available or fetch fails
        return simulated small series.
        """
        if yf is None:
            # simulated fallback
            x = np.arange(24)
            y = np.cumsum(np.random.randn(len(x))) + 100
            idx = pd.date_range(end=pd.Timestamp.now(), periods=len(x), freq='H')
            return pd.Series(y, index=idx)

        try:
            # prefer short intraday history for mini charts
            ticker = yf.Ticker(symbol)
            # try to fetch 1d 1m if supported otherwise fall back to intraday/period combos
            # Use history; some symbols (indices) accept period like '7d' with interval '60m'
            hist = ticker.history(period=period, interval=interval, actions=False)
            if hist is None or hist.empty:
                # fallback to 7 days daily
                hist = ticker.history(period="30d", interval="1d", actions=False)
            if hist is None or hist.empty:
                raise RuntimeError("no history")
            closes = hist["Close"].dropna()
            # reduce to up to 48 points for mini-plot
            if len(closes) > 48:
                closes = closes.iloc[-48:]
            return closes
        except Exception:
            # simulated fallback
            x = np.arange(24)
            y = np.cumsum(np.random.randn(len(x))) + 100
            idx = pd.date_range(end=pd.Timestamp.now(), periods=len(x), freq='H')
            return pd.Series(y, index=idx)

    def _update_indices_live(self):
        """
        Called every 10 seconds to update each mini chart.
        Color green if last close >= prev close, else red.
        """
        for w in self.indices_widgets:
            sym = w["symbol"]
            label = w["label"]
            # for intraday look nicer: try '7d' with '60m', if fails fallback inside fetch
            series = self._fetch_index_series(sym, period="7d", interval="60m")
            if series is None or series.empty:
                # nothing to plot
                ax = w["ax"]
                ax.clear()
                w["canvas"].draw()
                continue

            ax = w["ax"]
            ax.clear()
            # style
            ax.set_facecolor("#191B1E")
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

            # determine color based on last movement
            if len(series) >= 2:
                last = series.iloc[-1]
                prev = series.iloc[-2]
                color = "#5FE1C2" if last >= prev else "#FF6B6B"
            else:
                color = "#5FE1C2"

            # plot
            ax.plot(series.index, series.values, color=color, linewidth=2)
            # tiny area shading can be added if desired:
            # ax.fill_between(series.index, series.values, alpha=0.06, color=color)

            w["canvas"].draw()

# ---------------------------- run ----------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DashboardWindow()
    win.show()
    sys.exit(app.exec())
