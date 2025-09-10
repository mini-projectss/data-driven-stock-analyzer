# src/models/lstm_train.py

import numpy as np
import os
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.metrics import mean_squared_error, mean_absolute_error
import math

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
    model.add(LSTM(50, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.2))
    model.add(LSTM(50))
    model.add(Dropout(0.2))
    model.add(Dense(1))
    model.compile(optimizer='adam', loss='mse')
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

    # Early stopping
    es = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

    # Train
    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=100,
        batch_size=32,
        callbacks=[es],
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

# -----------------------------
# Train LSTM for 4 stocks
# -----------------------------
if __name__ == "__main__":
    stock_list = [
        (r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\sequences\NSE\INFY_NS", "INFY"),
        (r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\sequences\NSE\TCS_NS", "TCS"),
        (r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\sequences\BSE\RELIANCE_BO", "RELIANCE"),
        (r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\sequences\BSE\TATASTEEL_BO", "TATASTEEL")
    ]

    for seq_dir, stock_name in stock_list:
        train_evaluate_lstm(seq_dir, stock_name)
