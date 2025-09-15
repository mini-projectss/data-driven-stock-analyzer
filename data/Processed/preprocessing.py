# data/preprocess.py

import pandas as pd
import os
import ta

# -----------------------------
# Paths (update according to your PC)
# -----------------------------
RAW_DATA_DIR = os.path.join(os.getcwd(), "..", "historical")      # raw CSV folder
PROCESSED_DATA_DIR = os.path.join(os.getcwd(), "..", "processed")  # processed CSV folder

# Ensure processed folders exist
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

# -----------------------------
# Loop through NSE and BSE
# -----------------------------
for market_folder in os.listdir(RAW_DATA_DIR):
    market_path = os.path.join(RAW_DATA_DIR, market_folder)
    if os.path.isdir(market_path):
        processed_market_path = os.path.join(PROCESSED_DATA_DIR, market_folder)
        os.makedirs(processed_market_path, exist_ok=True)

        # Loop through each CSV
        for filename in os.listdir(market_path):
            if filename.endswith(".csv"):
                file_path = os.path.join(market_path, filename)
                df = pd.read_csv(file_path)

                # Convert Date column to datetime & sort
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                df.sort_values('Date', inplace=True)

                # Filter rows from 2015 onward
                df = df[df['Date'].dt.year >= 2015]

                # Ensure numeric columns
                numeric_cols = ['Open','High','Low','Close','Volume']
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                # Fill missing values
                df.ffill(inplace=True)

                # -----------------------------
                # Feature Engineering
                # -----------------------------
                df['MA_5'] = df['Close'].rolling(5).mean()
                df['MA_10'] = df['Close'].rolling(10).mean()
                df['MA_20'] = df['Close'].rolling(20).mean()
                df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()
                df['MACD'] = ta.trend.MACD(df['Close']).macd()
                df['Close_Lag1'] = df['Close'].shift(1)
                df['Close_Lag2'] = df['Close'].shift(2)
                df['Close_Lag3'] = df['Close'].shift(3)

                # Drop rows with NaN (from rolling/lag)
                df.dropna(inplace=True)

                # -----------------------------
                # Save Processed CSV
                # -----------------------------
                processed_file_path = os.path.join(processed_market_path, filename)
                df.to_csv(processed_file_path, index=False)

                print(f"✅ Processed {market_folder}/{filename}")