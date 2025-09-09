import os
import time
from datetime import date, timedelta, datetime
import pandas as pd
import yfinance as yf
from tqdm import tqdm

# --- CONFIGURATION ---
# Define the base path to your data directory.
# This assumes the script is run from the project's root folder.
BASE_DATA_PATH = "data/historical"
TICKER_LISTS_PATH = "." # Assumes ticker lists are in the root folder
DEFAULT_START_DATE = date(2020, 1, 1) # Default start date for new files

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
    except (pd.errors.EmptyDataError, ValueError):
        # Handle cases where the file is empty or the 'Date' column is problematic
        return None
    except Exception:
        # Catch other potential exceptions
        return None

def update_historical_data(exchange: str, tickers: list):
    """
    Updates all existing CSV files for a given exchange (BSE or NSE).
    If a file is empty or unreadable, it will be populated with full history.
    This function will NOT create new files if they are completely missing.

    Args:
        exchange (str): The stock exchange ('BSE' or 'NSE').
        tickers (list): A list of ticker symbols to update.
    """
    print(f"\n--- Starting update for {exchange} tickers ---")
    exchange_path = os.path.join(BASE_DATA_PATH, exchange)
    
    # Check if the directory exists.
    if not os.path.isdir(exchange_path):
        print(f"[Error] Directory for {exchange} not found at: {exchange_path}")
        print(f"--- {exchange} update skipped ---")
        return

    # Get today's and yesterday's dates
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Use tqdm for a progress bar
    for ticker in tqdm(tickers, desc=f"Updating {exchange}"):
        # Convert ticker format (e.g., 3MINDIA.BO) to filename format (3MINDIA_BO.csv)
        filename = f"{ticker.replace('.', '_')}.csv"
        csv_path = os.path.join(exchange_path, filename)

        # --- CORE LOGIC: Skip only if the file is completely missing ---
        if not os.path.exists(csv_path):
            tqdm.write(f"[Warning] No data file for '{ticker}' (looked for {filename}). Skipping creation.")
            continue

        # 1. Determine the date range for the download
        last_date = get_last_date_from_csv(csv_path)
        
        # This flag will determine if we need to overwrite the file (w) or append (a)
        is_empty_or_corrupt = (last_date is None)

        if is_empty_or_corrupt:
            # File exists but is empty/unreadable. We will re-populate it.
            start_date_for_download = DEFAULT_START_DATE
            tqdm.write(f"[Info] File for '{ticker}' is empty/unreadable. Repopulating from {start_date_for_download}.")
        else:
            # File has valid data. Check if it's already up-to-date.
            if last_date >= yesterday:
                continue # Skip if already up-to-date
            start_date_for_download = last_date + timedelta(days=1)

        # yfinance `end` is exclusive, so fetching up to `today` gets data up to `yesterday`.
        end_date_for_download = today

        # 2. Download new data from Yahoo Finance
        try:
            time.sleep(0.1) # Be polite to the server
            new_data = yf.download(
                ticker,
                start=start_date_for_download,
                end=end_date_for_download,
                progress=False
            )

            if new_data.empty:
                continue # No new data was available

            # 3. Format the new data
            new_data.reset_index(inplace=True)
            new_data['Date'] = pd.to_datetime(new_data['Date']).dt.strftime('%Y-%m-%d')
            new_data['Stock'] = ticker
            new_data = new_data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Stock']]
            
            # 4. Save the data: Overwrite if the file was empty, otherwise append
            if is_empty_or_corrupt:
                # Overwrite the empty/corrupt file with the full historical data
                new_data.to_csv(csv_path, mode='w', header=True, index=False)
                tqdm.write(f"[Success] {ticker}: Repopulated empty file with {len(new_data)} row(s).")
            else:
                # Append new data to the existing valid file
                new_data.to_csv(csv_path, mode='a', header=False, index=False)
                tqdm.write(f"[Success] {ticker}: Appended {len(new_data)} new row(s).")

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

