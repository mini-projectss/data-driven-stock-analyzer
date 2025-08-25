"""
prediction.py

Lightweight prediction module + a PyQt page widget for your app.

Features:
- Load historical CSVs from data/historical/{EXCHANGE}/{TICKER}.csv
- Optionally pull latest price points from yfinance and append to history
- Two model backends:
    * LSTM (TensorFlow/Keras) — sequence model trained on Close price
    * Prophet (fbprophet / prophet) — classical time-series model
- Evaluation (MAE, RMSE)
- A ready-to-add PyQt QWidget (PredictionWidget) that integrates with your app
  and runs training/prediction in a background thread (QThread) to avoid blocking UI.

Notes / Requirements:
- pip install pandas numpy scikit-learn matplotlib pyqt6
- For LSTM: pip install tensorflow
- For Prophet: pip install prophet (or pip install "fbprophet==0.7.1" on older systems)
- Optional: pip install yfinance  (live price pull)

Drop this file into your project and import PredictionWidget in your main app to
embed the page.

"""

import os
import sys
import time
import traceback
import math
from typing import Optional, Tuple, Dict

import pandas as pd
import numpy as np

# plotting & PyQt integration
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QMessageBox, QLineEdit, QSizePolicy, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

# ML imports (optional; code handles absence)
try:
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error
except Exception:
    MinMaxScaler = None

try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.callbacks import EarlyStopping
    TF_AVAILABLE = True
except Exception:
    TF_AVAILABLE = False

# Prophet import (may be prophet or fbprophet depending on install)
PROPHET_AVAILABLE = False
Prophet = None
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except Exception:
    try:
        from fbprophet import Prophet
        PROPHET_AVAILABLE = True
    except Exception:
        PROPHET_AVAILABLE = False

# yfinance optional
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except Exception:
    YFINANCE_AVAILABLE = False

# --------------------------- Utilities ---------------------------

def list_data_tickers(data_dir="data/historical") -> Dict[str, list]:
    """Return dict of exchange -> list of file tickers present on disk."""
    out = {}
    for exch in os.listdir(data_dir) if os.path.isdir(data_dir) else []:
        path = os.path.join(data_dir, exch)
        if not os.path.isdir(path):
            continue
        files = [os.path.splitext(f)[0] for f in os.listdir(path) if f.lower().endswith('.csv')]
        out[exch] = sorted(files)
    return out


