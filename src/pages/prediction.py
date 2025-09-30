#!/usr/bin/env python3
# Apex Analytics - Prediction Page (with full backend logic)
# Updated: integrated screener & analyze logic + CSV save + sorting + completer
# NOTE: Requires prophet, lightgbm, sklearn, yfinance for full functionality.

import sys
import os
import traceback
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QFrame, QHeaderView, QSizePolicy, QAbstractItemView, QTabWidget,
    QSpacerItem, QCheckBox, QMessageBox, QCompleter
)
from PyQt6.QtGui import QFont, QPainter, QColor, QLinearGradient, QBrush
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal

import matplotlib
matplotlib.use('qtagg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# --- ML/Data Imports ---
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except Exception:
    PROPHET_AVAILABLE = False
    Prophet = None

try:
    import lightgbm as lgb
    from sklearn.multioutput import MultiOutputRegressor
    LGBM_AVAILABLE = True
except Exception:
    LGBM_AVAILABLE = False
    lgb, MultiOutputRegressor = None, None

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except Exception:
    YFINANCE_AVAILABLE = False
    yf = None

# --- Constants (relative paths)
PREDICTIONS_PATH = os.path.join('data', 'predictions')
PROCESSED_PATH = os.path.join('data', 'processed')
HISTORICAL_PATH = os.path.join('data', 'historical')
TEMP_PATH = os.path.join('data', 'temp')

# ensure directories exist
os.makedirs(PREDICTIONS_PATH, exist_ok=True)
os.makedirs(TEMP_PATH, exist_ok=True)

# ---------------------------- Custom Gradient Background Widget ----------------------------
class GradientWidget(QWidget):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#0f0c29"))
        gradient.setColorAt(0.5, QColor("#302b63"))
        gradient.setColorAt(1.0, QColor("#24243e"))
        painter.fillRect(self.rect(), QBrush(gradient))
        super().paintEvent(event)

# ---------------------------- Worker for On-Demand Prediction ----------------------------
class AnalysisWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, ticker, exchange, time_range):
        super().__init__()
        self.ticker = ticker.upper()
        self.exchange = exchange  # "BSE" or "NSE"
        self.time_range = time_range
        self.is_running = True

    def run(self):
        try:
            # Make sure required libs available
            if not all([PROPHET_AVAILABLE, LGBM_AVAILABLE, YFINANCE_AVAILABLE]):
                raise ImportError("Required libraries missing. Prophet, LightGBM and yfinance must be installed to run on-demand analysis.")

            # Determine prediction periods and freq token
            if self.time_range.startswith("Days"):
                periods = 7
                freq = 'D'
                hist_periods = 7
            elif self.time_range.startswith("Hours"):
                periods = 24
                freq = 'h'
                hist_periods = 24
            else:  # Minutes
                periods = 60
                freq = 'min'
                hist_periods = 60

            # 1. Load historical/preprocessed and update with live yfinance
            combined_df = self._load_and_update_data(self.ticker, self.exchange, freq)

            # 2. Prepare and run Prophet (on Close series)
            prophet_preds = self._predict_prophet(combined_df.copy(), periods, freq)

            # 3. Prepare and run LightGBM (multi-output for OHLC)
            lgbm_preds = self._predict_lightgbm(combined_df.copy(), periods, freq)

            # 4. Return both historical slice + predictions
            historical_part = combined_df.tail(hist_periods)
            result = {
                "historical": historical_part,
                "prophet": prophet_preds,
                "lgbm": lgbm_preds
            }
            self.finished.emit(result)

        except Exception as e:
            tb = traceback.format_exc()
            self.error.emit(f"Analysis failed: {e}\n\n{tb}")

    def _load_and_update_data(self, ticker, exchange, freq):
        """Load processed/lightgbm data if present, fallback to historical raw; then append live yfinance if available."""
        suffix = 'BO' if exchange == 'BSE' else 'NS'
        # filenames used in your repo: data/processed/lightgbm/3MINDIA_BO.csv
        lgbm_processed_file = os.path.join(PROCESSED_PATH, 'lightgbm', f"{ticker}_{suffix}.csv")
        prophet_close_file = os.path.join(PROCESSED_PATH, 'prophet', f"{ticker}_{suffix}_close.csv")

        df = None

        # Try processed LightGBM file (preferred for features already prepared)
        if os.path.exists(lgbm_processed_file):
            try:
                df = pd.read_csv(lgbm_processed_file, parse_dates=['Date'], index_col='Date')
                # try to ensure required columns: Open, High, Low, Close
                req_cols = ['Open', 'High', 'Low', 'Close']
                if not all(c in df.columns for c in req_cols):
                    # try simple fallback: rename columns if present
                    pass
                # keep only OHLC if extra cols present
                df = df[[c for c in req_cols if c in df.columns]].copy()
            except Exception:
                df = None

        # Fallback to historical raw data
        if df is None:
            hist_file = os.path.join(HISTORICAL_PATH, exchange, f"{ticker}.csv")
            if os.path.exists(hist_file):
                df = pd.read_csv(hist_file, parse_dates=['Date'], index_col='Date')
                # expect 'Open','High','Low','Close' columns
            else:
                raise FileNotFoundError(f"Historical or processed data not found for {ticker} ({hist_file} / {lgbm_processed_file})")

        # fetch live data via yfinance and append rows not present
        # choose interval mapping for yfinance
        interval = '1d'
        if freq == 'h':
            interval = '60m'
        elif freq == 'min':
            interval = '1m'

        yf_symbol = f"{ticker}.{suffix}"
        live_df = pd.DataFrame()
        try:
            # fetch last 5 days for intraday intervals (enough to cover recent hours/min)
            period = "10d" if interval == '1m' else "30d" if interval == '60m' else "60d"
            raw_live = yf.download(yf_symbol, period=period, interval=interval, progress=False, auto_adjust=True)
            if raw_live is not None and not raw_live.empty:
                # standardize columns to Open/High/Low/Close
                raw_live = raw_live[['Open','High','Low','Close']]
                raw_live.index = pd.to_datetime(raw_live.index)
                live_df = raw_live
        except Exception:
            # swallow; proceed with historical only (user will be informed in UI)
            live_df = pd.DataFrame()

        if not live_df.empty:
            # only append rows that are not in df
            new_live = live_df[~live_df.index.isin(df.index)]
            if not new_live.empty:
                combined = pd.concat([df, new_live]).sort_index()
            else:
                combined = df.copy()
        else:
            combined = df.copy()

        # Ensure numeric columns
        for c in ['Open','High','Low','Close']:
            if c in combined.columns:
                combined[c] = pd.to_numeric(combined[c], errors='coerce')

        return combined

    def _predict_prophet(self, df, periods, freq):
        """Fit Prophet on Close series and return future DataFrame with yhat."""
        df_prop = df.reset_index()[['Date','Close']].rename(columns={'Date':'ds','Close':'y'})
        # if float/integer time index, ensure sorted ascending
        df_prop = df_prop.sort_values('ds').dropna()
        if df_prop.shape[0] < 10:
            raise ValueError("Not enough data points for Prophet modeling.")

        model = Prophet()
        model.fit(df_prop)
        # map freq to pandas offset string used by prophet
        freq_map = {'D':'D', 'h':'H', 'min':'min'}
        future = model.make_future_dataframe(periods=periods, freq=freq_map.get(freq,'D'))
        forecast = model.predict(future)
        # keep only tail(periods)
        preds = forecast[['ds','yhat']].tail(periods).set_index('ds')
        preds.index.name = None
        preds.columns = ['yhat']
        return preds

    def _predict_lightgbm(self, df, periods, freq):
        """Train simple LGBM multi-output on recent window and predict next 'periods' steps."""
        # feature engineering on Close only
        df_l = df.copy()
        df_l['MA_7_Close'] = df_l['Close'].rolling(window=min(7, max(2, len(df_l)))).mean()
        df_l['MA_30_Close'] = df_l['Close'].rolling(window=min(30, max(3, len(df_l)))).mean()
        df_l['Lag_1_Close'] = df_l['Close'].shift(1)
        df_l = df_l.dropna()
        features = [c for c in ['MA_7_Close','MA_30_Close','Lag_1_Close'] if c in df_l.columns]
        targets = ['Open','High','Low','Close']
        if len(df_l) < 10 or len(features) < 1:
            raise ValueError("Not enough processed data to train LightGBM model.")

        X = df_l[features]
        y = df_l[targets]

        lgbm = lgb.LGBMRegressor(verbosity=-1)
        model = MultiOutputRegressor(lgbm)
        model.fit(X, y)

        predictions = []
        last_known = df.copy()
        # determine step delta depending on freq
        delta_map = {'D': pd.Timedelta(days=1), 'h': pd.Timedelta(hours=1), 'min': pd.Timedelta(minutes=1)}
        delta = delta_map.get(freq, pd.Timedelta(days=1))

        for _ in range(periods):
            # build features from last_known
            window_for_7 = last_known['Close'].iloc[-7:] if len(last_known)>=7 else last_known['Close']
            window_for_30 = last_known['Close'].iloc[-30:] if len(last_known)>=30 else last_known['Close']
            feat = pd.DataFrame({
                'MA_7_Close': [window_for_7.mean()],
                'MA_30_Close': [window_for_30.mean()],
                'Lag_1_Close': [last_known['Close'].iloc[-1]]
            })
            feat = feat[features]  # keep same features order
            pred = model.predict(feat)[0]  # Open,High,Low,Close
            predictions.append(pred)
            next_idx = last_known.index[-1] + delta
            new_row = pd.DataFrame([pred], index=[next_idx], columns=targets)
            last_known = pd.concat([last_known, new_row])

        # create DataFrame for predictions with correct index and column names
        # ensure index dtype consistent with pandas date_range style
        last_date = df.index[-1]
        future_idx = pd.date_range(start=last_date + delta, periods=periods, freq=delta)
        pred_df = pd.DataFrame(predictions, index=future_idx, columns=targets)
        return pred_df

