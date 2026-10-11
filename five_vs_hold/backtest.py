"""
backtest.py - four popular strategies against simply holding NIFTYBEES,
all on one shared setup. (Momentum rotation, the fifth strategy, is in ../etf_momentum/.)

Shared setup
  * Test window: first trading day on or after 1 Oct 2016, to 25 Sep 2026 (last day in the data).
  * Signals come from the Nifty 50 index divided by 100. The index has no pre-open auction
    prints, which distort NIFTYBEES' own opens, highs and lows. Data from Oct 2015 warms up
    the indicators.
  * Every trade uses the real NIFTYBEES closing price on the next trading day after the
    signal (the 1:10 unit split of 19 Dec 2019 is adjusted). If NIFTYBEES has no price that
    day, the next available close is used.
  * Whole units, all available cash in each trade, idle cash earns nothing.
  * Zerodha delivery charges at equity-ETF statutory rates, the same as ../etf_dukan.
    The bid-ask spread is not included.
  * Positions still open on the last day are sold at that close, charges included.

Strategies
  * Supertrend 10, 3: hold while Supertrend is green, sell to cash when it turns red. Long only.
  * Golden cross: hold while the 50-day exponential average is above the 200-day one.
  * 44 moving average pullback: its own rules (see ../sma44/), with a 1:2 target. Entries,
    stops and targets use the index scaled to NIFTYBEES prices.
  * ETF ki Dukan: ../etf_dukan/etf_dukan_v1.py run unchanged on its 83-ETF list.
  * Holding NIFTYBEES: buy on the first day, sell on the last.

Usage:  python fetch_data.py   then   python backtest.py
"""
import os, sys, hashlib
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "etf_dukan"))
from etf_dukan_v1 import buy_cost, sell_cost, load, scores, run as dukan_run
import etf_dukan_v1

T0, T1 = "2016-10-01", "2026-09-25"
DATA = os.path.join(HERE, "data")
n = pd.read_csv(os.path.join(DATA, "NIFTY50.csv"), parse_dates=["Date"]).drop_duplicates("Date").set_index("Date").sort_index()
n = n.loc["2015-10-01":]
P = n[["Open", "High", "Low", "Close"]] / 100.0
nb = pd.read_csv(os.path.join(DATA, "NIFTYBEES.csv"), parse_dates=["Date"]).drop_duplicates("Date").set_index("Date").Close
nb[nb.index < "2019-12-19"] /= 10.0
P = P.loc[:T1]
days = P.index
nb_on = nb.reindex(days)
nbf = nb.reindex(days).ffill()
k = nbf / P.Close
test_days = days[days >= T0]
d0, d1 = test_days[0], test_days[-1]


def fill_close(i):
    while i < len(days) and np.isnan(nb_on.iloc[i]):
        i += 1
    return (i, nb_on.iloc[i]) if i < len(days) else (None, None)


def cagr(v0, v1):
    return (v1 / v0) ** (365.25 / (d1 - d0).days) - 1


def max_dd(s):
    return (s / s.cummax() - 1).min()


