# data/preprocess.py

import pandas as pd
import os
from sklearn.preprocessing import MinMaxScaler
import joblib
import ta

# Paths
RAW_DATA_DIR = r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\historical"
PROCESSED_DATA_DIR = r"C:\Users\Sunnyy\OneDrive\Desktop\data-driven-stock-analyzer\data\processed"

# Make sure processed folder exists
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

# Loop through NSE and BSE folders
for market_folder in os.listdir(RAW_DATA_DIR):
    market_path = os.path.join(RAW_DATA_DIR, market_folder)
    if os.path.isdir(market_path):
        processed_market_path = os.path.join(PROCESSED_DATA_DIR, market_folder)
        os.makedirs(processed_market_path, exist_ok=True)

        # Loop through each CSV in the market folder
        for filename in os.listdir(market_path):
            if filename.endswith(".csv"):
                file_path = os.path.join(market_path, filename)
                df = pd.read_csv(file_path)

                # Convert Date column to datetime
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                df.sort_values('Date', inplace=True)  # Ensure chronological order

                # Filter rows from 2015 onward
                df = df[df['Date'].dt.year >= 2015]

                # 1️⃣ Ensure numeric columns are numeric
                numeric_cols = ['Open','High','Low','Close','Volume']
                for col in numeric_cols:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                # Fill missing values
                df.ffill(inplace=True)

                # 2️⃣ Feature Engineering
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

                # 3️⃣ Scaling
                scaler = MinMaxScaler()
                scaled_cols = ['Open','High','Low','Close','Volume','MA_5','MA_10','MA_20','RSI','MACD',
                               'Close_Lag1','Close_Lag2','Close_Lag3']
                df[scaled_cols] = scaler.fit_transform(df[scaled_cols])

                # 4️⃣ Save Processed CSV
                processed_file_path = os.path.join(processed_market_path, filename)
                df.to_csv(processed_file_path, index=False)

                # Save scaler for this stock
                joblib.dump(scaler, processed_file_path.replace(".csv", "_scaler.pkl"))

                print(f"✅ Processed {market_folder}/{filename}")
