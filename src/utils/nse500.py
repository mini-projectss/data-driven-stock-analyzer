import pandas as pd

def convert_nifty500_to_tickers(input_csv="ind_nifty500list.csv", output_txt="tickers_nifty500.txt"):
    """
    Convert NSE NIFTY 500 symbols from official CSV into Yahoo Finance tickers (.NS)
    and save them to a text file.
    """
    # Read CSV
    df = pd.read_csv(input_csv)

    # Ensure Symbol column exists
    if "Symbol" not in df.columns:
        raise ValueError(f"'Symbol' column not found in {input_csv}")

    # Clean and append .NS
    tickers = df["Symbol"].dropna().astype(str).str.strip().unique()
    tickers = [t + ".NS" for t in tickers]

    # Save to text file
    with open(output_txt, "w") as f:
        for t in tickers:
            f.write(t + "\n")

    print(f"✅ Saved {len(tickers)} tickers to {output_txt}")


if __name__ == "__main__":
    convert_nifty500_to_tickers()