def load_historical_csv(exchange: str, file_ticker: str, data_dir: str = "data/historical") -> pd.DataFrame:
    """Load CSV and return DataFrame indexed by datetime. Normalises column names.
    Expects file at data_dir/{exchange}/{file_ticker}.csv
    """
    path = os.path.join(data_dir, exchange, f"{file_ticker}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_csv(path, low_memory=False)
    # try to find date column
    date_col = None
    for c in df.columns:
        if c.lower() in ("date", "timestamp", "time", "datetime"):
            date_col = c
            break
    if date_col is None:
        date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.set_index(date_col).sort_index()
    # Rename common OHLCV columns
    lc = {c.lower(): c for c in df.columns}
    rename = {}
    for low, orig in lc.items():
        if low in ("open", "o"): rename[orig] = 'Open'
        if low in ("high", "h"): rename[orig] = 'High'
        if low in ("low", "l"): rename[orig] = 'Low'
        if low in ("close", "c", "adj close", "adjclose"): rename[orig] = 'Close'
        if low in ("volume", "v", "vol", "totaltradequantity", "totaltradedqty"): rename[orig] = 'Volume'
    df = df.rename(columns=rename)
    # ensure Close exists
    if 'Close' not in df.columns:
        raise ValueError("CSV doesn't contain recognizable Close column")
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df = df.dropna(subset=['Close'])
    return df


def append_live_yfinance(df: pd.DataFrame, yf_symbol: str, lookback_minutes: int = 60) -> pd.DataFrame:
    """If yfinance is available, pull most recent tick(s) and append to df.
    This is optional convenience; it won't fill historic gaps.
    """
    if not YFINANCE_AVAILABLE:
        return df
    try:
        ticker = yf.Ticker(yf_symbol)
        # try to fetch last 1d with 1m resolution (may be limited)
        hist = ticker.history(period='1d', interval='1m', actions=False)
        if hist is None or hist.empty:
            # fallback: get last close
            info = ticker.history(period='5d', interval='1d', actions=False)
            if info is None or info.empty:
                return df
            last = info['Close'].iloc[-1]
            last_idx = info.index[-1]
            if last_idx not in df.index:
                df.loc[last_idx] = df.iloc[-1].to_dict()
                df.loc[last_idx, 'Close'] = last
            return df
        # keep recent N minutes (or last 60 points)
        closes = hist['Close'].dropna()
        # ensure index type matches
        # append rows that are newer than df.index.max()
        max_idx = df.index.max()
        app = closes[closes.index > max_idx]
        if not app.empty:
            new_df = pd.DataFrame({'Close': app.values}, index=app.index)
            # merge with original: prefer original columns where possible
            df = pd.concat([df, new_df], sort=False)
            df = df[~df.index.duplicated(keep='last')].sort_index()
        return df
    except Exception:
        return df

# ----------------------- LSTM pipeline -----------------------

def create_lstm_dataset(series: pd.Series, window: int = 60) -> Tuple[np.ndarray, np.ndarray, MinMaxScaler]:
    """Return X, y arrays suitable for LSTM training and the scaler used.
    X shape = (n_samples, window, 1)
    """
    if MinMaxScaler is None:
        raise RuntimeError("scikit-learn required for LSTM preprocessing")
    vals = series.values.reshape(-1, 1)
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(vals)
    X = []
    y = []
    for i in range(window, len(scaled)):
        X.append(scaled[i-window:i, 0])
        y.append(scaled[i, 0])
    X = np.array(X)
    y = np.array(y)
    X = X.reshape((X.shape[0], X.shape[1], 1))
    return X, y, scaler


def build_lstm_model(input_shape, units: int = 64, dropout: float = 0.12) -> Sequential:
    if not TF_AVAILABLE:
        raise RuntimeError("TensorFlow not available. Install tensorflow to use LSTM.")
    model = Sequential()
    model.add(LSTM(units, input_shape=input_shape, return_sequences=False))
    model.add(Dropout(dropout))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mse')
    return model


def train_lstm(series: pd.Series, window: int = 60, epochs: int = 40, batch_size: int = 32, verbose: int = 0) -> Tuple[Sequential, MinMaxScaler]:
    X, y, scaler = create_lstm_dataset(series, window)
    model = build_lstm_model(input_shape=(X.shape[1], X.shape[2]))
    callbacks = [EarlyStopping(monitor='loss', patience=6, restore_best_weights=True)]
    model.fit(X, y, epochs=epochs, batch_size=batch_size, verbose=verbose, callbacks=callbacks)
    return model, scaler


def predict_lstm(model: Sequential, scaler: MinMaxScaler, recent_series: pd.Series, window: int, steps: int = 1) -> np.ndarray:
    """Generate future 'steps' predictions using recursive forecasting.
    recent_series should contain the last `window` raw Close values (not scaled).
    Returns array of predicted raw Close values length=steps
    """
    seq = recent_series.values[-window:].reshape(-1, 1)
    scaled_seq = scaler.transform(seq)[:, 0].tolist()
    preds = []
    for _ in range(steps):
        x = np.array(scaled_seq[-window:]).reshape(1, window, 1)
        scaled_next = float(model.predict(x, verbose=0)[0, 0])
        preds.append(scaled_next)
        scaled_seq.append(scaled_next)
    preds = np.array(preds).reshape(-1, 1)
    raw = scaler.inverse_transform(preds)[:, 0]
    return raw

# ----------------------- Prophet pipeline -----------------------

def train_prophet(df: pd.DataFrame) -> 'Prophet':
    if not PROPHET_AVAILABLE:
        raise RuntimeError("Prophet not available. Install prophet (or fbprophet) to use this backend.")
    # prophet expects dataframe with ds (datetime) and y (value)
    tmp = df[['Close']].reset_index().rename(columns={df.index.name or 'index': 'ds', 'Close': 'y'})
    tmp = tmp[['ds', 'y']].dropna()
    m = Prophet(daily_seasonality=True)
    m.fit(tmp)
    return m


def predict_prophet(model: 'Prophet', periods: int = 30, freq: str = 'D') -> pd.DataFrame:
    future = model.make_future_dataframe(periods=periods, freq=freq)
    forecast = model.predict(future)
    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]

# ----------------------- Metrics -----------------------

def evaluate_forecast(true: np.ndarray, pred: np.ndarray) -> Dict[str, float]:
    # drop nan pairs
    mask = ~np.isnan(true) & ~np.isnan(pred)
    if mask.sum() == 0:
        return {'mae': float('nan'), 'rmse': float('nan')}
    mae = float(mean_absolute_error(true[mask], pred[mask])) if 'mean_absolute_error' in globals() else float('nan')
    rmse = float(math.sqrt(mean_squared_error(true[mask], pred[mask]))) if 'mean_squared_error' in globals() else float('nan')
    return {'mae': mae, 'rmse': rmse}

# ----------------------- Background thread for long ops -----------------------

