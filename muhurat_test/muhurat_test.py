"""Does buying Nifty 50 on the Diwali Muhurat day beat buying on an ordinary day?

Test rules (fixed before running):
  1. Exit day: entry date + 365 calendar days. If that is not a trading day,
     use the close of the next trading day. Any date present in the data file
     counts as a trading day.
  2. Ordinary entry days: every Monday-Friday trading day in the data, except
     the Muhurat days. An entry counts only if its exit day exists in the data.
  3. Fair comparison: for each Muhurat year, the ordinary days within 30 calendar
     days either side of that Muhurat day.
  4. Verdict: draw one ordinary day from each year's window (22 picks), repeat
     10,000 times, take the median return of each draw. Muhurat is called lucky
     only if its median return is above the 95th percentile of those medians.
  5. Return: close to close on the Nifty 50 price index. No dividends, no costs, no tax.
  6. Sample size: 22 Muhurat entries. Windows overlap, so results are not independent.

Usage:  python3 muhurat_test.py nifty_combined.csv results_dir
Input:  CSV with columns date (YYYY-MM-DD) and close.
"""
import csv, datetime as dt, os, random, statistics, sys

MUHURAT = [  # Diwali Muhurat trading days, 2004-2025
    "2004-11-12", "2005-11-01", "2006-10-21", "2007-11-09", "2008-10-28", "2009-10-17",
    "2010-11-05", "2011-10-26", "2012-11-13", "2013-11-03", "2014-10-23", "2015-11-11",
    "2016-10-30", "2017-10-19", "2018-11-07", "2019-10-27", "2020-11-14", "2021-11-04",
    "2022-10-24", "2023-11-12", "2024-11-01", "2025-10-21",
]
HOLD_DAYS = 365
WINDOW_DAYS = 30
DRAWS = 10_000
PERCENTILE = 95
SEED = 42


def load(path):
    close = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            close[dt.date.fromisoformat(r["date"])] = float(r["close"])
    return close


def pct(sorted_vals, p):
    k = (len(sorted_vals) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def main(data_path, out_dir):
    close = load(data_path)
    days = sorted(close)
    last = days[-1]
    muhurat = [dt.date.fromisoformat(d) for d in MUHURAT]
    missing = [d for d in muhurat if d not in close]
    if missing:
        sys.exit(f"Muhurat days missing from data: {missing}")

    def exit_of(entry):
        target = entry + dt.timedelta(days=HOLD_DAYS)
        if target > last:
            return None
        # first trading day on or after target
        lo, hi = 0, len(days)
        while lo < hi:
            mid = (lo + hi) // 2
            if days[mid] < target:
                lo = mid + 1
            else:
                hi = mid
        return days[lo] if lo < len(days) else None

    def ret(entry):
        ex = exit_of(entry)
        return None if ex is None else (ex, close[ex] / close[entry] - 1)

    mset = set(muhurat)
    ordinary = {}
    for d in days:
        if d.weekday() < 5 and d not in mset:
            r = ret(d)
            if r is not None:
                ordinary[d] = r[1]

    # Muhurat entries
    rows, m_returns, windows = [], [], []
    for d in muhurat:
        ex, r = ret(d)
        m_returns.append(r)
        win = [(e, v) for e, v in ordinary.items() if abs((e - d).days) <= WINDOW_DAYS]
        windows.append([v for _, v in win])
        wv = sorted(v for _, v in win)
        rank = sum(v < r for v in wv) / len(wv) * 100
        rows.append({
            "muhurat_date": d.isoformat(), "weekday": d.strftime("%a"),
            "entry_close": close[d], "exit_date": ex.isoformat(), "exit_close": close[ex],
            "return_pct": round(r * 100, 2),
            "window_days": len(win), "window_median_pct": round(statistics.median(wv) * 100, 2),
            "muhurat_minus_window_median_pct": round((r - statistics.median(wv)) * 100, 2),
            "rank_in_window_pct": round(rank, 1),
        })

    # simulation
    rng = random.Random(SEED)
    sim_medians, sim_means = [], []
    for _ in range(DRAWS):
        pick = [rng.choice(w) for w in windows]
        sim_medians.append(statistics.median(pick))
        sim_means.append(statistics.fmean(pick))
    sim_medians.sort(); sim_means.sort()

    m_med, m_mean = statistics.median(m_returns), statistics.fmean(m_returns)
    thr = pct(sim_medians, PERCENTILE)
    all_vals = list(ordinary.values())
    lucky = m_med > thr

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "muhurat_by_year.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    lines = [
        f"Data: {days[0]} to {last}, {len(days)} days",
        f"Muhurat entries: {len(m_returns)}  (exit on or before {last})",
        f"Ordinary entry days with an exit: {len(ordinary)}",
        "",
        f"Muhurat 1-year return:  median {m_med*100:.2f}%   mean {m_mean*100:.2f}%   "
        f"positive {sum(r > 0 for r in m_returns)} of {len(m_returns)}",
        f"All ordinary days:      median {statistics.median(all_vals)*100:.2f}%   "
        f"mean {statistics.fmean(all_vals)*100:.2f}%   "
        f"positive {sum(v > 0 for v in all_vals)/len(all_vals)*100:.1f}%",
        "",
        f"Same-season draws ({DRAWS} x 22 picks, seed {SEED}):",
        f"  median of medians {pct(sim_medians,50)*100:.2f}%   "
        f"5th {pct(sim_medians,5)*100:.2f}%   95th {thr*100:.2f}%",
        f"  Muhurat median beats {sum(x < m_med for x in sim_medians)/DRAWS*100:.1f}% of draws"
        f"   (mean beats {sum(x < m_mean for x in sim_means)/DRAWS*100:.1f}% of mean-draws)",
        f"  Muhurat days beat their own window median in "
        f"{sum(r['muhurat_minus_window_median_pct'] > 0 for r in rows)} of {len(rows)} years",
        "",
        f"VERDICT (95th-percentile rule): {'LUCKY' if lucky else 'NO EVIDENCE OF LUCK'}",
    ]
    text = "\n".join(lines)
    with open(os.path.join(out_dir, "summary.txt"), "w") as f:
        f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
