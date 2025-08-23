# utils/database.py

import sqlite3
import pandas as pd

DB_PATH = "data/stock.db"

def insert_processed_data(stock_symbol: str, df: pd.DataFrame):
    conn = sqlite3.connect(DB_PATH)

    # Add stock symbol column
    df["Symbol"] = stock_symbol

    # Write processed data (replace if exists)
    df.to_sql(f"{stock_symbol}_processed", conn, if_exists="replace", index=False)

    conn.close()
    print(f"Inserted processed data for {stock_symbol} into database.")
