import os
import pandas as pd
import yfinance as yf
from datetime import datetime
from tqdm import tqdm
import time

# --- Configuration ---
TICKERS_FILE = 'tickersbse.txt'
OUTPUT_DIR = 'BSE_Stock_Data_2020_to_Present'
START_DATE = '2020-01-01'
# Automatically get today's date as the end date
END_DATE = datetime.today().strftime('%Y-%-m-%d')

# --- Main Script ---

def read_tickers(file_path):
    """Reads tickers from a text file, one per line."""
    try:
        with open(file_path, 'r') as f:
            # Read tickers and remove any leading/trailing whitespace
            tickers = [line.strip() for line in f if line.strip()]
        if not tickers:
            print(f"Error: The file '{file_path}' is empty or contains no valid tickers.")
            return None
        return tickers
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        print("Please create this file and add your BSE ticker symbols, one on each line.")
        return None

def download_and_process_data(tickers):
    """
    Downloads, processes, and saves historical stock data for a list of tickers.
    """
    if not tickers:
        return

    # Create the output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Data will be saved in the '{OUTPUT_DIR}' directory.")

    failed_tickers = []
    
    # Use tqdm for a progress bar
    for ticker in tqdm(tickers, desc="Downloading BSE Data"):
        try:
            # === FIX STARTS HERE ===
            # Check if the ticker already has the .BO suffix to avoid duplication (e.g., RELIANCE.BO.BO)
            if ticker.upper().endswith('.BO'):
                yahoo_ticker = ticker
            else:
                yahoo_ticker = f"{ticker}.BO"
            
            # Download historical data
            # Set auto_adjust=False to get the 'Close' and 'Adj Close' columns separately.
            # This also resolves the FutureWarning message.
            data = yf.download(yahoo_ticker, 
                               start=START_DATE, 
                               end=END_DATE,
                               auto_adjust=False, # Explicitly added
                               progress=False) # Disable yfinance's own progress bar
            # === FIX ENDS HERE ===

            # --- Pre-processing Steps ---
            if data.empty:
                print(f"\nWarning: No data found for {ticker} ({yahoo_ticker}). It might be a delisted or invalid ticker.")
                failed_tickers.append(ticker)
                continue

            # 1. Reset index to make 'Date' a column instead of an index
            data.reset_index(inplace=True)

            # 2. Add the 'Stock' ticker column (using the original name from the file)
            data['Stock'] = ticker

            # 3. Select and reorder columns as per the requirement
            required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Stock']
            
            # Check if all required columns exist
            if not all(col in data.columns for col in required_columns):
                 print(f"\nWarning: Data for {ticker} is missing some columns. Skipping.")
                 failed_tickers.append(ticker)
                 continue

            data = data[required_columns]

            # 4. Handle any potential missing values in rows
            data.dropna(inplace=True)
            
            # 5. Ensure Date is in the correct format (YYYY-MM-DD)
            data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')

            # --- Save to CSV ---
            # Sanitize the original ticker name for use in a filename
            safe_ticker_name = ticker.replace('.','_')
            output_filename = f"{safe_ticker_name}.csv"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            data.to_csv(output_path, index=False)
            
            # Small delay to be polite to the API provider
            time.sleep(0.1)

        except Exception as e:
            print(f"\nError downloading or processing data for {ticker}: {e}")
            failed_tickers.append(ticker)
            continue

    print("\n----- Download Complete! -----")
    if failed_tickers:
        print("\nThe following tickers could not be downloaded or were empty:")
        print(", ".join(failed_tickers))
    else:
        print("All tickers were downloaded successfully.")


if __name__ == '__main__':
    print("Starting BSE historical data downloader...")
    bse_tickers = read_tickers(TICKERS_FILE)
    if bse_tickers:
        download_and_process_data(bse_tickers)