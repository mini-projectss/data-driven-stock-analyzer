#!/usr/bin/env python3
"""
updater.py - Robust updater for BSE/NSE historical CSVs (fixed header-dropping bug)

This is a full, drop-in script that:
- robustly reads/repairs malformed CSVs (encodings, delimiters, header-as-data, multiindex-like columns)
- normalizes files to canonical format: Date,Open,High,Low,Close,Volume,Stock
- correctly handles yfinance date window (end is exclusive -> end = today + 1)
- extracts OHLCV from yfinance responses even when columns are MultiIndex-like
- merges only truly new dates and reports merged counts
- IMPORTANT FIX: header-as-data detection will NOT drop rows where a valid Date is present,
  preventing accidental deletion of early historical rows (the issue you reported).
"""
from __future__ import annotations
import os
import time
import csv
import re
import argparse
from datetime import date, timedelta
import pandas as pd
import yfinance as yf
from tqdm import tqdm

# ---------- CONFIG ----------
BASE_DATA_PATH = "data/historical"
DEFAULT_START_DATE = date(2020, 1, 1)
EXPECTED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume", "Stock"]

# ---------- Utilities: flexible file read ----------
def try_read_lines(filepath, encodings=("utf-8-sig", "utf-8", "latin-1"), max_lines=120):
    for enc in encodings:
        try:
            lines = []
            with open(filepath, "r", encoding=enc, errors="replace") as fh:
                for _ in range(max_lines):
                    try:
                        lines.append(next(fh).rstrip("\n"))
                    except StopIteration:
                        break
            return lines, enc
        except Exception:
            continue
    return [], None

