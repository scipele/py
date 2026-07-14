"""Evaluate stocks with a beginner-friendly technical score.

Features:
- Loads your latest broker positions CSV (Schwab/Fidelity-style export).
- Separately scores current positions and watchlist candidates.
- Prints plain-language notes that explain what looks positive vs negative.

Examples:
	python stock_eval.py
	python stock_eval.py --watchlist "MSFT,NVDA,AMD"
	python stock_eval.py --watchlist-file /home/dev/py/stock/watchlist.txt
	python stock_eval.py --positions-file "/home/ts/Downloads/Community Property-Positions-2026-07-14-123800.csv"
"""

from __future__ import annotations

import argparse
import contextlib
import glob
import io
import json
import logging
import math
import os
import time
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import yfinance as yf


DEFAULT_DOWNLOADS_DIR = "/home/ts/Downloads"
DEFAULT_POSITIONS_PATTERN = "Community Property-Positions-*.csv"
DEFAULT_OTHER_TICKERS_FILENAME = "other_tickers_to_eval.csv"

# Personalize these values to match your own buy-vs-sell style.
SCORE_WEIGHTS = {
	"above_sma20": 7,
	"above_sma50": 10,
	"above_sma200": 12,
	"rsi_oversold_bonus": 4,
	"rsi_healthy_bonus": 8,
	"rsi_elevated_penalty": -4,
	"rsi_overbought_penalty": -10,
	"sma50_above_sma200": 8,
	"momentum_3m_positive": 8,
	"momentum_3m_negative": -8,
	"deep_pullback_bonus": 5,
	"near_52w_low_penalty": -6,
}

RATING_CUTOFFS = {
	"buy_leaning": 70,
	"watch_accumulate": 55,
	"hold_neutral": 45,
	"reduce_risk": 30,
}

# Legacy symbol aliases to improve Yahoo lookup success.
LEGACY_TICKER_MAP = {
	"RTN": "RTX",   # Raytheon -> RTX (Raytheon Technologies / RTX Corp)
	"FB": "META",   # Facebook -> Meta
	"ABC": "COR",   # AmerisourceBergen -> Cencora
	"ADS": "BFH",   # Alliance Data Systems -> Bread Financial
	"AET": "CVS",
	"AGN": "ABBV",
	"ALXN": "AZN",
	"ANDV": "MPC",
	"ANTM": "ELV",
	"ARNC": "HWM",
	"ATVI": "MSFT",
	"BHGE": "BKR",
	"CA": "AVGO",
	"CBG": "CBRE",
	"CBS": "PARA",
	"CELG": "BMY",
	"CERN": "ORCL",
	"COL": "RTX",
	"CSRA": "GD",
	"CTL": "LUMN",
	"CXO": "COP",
	"DISCA": "WBD",
	"DISCK": "WBD",
	"DPS": "KDP",
	"DRE": "PLD",
	"DWDP": "DD",
	"ESRX": "CI",
	"ETFC": "MS",
	"FBHS": "FBIN",
	"FLIR": "TDY",
	"HCN": "WELL",
	"HCP": "DOC",
	"HRS": "LHX",
	"JEC": "J",
	"KORS": "CPRI",
	"KSU": "CNI",
	"LLL": "LHX",
	"LUK": "JEF",
	"MON": "BAYRY",
	"MYL": "VTRS",
	"NBL": "CVX",
	"PBCT": "MTB",
	"PX": "LIN",
	"PXD": "XOM",
	"RHT": "IBM",
	"SCG": "D",
	"SNI": "WBD",
	"SYMC": "GEN",
	"TIF": "LVMUY",
	"TMK": "GL",
	"TSS": "GPN",
	"TWX": "WBD",
	"UTX": "RTX",
	"VIAB": "PARA",
	"WLTW": "WTW",
	"WYN": "WH",
	"XEC": "CVX",
	"XLNX": "AMD",
}


# Keep terminal output clean when Yahoo has stale/delisted symbols.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