# ---------------------------- Main Prediction Page Widget ----------------------------
class PredictionPage(GradientWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_predictions_df = None
        self.current_screener_df = None
        self.watchlist = set()
        self.analysis_worker = None
        self.current_analysis_result = None
        self.last_sort_state = {}  # table -> (col, order)

        self.setStyleSheet(self._get_page_stylesheet())

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        title = QLabel("Prediction & Analysis Platform")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #EAF2FF; background:transparent;")
        main_layout.addWidget(title)

        self.tab_widget = QTabWidget()

        self.analyze_tab = self._create_analyze_tab()
        self.screener_tab = self._create_screener_tab()
        self.watchlist_tab = self._create_watchlist_tab()

        self.tab_widget.addTab(self.analyze_tab, "Analyze")
        self.tab_widget.addTab(self.screener_tab, "Market Screener")
        self.tab_widget.addTab(self.watchlist_tab, "Watchlist")

        main_layout.addWidget(self.tab_widget)

        # Load saved predictions (if any) and populate screener filters
        self._load_all_predictions()
        self._populate_screener_filters()
        self._apply_screener_filters()

        # Setup completer for analyze search using tickers files (uploaded)
        self._setup_ticker_completer()

    # ----------------- Predictions loading (for Market Screener) -----------------
    def _load_all_predictions(self):
        all_dfs = []
        if not os.path.exists(PREDICTIONS_PATH):
            self.all_predictions_df = pd.DataFrame()
            return

        for filename in os.listdir(PREDICTIONS_PATH):
            if filename.endswith("_prediction.csv"):
                ticker_part = filename.replace("_prediction.csv", "")
                exchange = "BSE" if ticker_part.endswith("_BO") else "NSE"
                stock_name = ticker_part.replace("_BO", "").replace("_NS", "")
                try:
                    df = pd.read_csv(os.path.join(PREDICTIONS_PATH, filename))
                    # Ensure there is Date column for filtering
                    if 'Date' not in df.columns:
                        continue
                    df['Stock'] = stock_name
                    df['Exchange'] = exchange
                    # keep Date string copy for filter dropdown
                    df['Date_Str'] = df['Date'].astype(str)
                    all_dfs.append(df)
                except Exception:
                    continue

        if all_dfs:
            self.all_predictions_df = pd.concat(all_dfs, ignore_index=True)
            # ensure Date as datetime for any other use
            try:
                self.all_predictions_df['Date'] = pd.to_datetime(self.all_predictions_df['Date'])
            except Exception:
                pass
        else:
            self.all_predictions_df = pd.DataFrame()

    def _populate_screener_filters(self):
        if self.all_predictions_df is None or self.all_predictions_df.empty:
            return

        dates = sorted(self.all_predictions_df['Date_Str'].unique())
        self.screener_date_filter.clear()
        self.screener_date_filter.addItems(dates)

        self.watchlist_date_filter.clear()
        self.watchlist_date_filter.addItems(dates)

    def _apply_screener_filters(self):
        if self.all_predictions_df is None or self.all_predictions_df.empty:
            self._populate_table(self.screener_table, pd.DataFrame())
            return

        df = self.all_predictions_df.copy()

        # Filters
        exchange = self.screener_exchange_filter.currentText()
        model = self.screener_model_filter.currentText()
        date = self.screener_date_filter.currentText()
        trend = self.screener_trend_filter.currentText()

        if exchange != "All":
            df = df[df['Exchange'] == exchange]

        if date:
            df = df[df['Date_Str'] == date]

        # model prefix names must match CSV column names format "Prophet_Open" / "LGBM_Open"
        model_prefix = "Prophet_" if model == "Prophet" else "LGBM_"
        rename_map = {
            f'{model_prefix}Open': 'Open', f'{model_prefix}High': 'High',
            f'{model_prefix}Low': 'Low', f'{model_prefix}Close': 'Close'
        }
        model_cols = list(rename_map.keys())
        # If a model column not present, show empty table
        if not all(c in df.columns for c in model_cols):
            self._populate_table(self.screener_table, pd.DataFrame())
            return

        cols_to_show = ['Stock', 'Date_Str'] + model_cols
        df = df[cols_to_show].rename(columns=rename_map)

        if trend != "All":
            df['Change'] = df['Close'] - df['Open']
            if trend == "Advances":
                df = df[df['Change'] >= 0]
            else:  # Declines
                df = df[df['Change'] < 0]
            df = df.drop(columns=['Change'])

        # store current screener df and populate table
        self.current_screener_df = df
        self._populate_table(self.screener_table, self.current_screener_df)

    def _apply_watchlist_filters(self):
        # small placeholder: filter predictions by tickers in self.watchlist (if any)
        if self.all_predictions_df is None or self.all_predictions_df.empty:
            self._populate_table(self.watchlist_table, pd.DataFrame())
            return
        df = self.all_predictions_df.copy()
        if self.watchlist:
            df = df[df['Stock'].isin(list(self.watchlist))]
        model = self.watchlist_model_filter.currentText()
        date = self.watchlist_date_filter.currentText()
        if date:
            df = df[df['Date_Str'] == date]
        # reuse model renaming used in screener
        model_prefix = "Prophet_" if model == "Prophet" else "LGBM_"
        rename_map = {
            f'{model_prefix}Open': 'Open', f'{model_prefix}High': 'High',
            f'{model_prefix}Low': 'Low', f'{model_prefix}Close': 'Close'
        }
        model_cols = list(rename_map.keys())
        if not all(c in df.columns for c in model_cols):
            self._populate_table(self.watchlist_table, pd.DataFrame())
            return
        cols_to_show = ['Stock', 'Date_Str'] + model_cols
        df = df[cols_to_show].rename(columns=rename_map)
        self._populate_table(self.watchlist_table, df)

    def _populate_table(self, table, df):
        table.setRowCount(0)
        if df is None or df.empty:
            table.clear()
            table.setColumnCount(0)
            return

        # columns expected in all screener/watchlist: Stock, Date, Open, High, Low, Close
        headers = ["Stock", "Date", "Open", "High", "Low", "Close"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(df))

        for i, (_, row) in enumerate(df.iterrows()):
            table.setItem(i, 0, QTableWidgetItem(str(row.get('Stock', ''))))
            date_value = str(row.get('Date_Str') or row.get('Date') or '')
            table.setItem(i, 1, QTableWidgetItem(date_value))
            for j, col in enumerate(['Open', 'High', 'Low', 'Close'], 2):
                rawval = row.get(col, np.nan)
                try:
                    val = f"₹{float(rawval):.2f}"
                except Exception:
                    val = str(rawval)
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
                if col == 'High':
                    item.setForeground(QColor("#20C997"))
                if col == 'Low':
                    item.setForeground(QColor("#E35D6A"))
                table.setItem(i, j, item)

        table.resizeColumnsToContents()
        # make headers clickable and toggle sort
        table.setSortingEnabled(True)
        header = table.horizontalHeader()
        header.sectionClicked.connect(lambda idx, t=table: self._on_header_clicked(t, idx))

    # --- UI Creation ---
    def _create_analyze_tab(self):
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 10, 0, 0)
        tab_layout.setSpacing(12)

        # Controls
        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        controls_frame.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px; padding: 10px;")
        controls_layout = QHBoxLayout(controls_frame)

        self.analyze_search = QLineEdit()
        self.analyze_search.setPlaceholderText("Search BSE/NSE Ticker...")
        self.analyze_search.setFixedHeight(36)
        self.analyze_search.setStyleSheet(self._search_bar_style())
        controls_layout.addWidget(self.analyze_search, 2)

        self.analyze_exchange = self._create_filter_pill_combo(["BSE", "NSE"])
        self.analyze_timerange = self._create_filter_pill_combo(["Days (7D)", "Hours (24H)", "Minutes (1H)"])

        controls_layout.addWidget(QLabel("Exchange:"))
        controls_layout.addWidget(self.analyze_exchange)
        controls_layout.addWidget(QLabel("Time Range:"))
        controls_layout.addWidget(self.analyze_timerange)

        analyze_btn = QPushButton("Analyze Symbol")
        analyze_btn.setFixedHeight(36)
        analyze_btn.setStyleSheet(self._pill_button_style_accent())
        analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        analyze_btn.clicked.connect(self.run_analysis)
        controls_layout.addWidget(analyze_btn)

        tab_layout.addWidget(controls_frame)

        # Content
        content_layout = QHBoxLayout()
        chart_card = QFrame()
        chart_card.setFrameShape(QFrame.Shape.StyledPanel)
        chart_card.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px;")
        chart_layout = QVBoxLayout(chart_card)
        self.chart_fig = Figure(figsize=(8, 3), dpi=100)
        self.chart_fig.patch.set_alpha(0.0)
        self.chart_ax = self.chart_fig.add_subplot()
        self.chart_canvas = FigureCanvas(self.chart_fig)
        chart_layout.addWidget(self.chart_canvas)
        content_layout.addWidget(chart_card, 3)

        table_card = QFrame()
        table_card.setFrameShape(QFrame.Shape.StyledPanel)
        table_card.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px;")
        table_layout = QVBoxLayout(table_card)
        toggle_layout = QHBoxLayout()
        self.hist_fut_switch = QCheckBox("Historical")
        self.hist_fut_switch.setStyleSheet(self._slider_switch_style())
        # default checked -> show historical by default
        self.hist_fut_switch.setChecked(True)
        toggle_layout.addWidget(self.hist_fut_switch)
        toggle_layout.addStretch()
        table_layout.addLayout(toggle_layout)

        self.analyze_table = QTableWidget()
        self.analyze_table.setStyleSheet(self._table_style())
        self.analyze_table.setSortingEnabled(True)
        self.analyze_table.horizontalHeader().sectionClicked.connect(
            lambda idx: self._on_header_clicked(self.analyze_table, idx)
        )
        table_layout.addWidget(self.analyze_table)

        # now safe to connect the signal
        self.hist_fut_switch.toggled.connect(self._on_hist_fut_toggled)

        toggle_layout.addWidget(self.hist_fut_switch)
        toggle_layout.addStretch()
        table_layout.addLayout(toggle_layout)
        self.analyze_table = QTableWidget()
        self.analyze_table.setStyleSheet(self._table_style())
        self.analyze_table.setSortingEnabled(True)
        # clickable header
        self.analyze_table.horizontalHeader().sectionClicked.connect(lambda idx: self._on_header_clicked(self.analyze_table, idx))
        table_layout.addWidget(self.analyze_table)
        content_layout.addWidget(table_card, 2)

        tab_layout.addLayout(content_layout)
        return tab_widget

    def _create_screener_tab(self):
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 10, 0, 0)
        tab_layout.setSpacing(12)

        # Filters
        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        controls_frame.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px; padding: 10px;")
        controls_layout = QHBoxLayout(controls_frame)

        self.screener_exchange_filter = self._create_filter_pill_combo(["All", "BSE", "NSE"])
        self.screener_model_filter = self._create_filter_pill_combo(["Prophet", "LightGBM"])
        self.screener_date_filter = self._create_filter_pill_combo([])  # Populated later
        self.screener_trend_filter = self._create_filter_pill_combo(["All", "Advances", "Declines"])

        controls_layout.addWidget(QLabel("Exchange:"))
        controls_layout.addWidget(self.screener_exchange_filter)
        controls_layout.addWidget(QLabel("Model:"))
        controls_layout.addWidget(self.screener_model_filter)
        controls_layout.addWidget(QLabel("Date:"))
        controls_layout.addWidget(self.screener_date_filter)
        controls_layout.addWidget(QLabel("Trend:"))
        controls_layout.addWidget(self.screener_trend_filter)
        controls_layout.addStretch()

        # Connect signals
        for combo in [self.screener_exchange_filter, self.screener_model_filter, self.screener_date_filter, self.screener_trend_filter]:
            combo.currentTextChanged.connect(self._apply_screener_filters)

        tab_layout.addWidget(controls_frame)

        # Table
        table_card = QFrame()
        table_card.setFrameShape(QFrame.Shape.StyledPanel)
        table_card.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px;")
        table_layout = QVBoxLayout(table_card)
        self.screener_table = QTableWidget()
        self.screener_table.setStyleSheet(self._table_style())
        self.screener_table.setSortingEnabled(True)
        # make headers clickable and toggle
        self.screener_table.horizontalHeader().sectionClicked.connect(lambda idx: self._on_header_clicked(self.screener_table, idx))
        table_layout.addWidget(self.screener_table)
        tab_layout.addWidget(table_card)

        return tab_widget

    def _create_watchlist_tab(self):
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 10, 0, 0)
        tab_layout.setSpacing(12)

        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        controls_frame.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px; padding: 10px;")
        controls_layout = QHBoxLayout(controls_frame)

        self.watchlist_model_filter = self._create_filter_pill_combo(["Prophet", "LightGBM"])
        self.watchlist_date_filter = self._create_filter_pill_combo([])

        controls_layout.addWidget(QLabel("Model:"))
        controls_layout.addWidget(self.watchlist_model_filter)
        controls_layout.addWidget(QLabel("Date:"))
        controls_layout.addWidget(self.watchlist_date_filter)
        controls_layout.addStretch()

        tab_layout.addWidget(controls_frame)

        table_card = QFrame()
        table_card.setFrameShape(QFrame.Shape.StyledPanel)
        table_card.setStyleSheet("background:rgba(15, 18, 21, 0.85); border-radius:12px;")
        table_layout = QVBoxLayout(table_card)
        self.watchlist_table = QTableWidget()
        self.watchlist_table.setStyleSheet(self._table_style())
        self.watchlist_table.setSortingEnabled(True)
        table_layout.addWidget(self.watchlist_table)
        tab_layout.addWidget(table_card)

        return tab_widget

    def _create_filter_pill_combo(self, items):
        combo = QComboBox()
        combo.addItems(items)
        combo.setStyleSheet(self._combo_style())
        return combo

    # -------------------- Ticker completer using uploaded lists --------------------
    def _setup_ticker_completer(self):
        # read uploaded tickers files from root relative path (uploaded as /mnt/data but here assumed to be in working dir)
        bse_list, nse_list = [], []
        try:
            with open(os.path.join('tickersbse.txt'), 'r') as f:
                bse_list = [l.strip().replace('.BO', '') for l in f.readlines() if l.strip()]
        except Exception:
            bse_list = []
        try:
            with open(os.path.join('tickersnse.txt'), 'r') as f:
                nse_list = [l.strip().replace('.NS', '') for l in f.readlines() if l.strip()]
        except Exception:
            nse_list = []

        # store for quick swap on exchange change
        self._ticker_lists = {'BSE': sorted(list(set(bse_list))), 'NSE': sorted(list(set(nse_list)))}
        # initial completer
        completer = QCompleter(self._ticker_lists.get('BSE', []))
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.analyze_search.setCompleter(completer)

        # swap completer when exchange changes
        def on_exchange_changed(txt):
            lst = self._ticker_lists.get(txt, [])
            newc = QCompleter(lst)
            newc.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.analyze_search.setCompleter(newc)
        self.analyze_exchange.currentTextChanged.connect(on_exchange_changed)

    # -------------------- Analysis orchestration --------------------
    def run_analysis(self):
        ticker = self.analyze_search.text().strip().upper()
        if not ticker:
            QMessageBox.warning(self, "Input Error", "Please enter a ticker to analyze.")
            return

        if self.analysis_worker and self.analysis_worker.isRunning():
            QMessageBox.information(self, "Busy", "An analysis is already in progress.")
            return

        exchange = self.analyze_exchange.currentText()
        time_range = self.analyze_timerange.currentText()

        self.analyze_search.setEnabled(False)

        # start worker
        self.analysis_worker = AnalysisWorker(ticker, exchange, time_range)
        self.analysis_worker.finished.connect(self.on_analysis_finished)
        self.analysis_worker.error.connect(self.on_analysis_error)
        self.analysis_worker.start()

    def on_analysis_finished(self, result):
        self.analyze_search.setEnabled(True)
        self.current_analysis_result = result
        # plot chart
        try:
            self.plot_analysis_chart(result['historical'], result['prophet'], result['lgbm'])
        except Exception as e:
            # ensure user sees plot errors but still continue
            print("Plotting error:", e)

        # Save the combined CSV prediction to data/predictions/<TICKER>_<BO/NS>_prediction.csv
        try:
            ticker = self.analysis_worker.ticker
            exchange = self.analysis_worker.exchange
            self._save_prediction_csv(ticker, exchange, result['historical'], result['prophet'], result['lgbm'])
            # reload screener db
            self._load_all_predictions()
            self._populate_screener_filters()
            self._apply_screener_filters()
        except Exception as e:
            print("Save prediction failed:", e)

        # refresh table on right
        self._on_hist_fut_toggled(self.hist_fut_switch.isChecked())

    def on_analysis_error(self, error_msg):
        self.analyze_search.setEnabled(True)
        QMessageBox.critical(self, "Analysis Error", error_msg)

    def plot_analysis_chart(self, historical, prophet, lgbm):
        self.chart_ax.clear()
        self._style_axes_dark(self.chart_ax)
        self.chart_ax.set_title("On-Demand Price Prediction", color="#EAF2FF", fontsize=14)

        # Historical
        self.chart_ax.plot(historical.index, historical['Close'], color='white', label='Historical')
        # Prophet predicted close (yhat)
        if not prophet.empty:
            self.chart_ax.plot(prophet.index, prophet['yhat'], color='#A855F7', linestyle='--', label='Prophet')
        # LightGBM predicted close
        if not lgbm.empty and 'Close' in lgbm.columns:
            self.chart_ax.plot(lgbm.index, lgbm['Close'], color='#F97316', linestyle='--', label='LightGBM')

        self.chart_fig.legend(loc='lower center', ncol=3, frameon=False, labelcolor='white')
        self.chart_fig.tight_layout()
        self.chart_canvas.draw()

    def _on_hist_fut_toggled(self, checked):
        """Populate analyze_table with either historical or future values based on checkbox.
        checked=True -> Historical; checked=False -> Future
        """
        self.analyze_table.clear()
        if not self.current_analysis_result:
            return

        if checked:
            # show recent historical rows
            hist_df = self.current_analysis_result['historical'].copy()
            hist_df = hist_df.tail(50)  # cap rows displayed
            headers = ["Date", "Open", "High", "Low", "Close"]
            self.analyze_table.setColumnCount(len(headers))
            self.analyze_table.setRowCount(len(hist_df))
            self.analyze_table.setHorizontalHeaderLabels(headers)
            for i, (idx, row) in enumerate(hist_df.iterrows()):
                self.analyze_table.setItem(i, 0, QTableWidgetItem(str(idx)))
                for j, col in enumerate(['Open','High','Low','Close'], 1):
                    v = row.get(col, np.nan)
                    try:
                        s = f"₹{float(v):.2f}"
                    except Exception:
                        s = str(v)
                    item = QTableWidgetItem(s)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.analyze_table.setItem(i, j, item)
            self.analyze_table.resizeColumnsToContents()
        else:
            # show future predictions: combine prophet and lgbm predictions into a shared table
            prophet_df = self.current_analysis_result['prophet'].copy()
            lgbm_df = self.current_analysis_result['lgbm'].copy()
            # Build unified index (future dates)
            future_idx = sorted(set(list(prophet_df.index) + list(lgbm_df.index)))
            rows = []
            for dt in future_idx:
                p_close = prophet_df.loc[dt]['yhat'] if (not prophet_df.empty and dt in prophet_df.index) else np.nan
                l_open = lgbm_df.loc[dt]['Open'] if (not lgbm_df.empty and dt in lgbm_df.index and 'Open' in lgbm_df.columns) else np.nan
                l_high = lgbm_df.loc[dt]['High'] if (not lgbm_df.empty and dt in lgbm_df.index and 'High' in lgbm_df.columns) else np.nan
                l_low = lgbm_df.loc[dt]['Low'] if (not lgbm_df.empty and dt in lgbm_df.index and 'Low' in lgbm_df.columns) else np.nan
                l_close = lgbm_df.loc[dt]['Close'] if (not lgbm_df.empty and dt in lgbm_df.index and 'Close' in lgbm_df.columns) else np.nan
                rows.append((dt, p_close, l_open, l_high, l_low, l_close))

            headers = ["Date", "Prophet_Close", "LGBM_Open", "LGBM_High", "LGBM_Low", "LGBM_Close"]
            self.analyze_table.setColumnCount(len(headers))
            self.analyze_table.setRowCount(len(rows))
            self.analyze_table.setHorizontalHeaderLabels(headers)
            for i, row in enumerate(rows):
                self.analyze_table.setItem(i, 0, QTableWidgetItem(str(row[0])))
                # Prophet close (1)
                try:
                    s = f"₹{float(row[1]):.2f}" if not pd.isna(row[1]) else ""
                except Exception:
                    s = ""
                it = QTableWidgetItem(s)
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.analyze_table.setItem(i, 1, it)
                # LGBM columns (2-5)
                for j, val in enumerate(row[2:], 2):
                    try:
                        s = f"₹{float(val):.2f}" if not pd.isna(val) else ""
                    except Exception:
                        s = ""
                    it = QTableWidgetItem(s)
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.analyze_table.setItem(i, j, it)
            self.analyze_table.resizeColumnsToContents()

    # -------------------- Save combined CSV (historical + prophet + lgbm) --------------------
    def _save_prediction_csv(self, ticker, exchange, historical_df, prophet_df, lgbm_df):
        # Create unified index (past last N historical + future predictions)
        hist_idx = list(historical_df.index)
        future_idx = sorted(set(list(prophet_df.index) + list(lgbm_df.index)))
        all_idx = sorted(list(set(hist_idx + future_idx)))
        # build dataframe with required columns
        out = pd.DataFrame(index=all_idx)
        # Actual columns (from historical)
        out['Actual_Open'] = np.nan
        out['Actual_High'] = np.nan
        out['Actual_Low'] = np.nan
        out['Actual_Close'] = np.nan
        for idx in hist_idx:
            row = historical_df.loc[idx]
            out.at[idx, 'Actual_Open'] = row.get('Open', np.nan)
            out.at[idx, 'Actual_High'] = row.get('High', np.nan)
            out.at[idx, 'Actual_Low'] = row.get('Low', np.nan)
            out.at[idx, 'Actual_Close'] = row.get('Close', np.nan)
        # Prophet columns (only close predicted from prophet)
        out['Prophet_Open'] = np.nan
        out['Prophet_High'] = np.nan
        out['Prophet_Low'] = np.nan
        out['Prophet_Close'] = np.nan
        for idx in prophet_df.index:
            out.at[idx, 'Prophet_Close'] = prophet_df.loc[idx]['yhat']
        # LightGBM columns
        out['LGBM_Open'] = np.nan
        out['LGBM_High'] = np.nan
        out['LGBM_Low'] = np.nan
        out['LGBM_Close'] = np.nan
        for idx in lgbm_df.index:
            for col in ['Open','High','Low','Close']:
                if col in lgbm_df.columns:
                    out.at[idx, f"LGBM_{col}"] = lgbm_df.loc[idx][col]

        # reset index as Date column (string ISO)
        out = out.reset_index().rename(columns={'index':'Date'})
        out['Date'] = out['Date'].astype(str)
        # Write to data/predictions/<TICKER>_<BO/NS>_prediction.csv
        suffix = 'BO' if exchange == 'BSE' else 'NS'
        fname = f"{ticker}_{suffix}_prediction.csv"
        out.to_csv(os.path.join(PREDICTIONS_PATH, fname), index=False)

    # --- header click sort toggler ---
    def _on_header_clicked(self, table, col_idx):
        # Toggle sort order for the clicked column
        prev = self.last_sort_state.get(id(table), (None, Qt.SortOrder.AscendingOrder))
        prev_col, prev_order = prev
        new_order = Qt.SortOrder.DescendingOrder if (prev_col == col_idx and prev_order == Qt.SortOrder.AscendingOrder) else Qt.SortOrder.AscendingOrder
        table.sortItems(col_idx, new_order)
        self.last_sort_state[id(table)] = (col_idx, new_order)

    # --- Styles ---
    def _get_page_stylesheet(self):
        return """
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabWidget > QWidget > QWidget {
                background: transparent;
            }
            QTabBar::tab {
                background: transparent; color: #9aa4b6; font-size: 14px;
                font-weight: 600; padding: 10px 15px; margin-right: 10px; border: none;
            }
            QTabBar::tab:hover { color: #FFFFFF; }
            QTabBar::tab:selected {
                color: #FFFFFF;
                border-bottom: 3px solid #33C4B9;
            }
        """
    def _search_bar_style(self): return "QLineEdit { background-color: #1B2026; color: #DDE8F5; border: 1px solid #2B323A; border-radius: 18px; padding: 0px 15px; font-size: 11pt; } QLineEdit:hover { border: 1px solid #3B4652; } QLineEdit:focus { border: 1px solid #33C4B9; }"
    def _pill_button_style_accent(self): return "QPushButton { background-color: #33C4B9; color: #0A0D10; border-radius: 18px; padding: 5px 15px; font-weight: bold; font-size: 10pt; border: none; } QPushButton:hover { background-color: #2AA6A6; } QPushButton:pressed { background-color: #1F7A7A; }"
    def _slider_switch_style(self): return "QCheckBox { spacing: 10px; color: #DDE8F5; font-weight: 600; font-size: 10pt; } QCheckBox::indicator { width: 44px; height: 24px; background-color: #3B4652; border-radius: 12px; border: 1px solid #2B323A; } QCheckBox::indicator:checked { background-color: #33C4B9; border: 1px solid #2AA6A6; } QCheckBox::indicator::handle { width: 20px; height: 20px; background-color: white; border-radius: 10px; margin: 2px; } QCheckBox::indicator::handle:unchecked { margin-left: 2px; } QCheckBox::indicator::handle:checked { margin-left: 22px; }"
    def _style_axes_dark(self, ax): ax.set_facecolor("none"); ax.tick_params(axis='x', colors="#CCD6E4"); ax.tick_params(axis='y', colors="#CCD6E4"); [s.set_color("#2C2F34") for s in ax.spines.values()]; ax.grid(axis='y', linestyle=':', color="#2A2E33", alpha=0.35)
    def _combo_style(self): return "QComboBox { background-color: #1B2026; color: #DDE8F5; border: 1px solid #2B323A; border-radius: 10px; padding: 6px 25px 6px 10px; font-weight: 600; } QComboBox:hover { border: 1px solid #33C4B9; } QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: top right; width: 22px; border-left: 1px solid #2B323A; border-top-right-radius: 9px; border-bottom-right-radius: 9px; } QComboBox::down-arrow { image: url(assets/down-arrow.png); } QComboBox QAbstractItemView { background: #15181B; color: #E8F2FF; border: 1px solid #3B4652; border-radius: 8px; selection-background-color: #1F7A7A; padding: 4px; outline: 0px; }"
    def _table_style(self): return f"QTableWidget {{ background: transparent; color: #E6EEF6; border: none; gridline-color: #2B323A; selection-background-color: rgba(42, 166, 166, 0.3); alternate-background-color: rgba(255, 255, 255, 0.02); }} QTableWidget::item {{ padding: 6px 8px; border-bottom: 1px solid #2B323A; border-right: 1px solid #2B323A; }} QHeaderView::section {{ background-color: transparent; color: #9aa4b6; font-weight: 600; border: none; padding: 8px; border-bottom: 2px solid #33C4B9; }} {self._scrollbar_style()}"
    def _scrollbar_style(self): return "QScrollBar:vertical { border: none; background: transparent; width: 10px; } QScrollBar::handle:vertical { background: #4a5568; min-height: 20px; border-radius: 5px; } QScrollBar::handle:vertical:hover { background: #718096; } QScrollBar:horizontal { border: none; background: transparent; height: 10px; } QScrollBar::handle:horizontal { background: #4a5568; min-width: 20px; border-radius: 5px; } QScrollBar::handle:horizontal:hover { background: #718096; }"

# --- Standalone Run ---
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
