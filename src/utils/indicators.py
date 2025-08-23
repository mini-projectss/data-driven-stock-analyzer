# utils/indicators.py

import pandas as pd
import numpy as np

# -----------------------------
# Relative Strength Index (RSI)
# -----------------------------
def add_rsi(df, period: int = 14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

# -----------------------------
# Moving Averages (SMA & EMA)
# -----------------------------
def add_moving_averages(df, short_window: int = 20, long_window: int = 50):
    df['SMA20'] = df['Close'].rolling(window=short_window).mean()
    df['SMA50'] = df['Close'].rolling(window=long_window).mean()
    df['EMA20'] = df['Close'].ewm(span=short_window, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=long_window, adjust=False).mean()
    return df

# -----------------------------
# MACD (Moving Average Convergence Divergence)
# -----------------------------
def add_macd(df, short=12, long=26, signal=9):
    df['EMA12'] = df['Close'].ewm(span=short, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=long, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal_Line'] = df['MACD'].ewm(span=signal, adjust=False).mean()
    return df

# -----------------------------
# Bollinger Bands
# -----------------------------
def add_bollinger_bands(df, window: int = 20):
    sma = df['Close'].rolling(window=window).mean()
    std = df['Close'].rolling(window=window).std()

    df['Bollinger_Upper'] = sma + (2 * std)
    df['Bollinger_Lower'] = sma - (2 * std)
    return df

# -----------------------------
# Volume Moving Average
# -----------------------------
def add_volume_ma(df, period: int = 20):
    df['Volume_MA20'] = df['Volume'].rolling(window=period).mean()
    return df

# -----------------------------
# Apply all indicators
# -----------------------------
def add_all_indicators(df):
    df = add_rsi(df)
    df = add_moving_averages(df)
    df = add_macd(df)
    df = add_bollinger_bands(df)
    df = add_volume_ma(df)
    return df
