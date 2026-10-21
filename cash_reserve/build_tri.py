"""Rebuild a Nifty 50 total return index from the price index and the daily dividend yield.

Inputs (download from niftyindices.com > Reports > Historical Data, one year per file):
  data/price/  NIFTY 50 price files  (*NIFTY_50_Historical_PR_*.csv)
  data/yield/  NIFTY 50 P/E, P/B & Div Yield files  (*NIFTY_50-yield-*.csv)

  python build_tri.py

Each day: growth = (close_t / close_t-1) x (1 + yield_t-1 / 100 x calendar_days / 365).
A trading day with no yield uses the previous day's yield.
Writes data/nifty50_tri.csv with columns Date, price, dy, tri.
"""
import glob
import os
import pandas as pd

PRICE_DIR, YIELD_DIR, OUT = os.path.join("data", "price"), os.path.join("data", "yield"), os.path.join("data", "nifty50_tri.csv")

pr = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(PRICE_DIR, "*NIFTY_50_Historical_PR_*.csv"))])
pr.columns = [c.strip() for c in pr.columns]
pr["Date"] = pd.to_datetime(pr["Date"].str.strip(), format="%d %b %Y")
pr = pr.drop_duplicates("Date").sort_values("Date").set_index("Date")["Close"].astype(float)

dy = pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(YIELD_DIR, "*NIFTY_50-yield-*.csv"))])
dy.columns = [c.strip() for c in dy.columns]
dy["Date"] = pd.to_datetime(dy["Date"].str.strip(), format="%d-%b-%Y")
dy = dy.drop_duplicates("Date").sort_values("Date").set_index("Date")["Div Yield%"].astype(float)

df = pd.DataFrame({"price": pr}).join(dy.rename("dy"), how="left")
missing = int(df.dy.isna().sum())
df["dy"] = df["dy"].ffill().bfill()
gap = df.index.to_series().diff().dt.days.fillna(0)
growth = (df.price / df.price.shift(1)) * (1 + df.dy.shift(1) / 100 * gap / 365)
df["tri"] = growth.fillna(1).cumprod() * df.price.iloc[0]
df.to_csv(OUT)

yrs = (df.index[-1] - df.index[0]).days / 365.25
pc = (df.price.iloc[-1] / df.price.iloc[0]) ** (1 / yrs) - 1
tc = (df.tri.iloc[-1] / df.tri.iloc[0]) ** (1 / yrs) - 1
print(f"{len(df)} days, {df.index[0].date()} to {df.index[-1].date()}; {missing} days had no yield (previous day used)")
print(f"price index {pc*100:.2f}% a year, total return index {tc*100:.2f}% a year")
