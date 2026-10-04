"""
etf_dukan_v1.py - backtest of the "ETF shop" (version 1) on the creator's own
83-ETF list of 2 April 2023, from 3 April 2023 to the last date in the data.

Rules, as stated in the creator's videos:
  * Each day, rank ETFs by how far the close sits below its 20-day average
    (close / SMA20 - 1, most negative first). Look at the top 3.
  * Buy one ETF a day, sized at capital / 60.
  * Priority: the best-ranked top-3 ETF not already held.
    If all three are held, buy (average) the best-ranked one whose close is more
    than 2.5% below its last purchase price. If none qualifies, skip the day.
  * Sell at a 6% profit over average cost.

Readings where the videos are silent (stated, not the creator's):
  * Trades happen at the close (his fallback order price).
  * Every held ETF at +6% or more over average cost is sold that close; no daily limit.
  * Buy size stays fixed at starting capital / 60.
  * Whole units, rounded to the nearest unit, minimum one unit.
  * If cash is short, the buy is skipped. No averaging cap.
  * An ETF sold today is not bought back the same day (counted separately).

Costs: Zerodha delivery, equity-ETF statutory rates (rates verified 2026-09-09),
applied to every ETF. Gold, silver and international ETFs pay no STT, so this
overstates their cost by 0.001% of the sale. Statutory only; excludes the spread.
"""
import math
import numpy as np
import pandas as pd

TXN, SEBI, GST = 0.0000307, 10 / 1e7, 0.18
STAMP_BUY, STT_SELL, DP = 0.00015, 0.00001, 15.34

def buy_cost(v):  return v * (TXN + SEBI) * (1 + GST) + v * STAMP_BUY
def sell_cost(v): return v * (TXN + SEBI) * (1 + GST) + v * STT_SELL + DP

START = "2023-04-03"
SMA_N, TOP_N, TARGET, AVG_DROP, SLOTS = 20, 3, 0.06, 0.025, 60
SPLIT_LIMIT = 0.6


def load(symbols, folder="."):
    C = {}
    for s in symbols:
        x = pd.read_csv(f"{folder}/{s}.csv", parse_dates=["Date"])
        x = x.drop_duplicates("Date").set_index("Date").sort_index()
        c = x["Close"].astype(float)
        c = c[c > 0]
        r = c / c.shift(1)
        for dt in r[r < SPLIT_LIMIT].index:            # unadjusted splits
            f = round(1 / r[dt])
            c[c.index < dt] = c[c.index < dt] / f
        C[s] = c
    return pd.DataFrame(C).sort_index()


def scores(C):
    """close / own 20-day average - 1, using each ETF's own trading days."""
    S = pd.DataFrame(index=C.index, columns=C.columns, dtype=float)
    for s in C.columns:
        c = C[s].dropna()
        S.loc[c.index, s] = (c / c.rolling(SMA_N).mean() - 1).values
    return S


def run(C, S, capital):
    size = capital / SLOTS
    cash = capital
    pos = {}            # sym -> dict(units, cost_basis, last_buy, first_buy, n_buys)
    sales, buys, equity, skipped_cash, rebuy_blocked = [], [], [], 0, 0
    last_px = C.ffill()
    days = C.index[C.index >= START]
    for t in days:
        px = C.loc[t]
        sold_today = set()
        # sells
        for s in list(pos):
            p = px[s]
            if np.isnan(p):
                continue
            q = pos[s]
            avg = q["basis"] / q["units"]
            if p >= avg * (1 + TARGET):
                v = q["units"] * p
                c = sell_cost(v)
                cash += v - c
                sales.append(dict(sym=s, date=t, first_buy=q["first"], buys=q["n"],
                                  units=q["units"], basis=q["basis"], proceeds=v, cost=c,
                                  net=v - c - q["basis"], gross=v - q["basis"]))
                sold_today.add(s)
                del pos[s]
        # buy
        top = S.loc[t].dropna().sort_values().index[:TOP_N].tolist()
        pick = None
        for s in top:
            if s not in pos:
                if s in sold_today:
                    rebuy_blocked += 1
                    continue
                pick = s
                break
        if pick is None:
            for s in top:
                if s in pos and px[s] < pos[s]["last"] * (1 - AVG_DROP):
                    pick = s
                    break
        if pick is not None:
            p = px[pick]
            u = max(1, round(size / p))
            v = u * p
            c = buy_cost(v)
            if v + c <= cash:
                cash -= v + c
                q = pos.setdefault(pick, dict(units=0, basis=0.0, last=p, first=t, n=0))
                q["units"] += u
                q["basis"] += v + c
                q["last"] = p
                q["n"] += 1
                buys.append(dict(sym=pick, date=t, price=p, units=u, value=v, cost=c,
                                 averaging=q["n"] > 1))
            else:
                skipped_cash += 1
        held = sum(q["units"] * last_px.at[t, s] for s, q in pos.items())
        equity.append((t, cash, held))
    E = pd.DataFrame(equity, columns=["date", "cash", "held"]).set_index("date")
    E["equity"] = E.cash + E.held
    end = days[-1]
    open_rows = []
    for s, q in pos.items():
        p = last_px.at[end, s]
        open_rows.append(dict(sym=s, first_buy=q["first"], buys=q["n"], units=q["units"],
                              basis=q["basis"], value=q["units"] * p,
                              pnl_pct=q["units"] * p / q["basis"] - 1,
                              days_held=(end - q["first"]).days))
    liq = E.equity.iloc[-1] - sum(sell_cost(r["value"]) for r in open_rows)
    return dict(E=E, sales=pd.DataFrame(sales), buys=pd.DataFrame(buys),
                open=pd.DataFrame(open_rows), liquidated=liq,
                skipped_cash=skipped_cash, rebuy_blocked=rebuy_blocked, size=size)