def detect_delimiter(sample_text):
    try:
        s = "\n".join(sample_text)
        dialect = csv.Sniffer().sniff(s, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except Exception:
        return ","

def read_csv_flexible(filepath):
    """Return (df_or_None, date_col_or_None, debug_info)"""
    debug = {"filepath": filepath, "attempts": []}
    if not os.path.exists(filepath):
        debug["attempts"].append("file-not-found")
        return None, None, debug

    sample, enc = try_read_lines(filepath, max_lines=120)
    debug["sample_encoding"] = enc
    debug["sample_preview"] = sample[:8]
    delim = detect_delimiter(sample) if sample else ","
    debug["detected_delimiter"] = delim

    candidates = [
        ("utf-8-sig", "c"),
        ("utf-8", "c"),
        ("latin-1", "c"),
        ("utf-8-sig", "python"),
        ("utf-8", "python"),
        ("latin-1", "python"),
    ]
    for enc_try, engine in candidates:
        try:
            df = pd.read_csv(filepath, encoding=enc_try, engine=engine, delimiter=delim)
            debug["attempts"].append(f"read-success encoding={enc_try} engine={engine} shape={df.shape}")
            df.columns = [str(c).strip() for c in df.columns]
            # detect date-like column
            date_col = None
            for c in df.columns:
                if isinstance(c, str) and ("date" == c.strip().lower() or "date" in c.strip().lower()):
                    date_col = c
                    break
            if date_col is None and df.shape[1] >= 1:
                try:
                    parsed = pd.to_datetime(df.iloc[:, 0], errors="coerce", dayfirst=False)
                    if parsed.notna().any():
                        date_col = df.columns[0]
                except Exception:
                    pass
            return df, date_col, debug
        except Exception as e:
            debug["attempts"].append(f"failed encoding={enc_try} engine={engine} err={e}")
            continue

    # tail-scan fallback: look for any date-like token
    debug["attempts"].append("tail-scan-fallback")
    try:
        with open(filepath, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            read_size = min(8192, size)
            f.seek(max(0, size - read_size))
            chunk = f.read(read_size).decode("utf-8", errors="ignore")
            lines = chunk.splitlines()
            for line in reversed(lines):
                if not line.strip(): continue
                parts = list(csv.reader([line], delimiter=delim))[0]
                for cell in parts:
                    try:
                        dt = pd.to_datetime(cell.strip(), errors="coerce")
                        if pd.notna(dt):
                            debug["tail_found_date"] = str(dt.date())
                            return None, None, debug
                    except Exception:
                        continue
    except Exception as e:
        debug["attempts"].append(f"tail-scan-exception:{e}")

    return None, None, debug

# ---------- Normalization (with safer header detection) ----------
def flatten_column_name(col):
    if isinstance(col, (tuple, list)):
        parts = [str(p).strip() for p in col if p is not None and str(p).strip() != ""]
        return "_".join(parts) if parts else str(col)
    s = str(col)
    m = re.match(r"^\(?['\"]?([^'\",)]+)['\"]?(?:,\s*['\"]?([^'\",)]+)['\"]?)?\)?$", s)
    if m:
        return m.group(1).strip()
    return s.strip()

def row_has_valid_date(row, date_col_candidates):
    """
    Given a pandas Series row and list of candidate column names to treat as date,
    return True if any candidate cell in the row parses to a valid date.
    """
    for c in date_col_candidates:
        if c in row.index:
            try:
                val = row.get(c)
                if pd.isna(val):
                    continue
                dt = pd.to_datetime(val, errors="coerce", dayfirst=False)
                if pd.notna(dt):
                    return True
            except Exception:
                continue
    # fallback: try first cell
    try:
        val = row.iloc[0]
        dt = pd.to_datetime(val, errors="coerce", dayfirst=False)
        return pd.notna(dt)
    except Exception:
        return False

def normalize_existing_df(df: pd.DataFrame | None, ticker_hint: str | None = None) -> pd.DataFrame | None:
    """
    Return cleaned df with EXPECTED_COLUMNS or None if unusable.

    IMPORTANT: header-as-data detection is conservative and will NOT remove rows where
    any date-like value is present in that row. This prevents removal of legitimate early rows.
    """
    if df is None or df.shape[0] == 0:
        return None
    df = df.copy()
    df.columns = [flatten_column_name(c) for c in df.columns]

    # detect possible date-like column candidates early
    date_candidates = [c for c in df.columns if isinstance(c, str) and ("date" in c.lower())]
    if not date_candidates and df.shape[1] >= 1:
        date_candidates = [df.columns[0]]

    # Detect and drop header-like rows near top (but only if that row does NOT contain a valid date)
    header_like_rows = []
    for idx, row in df.head(6).iterrows():
        # If the row has a valid date in any candidate cell, treat it as real data -> skip marking it header-like
        if row_has_valid_date(row, date_candidates):
            continue

        non_empty = 0
        match_count = 0
        for c in df.columns:
            if isinstance(c, str) and c.lower() == "date":
                continue
            val = row.get(c)
            if pd.isna(val) or str(val).strip() == "":
                continue
            non_empty += 1
            s = str(val).strip()
            # heuristic: cell equals column name or contains ticker hint or looks like uppercase ticker/symbol
            if s == c or (ticker_hint and ticker_hint in s) or (s.upper() == s and len(s) > 1 and all(ch.isalnum() or ch in ".-" for ch in s)):
                match_count += 1
        if non_empty > 0 and match_count >= max(1, non_empty // 2):
            header_like_rows.append(idx)
    if header_like_rows:
        df = df.drop(index=header_like_rows)

    # Ensure Date exists; if not, assume first column is Date
    if "Date" not in df.columns and df.shape[1] >= 1:
        df.rename(columns={df.columns[0]: "Date"}, inplace=True)

    if "Date" not in df.columns:
        return None

    # Parse Date strictly then fallback
    df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="coerce")
    if df["Date"].isna().all():
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=False)
    df = df.dropna(subset=["Date"])
    if df.empty:
        return None

    # Map other columns or create empty ones
    for col in ["Open", "High", "Low", "Close", "Volume", "Stock"]:
        if col not in df.columns:
            found = None
            for c in df.columns:
                if col.lower() in c.lower():
                    found = c
                    break
            if found:
                df.rename(columns={found: col}, inplace=True)
            else:
                df[col] = pd.NA

    # Ensure exact expected columns (creates missing columns instead of KeyError)
    df = df.reindex(columns=EXPECTED_COLUMNS)

    # Coerce numeric columns
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Stock normalization
    df["Stock"] = df["Stock"].astype(str).replace("nan", "")
    if (df["Stock"] == "").all() and ticker_hint:
        df["Stock"] = ticker_hint

    # Format date & dedupe
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    df = df.drop_duplicates(subset=["Date"], keep="last").sort_values("Date").reset_index(drop=True)
    return df

# ---------- YFinance Helpers ----------
def flatten_df_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten MultiIndex-like column names into single strings."""
    df = df.copy()
    new_cols = []
    for col in df.columns:
        if isinstance(col, tuple):
            parts = [str(p) for p in col if p is not None and str(p) != ""]
            new_cols.append("_".join(parts))
        else:
            new_cols.append(str(col))
    df.columns = new_cols
    return df

def extract_expected_from_yf(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """
    Convert a yfinance reset_index DataFrame into canonical EXPECTED_COLUMNS DataFrame.
    Handles columns like 'Open', 'Open_3MINDIA.BO', or ('Open','3MINDIA.BO').
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    df = flatten_df_columns(df)

    # Ensure Date exists
    if "Date" not in df.columns:
        try:
            tmp = df.reset_index()
            if "Date" in tmp.columns:
                df = tmp
        except Exception:
            pass
    if "Date" not in df.columns:
        # try first date-like column
        found_date = None
        for c in df.columns:
            try:
                tmp = pd.to_datetime(df[c], errors="coerce")
                if tmp.notna().any():
                    found_date = c
                    break
            except Exception:
                continue
        if found_date is None:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)
        df["Date"] = pd.to_datetime(df[found_date], errors="coerce")

    res = pd.DataFrame()
    res["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")

    def find_col(target):
        if target in df.columns:
            return target
        cand = f"{target}_{ticker}"
        if cand in df.columns:
            return cand
        cand2 = f"{target}_{ticker.replace('.', '_')}"
        if cand2 in df.columns:
            return cand2
        # prefer short column names containing target
        for c in df.columns:
            if target.lower() in c.lower() and len(c) <= 80:
                return c
        return None

    for target in ["Open", "High", "Low", "Close", "Volume"]:
        colname = find_col(target)
        if colname:
            try:
                res[target] = pd.to_numeric(df[colname], errors="coerce")
            except Exception:
                res[target] = pd.to_numeric(df[colname].astype(str).str.replace(",", ""), errors="coerce")
        else:
            # sometimes yfinance returns adjusted and close only; attempt fallbacks
            res[target] = pd.NA

    res["Stock"] = ticker
    res = res.reindex(columns=EXPECTED_COLUMNS)
    res = res.dropna(subset=["Date"]).drop_duplicates(subset=["Date"], keep="last").reset_index(drop=True)
    return res

