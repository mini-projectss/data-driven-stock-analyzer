# Stock Prediction Platform

## Module 01 – Data Collection
This module fetches **NIFTY50 top 10 stock data** (daily OHLCV) using Yahoo Finance API, and stores it into:
- **CSV files** in `data/raw/`
- **SQLite database** (`data/stocks.db`)

### Run
```bash
pip install -r requirements.txt
python src/module1_collect.py


## Module 02 – Data Preprocessing

This module performs the preprocessing of the stock data fetched in **Module 01**. It prepares the data for machine learning by performing the following tasks:

- **Data Cleaning**: Removes or handles missing values and outliers to ensure data consistency.
- **Feature Engineering**: Creates additional features like:
  - Moving Averages (SMA, EMA)
  - Relative Strength Index (RSI)
  - Moving Average Convergence Divergence (MACD)
- **Data Normalization/Scaling**: Scales the features using techniques like MinMaxScaler or StandardScaler to ensure consistency in the input data for machine learning models.

### Run
```bash
python src/module2_preprocess.py