class PredictionWorker(QThread):
    """Run training and prediction in background to keep GUI responsive.
    Emits finished(dict) when done.
    """
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, mode: str, exchange: str, file_ticker: str, steps: int = 30,
                 window: int = 60, epochs: int = 40, method: str = 'lstm', use_live: bool = True):
        super().__init__()
        self.mode = mode  # 'train_predict'
        self.exchange = exchange
        self.file_ticker = file_ticker
        self.steps = steps
        self.window = window
        self.epochs = epochs
        self.method = method
        self.use_live = use_live

    def run(self):
        try:
            # load history
            df = load_historical_csv(self.exchange, self.file_ticker)
            if self.use_live and YFINANCE_AVAILABLE:
                # try to infer yfinance symbol from file_ticker (common pattern: SYMBOL_NS or SYMBOL.BO etc.)
                yf_symbol = None
                if self.file_ticker.endswith('_BO') or self.file_ticker.endswith('.BO'):
                    yf_symbol = self.file_ticker.replace('_BO', '.BO').replace('.BO', '.BO')
                elif self.file_ticker.endswith('_NS') or self.file_ticker.endswith('.NS'):
                    yf_symbol = self.file_ticker.replace('_NS', '.NS').replace('.NS', '.NS')
                else:
                    # fallback: use cleaned display
                    yf_symbol = self.file_ticker
                try:
                    df = append_live_yfinance(df, yf_symbol)
                except Exception:
                    pass

            result = {'exchange': self.exchange, 'file_ticker': self.file_ticker, 'method': self.method}

            if self.method == 'lstm':
                if not TF_AVAILABLE:
                    raise RuntimeError('TensorFlow required for LSTM but not available')
                series = df['Close'].dropna()
                # small check
                if len(series) < max(100, self.window + 10):
                    raise RuntimeError('Not enough history for reliable LSTM training')
                model, scaler = train_lstm(series, window=self.window, epochs=self.epochs, verbose=0)
                preds = predict_lstm(model, scaler, series, window=self.window, steps=self.steps)
                # build index for prediction days: next business days based on last index (approx daily)
                last_ts = series.index[-1]
                future_index = pd.date_range(start=last_ts, periods=self.steps + 1, closed='right', freq='B')
                result['forecast'] = pd.Series(preds, index=future_index).to_dict()
                # attach simple evaluation on holdout (last window -> test)
                # generate one-step predictions on the training tail for quick in-sample check
                X, y, _ = create_lstm_dataset(series, window=self.window)
                if len(X) > 20:
                    # take last 20 samples
                    x_test = X[-20:]
                    y_test = y[-20:]
                    y_pred_scaled = model.predict(x_test, verbose=0).reshape(-1, 1)
                    y_pred = scaler.inverse_transform(y_pred_scaled)[:, 0]
                    y_true = scaler.inverse_transform(y_test.reshape(-1, 1))[:, 0]
                    result['metrics'] = evaluate_forecast(y_true, y_pred)
                else:
                    result['metrics'] = {'mae': None, 'rmse': None}

            elif self.method == 'prophet':
                if not PROPHET_AVAILABLE:
                    raise RuntimeError('Prophet required but not available')
                model = train_prophet(df)
                fc = predict_prophet(model, periods=self.steps, freq='B')
                # return last `steps` rows as forecast
                future = fc.tail(self.steps).set_index('ds')['yhat']
                result['forecast'] = future.to_dict()
                result['metrics'] = {'mae': None, 'rmse': None}
            else:
                raise RuntimeError('Unknown method')

            self.finished.emit(result)
        except Exception as e:
            tb = traceback.format_exc()
            self.failed.emit(f"{e}\n{tb}")

# ----------------------- Simple PyQt page widget -----------------------

