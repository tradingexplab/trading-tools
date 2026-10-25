"""How long did each Nifty 50 fall of 13% or more take to get back to its old high?

Usage:
    python fetch_data.py
    python recovery.py

Definitions (all on daily closes of the Nifty 50 price index, dividends not included):
    old high   the highest close before the fall
    fall       a close at least 13% below the old high
    clock      starts on the first close 13% below the old high
               (also reported: from the old high itself)
    recovered  the first close at or above the old high
    bottom     the lowest close between the old high and recovery
Falls counted: those whose first -13% close is on or after 1 Jan 2016.
The data starts in Feb 2012. Nifty passed its 2010 high in 2014, so every old high used here
is a true all-time high.

Writes results/falls.csv and results/summary.txt, plus the same table at 10%, 15% and 20%
to check the result doesn't depend on the 13% line.
"""
import os

import pandas as pd

DATA = os.path.join("data", "nifty 50.csv")
FROM = pd.Timestamp("2016-01-01")
LINES = [0.13, 0.10, 0.15, 0.20]


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
    d = pd.read_csv(DATA, parse_dates=["Date"])[["Date", "Close"]].sort_values("Date").reset_index(drop=True)
    d["peak"] = d.Close.cummax()
    d["dd"] = d.Close / d.peak - 1
    os.makedirs("results", exist_ok=True)
    L = [f"Nifty 50 price index, {d.Date.min().date()} to {d.Date.max().date()}. "
         f"Falls whose first line-crossing is on or after {FROM.date()}.", ""]
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