def find_latest_positions_file(downloads_dir: str, pattern: str) -> str | None:
	matches = glob.glob(os.path.join(downloads_dir, pattern))
	if not matches:
		return None
	return max(matches, key=os.path.getmtime)


def parse_numeric(series: pd.Series) -> pd.Series:
	cleaned = (
		series.astype(str)
		.str.replace(",", "", regex=False)
		.str.replace("$", "", regex=False)
		.str.replace("%", "", regex=False)
		.str.replace("(", "-", regex=False)
		.str.replace(")", "", regex=False)
		.str.strip()
	)
	return pd.to_numeric(cleaned, errors="coerce")


def load_positions_csv(file_path: str) -> pd.DataFrame:
	with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
		lines = f.readlines()

	header_idx = None
	for i, line in enumerate(lines):
		if '"Symbol"' in line and '"Qty (Quantity)"' in line:
			header_idx = i
			break

	if header_idx is None:
		raise ValueError("Could not find the positions table header in the CSV file.")

	table_text = "".join(lines[header_idx:])
	df = pd.read_csv(StringIO(table_text), quotechar='"', skipinitialspace=True)

	# Remove extra unnamed columns caused by trailing commas in exported CSVs.
	df = df.loc[:, ~df.columns.str.contains(r"^Unnamed", na=False)]
	df.columns = [c.strip() for c in df.columns]

	rename_map = {
		"Symbol": "symbol",
		"Description": "description",
		"Qty (Quantity)": "qty",
		"Price": "price",
		"Mkt Val (Market Value)": "market_value",
		"Cost Basis": "cost_basis",
		"Gain % (Gain/Loss %)": "gain_pct",
		"Gain $ (Gain/Loss $)": "gain_dollars",
		"Asset Type": "asset_type",
	}
	df = df.rename(columns=rename_map)

	for col in ["qty", "price", "market_value", "cost_basis", "gain_pct", "gain_dollars"]:
		if col in df.columns:
			df[col] = parse_numeric(df[col])

	if "symbol" not in df.columns:
		raise ValueError("Positions CSV did not include a Symbol column.")

	df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
	df = df[df["symbol"].str.len() > 0].copy()
	return df


def rsi_14(close: pd.Series) -> pd.Series:
	delta = close.diff()
	gain = delta.clip(lower=0)
	loss = -delta.clip(upper=0)
	avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
	avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
	rs = avg_gain / avg_loss.replace(0, pd.NA)
	return 100 - (100 / (1 + rs))


def as_series(data: pd.Series | pd.DataFrame) -> pd.Series:
	"""Return a single numeric Series even if yfinance returns a one-column DataFrame."""
	if isinstance(data, pd.DataFrame):
		if data.shape[1] == 0:
			return pd.Series(dtype=float)
		return data.iloc[:, 0].astype(float)
	return data.astype(float)


def normalize_symbol_for_yahoo(symbol: str) -> str:
	"""Convert common broker ticker format to Yahoo ticker format."""
	# Example: BRK.B -> BRK-B
	return symbol.strip().upper().replace(".", "-")


def download_history(symbol: str, period: str, attempts: int = 3) -> pd.DataFrame:
	"""Download history with light retry to reduce transient empty responses."""
	last_hist = pd.DataFrame()
	for attempt in range(1, attempts + 1):
		with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
			hist = yf.download(symbol, period=period, interval="1d", progress=False, auto_adjust=False, threads=False)
		last_hist = hist
		if not hist.empty and len(hist) >= 60:
			return hist
		if attempt < attempts:
			time.sleep(0.35 * attempt)
	return last_hist


