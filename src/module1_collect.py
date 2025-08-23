import os
import time
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine

# -------- CONFIG --------
TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "ITC.NS", "LT.NS", "SBIN.NS", "BHARTIARTL.NS", "HINDUNILVR.NS"
]
START_DATE = "2015-01-01"   # adjust if needed
END_DATE = None             # None = today
DATA_DIR = os.path.join("data", "raw")
DB_PATH = os.path.join("data", "stocks.db")
# ------------------------

# Create folders if not exist
os.makedirs(DATA_DIR, exist_ok=True)

# SQLite engine
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

def download_stock_data(ticker: str) -> pd.DataFrame:
    """Download daily stock data from Yahoo Finance"""
    df = yf.download(ticker, start=START_DATE, end=END_DATE, interval="1d", progress=False)
    if df.empty:
        print(f"[WARN] No data for {ticker}")
        return df
    df.reset_index(inplace=True)
    df["Ticker"] = ticker
    return df

def save_to_csv(df: pd.DataFrame, ticker: str):
    """Save stock data to CSV"""
    filename = os.path.join(DATA_DIR, f"{ticker.replace('.NS','')}.csv")
    df.to_csv(filename, index=False)
    print(f"[OK] Saved CSV: {filename}")

def save_to_sqlite(df: pd.DataFrame, ticker: str):
    """Save stock data to SQLite (one table per ticker)"""
    table_name = f"daily_{ticker.replace('.','_').lower()}"
    df.to_sql(table_name, engine, if_exists="replace", index=False)
    print(f"[OK] Saved to SQLite table: {table_name}")

def main():
    all_data = []
    for i, ticker in enumerate(TICKERS, 1):
        print(f"[{i}/{len(TICKERS)}] Fetching {ticker}...")
        df = download_stock_data(ticker)
        if df.empty:
            continue
        save_to_csv(df, ticker)
        save_to_sqlite(df, ticker)
        all_data.append(df)
        time.sleep(1)  # polite delay
    
    # Combined table with all tickers
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined.to_sql("daily_all", engine, if_exists="replace", index=False)
        print("[OK] Combined table saved: daily_all")

if __name__ == "__main__":
    main()
