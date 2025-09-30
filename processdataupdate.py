import os
import pandas as pd
import numpy as np
from tqdm import tqdm

# --- Directory Configuration ---
# Calculate the project root (e.g., data-driven-stock-analyzer). 
# ASSUMPTION: Based on the error traceback, the script is likely located 
# directly in the project's root directory. BASE_DIR is set to the directory 
# where this script file resides.
BASE_DIR = os.path.abspath(os.path.dirname(__file__)) 

# We use the BASE_DIR to construct the paths you specified.
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "historical")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "Processed")

# Ensure the processed output directory exists
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)


def calculate_rsi(df: pd.DataFrame, window=14) -> pd.Series:
    """Calculates the Relative Strength Index (RSI)."""
    # 1. Calculate price change
    delta = df['Close'].diff()
    
    # 2. Separate gains (up) and losses (down)
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    # 3. Calculate Exponential Moving Average (EMA) of gains and losses
    avg_gain = gain.ewm(com=window - 1, min_periods=window).mean()
    avg_loss = loss.ewm(com=window - 1, min_periods=window).mean()

    # 4. Calculate Relative Strength (RS)
    # Handle division by zero for initial periods
    rs = np.where(avg_loss == 0, np.inf, avg_gain / avg_loss)
    
    # 5. Calculate RSI
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(df: pd.DataFrame, fast_period=12, slow_period=26) -> pd.Series:
    """Calculates the Moving Average Convergence Divergence (MACD)."""
    # 1. Calculate EMAs
    exp1 = df['Close'].ewm(span=fast_period, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow_period, adjust=False).mean()
    
    # 2. Calculate MACD Line
    macd = exp1 - exp2
    return macd

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds all technical indicator and lagged features required by the LSTM model.
    """
    # --- Moving Averages ---
    df['MA_5'] = df['Close'].rolling(window=5).mean()
    df['MA_10'] = df['Close'].rolling(window=10).mean()
    df['MA_20'] = df['Close'].rolling(window=20).mean()

    # --- RSI and MACD ---
    df['RSI'] = calculate_rsi(df, window=14)
    df['MACD'] = calculate_macd(df, fast_period=12, slow_period=26)

    # --- Lagged Prices ---
    df['Close_Lag1'] = df['Close'].shift(1)
    df['Close_Lag2'] = df['Close'].shift(2)
    df['Close_Lag3'] = df['Close'].shift(3)

    # Define the required feature columns in the exact order
    features = [
        'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 
        'MA_5', 'MA_10', 'MA_20', 'RSI', 'MACD', 
        'Close_Lag1', 'Close_Lag2', 'Close_Lag3'
    ]
    
    df = df[features].copy()
    
    # Drop initial NaN values created by feature calculations (approx 26 trading days)
    df.dropna(inplace=True) 
    
    return df


def process_all_market_data():
    """
    Iterates through all historical data files (data/historical/<market>) 
    and processes them into data/processed/<MARKET>.
    """
    print("==============================================")
    print("Starting Stock Data Feature Processing")
    print("==============================================")

    # Iterate over market folders (e.g., 'bse', 'nse')
    print(f"[DEBUG] Checking raw data directory: {RAW_DATA_DIR}")
    try:
        market_directories = os.listdir(RAW_DATA_DIR)
    except FileNotFoundError:
        print(f"❌ Error: Raw data directory not found at {RAW_DATA_DIR}")
        print("Please ensure your data/historical folder exists and contains market subfolders (e.g., BSE, NSE).")
        return

    for market in market_directories:
        market_path = os.path.join(RAW_DATA_DIR, market)
        if not os.path.isdir(market_path):
            continue

        print(f"\n--- Processing {market.upper()} Data ---")
        
        # Ensure output directory exists for the market
        processed_market_dir = os.path.join(PROCESSED_DATA_DIR, market.upper())
        os.makedirs(processed_market_dir, exist_ok=True)
        
        stock_files = [f for f in os.listdir(market_path) if f.endswith('.csv')]
        
        for filename in tqdm(stock_files, desc=f"Calculating features for {market.upper()}"):
            raw_csv_path = os.path.join(market_path, filename)
            # The processed filename should match the LSTM model loading logic (uppercase)
            processed_csv_path = os.path.join(processed_market_dir, filename.upper())

            try:
                # 1. Load Raw Data
                df = pd.read_csv(raw_csv_path, parse_dates=['Date'])
                
                # --- FIX: Ensure Numeric Types for Calculation ---
                numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                for col in numeric_cols:
                    # Attempt to convert column to numeric, setting errors='coerce' 
                    # replaces non-numeric values with NaN.
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Drop rows where critical financial data is missing or couldn't be converted
                df.dropna(subset=numeric_cols, inplace=True)
                
                if df.empty:
                    tqdm.write(f"[Warning] {filename}: Data became empty after cleaning/conversion. Skipping.")
                    continue
                # --------------------------------------------------
                
                # 2. Add Required Features
                processed_df = add_features(df.copy())
                
                if processed_df.empty:
                    tqdm.write(f"[Warning] {filename}: Insufficient data for feature calculation after cleaning. Skipping.")
                    continue
                
                # 3. Save Processed Data (Overwrites old processed file)
                processed_df.to_csv(processed_csv_path, index=False)
                tqdm.write(f"[Success] {filename}: Processed and saved {len(processed_df)} rows.")

            except Exception as e:
                tqdm.write(f"\n[Error] Failed to process {filename}. Reason: {e}")

    print("\n==============================================")
    print("✅ All Stock Data Processing Completed.")
    print("==============================================")


if __name__ == "__main__":
    # Execute the processing function
    process_all_market_data()
