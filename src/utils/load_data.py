import os
import pandas as pd

def load_processed_data(stock_symbol: str, market: str = "nse") -> pd.DataFrame:
    """
    Load processed stock data for a given symbol and market (nse/bse).

    Args:
        stock_symbol (str): Ticker symbol of the stock (e.g., 'INFY_NS').
        market (str): Market type, either 'nse' or 'bse'.

    Returns:
        pd.DataFrame: Processed stock data with Date as index.
    """
    # Path to processed data
    file_path = os.path.join("data", "processed", market, f"{stock_symbol}.csv")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Processed file not found: {file_path}")

    # Load CSV
    df = pd.read_csv(file_path, parse_dates=["Date"], index_col="Date")
    return df


# -------------------------
# Run a quick test
# -------------------------
if __name__ == "__main__":
    stock_symbol = "INFY_NS"   # ✅ match your saved file name
    market = "nse"

    try:
        df = load_processed_data(stock_symbol, market)
        print(f"✅ Successfully loaded {stock_symbol} from {market}")
        print("Data sample:")
        print(df.head())
        print("\nColumns:", df.columns.tolist())
    except Exception as e:
        print(f"❌ Error loading data: {e}")
