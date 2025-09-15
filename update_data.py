import pandas as pd
import yfinance as yf
import os
from tqdm import tqdm

# --- Configuration ---
DATA_PATH = 'data'
HISTORICAL_PATH = os.path.join(DATA_PATH, 'historical')
PROCESSED_PATH = os.path.join(DATA_PATH, 'processed')

# --- Pre-processing Functions ---

def preprocess_for_prophet(df, filename_ticker):
    """Prepares and saves four dataframes for Prophet, one for each OHLC value."""
    df_prophet = df.copy()
    df_prophet.reset_index(inplace=True)
    df_prophet.rename(columns={'Date': 'ds'}, inplace=True)
    
    for column in ['Open', 'High', 'Low', 'Close']:
        df_single_value = df_prophet[['ds', column]].rename(columns={column: 'y'})
        output_path = os.path.join(PROCESSED_PATH, 'prophet', f'{filename_ticker}_{column.lower()}.csv')
        df_single_value.to_csv(output_path, index=False)

def preprocess_for_lightgbm(df, filename_ticker):
    """Prepares and saves a dataframe for LightGBM with features for OHLC prediction."""
    df_lgbm = df.copy()
    
    df_lgbm['MA_7_Close'] = df_lgbm['Close'].rolling(window=7).mean()
    df_lgbm['MA_30_Close'] = df_lgbm['Close'].rolling(window=30).mean()
    df_lgbm['Lag_1_Close'] = df_lgbm['Close'].shift(1)
    
    df_lgbm.dropna(inplace=True)
    
    output_path = os.path.join(PROCESSED_PATH, 'lightgbm', f'{filename_ticker}.csv')
    df_lgbm.to_csv(output_path)

def run_update():
    """Main function to update historical data and trigger pre-processing."""
    with open('tickersbse.txt', 'r') as f:
        bse_tickers = [line.strip() for line in f.readlines()]
    with open('tickersnse.txt', 'r') as f:
        nse_tickers = [line.strip() for line in f.readlines()]
    all_tickers = bse_tickers + nse_tickers
    
    # --- UPGRADE: Added tqdm for a progress bar ---
    for ticker in tqdm(all_tickers, desc="Updating and Processing Tickers"):
        
        filename_ticker = ticker.replace('.', '_')
        exchange = 'BSE' if ticker.endswith('.BO') else 'NSE'
        file_path = os.path.join(HISTORICAL_PATH, exchange, f'{filename_ticker}.csv')

        if not os.path.exists(file_path):
            continue
            
        historical_df = pd.read_csv(file_path, index_col='Date', parse_dates=True)
        
        ohlc_columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        for col in ohlc_columns:
            if col in historical_df.columns:
                historical_df[col] = pd.to_numeric(historical_df[col], errors='coerce')
        
        historical_df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
        
        new_data = yf.download(ticker, period="5d", progress=False, auto_adjust=True)
        
        # --- FIX: Clean and standardize column names from yfinance download ---
        if isinstance(new_data.columns, pd.MultiIndex):
            new_data.columns = new_data.columns.droplevel(1) # Drop the ticker level
        # Ensure new_data has the same simple column structure
        new_data = new_data[['Open', 'High', 'Low', 'Close', 'Volume']]

        original_rows = len(historical_df)
        historical_df = pd.concat([historical_df, new_data[~new_data.index.isin(historical_df.index)]])
        
        if len(historical_df) > original_rows:
            historical_df.sort_index(inplace=True)
            historical_df.to_csv(file_path)

        preprocess_for_prophet(historical_df, filename_ticker)
        preprocess_for_lightgbm(historical_df, filename_ticker)

if __name__ == "__main__":
    os.makedirs(os.path.join(PROCESSED_PATH, 'prophet'), exist_ok=True)
    os.makedirs(os.path.join(PROCESSED_PATH, 'lightgbm'), exist_ok=True)
    run_update()