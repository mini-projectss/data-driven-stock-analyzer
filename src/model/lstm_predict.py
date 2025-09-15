# src/model/lstm_predict.py

import os
import pandas as pd
import numpy as np
import joblib
from tensorflow.keras.models import load_model

# Directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MODEL_DIR = os.path.join(BASE_DIR, "models", "lstm_ohlc")
SEQUENCE_DIR = os.path.join(BASE_DIR, "data", "sequences")
PREDICTIONS_DIR = os.path.join(BASE_DIR, "predictions")
os.makedirs(PREDICTIONS_DIR, exist_ok=True)


def predict_single_step(model, input_sequence, feature_scaler, target_scaler):
    """
    Makes a single-step prediction and inverse transforms the output.
    """
    scaled_prediction = model.predict(input_sequence, verbose=0)
    prediction = target_scaler.inverse_transform(scaled_prediction)
    return prediction[0]


def generate_future_features(predicted_ohlc, last_data, features):
    """
    Creates a new feature vector (as a DataFrame) for the next prediction step.
    This is a placeholder and assumes non-OHLC features are relatively stable.
    """
    new_row_df = last_data.tail(1).copy()
    
    new_row_df.loc[:, 'Open'] = predicted_ohlc[0]
    new_row_df.loc[:, 'High'] = predicted_ohlc[1]
    new_row_df.loc[:, 'Low'] = predicted_ohlc[2]
    new_row_df.loc[:, 'Close'] = predicted_ohlc[3]
    
    new_sequence = pd.concat([last_data.iloc[1:], new_row_df], ignore_index=True)
    return new_sequence


def main(base_stock_name, market_of_stock):
    sequence_length = 60
    market_type = market_of_stock.lower()

    # Define paths
    model_path = os.path.join(MODEL_DIR, market_type, base_stock_name, "lstm_ohlc_model.keras")
    
    # We now need to find the correct data folder name (with the suffix)
    # to load the scalers from. We will search for it.
    stock_to_predict_with_suffix = None
    try:
        sequence_market_dir = os.path.join(SEQUENCE_DIR, market_type)
        stock_folders = [d for d in os.listdir(sequence_market_dir) if d.startswith(base_stock_name)]
        if stock_folders:
            stock_to_predict_with_suffix = stock_folders[0]
        else:
            print(f"❌ Sequence data folder not found for {base_stock_name} in {market_type}")
            return
    except FileNotFoundError:
        print(f"❌ Sequence directory not found: {sequence_market_dir}")
        return

    feature_scaler_path = os.path.join(SEQUENCE_DIR, market_type, stock_to_predict_with_suffix, "feature_scaler.pkl")
    target_scaler_path = os.path.join(SEQUENCE_DIR, market_type, stock_to_predict_with_suffix, "target_scaler.pkl")
    processed_csv_path = os.path.join(PROCESSED_DIR, market_type.upper(), f"{stock_to_predict_with_suffix.upper()}.csv")
    
    STOCK_PREDICTIONS_DIR = os.path.join(PREDICTIONS_DIR, market_type, base_stock_name)
    os.makedirs(STOCK_PREDICTIONS_DIR, exist_ok=True)
    
    try:
        model = load_model(model_path)
        feature_scaler = joblib.load(feature_scaler_path)
        target_scaler = joblib.load(target_scaler_path)
        df = pd.read_csv(processed_csv_path)
        df['Date'] = pd.to_datetime(df['Date'])
    except Exception as e:
        print(f"❌ Failed to load model or data for {base_stock_name}: {e}")
        return

    features = [
        'Open', 'High', 'Low', 'Close', 'Volume', 'MA_5', 'MA_10', 'MA_20',
        'RSI', 'MACD', 'Close_Lag1', 'Close_Lag2', 'Close_Lag3'
    ]

    # ... (rest of the code for past and future predictions)
    print(f"\n--- Past 1-Year Comparison for {base_stock_name.upper()} ---")
    comparison_results = []
    
    test_start_index = len(df) - 252 - sequence_length
    if test_start_index < 0:
        test_start_index = 0
    
    comparison_df = df[features].iloc[test_start_index:].copy()
    
    for i in range(sequence_length, len(comparison_df) - 1):
        input_sequence = comparison_df.iloc[i - sequence_length:i]
        scaled_input_sequence = feature_scaler.transform(input_sequence)
        scaled_input_sequence = scaled_input_sequence.reshape(1, sequence_length, len(features))
        predicted_values = predict_single_step(model, scaled_input_sequence, feature_scaler, target_scaler)
        
        actual_ohlc = df[['Open', 'High', 'Low', 'Close']].iloc[test_start_index + i + 1].values
        
        comparison_results.append({
            'Date': df['Date'].iloc[test_start_index + i + 1],
            'Predicted_Open': predicted_values[0],
            'Predicted_High': predicted_values[1],
            'Predicted_Low': predicted_values[2],
            'Predicted_Close': predicted_values[3],
            'Actual_Open': actual_ohlc[0],
            'Actual_High': actual_ohlc[1],
            'Actual_Low': actual_ohlc[2],
            'Actual_Close': actual_ohlc[3]
        })

    comparison_df_results = pd.DataFrame(comparison_results)
    comparison_file = os.path.join(STOCK_PREDICTIONS_DIR, f"{base_stock_name}_past_year_comparison.csv")
    comparison_df_results.to_csv(comparison_file, index=False)
    print(f"✅ Past year comparison saved to {comparison_file}")
    
    print(f"\n--- Future 5-Day Prediction for {base_stock_name.upper()} ---")
    future_predictions = []
    current_sequence = df[features].tail(sequence_length).copy()
    
    last_known_date = df['Date'].iloc[-1]

    for day in range(1, 6):
        scaled_input = feature_scaler.transform(current_sequence)
        scaled_input = scaled_input.reshape(1, sequence_length, len(features))
        predicted_values = predict_single_step(model, scaled_input, feature_scaler, target_scaler)
        
        predicted_date = last_known_date + pd.Timedelta(days=day)

        future_predictions.append({
            'Date': predicted_date.strftime('%Y-%m-%d'),
            'Open': predicted_values[0],
            'High': predicted_values[1],
            'Low': predicted_values[2],
            'Close': predicted_values[3]
        })
        
        current_sequence = generate_future_features(predicted_values, current_sequence, features)
    
    future_df = pd.DataFrame(future_predictions)
    future_file = os.path.join(STOCK_PREDICTIONS_DIR, f"{base_stock_name}_future_5_day_prediction.csv")
    future_df.to_csv(future_file, index=False)
    print(f"✅ Future 5-day prediction saved to {future_file}")
    
    print("\nAll tasks completed.")

if __name__ == "__main__":
    for market in ["nse", "bse"]:
        market_dir = os.path.join(MODEL_DIR, market)
        if not os.path.exists(market_dir):
            continue
            
        stocks = sorted([d for d in os.listdir(market_dir) if os.path.isdir(os.path.join(market_dir, d))])
        
        for stock in stocks:
            main(stock, market)
    
    print("✅ Prediction for all available stocks completed.")