def score_one_ticker(symbol: str, period: str = "1y") -> dict:
	original_symbol = symbol.strip().upper()
	yahoo_symbol = normalize_symbol_for_yahoo(original_symbol)
	lookup_symbol = LEGACY_TICKER_MAP.get(yahoo_symbol, yahoo_symbol)
	mapped_note = f" (mapped to {lookup_symbol})" if lookup_symbol != yahoo_symbol else ""
	hist = download_history(lookup_symbol, period=period)

	# Retry normalized symbol if alias lookup returned no data.
	if (hist.empty or len(hist) < 60) and lookup_symbol != yahoo_symbol:
		hist = download_history(yahoo_symbol, period=period)

	# Retry original symbol only if different and first attempt returned no data.
	if (hist.empty or len(hist) < 60) and yahoo_symbol != original_symbol:
		hist = download_history(original_symbol, period=period)

	if hist.empty or len(hist) < 60:
		return {
			"symbol": original_symbol,
			"status": "No/limited data",
			"score": math.nan,
			"rating": "Insufficient data",
			"notes": f"Not enough price history to compute indicators{mapped_note}. Legacy ticker changes or temporary data-source misses can cause this.",
		}

	close = as_series(hist["Close"])
	high = as_series(hist["High"])
	low = as_series(hist["Low"])

	price = float(close.iloc[-1])
	sma20 = float(close.rolling(20).mean().iloc[-1])
	sma50 = float(close.rolling(50).mean().iloc[-1])
	sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else math.nan
	rsi = float(rsi_14(close).iloc[-1])

	high_52 = float(high.max())
	low_52 = float(low.min())
	pct_fr_52w_h = ((price / high_52) - 1) * 100 if high_52 else math.nan
	pct_fr_52w_l = ((price / low_52) - 1) * 100 if low_52 else math.nan
	momentum_3m = ((price / float(close.iloc[-63])) - 1) * 100 if len(close) >= 63 else math.nan

	score = 50
	positives: list[str] = []
	negatives: list[str] = []

	if price > sma20:
		score += SCORE_WEIGHTS["above_sma20"]
		positives.append("Price is above 20-day trend (short-term strength).")
	else:
		score -= SCORE_WEIGHTS["above_sma20"]
		negatives.append("Price is below 20-day trend (short-term weakness).")

	if price > sma50:
		score += SCORE_WEIGHTS["above_sma50"]
		positives.append("Price is above 50-day trend (medium-term support).")
	else:
		score -= SCORE_WEIGHTS["above_sma50"]
		negatives.append("Price is below 50-day trend (momentum cooling).")

	if not math.isnan(sma200):
		if price > sma200:
			score += SCORE_WEIGHTS["above_sma200"]
			positives.append("Price is above 200-day trend (long-term uptrend).")
		else:
			score -= SCORE_WEIGHTS["above_sma200"]
			negatives.append("Price is below 200-day trend (long-term caution).")

	if not math.isnan(rsi):
		if rsi < 35:
			score += SCORE_WEIGHTS["rsi_oversold_bonus"]
			positives.append("RSI is low (<35), could be oversold and mean-revert.")
		elif 45 <= rsi <= 60:
			score += SCORE_WEIGHTS["rsi_healthy_bonus"]
			positives.append("RSI is in a healthy zone (45-60).")
		elif rsi > 70:
			score += SCORE_WEIGHTS["rsi_overbought_penalty"]
			negatives.append("RSI is high (>70), risk of pullback.")
		elif rsi > 60:
			score += SCORE_WEIGHTS["rsi_elevated_penalty"]
			negatives.append("RSI is getting elevated (>60), monitor closely.")

	if not math.isnan(sma200) and not math.isnan(sma50):
		if sma50 > sma200:
			score += SCORE_WEIGHTS["sma50_above_sma200"]
			positives.append("50-day average is above 200-day average (bullish structure).")
		else:
			score -= SCORE_WEIGHTS["sma50_above_sma200"]
			negatives.append("50-day average is below 200-day average (bearish structure).")

	if not math.isnan(momentum_3m):
		if momentum_3m > 5:
			score += SCORE_WEIGHTS["momentum_3m_positive"]
			positives.append("3-month momentum is positive (>5%).")
		elif momentum_3m < -5:
			score += SCORE_WEIGHTS["momentum_3m_negative"]
			negatives.append("3-month momentum is negative (<-5%).")

	if not math.isnan(pct_fr_52w_h) and pct_fr_52w_h <= -25:
		score += SCORE_WEIGHTS["deep_pullback_bonus"]
		positives.append("Trades >25% below 52-week high (potential value setup).")
	if not math.isnan(pct_fr_52w_l) and pct_fr_52w_l < 10:
		score += SCORE_WEIGHTS["near_52w_low_penalty"]
		negatives.append("Trading close to 52-week low (higher downside risk).")

	score_for_rating = max(0.0, min(100.0, float(score)))

	if score_for_rating >= RATING_CUTOFFS["buy_leaning"]:
		rating = "Buy-leaning"
	elif score_for_rating >= RATING_CUTOFFS["watch_accumulate"]:
		rating = "Watch / Accumulate"
	elif score_for_rating >= RATING_CUTOFFS["hold_neutral"]:
		rating = "Hold / Neutral"
	elif score_for_rating >= RATING_CUTOFFS["reduce_risk"]:
		rating = "Reduce risk"
	else:
		rating = "Sell-leaning"

	note_parts = []
	if positives:
		note_parts.append("+ " + " | ".join(positives[:3]))
	if negatives:
		note_parts.append("- " + " | ".join(negatives[:3]))

	return {
		"symbol": original_symbol,
		"status": "OK",
		"price": round(price, 2),
		"rsi14": round(rsi, 1) if not math.isnan(rsi) else math.nan,
		"sma20": round(sma20, 2),
		"sma50": round(sma50, 2),
		"sma200": round(sma200, 2) if not math.isnan(sma200) else math.nan,
		"%_fr_52w_h": round(pct_fr_52w_h, 1) if not math.isnan(pct_fr_52w_h) else math.nan,
		"%_fr_52w_l": round(pct_fr_52w_l, 1) if not math.isnan(pct_fr_52w_l) else math.nan,
		"mom_3m_%": round(momentum_3m, 1) if not math.isnan(momentum_3m) else math.nan,
		"score": round(float(score), 2),
		"rating": rating,
		"notes": " ".join(note_parts) if note_parts else "No clear signals yet.",
	}


