"""How long did each Nifty 50 fall of 13% or more, since 2004, take to get back to its old high?

Usage:
    python fetch_data.py
    python recovery.py

Definitions (all on daily closes of the Nifty 50 price index, dividends not included):
    old high   the highest close so far (tracked from the first row of data, Jan 2003)
    fall       a close at least 13% below the old high
    clock      starts on the first close 13% below the old high
               (also reported: from the old high itself)
    recovered  the first close at or above the old high
    bottom     the lowest close between the old high and recovery
Falls counted: those whose first -13% close is on or after 1 Jan 2004.
Nifty's Feb 2000 high (about 1,756) was passed in Dec 2003, and the old high is tracked from
Jan 2003, so every old high behind a counted fall is a true all-time high.

Data: niftyindices.com yearly CSVs for 2003-2011 (saved in data/) and the EOD2 file from Feb 2012
(fetch_data.py). The EOD2 file has no rows for Jan-Feb 2012; no fall starts, ends or reaches
its low in that gap.

Writes results/falls.csv and results/summary.txt, plus the same table at 10%, 15% and 20%
to check the result doesn't depend on the 13% line.
"""
import glob
import os

import pandas as pd

EOD2 = os.path.join("data", "nifty 50.csv")
EARLY = os.path.join("data", "NIFTY_50_Historical_PR_*.csv")
FROM = pd.Timestamp("2004-01-01")
LINES = [0.13, 0.10, 0.15, 0.20]


def load():
    parts = []
    for p in sorted(glob.glob(EARLY)):
        e = pd.read_csv(p, encoding="utf-8-sig")
        e.columns = [c.strip() for c in e.columns]
        e["Date"] = pd.to_datetime(e["Date"].str.strip(), format="%d %b %Y")
        parts.append(e[["Date", "Close"]])
    if os.path.exists(EOD2):
        parts.append(pd.read_csv(EOD2, parse_dates=["Date"])[["Date", "Close"]])
    if not parts:
        raise SystemExit("No data in data/. Run fetch_data.py and add the niftyindices.com files (see README.md).")
    d = pd.concat(parts).drop_duplicates("Date", keep="last").sort_values("Date").reset_index(drop=True)
    d["Close"] = d.Close.astype(float)
    return d


def falls(d, line):
    out, i, n = [], 0, len(d)
    while i < n:
        if d.dd[i] <= -line:
            hi = d.peak[i]
            hi_i = d.index[(d.Close == hi) & (d.index <= i)][-1]
            j = i
            while j < n and d.Close[j] < hi:
                j += 1
            seg = d.iloc[hi_i:j]
            lo_i = seg.Close.idxmin()
            rec = j < n
            out.append(dict(
                old_high_date=d.Date[hi_i].date(), old_high=hi,
                first_line_date=d.Date[i].date(),
                bottom_date=d.Date[lo_i].date(), bottom=d.Close[lo_i],
                depth_pct=round(100 * (d.Close[lo_i] / hi - 1), 1),
                recovered_date=d.Date[j].date() if rec else None,
                days_from_line=(d.Date[j] - d.Date[i]).days if rec else None,
                days_from_high=(d.Date[j] - d.Date[hi_i]).days if rec else None,
                days_so_far=None if rec else (d.Date[n - 1] - d.Date[i]).days,
                sessions_from_line=(j - i) if rec else None))
            i = j + 1
        else:
            i += 1
    f = pd.DataFrame(out)
    return f[pd.to_datetime(f.first_line_date) >= FROM].reset_index(drop=True)


def main():
    d = load()
    d["peak"] = d.Close.cummax()
    d["dd"] = d.Close / d.peak - 1
    gaps = d[d.Date.diff().dt.days > 10]
    os.makedirs("results", exist_ok=True)
    L = [f"Nifty 50 price index, {d.Date.min().date()} to {d.Date.max().date()}. "
         f"Falls whose first line-crossing is on or after {FROM.date()}."]
    for i in gaps.index:
        L.append(f"Note: no data between {d.Date[i - 1].date()} and {d.Date[i].date()}.")
    L.append("")
    for line in LINES:
        f = falls(d, line)
        if line == 0.13:
            f.to_csv("results/falls.csv", index=False, lineterminator="\n")
        L.append(f"--- line: {int(line * 100)}% below the old high ---")
        for _, r in f.iterrows():
            if r.recovered_date is not None and not pd.isna(r.recovered_date):
                L.append(f"  high {r.old_high_date} ({r.old_high:,.0f}) | -{int(line*100)}% on {r.first_line_date} | "
                         f"bottom {r.bottom_date} {r.depth_pct}% | back {r.recovered_date} | "
                         f"{int(r.days_from_line)} days (~{r.days_from_line / 30.44:.1f} months) from the line, "
                         f"{int(r.days_from_high)} days from the high")
            else:
                L.append(f"  high {r.old_high_date} ({r.old_high:,.0f}) | -{int(line*100)}% on {r.first_line_date} | "
                         f"lowest so far {r.bottom_date} {r.depth_pct}% | NOT RECOVERED, "
                         f"{int(r.days_so_far)} days (~{r.days_so_far / 30.44:.1f} months) so far")
        done = f[f.recovered_date.notna()]
        w = sorted(int(x) for x in done.days_from_line)
        L.append(f"  {len(f)} falls, {len(w)} recovered. Days from the line: {w}")
        if w:
            L.append(f"  shortest {w[0]}, median {done.days_from_line.median():g}, longest {w[-1]}; "
                     f"{sum(x <= 365 for x in w)} of {len(w)} within 365 days; "
                     f"median from the old high {done.days_from_high.median():g}")
        L.append("")
    last = d.iloc[-1]
    L.append(f"Last close {last.Date.date()}: {last.Close:,.2f}, {100 * last.dd:.1f}% below the high of "
             f"{last.peak:,.2f}")
    text = "\n".join(L)
    with open("results/summary.txt", "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
