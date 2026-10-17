"""
Three ways to deploy Rs 1,00,000 after a 10% fall in Nifty 50 (NIFTYBEES).

Usage:  python backtest.py path/to/niftybees.csv
Data:   EOD2 daily file (github.com/BennyThadikaran/eod2_data, daily/niftybees.csv)
Output: prints a table per fall plus a summary, and writes results.csv

Path A: buy NIFTYBEES the next day.
Path B: park in cash, move 1/6 into NIFTYBEES every 21 trading days (6 instalments).
Path C: park in cash, move everything into NIFTYBEES the day after the close
        crosses above its 50-day simple moving average. If the close is already
        above the 50 DMA on the trigger day, buy the next day (same as Path A).

Rules
- Trigger: NIFTYBEES close is 10% or more below its highest close so far.
- A new trigger needs a new closing high first (one correction = one event).
- Fills at the NEXT DAY'S CLOSE. (NIFTYBEES opens in this data carry stray
  pre-open auction prints, so opens are not used.)
- Cash earns a fixed 6% a year (stands in for LIQUIDBEES, whose price stays
  near Rs 1,000 because it pays its return as extra units).
- Every path is measured over the same 252 trading days from the trigger day,
  then everything is sold at that day's close.
- Post-entry drawdown = worst value of the whole Rs 1,00,000 below Rs 1,00,000
  during the window, cash included.
- Fractional units. Price only: NIFTYBEES dividends are not added back.

Costs (Zerodha, NSE delivery, per side, as a share of trade value)
- NIFTYBEES (equity ETF): STT 0.001% sell only.
- Cash/LIQUIDBEES: no STT.
- Exchange 0.00307% + SEBI 0.0001% each side, GST 18% on those,
  stamp duty 0.015% buy side.
- DP charge Rs 15.34 per scrip per sell day.
"""
import sys
import pandas as pd

DATA = sys.argv[1] if len(sys.argv) > 1 else "niftybees.csv"
CAPITAL = 100_000
DROP = 0.10
WINDOW = 252
STEP = 21
N_INST = 6
CASH_RATE = 0.06
DAILY_CASH = (1 + CASH_RATE) ** (1 / 252) - 1

EXCH, SEBI, STAMP, GST = 0.0000307, 0.000001, 0.00015, 0.18
BUY = EXCH + SEBI + STAMP + GST * (EXCH + SEBI)
SELL_EQ = EXCH + SEBI + 0.00001 + GST * (EXCH + SEBI)
SELL_CASH = EXCH + SEBI + GST * (EXCH + SEBI)
DP = 15.34

NAMES = {"A": "Buy now", "B": "Spread 6 months", "C": "Wait for 50 DMA"}


def load(path):
    d = pd.read_csv(path, parse_dates=["Date"]).set_index("Date").sort_index()
    c = d["Close"].astype(float).copy()
    c[c.index < "2019-12-19"] /= 10  # 1:10 unit split on 2019-12-19
    return c


def find_events(c, sma):
    events, peak, armed = [], c.iloc[0], True
    for i in range(len(c)):
        p = c.iloc[i]
        if p > peak:
            peak, armed = p, True
        elif armed and p <= peak * (1 - DROP) and not pd.isna(sma.iloc[i]):
            events.append(i)
            armed = False
    return events