def hold_basket(C, capital, syms):
    """Buy each symbol equally at the first close, hold, sell at the last close."""
    days = C.index[C.index >= START]
    t0, t1 = days[0], days[-1]
    syms = [s for s in syms if not np.isnan(C.at[t0, s])]
    each = capital / len(syms)
    L = C.ffill()
    val = pd.Series(0.0, index=days)
    spent = 0.0
    finals = 0.0
    for s in syms:
        p0 = C.at[t0, s]
        u = max(1, round(each / p0))
        spent += u * p0 + buy_cost(u * p0)
        val += u * L.loc[days, s]
        finals += sell_cost(u * L.at[t1, s])
    val += capital - spent
    return val, val.iloc[-1] - finals, len(syms)


def cagr(v0, v1, d0, d1):
    return (v1 / v0) ** (365.25 / (d1 - d0).days) - 1


def max_dd(s):
    return (s / s.cummax() - 1).min()


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    lst = pd.read_csv(os.path.join(here, "etf_list_2023-04-02.csv"))
    syms = lst.symbol.tolist()
    metal = lst[lst.underlying.str.lower().str.contains("gold|silver")].symbol.tolist()
    C = load(syms, os.path.join(here, "data"))
    S = scores(C)
    days = C.index[C.index >= START]
    d0, d1 = days[0], days[-1]
    print(f"Test period: {d0.date()} to {d1.date()}\n")
    for cap in (200_000, 10_000):
        R = run(C, S, cap)
        E, sl, op = R["E"], R["sales"], R["open"]
        liq = R["liquidated"]
        nb, nbl, _ = hold_basket(C, cap, ["NIFTYBEES"])
        print(f"Capital Rs {cap:,} (Rs {R['size']:.0f} a buy)")
        print(f"  Strategy:        Rs {liq:,.0f}  {100*cagr(cap, liq, d0, d1):5.2f}% a year  worst fall {100*max_dd(E.equity):.1f}%")
        print(f"  Hold NIFTYBEES:  Rs {nbl:,.0f}  {100*cagr(cap, nbl, d0, d1):5.2f}% a year  worst fall {100*max_dd(nb):.1f}%")
        print(f"  Sales {len(sl)}, losing after charges {(sl.net <= 0).sum()}; open at end {len(op)}, "
              f"below cost {(op.pnl_pct < 0).sum()}; average share invested {100*(E.held/E.equity).mean():.0f}%")
        if cap >= 100_000:
            ew, ewl, n = hold_basket(C, cap, syms)
            nm, nml, k = hold_basket(C, cap, [s for s in syms if s not in metal])
            print(f"  Hold all {n} equally:            {100*cagr(cap, ewl, d0, d1):5.2f}% a year")
            print(f"  Hold the {k} without gold/silver: {100*cagr(cap, nml, d0, d1):5.2f}% a year")
        os.makedirs(os.path.join(here, "results"), exist_ok=True)
        for name, df in (("sales", sl), ("buys", R["buys"]), ("open", op)):
            df.to_csv(os.path.join(here, "results", f"{name}_{cap}.csv"), index=False)
        E.to_csv(os.path.join(here, "results", f"equity_{cap}.csv"))
        print()