def parse_watchlist(args_watchlist: str, watchlist_file: str | None) -> list[str]:
	tickers: set[str] = set()

	if args_watchlist:
		for item in args_watchlist.replace(";", ",").split(","):
			t = item.strip().upper()
			if t:
				tickers.add(t)

	if watchlist_file:
		# Support CSV files with a symbol/ticker header, or plain text lists.
		try:
			df = pd.read_csv(watchlist_file)
			df.columns = [str(c).strip().lower() for c in df.columns]
			symbol_col = None
			for candidate in ["symbol", "ticker", "tickers"]:
				if candidate in df.columns:
					symbol_col = candidate
					break
			if symbol_col:
				for item in df[symbol_col].dropna().astype(str).tolist():
					t = item.strip().upper()
					if t:
						tickers.add(t)
			else:
				with open(watchlist_file, "r", encoding="utf-8", errors="ignore") as f:
					text = f.read().replace("\n", ",").replace(";", ",")
				for item in text.split(","):
					t = item.strip().upper()
					if t:
						tickers.add(t)
		except Exception:
			with open(watchlist_file, "r", encoding="utf-8", errors="ignore") as f:
				text = f.read().replace("\n", ",").replace(";", ",")
			for item in text.split(","):
				t = item.strip().upper()
				if t:
					tickers.add(t)

	return sorted(tickers)


