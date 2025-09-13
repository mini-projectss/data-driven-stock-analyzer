# src/models/lstm_predict.py

import os
import numpy as np
import pandas as pd
import joblib
from tensorflow.keras.models import load_model
from tensorflow.keras import metrics
from datetime import timedelta

# -----------------------------
# Base directories
# -----------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEQUENCE_DIR = os.path.join(BASE_DIR, "data", "sequences")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
PREDICTIONS_DIR = os.path.join(BASE_DIR, "data", "Predictions")

# -----------------------------
# Inverse scaling for Close column
# -----------------------------
def inverse_transform_close(y_scaled, scaler, features):
    feature_count = len(features)
    dummy = np.zeros((y_scaled.shape[0], feature_count))
    dummy[:, features.index("Close")] = y_scaled.reshape(-1)
    return scaler.inverse_transform(dummy)[:, features.index("Close")]

# -----------------------------
# Predict LSTM
# -----------------------------
def predict_lstm(stock_name, market_type, future_days=10):
    print(f"\n🔮 Predicting {stock_name}...")

    model_stock_name = stock_name.split("_")[0]

    # Paths
    seq_dir = os.path.join(SEQUENCE_DIR, market_type, stock_name)
    model_path = os.path.join(seq_dir, f"{model_stock_name}_lstm.h5")
    scaler_path = os.path.join(PROCESSED_DIR, market_type, f"{stock_name}_scaler.pkl")
    processed_csv = os.path.join(PROCESSED_DIR, market_type, f"{stock_name}.csv")

    if not os.path.exists(model_path) or not os.path.exists(scaler_path) or not os.path.exists(processed_csv):
        print(f"❌ Missing files for {stock_name}. Skipping.")
        return

    # Load sequences
    X_test = np.load(os.path.join(seq_dir, "X_test.npy"))
    y_test = np.load(os.path.join(seq_dir, "y_test.npy"))

    # Load scaler and features
    scaler_dict = joblib.load(scaler_path)
    scaler = scaler_dict["scaler"]
    features = scaler_dict["features"]

    # Load model
    try:
        model = load_model(model_path, custom_objects={"mae": metrics.MeanAbsoluteError()})
    except Exception as e:
        print(f"⚠️ Failed to load model: {e}")
        return

    # Predictions
    y_pred_scaled = model.predict(X_test)
    y_pred_actual = inverse_transform_close(y_pred_scaled, scaler, features)
    y_test_actual = inverse_transform_close(y_test.reshape(-1, 1), scaler, features)

    # Load dates from CSV
    df = pd.read_csv(processed_csv)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    test_dates = df['Date'].iloc[-len(y_test_actual):].reset_index(drop=True)

    # -----------------------------
    # Prepare folder structure
    # -----------------------------
    stock_pred_dir = os.path.join(PREDICTIONS_DIR, market_type, stock_name)
    os.makedirs(stock_pred_dir, exist_ok=True)

    # -----------------------------
    # Store past predictions
    # -----------------------------
    past_df = pd.DataFrame({
        "Date": test_dates,
        "Actual_Close": y_test_actual,
        "Predicted_Close": y_pred_actual
    })
    past_file = os.path.join(stock_pred_dir, "past_predictions.csv")
    past_df.to_csv(past_file, index=False)
    print(f"✅ Past predictions stored: {past_file}")

    # -----------------------------
    # Future 10-day prediction
    # -----------------------------
    last_sequence = X_test[-1]
    last_date = test_dates.iloc[-1]
    future_predictions = []
    future_dates = []

    for i in range(future_days):
        pred_scaled = model.predict(last_sequence.reshape(1, *last_sequence.shape))
        pred_actual = inverse_transform_close(pred_scaled, scaler, features)[0]
        future_predictions.append(pred_actual)
        future_dates.append(last_date + timedelta(days=i+1))

        # update sequence
        new_row = np.zeros((1, last_sequence.shape[1]))
        new_row[0, features.index("Close")] = pred_scaled
        last_sequence = np.vstack([last_sequence[1:], new_row])

    future_df = pd.DataFrame({
        "Date": future_dates,
        "Predicted_Close": future_predictions
    })
    future_file = os.path.join(stock_pred_dir, "future_10days.csv")
    future_df.to_csv(future_file, index=False)
    print(f"✅ Future 10-day predictions stored: {future_file}")

    return past_df, future_df

# -----------------------------
# Main run
# -----------------------------
if __name__ == "__main__":
    stock_list = [
        ("INFY_NS", "NSE"),
        ("TCS_NS", "NSE"),
        ("RELIANCE_BO", "BSE"),
        ("TATASTEEL_BO", "BSE"),
    ]

    for stock_name, market in stock_list:
        try:
            predict_lstm(stock_name, market, future_days=10)
        except Exception as e:
            print(f"⚠️ Error predicting {stock_name}: {e}")
