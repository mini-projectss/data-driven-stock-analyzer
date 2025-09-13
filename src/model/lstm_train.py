# src/models/lstm_train.py

import os
import pandas as pd
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from sklearn.preprocessing import MinMaxScaler
import joblib
import traceback

# Directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MODEL_DIR = os.path.join(BASE_DIR, "models", "lstm")

os.makedirs(MODEL_DIR, exist_ok=True)

SEQUENCE_LEN = 60  # You can adjust this

def prepare_data(stock_path, seq_len=SEQUENCE_LEN):
    df = pd.read_csv(stock_path)
    if len(df) <= seq_len:
        raise ValueError(f"Not enough data for sequence length {seq_len}")
    
    data = df["Close"].values.reshape(-1, 1)
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(data)

    X, y = [], []
    for i in range(seq_len, len(scaled)):
        X.append(scaled[i - seq_len:i, 0])
        y.append(scaled[i, 0])

    X = np.array(X)
    y = np.array(y)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))
    return X, y, scaler

def train_model(stock, stock_path):
    try:
        X, y, scaler = prepare_data(stock_path)
        model = Sequential([
            Input(shape=(X.shape[1], 1)),
            LSTM(50, return_sequences=True),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])

        model.compile(optimizer="adam", loss="mean_squared_error")
        
        # Try to fit with batch_size=32, reduce if memory error occurs
        try:
            model.fit(X, y, epochs=5, batch_size=32, verbose=0)
        except Exception as e:
            print(f"⚠ Memory issue with batch_size=32 for {stock}, retrying with 16...")
            model.fit(X, y, epochs=5, batch_size=16, verbose=0)

        # Save model & scaler
        stock_dir = os.path.join(MODEL_DIR, stock)
        os.makedirs(stock_dir, exist_ok=True)

        model.save(os.path.join(stock_dir, "lstm_model.keras"))
        joblib.dump(scaler, os.path.join(stock_dir, "scaler.pkl"))

        print(f"✅ Trained and saved model for {stock}")

    except Exception as e:
        print(f"❌ Error training {stock}: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    for exchange in ["bse"]:
        exchange_path = os.path.join(PROCESSED_DIR, exchange)
        if not os.path.exists(exchange_path):
            continue
        
        for stock_file in os.listdir(exchange_path):
            if stock_file.endswith(".csv"):
                stock_name = stock_file.replace(".csv", "")
                stock_path = os.path.join(exchange_path, stock_file)
                train_model(stock_name, stock_path)

    print("✅ Training completed for all available stocks")
