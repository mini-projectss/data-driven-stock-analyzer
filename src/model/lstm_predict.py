# src/models/lstm_predict.py

import numpy as np
import os
import joblib
import pandas as pd
from tensorflow.keras.models import load_model

# -----------------------------
# Metrics
# -----------------------------
def mape(y_true, y_pred):
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

# -----------------------------
# Function to predict and save results + future n-day forecast
# -----------------------------
def predict_lstm(stock_name, sequence_dir, processed_csv_path, save_dir, future_days=5):
    print(f"\nPredicting for {stock_name}...")

    # Load model
    model_path = os.path.join(sequence_dir, f"{stock_name}_lstm.h5")
    if not os.path.exists(model_path):
        print(f"❌ Model not found: {model_path}")
        return
    model = load_model(model_path, compile=False)  # ✅ compile=False

    # Load sequences
    X_test = np.load(os.path.join(sequence_dir, "X_test.npy"))
    y_test = np.load(os.path.join(sequence_dir, "y_test.npy"))

    # Predict scaled
    y_pred_scaled = model.predict(X_test)

    # Load scaler
    scaler = joblib.load(processed_csv_path.replace(".csv", "_scaler.pkl"))

    # Inverse transform Close price
    y_pred_actual = scaler.inverse_transform(
        np.concatenate([np.zeros((y_pred_scaled.shape[0], 12)), y_pred_scaled], axis=1)
    )[:, -1]

    y_test_actual = scaler.inverse_transform(
        np.concatenate([np.zeros((y_test.shape[0], 12)), y_test.reshape(-1,1)], axis=1)
    )[:, -1]

    # Print last 10 predictions vs actual
    print("\nLast 10 predictions vs actual:")
    for i in range(-10, 0):
        print(f"Predicted: {y_pred_actual[i]:.2f}, Actual: {y_test_actual[i]:.2f}")

    # Metrics
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    import math
    rmse = math.sqrt(mean_squared_error(y_test_actual, y_pred_actual))
    mae = mean_absolute_error(y_test_actual, y_pred_actual)
    mape_val = mape(y_test_actual, y_pred_actual)
    print(f"\n{stock_name} - Test RMSE: {rmse:.4f}, MAE: {mae:.4f}, MAPE: {mape_val:.2f}%")

    # -----------------------------
    # Save predictions to CSV
    # -----------------------------
    df = pd.read_csv(processed_csv_path)
    dates = pd.to_datetime(df['Date'].iloc[-len(y_test_actual):])

    results_df = pd.DataFrame({
        "Date": dates,
        "Actual_Close": y_test_actual,
        "Predicted_Close": y_pred_actual
    })

    # ---- Future n-day forecast ----
    last_sequence = df.iloc[-60:].copy()  # last 60 rows
    future_preds = []

    for i in range(future_days):
        features = last_sequence[['Open','High','Low','Close','Volume','MA_5','MA_10','MA_20','RSI','MACD',
                                  'Close_Lag1','Close_Lag2','Close_Lag3']].values
        features = features.reshape(1, features.shape[0], features.shape[1])
        pred_scaled = model.predict(features)[0][0]
        pred_actual = scaler.inverse_transform(np.concatenate([np.zeros((1,12)), [[pred_scaled]]], axis=1))[:, -1][0]
        future_preds.append(pred_actual)

        # Update last_sequence with predicted Close using pd.concat
        new_row = last_sequence.iloc[-1].copy()
        new_row['Close'] = pred_actual
        new_row['Close_Lag3'] = new_row['Close_Lag2']
        new_row['Close_Lag2'] = new_row['Close_Lag1']
        new_row['Close_Lag1'] = pred_actual
        last_sequence = pd.concat([last_sequence, pd.DataFrame([new_row])], ignore_index=True)

    # Add future dates
    last_date = pd.to_datetime(df['Date'].iloc[-1])
    future_dates = [last_date + pd.Timedelta(days=i+1) for i in range(future_days)]
    future_df = pd.DataFrame({
        "Date": future_dates,
        "Actual_Close": [np.nan]*future_days,
        "Predicted_Close": future_preds
    })

    results_df = pd.concat([results_df, future_df], ignore_index=True)

    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{stock_name}_lstm_predictions.csv")
    results_df.to_csv(save_path, index=False)
    print(f"✅ Predictions + {future_days}-day forecast saved to: {save_path}")


# -----------------------------
# Main: Predict for all 4 stocks
# -----------------------------
if __name__ == "__main__":
    save_dir = r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\predictions"
    future_days = 5  # can change number of forecast days

    stock_list = [
        ("INFY", r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\sequences\NSE\INFY_NS",
         r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\processed\NSE\INFY_NS.csv"),
        ("TCS", r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\sequences\NSE\TCS_NS",
         r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\processed\NSE\TCS_NS.csv"),
        ("RELIANCE", r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\sequences\BSE\RELIANCE_BO",
         r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\processed\BSE\RELIANCE_BO.csv"),
        ("TATASTEEL", r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\sequences\BSE\TATASTEEL_BO",
         r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\processed\BSE\TATASTEEL_BO.csv")
    ]

    for stock_name, seq_dir, processed_csv in stock_list:
        predict_lstm(stock_name, seq_dir, processed_csv, save_dir, future_days)
