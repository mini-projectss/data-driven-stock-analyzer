# src/models/lstm_train.py

import numpy as np
import os
import math
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.metrics import mean_squared_error, mean_absolute_error

# -----------------------------
# Base directories
# -----------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEQUENCE_DIR = os.path.join(BASE_DIR, "data", "sequences")
MODEL_DIR = os.path.join(BASE_DIR, "data", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

# -----------------------------
# Metrics
# -----------------------------
def mape(y_true, y_pred):
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

# -----------------------------
# Build LSTM
# -----------------------------
def build_lstm(input_shape):
    model = Sequential()
    model.add(LSTM(128, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.3))
    model.add(LSTM(64, return_sequences=False))
    model.add(Dropout(0.3))
    model.add(Dense(32, activation="relu"))
    model.add(Dense(1, activation="linear"))
    model.compile(optimizer='adam', loss='mae')
    return model

# -----------------------------
# Train & Evaluate
# -----------------------------
def train_evaluate_lstm(sequence_dir, stock_name, exchange, metrics_log):
    try:
        X_train = np.load(os.path.join(sequence_dir, "X_train.npy"))
        y_train = np.load(os.path.join(sequence_dir, "y_train.npy"))
        X_val = np.load(os.path.join(sequence_dir, "X_val.npy"))
        y_val = np.load(os.path.join(sequence_dir, "y_val.npy"))
        X_test = np.load(os.path.join(sequence_dir, "X_test.npy"))
        y_test = np.load(os.path.join(sequence_dir, "y_test.npy"))
    except:
        print(f"❌ Missing sequence files for {exchange}/{stock_name}, skipping...")
        return

    print(f"\n🔹 Training {exchange}/{stock_name}...")

    model = build_lstm((X_train.shape[1], X_train.shape[2]))
    es = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)
    lr = ReduceLROnPlateau(monitor='val_loss', patience=5, factor=0.5, min_lr=1e-5)

    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=200,
        epochs=200,
        batch_size=32,
        callbacks=[es, lr],
        verbose=0
    )

    y_pred = model.predict(X_test)
    rmse = math.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    mape_val = mape(y_test, y_pred)

    print(f"✅ {stock_name}: RMSE={rmse:.4f}, MAE={mae:.4f}, MAPE={mape_val:.2f}%")

    # Save model
    model_dir = os.path.join(MODEL_DIR, exchange.lower())
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, f"{stock_name}_lstm.h5")
    model.save(model_path)

    # Save metrics
    metrics_log.append({
        "Exchange": exchange,
        "Stock": stock_name,
        "RMSE": rmse,
        "MAE": mae,
        "MAPE": mape_val
    })

if __name__ == "__main__":
    metrics_log = []

    for exchange in ["nse", "bse"]:
        exchange_dir = os.path.join(SEQUENCE_DIR, exchange)
        if not os.path.exists(exchange_dir):
            continue

        for stock_name in os.listdir(exchange_dir):
            seq_dir = os.path.join(exchange_dir, stock_name)
            if os.path.isdir(seq_dir):
                train_evaluate_lstm(seq_dir, stock_name, exchange.upper(), metrics_log)

    # Save metrics summary
    metrics_df = pd.DataFrame(metrics_log)
    metrics_file = os.path.join(MODEL_DIR, "training_metrics.csv")
    metrics_df.to_csv(metrics_file, index=False)
    print(f"\n📊 Metrics saved: {metrics_file}")

    print("✅ LSTM models trained and evaluated for all stocks")