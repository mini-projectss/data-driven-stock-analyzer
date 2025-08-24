#!/usr/bin/env python3
"""
get_bse500_official.py

Fetch BSE-500 constituents using official BSE CSV download, normalize as <SYMBOL>.BO,
verify each with yfinance, and write validated tickers to tickersbse.txt.

This script is resumable. If stopped, it will continue where it left off.

Usage:
    python get_bse500_official.py
"""

import requests
import pandas as pd
import time
from tqdm import tqdm
import yfinance as yf
import os # --- MODIFICATION: Added for file existence check ---

BSE_CSV_URL = (
    "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
)

# --- MODIFICATION: Changed OUT_FILE to append mode and added a progress log file ---
OUT_FILE = "tickersbse.txt"
PROGRESS_FILE = "verification_progress.log" # Stores every ticker attempted (success or fail)
VERIFY_PAUSE = 0.5

def get_processed_tickers():
    """Reads the progress log and returns a set of tickers already processed."""
    if not os.path.exists(PROGRESS_FILE):
        return set()
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        # Reads the first column (the base symbol, e.g., "RELIANCE")
        return {line.strip().split(',')[0] for line in f}

def download_bse500_csv():
    print("Downloading constituent list...")
    # Using headers to mimic a browser, which can help avoid getting blocked
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    resp = requests.get(BSE_CSV_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.content

def parse_csv(content):
    df = pd.read_csv(pd.io.common.BytesIO(content))
    return df

def verify(symbol):
    """Verifies a single ticker. Returns True on success, False on failure."""
    try:
        # Use a session for potentially faster downloads
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="5d", interval="1d", auto_adjust=True, progress=False)
        return not df.empty
    except Exception as e:
        # Print the error for the specific failing ticker
        print(f"\nCould not verify {symbol}. Error: {e}")
        return False

def main():
    content = download_bse500_csv()
    df = parse_csv(content)
    
    if "Symbol" not in df.columns:
        raise ValueError("CSV format unexpected — no 'Symbol' column found.")
    
    # Get the full list of symbols from the CSV
    all_symbols = set(df["Symbol"].str.strip().str.upper().tolist())
    
    # --- MODIFICATION: Check for already processed symbols ---
    processed_symbols = get_processed_tickers()
    symbols_to_check = sorted([s for s in all_symbols if s not in processed_symbols])

    if not symbols_to_check:
        print("All symbols have already been processed. Nothing to do.")
        return

    print(f"Found {len(processed_symbols)} previously processed tickers. Verifying {len(symbols_to_check)} new tickers.")
    
    # --- MODIFICATION: Open both files in append ('a') mode ---
    with open(OUT_FILE, "a", encoding="utf-8") as f_out, \
         open(PROGRESS_FILE, "a", encoding="utf-8") as f_progress:
        
        valid_count_this_run = 0
        for sym in tqdm(symbols_to_check, desc="Verifying tickers"):
            candidate = sym + ".BO"
            is_valid = verify(candidate)
            
            # --- MODIFICATION: Log every attempt to the progress file ---
            status = "success" if is_valid else "failure"
            f_progress.write(f"{sym},{status}\n")
            f_progress.flush() # Ensure it's written to disk immediately

            if is_valid:
                f_out.write(candidate + "\n")
                f_out.flush() # Ensure it's written to disk immediately
                valid_count_this_run += 1
            
            time.sleep(VERIFY_PAUSE)
            
        print(f"Done. Valid tickers found in this run: {valid_count_this_run}")

if __name__ == "__main__":
    main()