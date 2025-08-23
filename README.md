# Stock Prediction Platform

## Module 01 – Data Collection
This module fetches **NIFTY50 top 10 stock data** (daily OHLCV) using Yahoo Finance API, and stores it into:
- **CSV files** in `data/raw/`
- **SQLite database** (`data/stocks.db`)

### Run
```bash
pip install -r requirements.txt
python src/module1_collect.py