# ---------- Last-date detection ----------
def get_last_date_from_csv(filepath: str, debug: bool = False):
    df, date_col, debug_info = read_csv_flexible(filepath)
    if df is None:
        if debug:
            return None, debug_info
        return None
    try:
        if date_col is not None and date_col in df.columns:
            s = pd.to_datetime(df[date_col], format="%Y-%m-%d", errors="coerce")
            if s.isna().all():
                s = pd.to_datetime(df[date_col], errors="coerce", dayfirst=False)
            s = s.dropna()
            if not s.empty:
                last = s.max().date()
                if debug:
                    debug_info["detected_date_col"] = date_col
                    debug_info["last_date"] = str(last)
                    return last, debug_info
                return last
        s = pd.to_datetime(df.iloc[:, 0], format="%Y-%m-%d", errors="coerce")
        if s.isna().all():
            s = pd.to_datetime(df.iloc[:, 0], errors="coerce", dayfirst=False)
        s = s.dropna()
        if not s.empty:
            last = s.max().date()
            if debug:
                debug_info["detected_date_col"] = df.columns[0]
                debug_info["last_date"] = str(last)
                return last, debug_info
            return last
    except Exception as e:
        debug_info = debug_info or {}
        debug_info["last_date_error"] = str(e)
        if debug:
            return None, debug_info
        return None
    if debug:
        return None, debug_info
    return None

