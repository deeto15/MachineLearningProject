import yfinance as yf
from datetime import datetime, timedelta

# set the ticker symbol
ticker = "AAPL"

# set the start date
start_date = "2025-01-15"
start_date = datetime.strptime(start_date, "%Y-%m-%d")

# set end date
end_date = start_date + timedelta(days=30)

# get data for ticker over 30 day period, excluding non trading days, only closing price
data = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)

# print only the date (as index) and the 'Close' column
print(data[['Close']].to_string())

# determine price trends over 1 day, 7 day, and 30 day periods
if not data.empty:
    close_initial = data["Close"].iloc[0].item()
    
    # 1 day period
    close_1d = data["Close"].iloc[1].item()
    price_trend_1d = close_1d - close_initial
    percent_change_1d = (price_trend_1d / close_initial) * 100
    
    # 1 week period
    close_1w = data["Close"].iloc[7].item()
    price_trend_1w = close_1w - close_initial
    percent_change_1w = (price_trend_1w / close_initial) * 100
    
    # 1 month period
    close_last = data["Close"].iloc[-1].item()
    price_trend_1m = close_last - close_initial
    percent_change_1m = (price_trend_1m / close_initial) * 100

# calculate the trend type
trend_type_1d = "increasing" if price_trend_1d > 0 else "decreasing"
trend_type_1w = "increasing" if price_trend_1w > 0 else "decreasing"
trend_type_1m = "increasing" if price_trend_1m > 0 else "decreasing"

# print the price trends
print(f"Price trend over 1 day period: {price_trend_1d:.2f} ({trend_type_1d})")
print(f"Price trend over 1 week period: {price_trend_1w:.2f} ({trend_type_1w})")
print(f"Price trend over 1 month period: {price_trend_1m:.2f} ({trend_type_1m})")
