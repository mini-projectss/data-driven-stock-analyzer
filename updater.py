import os
import time
from datetime import date, timedelta
import pandas as pd
import yfinance as yf
from tqdm import tqdm

# --- CONFIGURATION ---
# Define the base path to your data directory.
# This assumes the script is run from the project's root folder.
BASE_DATA_PATH = "data/historical"
TICKER_LISTS_PATH = "." # Assumes ticker lists are in the root folder

def get_tickers_from_file(filepath: str) -> list:
    """Reads a list of tickers from a given text file."""
    if not os.path.exists(filepath):
        print(f"[Error] Ticker file not found: {filepath}")
        return []
    try:
        with open(filepath, 'r') as f:
            tickers = [line.strip() for line in f if line.strip()]
        return tickers
    except Exception as e:
        print(f"[Error] Could not read tickers from {filepath}: {e}")
        return []

def get_last_date_from_csv(filepath: str) -> date | None:
    """
    Efficiently reads the last date from a large CSV file.
    Returns the date as a datetime.date object or None if not found.
    """
    if not os.path.exists(filepath):
        return None
    try:
        # Read the file, letting pandas handle potential formatting issues.
        # We only need the 'Date' column to find the last entry.
        df = pd.read_csv(filepath, usecols=['Date'], parse_dates=['Date'], errors='coerce')
        # Drop any rows where date parsing failed
        df.dropna(subset=['Date'], inplace=True)
        if not df.empty:
            # Get the last valid date and return it as a date object
            return df['Date'].iloc[-1].date()
        return None
    except Exception:
        # This can happen if the file is empty, corrupt, or has no 'Date' column
        return None

def update_historical_data(exchange: str, tickers: list):
    """
    Updates all CSV files for a given exchange (BSE or NSE).

    Args:
        exchange (str): The stock exchange ('BSE' or 'NSE').
        tickers (list): A list of ticker symbols to update.
    """
    print(f"\n--- Starting update for {exchange} tickers ---")
    exchange_path = os.path.join(BASE_DATA_PATH, exchange)
    os.makedirs(exchange_path, exist_ok=True)

    # Get today's and yesterday's dates
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Use tqdm for a progress bar
    for ticker in tqdm(tickers, desc=f"Updating {exchange}"):
        csv_path = os.path.join(exchange_path, f"{ticker}.csv")

        # 1. Determine the date range for the download
        last_date = get_last_date_from_csv(csv_path)

        if last_date is None:
            print(f"\n[Warning] No existing data for {ticker}. Skipping update. Please create the initial file first.")
            continue
        
        if last_date >= yesterday:
            # Data is already up-to-date, no need to do anything.
            continue

        start_date_for_download = last_date + timedelta(days=1)
        # yfinance `end` is exclusive, so fetching up to `today` gets data up to `yesterday`.
        end_date_for_download = today

        # 2. Download new data from Yahoo Finance
        try:
            # Add a small delay to be polite to the server
            time.sleep(0.1)
            new_data = yf.download(
                ticker,
                start=start_date_for_download,
                end=end_date_for_download,
                progress=False
            )

            if new_data.empty:
                # No new data was available for this period (e.g., market holidays)
                continue

            # 3. Format and append the new data
            # Reset index to make 'Date' a column
            new_data.reset_index(inplace=True)

            # Ensure 'Date' is in the correct format
            new_data['Date'] = pd.to_datetime(new_data['Date']).dt.strftime('%Y-%m-%d')
            
            # Add the 'Stock' column
            new_data['Stock'] = ticker

            # Ensure column order matches the existing files
            new_data = new_data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Stock']]
            
            # Append to the existing CSV file without writing the header
            new_data.to_csv(csv_path, mode='a', header=False, index=False)
            
            tqdm.write(f"[Success] {ticker}: Added {len(new_data)} new row(s).")

        except Exception as e:
            tqdm.write(f"\n[Error] Could not update data for {ticker}. Reason: {e}")

    print(f"--- {exchange} update complete ---")

def run_update():
    """Main function to run the update process for both exchanges."""
    print("==============================================")
    print("Starting Historical Stock Data Update Process")
    print(f"Today's Date: {date.today().strftime('%Y-%m-%d')}")
    print("==============================================")
    
    # Update BSE tickers
    bse_tickers_file = os.path.join(TICKER_LISTS_PATH, "tickersbse.txt")
    bse_tickers = get_tickers_from_file(bse_tickers_file)
    if bse_tickers:
        update_historical_data("BSE", bse_tickers)

    # Update NSE tickers
    nse_tickers_file = os.path.join(TICKER_LISTS_PATH, "tickersnse.txt")
    nse_tickers = get_tickers_from_file(nse_tickers_file)
    if nse_tickers:
        update_historical_data("NSE", nse_tickers)

    print("\nAll updates finished.")

if __name__ == "__main__":
    # This allows the script to be run directly from the command line
    run_update()