def run_path(c, sma, t, path):
    """Daily value of the Rs 1L from trigger day t to t+WINDOW, then sold."""
    end = t + WINDOW
    units, cash, value, entry_day = 0.0, 0.0, [], None
    buy_days = {}
    if path == "A":
        buy_days = {t + 1: 1.0}
    elif path == "B":
        buy_days = {t + 1 + k * STEP: 1 / N_INST for k in range(N_INST)}
    elif path == "C" and c.iloc[t] > sma.iloc[t]:
        buy_days = {t + 1: 1.0}

    # money not bought on day t+1 goes into cash (LIQUIDBEES) on day t+1
    in_cash = path != "A" and not (path == "C" and buy_days)
    if in_cash:
        cash = CAPITAL * (1 - BUY)
        uninvested = 0.0
    else:
        uninvested = CAPITAL

    remaining = 1.0
    for i in range(t + 1, end + 1):
        cash *= 1 + DAILY_CASH
        # Path C signal: close crossed above the 50 DMA yesterday -> buy today
        if path == "C" and not buy_days and in_cash and i - 1 > t:
            j = i - 1
            if c.iloc[j] > sma.iloc[j] and c.iloc[j - 1] <= sma.iloc[j - 1]:
                buy_days = {i: 1.0}
        if i in buy_days:
            frac = buy_days[i] / remaining
            if in_cash:
                amount = cash * frac
                cash -= amount
                amount = amount * (1 - SELL_CASH) - DP
            else:
                amount = uninvested * frac
                uninvested -= amount
            units += amount * (1 - BUY) / c.iloc[i]
            remaining -= buy_days[i]
            entry_day = entry_day or i
        value.append(units * c.iloc[i] + cash + uninvested)

    final = units * c.iloc[end] * (1 - SELL_EQ) - (DP if units else 0)
    final += cash * (1 - SELL_CASH) - (DP if cash > 1 else 0) + uninvested
    worst = min(value)
    return {
        "return": final / CAPITAL - 1,
        "drawdown": max(0.0, 1 - worst / CAPITAL),
        "entry": c.index[entry_day].date() if entry_day else None,
        "invested": entry_day is not None,
        "values": value,
    }


def main():
    c = load(DATA)
    sma = c.rolling(50).mean()
    rows = []
    for t in find_events(c, sma):
        if t + WINDOW >= len(c):
            print(f"Skipped {c.index[t].date()}: fewer than {WINDOW} days of data after it")
            continue
        row = {"trigger": c.index[t].date(),
               "next_12m_low": c.iloc[t:t + WINDOW + 1].min() / c.iloc[t] - 1}
        for p in "ABC":
            r = run_path(c, sma, t, p)
            row[f"{p}_ret"], row[f"{p}_dd"] = r["return"], r["drawdown"]
            if p == "C":
                row["C_entry"] = r["entry"]
        rows.append(row)

    df = pd.DataFrame(rows)
    pct = lambda s: s.map(lambda x: f"{x*100:6.1f}%")
    show = df.copy()
    for col in df.columns:
        if col.endswith(("_ret", "_dd", "_low")):
            show[col] = pct(df[col])
    print(show.to_string(index=False))
    print(f"\nEvents: {len(df)}")
    for p in "ABC":
        print(f"{NAMES[p]:<16}: avg return {df[p+'_ret'].mean()*100:5.1f}%  "
              f"median {df[p+'_ret'].median()*100:5.1f}%  "
              f"avg drawdown {df[p+'_dd'].mean()*100:4.1f}%  "
              f"worst drawdown {df[p+'_dd'].max()*100:4.1f}%  "
              f"losing years {(df[p+'_ret'] < 0).sum()}")
    best = df[["A_ret", "B_ret", "C_ret"]].idxmax(axis=1).str[0].value_counts()
    print("Best of the three:", {NAMES[k]: int(v) for k, v in best.items()})
    a_b = (df.A_ret > df.B_ret).sum(), (df.B_ret > df.A_ret).sum()
    eps = 1e-9
    c_a = ((df.C_ret > df.A_ret + eps).sum(), (df.C_ret < df.A_ret - eps).sum(),
           ((df.C_ret - df.A_ret).abs() <= eps).sum())
    print(f"Buy now vs Spread: {a_b[0]}-{a_b[1]}")
    print(f"Wait vs Buy now: won {c_a[0]}, lost {c_a[1]}, tied {c_a[2]}")
    df.round(6).to_csv("results.csv", index=False)


if __name__ == "__main__":
    main()