def load_ticker_metadata(file_path: str | None) -> pd.DataFrame:
	"""Load optional company_name/sector metadata from a ticker CSV file."""
	if not file_path:
		return pd.DataFrame(columns=["symbol", "company_name", "sector"])

	try:
		df = pd.read_csv(file_path)
		df.columns = [str(c).strip().lower() for c in df.columns]

		symbol_col = None
		for candidate in ["symbol", "ticker", "tickers"]:
			if candidate in df.columns:
				symbol_col = candidate
				break

		if not symbol_col:
			return pd.DataFrame(columns=["symbol", "company_name", "sector"])

		name_col = None
		for candidate in ["company_name", "name", "description"]:
			if candidate in df.columns:
				name_col = candidate
				break

		sector_col = None
		for candidate in ["sector", "industry", "asset_type"]:
			if candidate in df.columns:
				sector_col = candidate
				break

		meta = pd.DataFrame()
		meta["symbol"] = df[symbol_col].astype(str).str.strip().str.upper()
		meta["company_name"] = df[name_col].astype(str).str.strip() if name_col else pd.NA
		meta["sector"] = df[sector_col].astype(str).str.strip() if sector_col else pd.NA
		meta = meta[meta["symbol"].str.len() > 0].drop_duplicates(subset=["symbol"], keep="first")
		return meta
	except Exception:
		return pd.DataFrame(columns=["symbol", "company_name", "sector"])


def evaluate_group(tickers: list[str], period: str, group_label: str = "Tickers", show_progress: bool = True) -> pd.DataFrame:
	rows = []
	total = len(tickers)
	for idx, t in enumerate(tickers, start=1):
		if show_progress:
			print(f"\r[{idx}/{total}] {group_label}: evaluating {t}...", end="", flush=True)
		try:
			rows.append(score_one_ticker(t, period=period))
		except Exception as exc:
			rows.append(
				{
					"symbol": t,
					"status": "Error",
					"score": math.nan,
					"rating": "Error",
					"notes": f"Failed to retrieve/process data: {exc}",
				}
			)

	if show_progress and total > 0:
		print(f"\r[{total}/{total}] {group_label}: complete.{' ' * 20}")

	df = pd.DataFrame(rows)
	if "score" in df.columns:
		df = df.sort_values(by=["score", "symbol"], ascending=[False, True], na_position="last")
	return df


def print_notes_legend() -> None:
	print("\nHow to read this output:")
	print("- Score 70-100: Buy-leaning technical setup (trend + momentum stronger).")
	print("- Score 55-69: Watch/Accumulate (mixed but constructive signals).")
	print("- Score 45-54: Hold/Neutral (no strong technical edge).")
	print("- Score 30-44: Reduce risk (multiple warning signs).")
	print("- Score 0-29: Sell-leaning (weak trend/momentum profile).")
	print("- RSI below 35 can mean oversold; RSI above 70 can mean overbought.")
	print("- Above 50/200-day averages is usually positive; below is usually negative.")


def write_csv_exports(
	output_dir: Path,
	timestamp: str,
	positions_table: pd.DataFrame,
	watchlist_table: pd.DataFrame,
) -> dict[str, str]:
	paths: dict[str, str] = {}

	if not positions_table.empty:
		p = output_dir / f"positions_scores_{timestamp}.csv"
		positions_table.to_csv(p, index=False)
		paths["positions_csv"] = str(p)

	if not watchlist_table.empty:
		w = output_dir / f"watchlist_scores_{timestamp}.csv"
		watchlist_table.to_csv(w, index=False)
		paths["watchlist_csv"] = str(w)

	if not positions_table.empty or not watchlist_table.empty:
		all_rows = []
		if not positions_table.empty:
			p2 = positions_table.copy()
			p2.insert(0, "group", "current_positions")
			all_rows.append(p2)
		if not watchlist_table.empty:
			w2 = watchlist_table.copy()
			w2.insert(0, "group", "watchlist")
			all_rows.append(w2)

		combined = pd.concat(all_rows, ignore_index=True)
		c = output_dir / f"stock_scores_combined_{timestamp}.csv"
		combined.to_csv(c, index=False)
		paths["combined_csv"] = str(c)

	return paths