def run_signal(want, capital):
    cash, units, trades = capital, 0, []
    eq = pd.Series(np.nan, index=test_days)
    pending = None
    idx = {d: i for i, d in enumerate(days)}
    i0 = idx[d0]
    prev = bool(want.iloc[i0 - 1])
    for i in range(i0, len(days)):
        t = days[i]
        if pending is not None and i == pending[1] + 1:
            j, px = fill_close(i)
            if j == i:
                if pending[0] == "buy" and units == 0:
                    u = int(cash // (px * (1 + 0.0002)))
                    while u > 0 and u * px + buy_cost(u * px) > cash:
                        u -= 1
                    if u > 0:
                        cash -= u * px + buy_cost(u * px); units = u
                        trades.append(dict(sig=days[pending[1]], buy_date=t, buy=px, units=u))
                elif pending[0] == "sell" and units > 0:
                    v = units * px; cash += v - sell_cost(v); units = 0
                    trades[-1].update(sell_sig=days[pending[1]], sell_date=t, sell=px)
                pending = None
            else:
                pending = (pending[0], i)
        w = bool(want.iloc[i])
        if w and not prev and units == 0:
            pending = ("buy", i)
        elif not w and prev and units > 0:
            pending = ("sell", i)
        prev = w
        eq[t] = cash + units * nbf.iloc[i]
    if units:
        v = units * nbf.iloc[-1]
        cash += v - sell_cost(v); trades[-1].update(sell_date=d1, sell=v / units)
    return cash, eq, pd.DataFrame(trades)


def supertrend(df, n=10, m=3.0):
    h, l, c = df.High, df.Low, df.Close
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    mid = (h + l) / 2
    ub, lb = (mid + m * atr).values, (mid - m * atr).values
    fu, fl, up = ub.copy(), lb.copy(), np.zeros(len(df), bool)
    cv = c.values
    for i in range(1, len(df)):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or cv[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or cv[i - 1] < fl[i - 1]) else fl[i - 1]
        up[i] = (cv[i] >= fl[i]) if up[i - 1] else (cv[i] > fu[i])
    return pd.Series(up, index=df.index)


def golden(df):
    c = df.Close
    return c.ewm(span=50, adjust=False).mean() > c.ewm(span=200, adjust=False).mean()


def sma44(capital, R=2.0, tick=0.05):
    O, H, L, C = (P[x] * k for x in ["Open", "High", "Low", "Close"])
    sma = C.rolling(44).mean()
    rising = sma >= sma.shift(5) * 1.005
    away = L > sma * 1.01
    cash, units, trades = capital, 0, []
    eq = pd.Series(np.nan, index=test_days)
    visit_used, order, pos = False, None, None
    for i, t in enumerate(days):
        if i < 50:
            continue
        intest = t >= d0
        if pos:
            o, h, l = O.iloc[i], H.iloc[i], L.iloc[i]
            ex = None
            if o <= pos["stop"]: ex = o
            elif o >= pos["tgt"]: ex = o
            elif l <= pos["stop"]: ex = pos["stop"]
            elif h >= pos["tgt"]: ex = pos["tgt"]
            if ex is not None:
                v = units * ex; cash += v - sell_cost(v)
                trades[-1].update(sell_date=t, sell=ex); units, pos = 0, None
        if order and not pos:
            o, h, l = O.iloc[i], H.iloc[i], L.iloc[i]
            if o > order["entry"] or o <= order["stop"]:
                order = None
            elif h >= order["entry"]:
                px = order["entry"]
                u = int(cash // px)
                while u > 0 and u * px + buy_cost(u * px) > cash: u -= 1
                if u > 0:
                    cash -= u * px + buy_cost(u * px); units = u
                    pos = dict(stop=order["stop"], tgt=px + R * (px - order["stop"]))
                    trades.append(dict(buy_date=t, buy=px, units=u, stop=order["stop"]))
                    if l <= pos["stop"]:
                        v = units * pos["stop"]; cash += v - sell_cost(v)
                        trades[-1].update(sell_date=t, sell=pos["stop"]); units, pos = 0, None
                order = None
            else:
                order["left"] -= 1
                if order["left"] == 0: order = None
        if away.iloc[i]:
            visit_used = False
        touch = abs(L.iloc[i] / sma.iloc[i] - 1) <= 0.01
        if (intest and rising.iloc[i] and touch and C.iloc[i] > O.iloc[i]
                and not visit_used and not pos):
            visit_used = True
            order = dict(entry=H.iloc[i] + tick, stop=L.iloc[i] - tick, left=3)
        if intest:
            eq[t] = cash + units * C.iloc[i]
    if units:
        v = units * nbf.iloc[-1]; cash += v - sell_cost(v)
        trades[-1].update(sell_date=d1, sell=v / units)
    return cash, eq, pd.DataFrame(trades)


def hold(capital):
    j, px = fill_close(days.get_loc(d0))
    u = int(capital // px)
    while u * px + buy_cost(u * px) > capital: u -= 1
    left = capital - u * px - buy_cost(u * px)
    eq = left + u * nb.reindex(test_days).ffill()
    last = nbf.iloc[-1]
    return left + u * last - sell_cost(u * last), eq


def dukan(capital):
    lst = pd.read_csv(os.path.join(HERE, "..", "etf_dukan", "etf_list_2023-04-02.csv"))
    Cd = load(lst.symbol.tolist(), DATA).loc[:T1]
    etf_dukan_v1.START = str(d0.date())
    R = dukan_run(Cd, scores(Cd), capital)
    return R["liquidated"], R["E"].equity, R["sales"], R


if __name__ == "__main__":
    out = os.path.join(HERE, "results"); os.makedirs(out, exist_ok=True)
    print(f"Window {d0.date()} to {d1.date()}\n")
    for cap in (1_000_000, 10_000):
        rows = []
        f, e = hold(cap); rows.append(("Hold NIFTYBEES", f, e, 1, None))
        f, e, t = run_signal(supertrend(P), cap); rows.append(("Supertrend 10,3", f, e, len(t), t))
        f, e, t = run_signal(golden(P), cap); rows.append(("Golden cross EMA 50/200", f, e, len(t), t))
        f, e, t = sma44(cap); rows.append(("44 MA pullback 1:2", f, e, len(t), t))
        f, e, t, _ = dukan(cap); rows.append(("ETF ki Dukan", f, e, len(t), t))
        print(f"Capital Rs {cap:,}")
        for name, f, e, nt, t in rows:
            print(f"  {name:26s} Rs {f:>12,.0f}  {100*cagr(cap,f):6.2f}% a year  worst fall {100*max_dd(e.dropna()):6.1f}%  trades {nt}")
            if t is not None:
                fn = os.path.join(out, f"trades_{name.split()[0].lower()}_{cap}.csv")
                t.to_csv(fn, index=False)
        print()
    print("SHA-256 of the trade logs:")
    for fn in sorted(os.listdir(out)):
        print(" ", fn, hashlib.sha256(open(os.path.join(out, fn), "rb").read()).hexdigest()[:16])
