# src/model/lstm_prep.py

import pandas as pd
import numpy as np
import os
import joblib
from sklearn.preprocessing import MinMaxScaler

# Define base directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
SEQUENCE_DIR = os.path.join(BASE_DIR, "data", "sequences")
os.makedirs(SEQUENCE_DIR, exist_ok=True)

# Function to prepare LSTM sequences
def prepare_lstm_sequences(stock_csv, market_type, sequence_length=60):
    csv_path = os.path.join(PROCESSED_DIR, market_type, stock_csv)
    if not os.path.exists(csv_path):
        print(f"❌ Missing file for {market_type}/{stock_csv}, skipping...")
        return

    # Load CSV
    df = pd.read_csv(csv_path)

    # Features to be used as input (X)
    features = [
        'Open', 'High', 'Low', 'Close', 'Volume', 'MA_5', 'MA_10', 'MA_20',
        'RSI', 'MACD', 'Close_Lag1', 'Close_Lag2', 'Close_Lag3'
    ]
    
    # Target values to be predicted (y)
    target_cols = ['Open', 'High', 'Low', 'Close']

    # Drop rows with any NaN values from feature engineering
    df.dropna(inplace=True)
    if len(df) <= sequence_length + 1:
        print(f"⚠️ Not enough data for {stock_csv} ({market_type}), skipping...")
        return

    # Scale the features and targets separately
    feature_scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_features = feature_scaler.fit_transform(df[features])
    
    target_scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_targets = target_scaler.fit_transform(df[target_cols])
    
    # Create sequences
    X, y = [], []
    for i in range(sequence_length, len(df) - 1):
        X.append(scaled_features[i - sequence_length:i])
        y.append(scaled_targets[i + 1])
    
    X, y = np.array(X), np.array(y)

    # Save sequences and scalers
    stock_name = os.path.splitext(os.path.basename(stock_csv))[0]
    sequence_dir = os.path.join(SEQUENCE_DIR, market_type.lower(), stock_name)
    os.makedirs(sequence_dir, exist_ok=True)

    np.save(os.path.join(sequence_dir, "X.npy"), X)
    np.save(os.path.join(sequence_dir, "y.npy"), y)
    
    # Save both scalers
    joblib.dump(feature_scaler, os.path.join(sequence_dir, "feature_scaler.pkl"))
    joblib.dump(target_scaler, os.path.join(sequence_dir, "target_scaler.pkl"))

    print(f"✅ Sequences prepared and saved for {stock_name} ({market_type})")

# Main Execution
if __name__ == "__main__":
    for market in ["NSE", "BSE"]:
        market_dir = os.path.join(PROCESSED_DIR, market)
        if not os.path.exists(market_dir):
            continue

        for stock_file in os.listdir(market_dir):
            if stock_file.endswith(".csv"):
                prepare_lstm_sequences(stock_file, market)

    print("✅ LSTM sequences prepared for all available stocks")