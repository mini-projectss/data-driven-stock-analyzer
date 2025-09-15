import pandas as pd
from prophet import Prophet
import lightgbm as lgb
from sklearn.multioutput import MultiOutputRegressor
import os

# --- Configuration ---
DATA_PATH = 'data'
PROCESSED_PATH = os.path.join(DATA_PATH, 'processed')
PREDICTIONS_PATH = os.path.join(DATA_PATH, 'predictions')
PREDICTION_DAYS = 7

def run_prediction():
    """Main function to generate and save 7-day OHLC predictions."""
    with open('tickersbse.txt', 'r') as f:
        bse_tickers = [line.strip() for line in f.readlines()]
    with open('tickersnse.txt', 'r') as f:
        nse_tickers = [line.strip() for line in f.readlines()]
    all_tickers = bse_tickers + nse_tickers

    print(f"Starting OHLC predictions for {len(all_tickers)} tickers...")

    for ticker in all_tickers:
        print(f"\nPredicting for {ticker}...")

        # --- FIX: Convert ticker name to filename format (e.g., FSL.NS -> FSL_NS) ---
        filename_ticker = ticker.replace('.', '_')
        
        # --- Prophet Prediction (Four Models) ---
        prophet_predictions = {}
        for column in ['Open', 'High', 'Low', 'Close']:
            input_file = os.path.join(PROCESSED_PATH, 'prophet', f'{filename_ticker}_{column.lower()}.csv')
            if not os.path.exists(input_file):
                print(f"  - Prophet data for {column} not found. Skipping ticker.")
                prophet_predictions = None
                break
            
            df_prophet = pd.read_csv(input_file)
            model = Prophet()
            model.fit(df_prophet)
            future = model.make_future_dataframe(periods=PREDICTION_DAYS)
            forecast = model.predict(future)
            prophet_predictions[f'Prophet_{column}'] = forecast[['ds', 'yhat']].tail(PREDICTION_DAYS).set_index('ds')['yhat']
        
        if prophet_predictions:
            final_prophet_preds = pd.DataFrame(prophet_predictions)
            final_prophet_preds.index.name = 'Date'
            print("  - Prophet OHLC prediction complete.")
        else:
            continue

        # --- LightGBM Multi-Output Prediction ---
        lgbm_input_path = os.path.join(PROCESSED_PATH, 'lightgbm', f'{filename_ticker}.csv')
        if not os.path.exists(lgbm_input_path):
            print(f"  - LightGBM data not found for {ticker}. Skipping.")
            continue
            
        df_lgbm = pd.read_csv(lgbm_input_path, index_col='Date', parse_dates=True)
        
        features = ['MA_7_Close', 'MA_30_Close', 'Lag_1_Close']
        targets = ['Open', 'High', 'Low', 'Close']
        
        X = df_lgbm[features]
        y = df_lgbm[targets]
        
        lgbm = lgb.LGBMRegressor()
        model_lgbm = MultiOutputRegressor(lgbm)
        model_lgbm.fit(X, y)
        
        lgbm_predictions = []
        last_known_data = df_lgbm.copy()

        for _ in range(PREDICTION_DAYS):
            last_features = pd.DataFrame({
                'MA_7_Close': [last_known_data['Close'].iloc[-7:].mean()],
                'MA_30_Close': [last_known_data['Close'].iloc[-30:].mean()],
                'Lag_1_Close': [last_known_data['Close'].iloc[-1]]
            })
            
            prediction = model_lgbm.predict(last_features)[0]
            lgbm_predictions.append(prediction)
            
            next_day_index = last_known_data.index[-1] + pd.Timedelta(days=1)
            new_row_data = {
                'Open': prediction[0], 'High': prediction[1], 'Low': prediction[2], 'Close': prediction[3]
            }
            new_row = pd.DataFrame(new_row_data, index=[next_day_index])
            last_known_data = pd.concat([last_known_data, new_row])

        future_dates = final_prophet_preds.index
        final_lgbm_preds = pd.DataFrame(lgbm_predictions, index=future_dates, columns=[f'LGBM_{col}' for col in targets])
        print("  - LightGBM OHLC prediction complete.")

        # --- Combine and Save Predictions ---
        final_predictions = final_prophet_preds.join(final_lgbm_preds)
        output_path = os.path.join(PREDICTIONS_PATH, f'{filename_ticker}_prediction.csv')
        final_predictions.to_csv(output_path)
        print(f"  -> Combined OHLC predictions saved to {output_path}")

    print("\nPrediction process complete.")

if __name__ == "__main__":
    os.makedirs(PREDICTIONS_PATH, exist_ok=True)
    run_prediction()