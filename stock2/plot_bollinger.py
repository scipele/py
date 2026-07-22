import pandas as pd
import json
from pathlib import Path

# Adjust path to your C++ output
jsonl_path = Path("/home/dev/cpp/stock/output/bulk_stock_data.jsonl")

data = []
with open(jsonl_path, 'r') as f:
    for line in f:
        if line.strip():
            data.append(json.loads(line))

df = pd.DataFrame(data)

# Handle missing columns (for older data)
for col in ['volatility', 'short_score', 'long_score', 'rsi', 'mom_3m']:
    if col not in df.columns:
        df[col] = None

print("=== Top Stocks by Short Score ===")
print(df[['ticker', 'short_score', 'long_score', 'volatility', 'rsi', 'mom_3m']]
      .round(1)
      .sort_values('short_score', ascending=False)
      .head(20))

print("\n=== Top Stocks by Long Score ===")
print(df[['ticker', 'long_score', 'short_score', 'volatility', 'rsi']]
      .round(1)
      .sort_values('long_score', ascending=False)
      .head(15))

# Volatility summary
if 'volatility' in df.columns:
    print("\n=== Volatility Summary ===")
    print(df['volatility'].describe().round(2))