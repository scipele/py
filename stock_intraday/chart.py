import logging
import argparse
import pandas as pd
import mplfinance as mpf
from pathlib import Path

# Silence the matplotlib font manager warnings specifically
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)

INPUT_FOLDER = Path("/home/dev/cpp/stock_intraday/output")
CHART_FOLDER = Path("/home/dev/py/stock_intraday/charts")


def find_swing_levels(df, previous_day_high, previous_day_low):

    swing_high = None
    swing_low = None

    lookback = 3   # candles on each side


    # Search backward, skipping newest candles
    for i in range(len(df)-lookback-1, lookback, -1):

        high = df["High"].iloc[i]
        low = df["Low"].iloc[i]


        # Swing high:
        # higher than 3 candles before and after
        if swing_high is None:

            left_highs = df["High"].iloc[i-lookback:i]
            right_highs = df["High"].iloc[i+1:i+lookback+1]

            if (
                high > left_highs.max()
                and high > right_highs.max()
                and high > previous_day_high
            ):
                swing_high = high


        # Swing low:
        if swing_low is None:

            left_lows = df["Low"].iloc[i-lookback:i]
            right_lows = df["Low"].iloc[i+1:i+lookback+1]

            if (
                low < left_lows.min()
                and low < right_lows.min()
                and low < previous_day_low
            ):
                swing_low = low


        if swing_high and swing_low:
            break


    return swing_high, swing_low


def create_chart(csv_file):

    ticker = csv_file.stem

    print(f"Creating chart: {ticker}")


    # Read CSV
    df = pd.read_csv(
        csv_file,
        parse_dates=["Datetime"]
    )


    # mplfinance requires datetime index
    df.set_index("Datetime", inplace=True)

    # -----------------------------
    # Calculate support/resistance
    # -----------------------------

    # Most recent trading day
    last_day = df.index[-1].date()

    recent_day = df[
        df.index.date == last_day
    ]


    previous_day_high = recent_day["High"].max()
    previous_day_low  = recent_day["Low"].min()

    swing_high, swing_low = find_swing_levels(
        df,
        previous_day_high,
        previous_day_low
    )


    print(
        f"{ticker}: "
        f"Swing High={swing_high}, "
        f"Swing Low={swing_low}"
    )


    print(
        f"{ticker}: "
        f"Day High={previous_day_high:.2f}, "
        f"Day Low={previous_day_low:.2f} "
    )


    # Rename columns to mplfinance format
    df.rename(
        columns={
            "Open": "Open",
            "High": "High",
            "Low": "Low",
            "Close": "Close",
            "Volume": "Volume"
        },
        inplace=True
    )

    recent = df.tail(234)   # 3 days x 78 candles

    # 1. Parse the command-line arguments FIRST
    parser = argparse.ArgumentParser(description=f"Plot a candlestick chart for a given ticker.")
    parser.add_argument(
        "-d", "--days", 
        type=int, 
        default=8, 
        help="Number of days to include in the chart (default: 8)"
    )

    # handle the entry prices or '0' to ignore
    parser.add_argument(
        "-e", "--entry", 
        type=str,       
        default="0", 
        help="Comma-separated entry prices or 0 for placeholders"
    )

    args = parser.parse_args()
    days_to_plot = args.days
    entry_price = args.entry

    # 2. Immediately create your day mask and filter your DataFrame
    unique_days = df.index.normalize().unique()
    last_x_days = unique_days[-days_to_plot:]
    day_mask = df.index.normalize().isin(last_x_days)

    df_filtered = df[day_mask] # This scales your data down to 320 rows

    # 3. Create horizontal support/resistance lines USING THE FILTERED INDEX
    levels = [] 

    # Swing high
    if swing_high is not None:
        levels.append(
            mpf.make_addplot(
                pd.Series(swing_high, index=df_filtered.index), # <- Changed to df_filtered.index
                color="red", linestyle="--", width=1, 
                label=f"{swing_high:.2f} swing_high"
            )
        )

    # Swing low
    if swing_low is not None:
        levels.append(
            mpf.make_addplot(
                pd.Series(swing_low, index=df_filtered.index), # <- Changed to df_filtered.index
                color="green", linestyle="--", width=1,
                label=f"{swing_low:.2f} swing_low"
            )
        )

    # Previous day high
    levels.append(
        mpf.make_addplot(
            pd.Series(previous_day_high, index=df_filtered.index), # <- Changed to df_filtered.index
            color="orange", linestyle=":", width=1,
            label=f"{previous_day_high:.2f} previous_day_high"
        )
    )

    # Previous day low
    levels.append(
        mpf.make_addplot(
            pd.Series(previous_day_low, index=df_filtered.index), # <- Changed to df_filtered.index
            color="blue", linestyle=":", width=1, 
            label=f"{previous_day_low:.2f} previous_day_low"
        )
    )

    # Extract the active raw numeric prices from your variables
    active_prices = [p for p in [swing_high, swing_low, previous_day_high, previous_day_low] if p is not None]

    # 4. Pass both cleanly to mpf.plot
    mpf.plot(
        df_filtered,                  # 320 rows
        type="candle",
        volume=True,
        style="yahoo",
        title=f"{ticker} - 5 Minute Chart ({days_to_plot} days)",
        ylabel="Price",
        ylabel_lower="Volume",
        mav=(days_to_plot, 50),       
        addplot=levels,               # Now 320 rows (Matches perfectly!)
        figsize=(14, 8),
        savefig=CHART_FOLDER / f"{ticker}.png",
        warn_too_much_data=5000,
        hlines=dict(hlines=active_prices, colors='none'),
        xrotation=90
    )




def main():

    CHART_FOLDER.mkdir(
        exist_ok=True
    )


    files = INPUT_FOLDER.glob("*.csv")


    for file in files:
        create_chart(file)


if __name__ == "__main__":
    main()