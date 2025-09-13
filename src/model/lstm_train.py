# src/models/lstm_train.py

import numpy as np
import os
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.metrics import mean_squared_error, mean_absolute_error
import math

# -----------------------------
# Define base directory (relative to project root)
# -----------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEQUENCE_DIR = os.path.join(BASE_DIR, "data", "sequences")

# -----------------------------
# Metrics
# -----------------------------
def mape(y_true, y_pred):
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

# -----------------------------
# Function to build LSTM
# -----------------------------
def build_lstm(input_shape):
    model = Sequential()
    model.add(LSTM(128, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.3))
    model.add(LSTM(64, return_sequences=False))
    model.add(Dropout(0.3))
    model.add(Dense(32, activation="relu"))
    model.add(Dense(1, activation="linear"))
    model.compile(optimizer='adam', loss='mae')  # ✅ MAE better for stocks
    return model

# -----------------------------
# Function to train and evaluate
# -----------------------------
def train_evaluate_lstm(sequence_dir, stock_name):
    # Load sequences
    X_train = np.load(os.path.join(sequence_dir, "X_train.npy"))
    y_train = np.load(os.path.join(sequence_dir, "y_train.npy"))
    X_val = np.load(os.path.join(sequence_dir, "X_val.npy"))
    y_val = np.load(os.path.join(sequence_dir, "y_val.npy"))
    X_test = np.load(os.path.join(sequence_dir, "X_test.npy"))
    y_test = np.load(os.path.join(sequence_dir, "y_test.npy"))

    print(f"\nTraining LSTM for {stock_name}:")
    print(f"X_train shape: {X_train.shape}, y_train shape: {y_train.shape}")

    # Build model
    model = build_lstm((X_train.shape[1], X_train.shape[2]))

    # Early stopping + learning rate reduction
    es = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True)
    lr = ReduceLROnPlateau(monitor='val_loss', patience=5, factor=0.5, min_lr=1e-5)

    # Train
    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=200,
        batch_size=32,
        callbacks=[es, lr],
        verbose=2
    )

    # Evaluate
    y_pred = model.predict(X_test)
    rmse = math.sqrt(mean_squared_error(y_test, y_pred))
    mae = mean_absolute_error(y_test, y_pred)
    mape_val = mape(y_test, y_pred)

    print(f"{stock_name} - Test RMSE: {rmse:.4f}, MAE: {mae:.4f}, MAPE: {mape_val:.2f}%")

    # Save model
    model_path = os.path.join(sequence_dir, f"{stock_name}_lstm.h5")
    model.save(model_path)
    print(f"✅ Model saved at {model_path}")


if __name__ == "__main__":
    stock_list = [
        ("NSE/INFY_NS", "INFY"),
        ("NSE/TCS_NS", "TCS"),
        ("BSE/RELIANCE_BO", "RELIANCE"),
        ("BSE/TATASTEEL_BO", "TATASTEEL")
    ]

    for seq_subdir, stock_name in stock_list:
        seq_dir = os.path.join(SEQUENCE_DIR, seq_subdir)
        train_evaluate_lstm(seq_dir, stock_name)

    print("\n✅ LSTM training complete!")