class PredictionWidget(QWidget):
    """A compact prediction page you can drop into your main window.

    Usage: from prediction import PredictionWidget
           widget = PredictionWidget(data_dir='data/historical')
           main_layout.addWidget(widget)
    """
    def __init__(self, data_dir='data/historical', parent=None):
        super().__init__(parent)
        self.data_dir = data_dir
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        hl = QHBoxLayout()
        self.exchange_combo = QComboBox(); self.exchange_combo.setFixedWidth(120)
        self.exchange_combo.addItems(sorted([d for d in os.listdir(self.data_dir) if os.path.isdir(os.path.join(self.data_dir, d))]))
        hl.addWidget(QLabel('Exchange:'))
        hl.addWidget(self.exchange_combo)
        self.ticker_combo = QComboBox(); self.ticker_combo.setEditable(True)
        self._refresh_tickers()
        self.exchange_combo.currentTextChanged.connect(self._refresh_tickers)
        hl.addWidget(QLabel('Ticker:'))
        hl.addWidget(self.ticker_combo)

        self.method_combo = QComboBox(); self.method_combo.addItems(['lstm', 'prophet'])
        hl.addWidget(QLabel('Method:'))
        hl.addWidget(self.method_combo)

        self.steps_edit = QLineEdit('30'); self.steps_edit.setFixedWidth(60)
        hl.addWidget(QLabel('Days:'))
        hl.addWidget(self.steps_edit)

        self.train_btn = QPushButton('Train & Forecast')
        self.train_btn.clicked.connect(self._on_run)
        hl.addWidget(self.train_btn)

        layout.addLayout(hl)

        # figure area
        self.fig = Figure(figsize=(8, 3), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        # status
        self.status_lbl = QLabel('Ready')
        layout.addWidget(self.status_lbl)

        self.setLayout(layout)

    def _refresh_tickers(self):
        exch = self.exchange_combo.currentText()
        folder = os.path.join(self.data_dir, exch)
        items = []
        if os.path.isdir(folder):
            items = [os.path.splitext(f)[0] for f in os.listdir(folder) if f.lower().endswith('.csv')]
        self.ticker_combo.clear()
        self.ticker_combo.addItems(sorted(items))

    def _on_run(self):
        exchange = self.exchange_combo.currentText()
        file_ticker = self.ticker_combo.currentText().strip()
        method = self.method_combo.currentText()
        try:
            steps = int(self.steps_edit.text())
        except ValueError:
            QMessageBox.warning(self, 'Bad input', 'Days must be integer')
            return
        if not exchange or not file_ticker:
            QMessageBox.warning(self, 'Missing', 'Please select exchange and ticker')
            return

        # disable UI while running
        self.train_btn.setEnabled(False)
        self.status_lbl.setText('Running...')

        self.worker = PredictionWorker(mode='train_predict', exchange=exchange, file_ticker=file_ticker,
                                       steps=steps, window=60, epochs=30, method=method, use_live=YFINANCE_AVAILABLE)
        self.worker.finished.connect(self._on_result)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_failed(self, text):
        self.status_lbl.setText('Failed')
        QMessageBox.critical(self, 'Prediction failed', text)
        self.train_btn.setEnabled(True)

    def _on_result(self, result):
        self.status_lbl.setText('Done')
        self.train_btn.setEnabled(True)
        # plot recent history + forecast
        try:
            df = load_historical_csv(result['exchange'], result['file_ticker'])
            recent = df['Close'].last('180D')
            forecast = pd.Series(result['forecast'])
            # forecasting dict may have timestamp keys as strings -> try to coerce
            try:
                forecast = pd.Series({pd.to_datetime(k): v for k, v in result['forecast'].items()}).sort_index()
            except Exception:
                forecast = pd.Series(result['forecast'])

            self.fig.clear()
            ax = self.fig.add_subplot()
            ax.set_facecolor('#0F1215')
            # plot history
            ax.plot(recent.index, recent.values, label='History')
            # plot forecast
            if not forecast.empty:
                ax.plot(forecast.index, forecast.values, linestyle='--', label='Forecast')
            ax.set_title(f"Forecast for {result['file_ticker']} ({result['method']})")
            ax.legend()
            self.canvas.draw()
            # show metrics if exist
            metrics = result.get('metrics')
            if metrics:
                s = f"MAE: {metrics.get('mae')}, RMSE: {metrics.get('rmse')}"
                self.status_lbl.setText(s)
        except Exception as e:
            self.status_lbl.setText('Plot error')
            QMessageBox.warning(self, 'Plotting error', str(e))


# ----------------------- CLI entrypoint (optional) -----------------------
if __name__ == '__main__':
    # quick CLI usage to test module independently
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--exchange', default='NSE')
    parser.add_argument('--ticker', required=True)
    parser.add_argument('--method', default='lstm', choices=['lstm', 'prophet'])
    parser.add_argument('--days', default=30, type=int)
    args = parser.parse_args()

    # run prediction synchronously as a simple demo
    df = load_historical_csv(args.exchange, args.ticker)
    if args.method == 'lstm':
        if not TF_AVAILABLE:
            print('tensorflow not installed — cannot run LSTM demo')
            sys.exit(1)
        series = df['Close'].dropna()
        model, scaler = train_lstm(series, window=60, epochs=20, verbose=1)
        preds = predict_lstm(model, scaler, series, window=60, steps=args.days)
        print('Predictions:')
        for i, p in enumerate(preds, 1):
            print(i, p)
    else:
        if not PROPHET_AVAILABLE:
            print('prophet not installed — cannot run Prophet demo')
            sys.exit(1)
        m = train_prophet(df)
        fc = predict_prophet(m, periods=args.days, freq='B')
        print(fc.tail(args.days))

