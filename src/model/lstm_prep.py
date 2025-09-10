# src/models/lstm_prep_multi.py

import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split

# -----------------------------
# Function to prepare LSTM sequences for any stock
# -----------------------------
def prepare_lstm_sequences(stock_csv, market_type, sequence_length=60):
    """
    stock_csv: full path to processed CSV
    market_type: 'NSE' or 'BSE'
    """
    scaler_pkl = stock_csv.replace(".csv", "_scaler.pkl")
    
    # Load CSV and scaler
    df = pd.read_csv(stock_csv)
    scaler = joblib.load(scaler_pkl)

    features = ['Open','High','Low','Close','Volume','MA_5','MA_10','MA_20','RSI','MACD',
                'Close_Lag1','Close_Lag2','Close_Lag3']
    data = df[features].values

    # Prepare sequences
    X, y = [], []
    for i in range(sequence_length, len(data)):
        X.append(data[i-sequence_length:i])
        y.append(data[i, features.index('Close')])
    X, y = np.array(X), np.array(y)

    # Train/Validation/Test split
    train_size = 0.7
    val_size = 0.15

    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=(1-train_size), shuffle=False
    )

    val_relative_size = val_size / (train_size + val_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=val_relative_size, shuffle=False
    )

    # Save sequences in organized folder (separate NSE/BSE)
    stock_name = os.path.splitext(os.path.basename(stock_csv))[0]
    sequence_dir = os.path.join(r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\sequences", market_type, stock_name)
    os.makedirs(sequence_dir, exist_ok=True)

    np.save(os.path.join(sequence_dir, "X_train.npy"), X_train)
    np.save(os.path.join(sequence_dir, "y_train.npy"), y_train)
    np.save(os.path.join(sequence_dir, "X_val.npy"), X_val)
    np.save(os.path.join(sequence_dir, "y_val.npy"), y_val)
    np.save(os.path.join(sequence_dir, "X_test.npy"), X_test)
    np.save(os.path.join(sequence_dir, "y_test.npy"), y_test)

    print(f"✅ Sequences saved for {stock_name} in {market_type} at {sequence_dir}")

# -----------------------------
# Example usage for two stocks
# -----------------------------
if __name__ == "__main__":
    stock_list = [
        (r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\processed\NSE\INFY_NS.csv", "NSE"),
        (r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\processed\NSE\TCS_NS.csv", "NSE"),
        (r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\processed\BSE\RELIANCE_BO.csv", "BSE"),
        (r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\processed\BSE\TATASTEEL_BO.csv", "BSE")
    ]

    for stock_csv, market in stock_list:
        prepare_lstm_sequences(stock_csv, market)
