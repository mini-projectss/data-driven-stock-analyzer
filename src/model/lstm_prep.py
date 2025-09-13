# src/model/lstm_prep.py

import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split

# -----------------------------
# Define base directories
# -----------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
SEQUENCE_DIR = os.path.join(BASE_DIR, "data", "sequences")

# -----------------------------
# Function to prepare LSTM sequences
# -----------------------------
def prepare_lstm_sequences(stock_csv, market_type, sequence_length=60):
    csv_path = os.path.join(PROCESSED_DIR, market_type, stock_csv)
    scaler_pkl = csv_path.replace(".csv", "_scaler.pkl")
    
    if not os.path.exists(csv_path) or not os.path.exists(scaler_pkl):
        print(f"❌ Missing file for {market_type}/{stock_csv}, skipping...")
        return

    # Load CSV and scaler
    df = pd.read_csv(csv_path)
    scaler = joblib.load(scaler_pkl)

    features = [
        'Open','High','Low','Close','Volume','MA_5','MA_10','MA_20','RSI','MACD',
        'Close_Lag1','Close_Lag2','Close_Lag3'
    ]
    data = df[features].values

    # Save scaler + features for later
    joblib.dump({"scaler": scaler, "features": features}, scaler_pkl)

    # Create sequences
    X, y = [], []
    for i in range(sequence_length, len(data)):
        X.append(data[i-sequence_length:i])
        y.append(data[i, features.index('Close')])
    X, y = np.array(X), np.array(y)

    # Skip if too few samples
    if len(X) < 10:
        print(f"⚠️ Not enough data for {stock_csv} ({market_type}), skipping...")
        return

    # Split
    train_size = 0.7
    val_size = 0.15

    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=(1-train_size), shuffle=False
    )

    val_relative_size = val_size / (train_size + val_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=val_relative_size, shuffle=False
    )

    # Save
    stock_name = os.path.splitext(os.path.basename(stock_csv))[0]
    sequence_dir = os.path.join(SEQUENCE_DIR, market_type.lower(), stock_name)
    os.makedirs(sequence_dir, exist_ok=True)

    np.save(os.path.join(sequence_dir, "X_train.npy"), X_train)
    np.save(os.path.join(sequence_dir, "y_train.npy"), y_train)
    np.save(os.path.join(sequence_dir, "X_val.npy"), X_val)
    np.save(os.path.join(sequence_dir, "y_val.npy"), y_val)
    np.save(os.path.join(sequence_dir, "X_test.npy"), X_test)
    np.save(os.path.join(sequence_dir, "y_test.npy"), y_test)

    print(f"✅ Sequences saved for {stock_name} ({market_type})")

# -----------------------------
# Main Execution
# -----------------------------
if __name__ == "__main__":
    for market in ["NSE", "BSE"]:
        market_dir = os.path.join(PROCESSED_DIR, market)
        if not os.path.exists(market_dir):
            continue

        for stock_file in os.listdir(market_dir):
            if stock_file.endswith(".csv"):
                prepare_lstm_sequences(stock_file, market)

    print("✅ LSTM sequences prepared for all available stocks")
