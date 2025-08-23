import os
import pandas as pd
import sqlite3
import logging

# Set up logging to a file
logging.basicConfig(filename="stock_data_processing.log", level=logging.INFO, format="%(asctime)s - %(message)s")

# Paths
RAW_DATA_DIR = os.path.join("data", "raw")
PROCESSED_DATA_DIR = os.path.join("data", "processed")
DB_PATH = "stocks.db"

# Make sure processed folder exists
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

def clean_stock_data(file_path, stock_name):
    """Read and clean stock CSV file"""
    try:
        df = pd.read_csv(file_path)
        
        # Standardize column names (lowercase, strip spaces)
        df.columns = [col.strip().lower() for col in df.columns]

        # Ensure 'date' column exists and convert to datetime
        if 'date' not in df.columns:
            raise ValueError(f"'date' column missing in {file_path}")
        
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])  # Drop rows where date conversion failed
        
        # Sort by date
        df = df.sort_values(by='date').reset_index(drop=True)
        
        # Keep only useful columns if present
        keep_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        df = df[[col for col in keep_cols if col in df.columns]]
        
        # Handle missing values (forward fill)
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        # Add stock name column
        df['stock'] = stock_name.upper()
        
        return df
    except Exception as e:
        logging.error(f"❌ Error cleaning {file_path}: {e}")
        return None

def save_to_csv(df, stock_name):
    """Save cleaned dataframe to processed folder"""
    out_path = os.path.join(PROCESSED_DATA_DIR, f"{stock_name}_clean.csv")
    df.to_csv(out_path, index=False)
    logging.info(f"✅ Saved cleaned CSV: {out_path}")

def save_to_db(df, conn):
    """Save cleaned dataframe to SQLite database"""
    df.to_sql("stocks_cleaned", conn, if_exists="append", index=False)

def main():
    try:
        conn = sqlite3.connect(DB_PATH)
        
        # Clear old table if exists
        conn.execute("DROP TABLE IF EXISTS stocks_cleaned;")
        
        for file in os.listdir(RAW_DATA_DIR):
            if file.endswith(".csv"):
                stock_name = file.replace(".csv", "").upper()
                file_path = os.path.join(RAW_DATA_DIR, file)
                
                logging.info(f"\n📂 Processing {file}...")
                df = clean_stock_data(file_path, stock_name)
                
                if df is not None:
                    save_to_csv(df, stock_name)
                    save_to_db(df, conn)
                else:
                    logging.warning(f"⚠️ Skipped {file} due to errors during cleaning.")
            else:
                logging.warning(f"⚠️ Non-CSV file detected: {file}. Skipping.")

    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")
    
    finally:
        conn.close()
        logging.info("\n🎉 All stocks processed and saved in data/processed/ and stocks.db")

if __name__ == "__main__":
    main()
