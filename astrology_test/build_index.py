"""Build data/nifty_index_2003_2026.csv, the Nifty 50 index series run.py uses.

Inputs (download them yourself, see README):
- data/niftyindices/*.csv : NIFTY 50 historical price files from niftyindices.com,
  one per year, 2003 to 2012 (columns: Index Name, Date, Open, High, Low, Close)
- data/eod2/nifty 50.csv  : EOD2 index file (Date, Open, High, Low, Close, Volume), Feb 2012 onward
- data/eod2/niftybees.csv : EOD2 NIFTYBEES file (its volume is used before Feb 2012,
  where the index files have no volume)
"""
import glob
import pandas as pd

SWITCH = pd.Timestamp("2012-02-21")  # first date taken from the EOD2 index file

files = sorted(glob.glob("data/niftyindices/*.csv"))
if not files:
    raise SystemExit("No niftyindices files found in data/niftyindices/")
old = pd.concat([pd.read_csv(f) for f in files])
old.columns = [c.strip() for c in old.columns]
old["Date"] = pd.to_datetime(old["Date"].str.strip(), format="%d %b %Y")
old = old.drop_duplicates("Date").set_index("Date").sort_index()
old["Close"] = pd.to_numeric(old["Close"].astype(str).str.replace(",", ""))

new = pd.read_csv("data/eod2/nifty 50.csv", parse_dates=["Date"]).set_index("Date").sort_index()
nb = pd.read_csv("data/eod2/niftybees.csv", parse_dates=["Date"]).set_index("Date").sort_index()

overlap = old[["Close"]].join(new.Close.rename("eod2"), how="inner")
if len(overlap):
    print(f"Overlap check: {len(overlap)} common days, max close difference {(overlap.Close - overlap.eod2).abs().max():.2f}")

comb = pd.concat([old.loc[:SWITCH - pd.Timedelta(days=1), ["Close"]], new.loc[SWITCH:, ["Close"]]])
vol = nb.Volume.reindex(comb.index)
vol.loc[SWITCH:] = new.Volume.reindex(comb.loc[SWITCH:].index)
comb["Volume"] = vol
comb.reset_index().to_csv("data/nifty_index_2003_2026.csv", index=False)
print(f"Wrote data/nifty_index_2003_2026.csv: {len(comb)} days, {comb.index[0].date()} to {comb.index[-1].date()}")