def _chart_payload(df: pd.DataFrame) -> tuple[list[str], list[float]]:
	if df.empty or "symbol" not in df.columns or "score" not in df.columns:
		return [], []
	temp = df[["symbol", "score"]].copy()
	temp["score"] = pd.to_numeric(temp["score"], errors="coerce")
	temp = temp.dropna(subset=["score"])
	temp["score"] = temp["score"].clip(lower=0, upper=100)
	temp = temp.sort_values(by="score", ascending=False)
	return temp["symbol"].astype(str).tolist(), temp["score"].astype(float).tolist()


def write_html_report(
	output_dir: Path,
	timestamp: str,
	positions_source: str | None,
	positions_table: pd.DataFrame,
	watchlist_table: pd.DataFrame,
) -> str:
	output_path = output_dir / f"stock_dashboard_{timestamp}.html"

	positions_labels, positions_scores = _chart_payload(positions_table)
	watch_labels, watch_scores = _chart_payload(watchlist_table)

	positions_html = (
		positions_table.to_html(index=False, classes="data-table", na_rep="")
		if not positions_table.empty
		else "<p>No current positions were available.</p>"
	)
	watchlist_html = (
		watchlist_table.to_html(index=False, classes="data-table", na_rep="")
		if not watchlist_table.empty
		else "<p>No watchlist tickers were provided.</p>"
	)

	html = f"""<!doctype html>
<html lang=\"en\">
<head>
	<meta charset=\"utf-8\" />
	<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
	<title>Sciple's Stock Technical Evaluator Dashboard</title>
	<script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
	<style>
		:root {{
			--bg: #f4f7fb;
			--card: #ffffff;
			--text: #0f172a;
			--muted: #475569;
			--good: #0f766e;
			--warn: #b45309;
			--bad: #b91c1c;
			--accent: #0ea5e9;
			--border: #dbe4f0;
		}}
		body {{
			margin: 0;
			font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
			color: var(--text);
			background: radial-gradient(circle at top right, #dbeafe, var(--bg) 40%);
		}}
		.wrap {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
		.hero {{
			background: linear-gradient(120deg, #0f172a, #0c4a6e);
			color: #e2e8f0;
			border-radius: 16px;
			padding: 20px 24px;
			box-shadow: 0 8px 26px rgba(15, 23, 42, 0.22);
		}}
		.hero h1 {{ margin: 0 0 8px; font-size: 1.6rem; }}
		.hero p {{ margin: 4px 0; color: #cbd5e1; }}
		.grid {{ display: grid; grid-template-columns: 1fr; gap: 18px; margin-top: 18px; }}
		.card {{
			background: var(--card);
			border: 1px solid var(--border);
			border-radius: 14px;
			padding: 16px;
			overflow: auto;
			box-shadow: 0 8px 18px rgba(15, 23, 42, 0.07);
		}}
		h2 {{ margin: 0 0 12px; font-size: 1.2rem; }}
		.data-table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
		.data-table th, .data-table td {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; }}
		.data-table th {{ background: #f8fafc; position: sticky; top: 0; }}
		/* Keep notes mostly on one line; table can scroll horizontally as needed. */
		.data-table th:last-child, .data-table td:last-child {{
			min-width: 640px;
			white-space: nowrap;
		}}
		.legend li {{ margin: 6px 0; color: var(--muted); }}
		.good {{ color: var(--good); font-weight: 600; }}
		.warn {{ color: var(--warn); font-weight: 600; }}
		.bad {{ color: var(--bad); font-weight: 600; }}
		@media (min-width: 980px) {{
			.grid {{ grid-template-columns: 1fr 1fr; }}
			.span-2 {{ grid-column: span 2; }}
		}}
	</style>
</head>
<body>
	<div class=\"wrap\">
		<section class=\"hero\">
			<h1>Stock Technical Evaluator Dashboard</h1>
			<p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
			<p>Positions source: {positions_source or "Not found"}</p>
		</section>

		<div class=\"grid\">
			<section class=\"card\">
				<h2>Current Positions Scores</h2>
				<canvas id=\"positionsChart\" height=\"160\"></canvas>
			</section>

			<section class=\"card\">
				<h2>Watchlist Scores</h2>
				<canvas id=\"watchlistChart\" height=\"160\"></canvas>
			</section>

			<section class=\"card span-2\">
				<h2>Current Positions Table</h2>
				{positions_html}
			</section>

			<section class=\"card span-2\">
				<h2>Watchlist Table</h2>
				{watchlist_html}
			</section>

			<section class=\"card span-2\">
				<h2>How to Read This</h2>
				<ul class=\"legend\">
					<li><span class=\"good\">Score 70-100:</span> Buy-leaning technical setup.</li>
					<li><span class=\"good\">Score 55-69:</span> Watch/Accumulate.</li>
					<li><span class=\"warn\">Score 45-54:</span> Hold/Neutral.</li>
					<li><span class=\"warn\">Score 30-44:</span> Reduce risk.</li>
					<li><span class=\"bad\">Score 0-29:</span> Sell-leaning.</li>
					<li>RSI below 35 may indicate oversold; above 70 may indicate overbought.</li>
					<li>Above 50/200-day averages is typically stronger; below is typically weaker.</li>
					<li>This is educational and not financial advice.</li>
				</ul>
			</section>
		</div>
	</div>

	<script>
		function makeChart(canvasId, labels, values, color) {{
			const ctx = document.getElementById(canvasId);
			if (!ctx || labels.length === 0) return;
			new Chart(ctx, {{
				type: 'bar',
				data: {{
					labels,
					datasets: [{{
						label: 'Technical Score',
						data: values,
						backgroundColor: color,
						borderRadius: 6
					}}]
				}},
				options: {{
					responsive: true,
					scales: {{
						y: {{ min: 0, max: 100, ticks: {{ stepSize: 10 }} }}
					}},
					plugins: {{
						legend: {{ display: false }}
					}}
				}}
			}});
		}}

		makeChart('positionsChart', {json.dumps(positions_labels)}, {json.dumps(positions_scores)}, 'rgba(14, 165, 233, 0.75)');
		makeChart('watchlistChart', {json.dumps(watch_labels)}, {json.dumps(watch_scores)}, 'rgba(20, 184, 166, 0.75)');
	</script>
</body>
</html>
"""

	output_path.write_text(html, encoding="utf-8")
	return str(output_path)


