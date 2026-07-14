import yfinance as yf
import pandas as pd
import ta

# Pull historical daily data for AMZN
ticker = "AMZN"
df = yf.download(ticker, period="1y", interval="1d")

# 1. Calculate the 14-Day Relative Strength Index (RSI)
df['RSI'] = ta.momentum.rsi(df['Close'], window=14)

# 2. Calculate the 0.5 Fibonacci Retracement from the recent 52-week high/low
high_52 = df['High'].max()
low_52 = df['Low'].min()
fib_50 = high_52 - (0.5 * (high_52 - low_52))

# Extract the most recent data points
latest_price = df['Close'].iloc[-1]
latest_rsi = df['RSI'].iloc[-1]

print(f"=== Short-Term {ticker} Technical Summary ===")
print(f"Latest Closing Price: ${latest_price:.2f}")
print(f"14-Day RSI:            {latest_rsi:.1f}")
print(f"0.5 Fib Retracement:  ${fib_50:.2f}")