# ---------- Core updater ----------
def update_historical_data(exchange: str, tickers: list[str], debug_mode: bool = False, create_missing: bool = False):
    print(f"\n--- Starting update for {exchange} ({len(tickers)} tickers) ---")
    exchange_path = os.path.join(BASE_DATA_PATH, exchange)
    if not os.path.isdir(exchange_path):
        print(f"[Error] Directory for {exchange} not found at: {exchange_path}")
        return

    today = date.today()
    end_exclusive_for_yfinance = today + timedelta(days=1)

    for ticker in tqdm(tickers, desc=f"Updating {exchange}"):
        filename = f"{ticker.replace('.', '_')}.csv"
        csv_path = os.path.join(exchange_path, filename)

        if not os.path.exists(csv_path):
            if create_missing:
                pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(csv_path, index=False)
                tqdm.write(f"[Info] Created missing file for '{ticker}' at {csv_path}")
            else:
                tqdm.write(f"[Warning] No data file for '{ticker}' (looked for {filename}). Skipping.")
                continue

        # read raw & normalize (auto-apply repair)
        existing_raw, _, debug_info = read_csv_flexible(csv_path)
        existing_clean = None
        try:
            if existing_raw is not None:
                fname = os.path.basename(csv_path)
                ticker_hint = None
                if fname.endswith("_BO.csv") or fname.endswith("_NS.csv"):
                    ticker_hint = fname.rsplit(".", 1)[0].replace("_", ".")
                existing_clean = normalize_existing_df(existing_raw, ticker_hint=ticker_hint)
                if existing_clean is not None:
                    try:
                        existing_clean = existing_clean.reindex(columns=EXPECTED_COLUMNS)
                        existing_clean.to_csv(csv_path, index=False, header=EXPECTED_COLUMNS)
                        if debug_mode:
                            tqdm.write(f"[Debug] {ticker}: cleaned canonical written ({len(existing_clean)} rows)")
                    except Exception as e:
                        tqdm.write(f"[Warning] {ticker}: cleaned present but failed write: {e}")
        except Exception as e:
            tqdm.write(f"[Warning] {ticker}: normalization threw: {e}")
            existing_clean = None

        # determine last date
        last_date_result = None
        if existing_clean is not None and not existing_clean.empty:
            try:
                last_date_result = pd.to_datetime(existing_clean["Date"], errors="coerce").max().date()
            except Exception:
                last_date_result = None
        else:
            if debug_mode:
                last_date_result, dbg = get_last_date_from_csv(csv_path, debug=True)
                tqdm.write(f"[Debug] {ticker}: last_date fallback: {dbg}")
            else:
                last_date_result = get_last_date_from_csv(csv_path, debug=False)

        is_empty_or_corrupt = last_date_result is None
        if is_empty_or_corrupt:
            start_date_for_download = DEFAULT_START_DATE
            tqdm.write(f"[Info] {ticker}: unreadable/missing valid dates; will repopulate from {start_date_for_download}")
        else:
            start_date_for_download = last_date_result + timedelta(days=1)

        # skip empty request (end exclusive)
        if start_date_for_download >= end_exclusive_for_yfinance:
            continue

        # fetch from yfinance
        try:
            time.sleep(0.02)
            if debug_mode:
                tqdm.write(f"[Debug] {ticker}: requesting start={start_date_for_download} end(exclusive)={end_exclusive_for_yfinance}")
            raw = yf.download(
                ticker,
                start=start_date_for_download,
                end=end_exclusive_for_yfinance,
                progress=False,
                auto_adjust=False,
            )
            if raw is None or raw.empty:
                tqdm.write(f"[Info] {ticker}: No new data returned for {start_date_for_download} -> {end_exclusive_for_yfinance - timedelta(days=1)}.")
                continue

            raw_reset = raw.reset_index()
            new_df = extract_expected_from_yf(raw_reset, ticker)
            if new_df.empty:
                tqdm.write(f"[Info] {ticker}: yfinance returned rows but none parsed to canonical columns.")
                continue

            existing_dates = set(existing_clean["Date"]) if existing_clean is not None else set()
            new_dates_all = set(new_df["Date"].astype(str))
            new_dates_to_add = sorted(d for d in new_dates_all if d not in existing_dates)
            merged_count = len(new_dates_to_add)

            if existing_clean is None:
                to_write = new_df.drop_duplicates(subset=["Date"], keep="last").reset_index(drop=True)
                to_write = to_write.reindex(columns=EXPECTED_COLUMNS)
                to_write.to_csv(csv_path, index=False, header=EXPECTED_COLUMNS)
                tqdm.write(f"[Success] {ticker}: Wrote {len(to_write)} rows (created canonical).")
            else:
                if merged_count == 0:
                    # still rewrite canonical to keep formatting stable
                    existing_clean.to_csv(csv_path, index=False, header=EXPECTED_COLUMNS)
                    tqdm.write(f"[Success] {ticker}: Merged 0 new rows. File now {len(existing_clean)} rows.")
                else:
                    to_append = new_df[new_df["Date"].isin(new_dates_to_add)].copy()
                    combined = pd.concat([existing_clean, to_append], ignore_index=True, sort=False)
                    combined = combined.reindex(columns=EXPECTED_COLUMNS)
                    combined["Date"] = pd.to_datetime(combined["Date"], errors="coerce")
                    combined = combined.dropna(subset=["Date"])
                    combined = combined.drop_duplicates(subset=["Date"], keep="last").sort_values("Date").reset_index(drop=True)
                    combined["Date"] = combined["Date"].dt.strftime("%Y-%m-%d")
                    combined.to_csv(csv_path, index=False, header=EXPECTED_COLUMNS)
                    tqdm.write(f"[Success] {ticker}: Merged {merged_count} new rows. File now {len(combined)} rows.")
            if debug_mode:
                tqdm.write(f"[Debug] {ticker}: yfinance raw rows={len(raw)} parsed new rows={len(new_df)} adding={merged_count}")
        except Exception as e:
            tqdm.write(f"[Error] Could not update data for {ticker}. Reason: {e}")

    print(f"--- {exchange} update complete ---")