def main() -> None:
	parser = argparse.ArgumentParser(
		description="Evaluate current positions and watchlist stocks with technical scoring."
	)
	parser.add_argument("--positions-file", help="Path to positions CSV export.")
	parser.add_argument("--downloads-dir", default=DEFAULT_DOWNLOADS_DIR)
	parser.add_argument("--positions-pattern", default=DEFAULT_POSITIONS_PATTERN)
	parser.add_argument("--watchlist", default="", help="Comma-separated tickers (ex: MSFT,NVDA,AMD)")
	parser.add_argument("--watchlist-file", help="File containing watchlist tickers.")
	parser.add_argument(
		"--other-tickers-file",
		help="CSV file of additional tickers (default: other_tickers_to_eval.csv in script folder)",
	)
	parser.add_argument("--period", default="1y", help="History period for indicators (default: 1y)")
	parser.add_argument("--output-dir", default="/home/dev/py/stock/output", help="Directory for HTML and CSV output files")
	parser.add_argument("--no-progress", action="store_true", help="Disable progress indicator output")
	args = parser.parse_args()

	positions_file = args.positions_file or find_latest_positions_file(
		downloads_dir=args.downloads_dir,
		pattern=args.positions_pattern,
	)

	positions_df = pd.DataFrame()
	position_tickers: list[str] = []

	if positions_file:
		try:
			positions_df = load_positions_csv(positions_file)
			if "asset_type" in positions_df.columns:
				included = positions_df[
					positions_df["asset_type"].astype(str).str.contains("Equity|ETF", case=False, na=False)
				]
				position_tickers = sorted(included["symbol"].dropna().unique().tolist())
				if not position_tickers:
					position_tickers = sorted(positions_df["symbol"].dropna().unique().tolist())
			else:
				position_tickers = sorted(positions_df["symbol"].dropna().unique().tolist())
		except Exception as exc:
			print(f"Warning: could not parse positions file: {positions_file}")
			print(f"Reason: {exc}")
			positions_file = None

	script_dir = Path(__file__).resolve().parent
	auto_other_tickers_file = script_dir / DEFAULT_OTHER_TICKERS_FILENAME

	watchlist_file = args.watchlist_file
	if args.other_tickers_file:
		watchlist_file = args.other_tickers_file
	elif not watchlist_file and auto_other_tickers_file.exists():
		watchlist_file = str(auto_other_tickers_file)

	watchlist_tickers = parse_watchlist(args.watchlist, watchlist_file)
	watchlist_meta = load_ticker_metadata(watchlist_file)
	watchlist_only = [t for t in watchlist_tickers if t not in set(position_tickers)]

	output_dir = Path(args.output_dir)
	output_dir.mkdir(parents=True, exist_ok=True)
	timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

	positions_table = pd.DataFrame()
	watchlist_table = pd.DataFrame()

	if position_tickers:
		positions_scores = evaluate_group(
			position_tickers,
			period=args.period,
			group_label="Positions",
			show_progress=not args.no_progress,
		)

		if not positions_df.empty:
			if "description" in positions_df.columns and "company_name" not in positions_df.columns:
				positions_df["company_name"] = positions_df["description"]
			if "asset_type" in positions_df.columns and "sector" not in positions_df.columns:
				positions_df["sector"] = positions_df["asset_type"]

			display_cols = [
				c for c in ["symbol", "company_name", "sector", "qty", "cost_basis", "market_value", "gain_pct"] if c in positions_df.columns
			]
			merged = positions_scores.merge(positions_df[display_cols], on="symbol", how="left")
			ordered = [
				"symbol",
				"company_name",
				"sector",
				"qty",
				"cost_basis",
				"market_value",
				"gain_pct",
				"price",
				"rsi14",
				"mom_3m_%",
				"score",
				"rating",
				"notes",
			]
			ordered = [c for c in ordered if c in merged.columns]
			positions_table = merged[ordered].copy()
		else:
			positions_table = positions_scores.copy()

	if watchlist_only:
		watch_scores = evaluate_group(
			watchlist_only,
			period=args.period,
			group_label="Watchlist",
			show_progress=not args.no_progress,
		)
		if not watchlist_meta.empty:
			watch_scores = watch_scores.merge(watchlist_meta, on="symbol", how="left")
		ordered = [
			"symbol",
			"company_name",
			"sector",
			"price",
			"rsi14",
			"%_fr_52w_h",
			"%_fr_52w_l",
			"mom_3m_%",
			"score",
			"rating",
			"notes",
		]
		ordered = [c for c in ordered if c in watch_scores.columns]
		watchlist_table = watch_scores[ordered].copy()

	exports = write_csv_exports(output_dir, timestamp, positions_table, watchlist_table)
	html_path = write_html_report(
		output_dir=output_dir,
		timestamp=timestamp,
		positions_source=positions_file,
		positions_table=positions_table,
		watchlist_table=watchlist_table,
	)

	print("Visual report generated successfully.")
	print(f"HTML dashboard: {html_path}")
	for label, path in exports.items():
		print(f"{label}: {path}")
	if watchlist_file:
		print(f"Other tickers source: {watchlist_file}")
	if not watchlist_only:
		print("Tip: add --watchlist \"MSFT,NVDA,AMD\" or provide --other-tickers-file /path/to/file.csv")


if __name__ == "__main__":
	main()
