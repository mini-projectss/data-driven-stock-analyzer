# src/model/lstm_train.py

import os
import numpy as np
import joblib
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
import tensorflow as tf

# Directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEQUENCE_DIR = os.path.join(BASE_DIR, "data", "sequences")
MODEL_DIR = os.path.join(BASE_DIR, "models", "lstm_ohlc")
os.makedirs(MODEL_DIR, exist_ok=True)

def build_model(input_shape):
    """Builds and compiles the LSTM model for OHLC prediction."""
    model = Sequential([
        Input(shape=input_shape),
        LSTM(units=50, return_sequences=True),
        Dropout(0.2),
        LSTM(units=50),
        Dropout(0.2),
        Dense(units=4)  # 4 outputs for OHLC
    ])
    model.compile(optimizer="adam", loss="mean_squared_error")
    return model

def train_model(stock_name, market_type):
    """Loads sequences, trains the model, and saves it."""
    sequence_path = os.path.join(SEQUENCE_DIR, market_type, stock_name)
    
    if not os.path.exists(sequence_path):
        print(f"❌ Sequence data not found for {stock_name} ({market_type}), skipping...")
        return

    base_stock_name = stock_name.replace('_ns', '').replace('_be', '')

    try:
        X = np.load(os.path.join(sequence_path, "X.npy"))
        y = np.load(os.path.join(sequence_path, "y.npy"))

        # Split data (chronologically)
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]

        model = build_model(input_shape=(X_train.shape[1], X_train.shape[2]))
        
        # Train model
        model.fit(X_train, y_train, epochs=50, batch_size=32, verbose=0)
        
        # Evaluate performance
        loss = model.evaluate(X_test, y_test, verbose=0)
        print(f"✅ Trained {base_stock_name.upper()} ({market_type.upper()}). Test Loss: {loss:.4f}")

        # Save model
        model_path = os.path.join(MODEL_DIR, market_type, base_stock_name)
        os.makedirs(model_path, exist_ok=True)
        model.save(os.path.join(model_path, "lstm_ohlc_model.keras"))
    
    except MemoryError:
        print(f"⚠️ Insufficient memory to train {stock_name} ({market_type}). Skipping...")
    except Exception as e:
        print(f"❌ Error training {stock_name} ({market_type}): {e}")

if __name__ == "__main__":
    for market in ["nse", "bse"]:
        market_dir = os.path.join(SEQUENCE_DIR, market)
        if not os.path.exists(market_dir):
            continue
        
        stocks = sorted([d for d in os.listdir(market_dir) if os.path.isdir(os.path.join(market_dir, d))])
        for stock in stocks:
            train_model(stock, market)

    print("✅ Training completed for all available stocks")