# ---------- Helpers / Runner ----------
def get_tickers_from_file(filepath: str) -> list[str]:
    if not os.path.exists(filepath):
        print(f"[Error] ticker file not found: {filepath}")
        return []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        return [line.strip() for line in f if line.strip()]

def run_update(exchange_filter: str | None = None, debug_mode: bool = False, create_missing: bool = False, tickers_file: str | None = None):
    print("==============================================")
    print("Starting Historical Stock Data Update Process")
    print(f"Today's Date: {date.today().strftime('%Y-%m-%d')}")
    print("==============================================")

    exchanges = ["BSE", "NSE"] if exchange_filter is None else [exchange_filter]
    for exch in exchanges:
        ticker_list_path = tickers_file if tickers_file else os.path.join(".", f"tickers{exch.lower()}.txt")
        tickers = get_tickers_from_file(ticker_list_path)
        if not tickers:
            print(f"[Info] No tickers found for {exch} at {ticker_list_path}. Skipping.")
            continue
        update_historical_data(exch, tickers, debug_mode=debug_mode, create_missing=create_missing)

    print("\nAll updates finished.")

# ---------- CLI ----------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Robust historical updater for BSE/NSE tickers")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (prints sample lines for unreadable files and yfinance info)")
    parser.add_argument("--create-missing", action="store_true", help="Create missing CSV files before updating")
    parser.add_argument("--exchange", choices=["BSE", "NSE"], help="Limit to single exchange")
    parser.add_argument("--tickers", help="Path to a single tickers file to use instead of defaults")
    args = parser.parse_args()

    run_update(exchange_filter=args.exchange, debug_mode=args.debug, create_missing=args.create_missing, tickers_file=args.tickers)
