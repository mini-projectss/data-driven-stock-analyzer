# check_yf_one_ticker.py
from datetime import date, timedelta
import yfinance as yf
import pandas as pd

ticker = "3MINDIA.BO"   # change as needed
last_date = pd.to_datetime("2025-09-29").date()   # replace with the last date from your cleaned CSV for that ticker
start = last_date + timedelta(days=1)
end = date.today() + timedelta(days=1)  # yfinance end is exclusive

print("Requesting:", ticker, " start=", start, " end(exclusive)=", end)
df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
print("yfinance returned rows:", df.shape[0])
if not df.empty:
    print(df.tail(10))
else:
    print("No rows returned — likely no published data yet or ticker delisted/absent on Yahoo.")
