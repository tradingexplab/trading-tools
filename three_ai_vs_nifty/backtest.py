"""Backtest of the Fable 5.2 swing strategy (buy short pullbacks in uptrends), Nifty 50 point-in-time universe.

Conventions:
  - Daily bars. Wilder RSI(3) and ATR(14). EMA(20) seeded from a 20-day SMA. 200 days of data before any signal.
  - Signal at the close of day t. Buy-stop at high_t * 1.001 live for sessions t+1..t+3.
  - Open >= trigger fills at the open; open > trigger*1.02 cancels the order for good; else fill at trigger if high >= trigger.
  - Entry day: only the stop is checked (stop first). Targets and the +1R high count from the next session.
  - Same bar: stop first. Gap through a stop or target fills at the open.
  - Stop = E - 2*ATR(signal day). T1 = E + 4*ATR: sell int(q/2), stop moves to E.
    Worst case after T1 on the same bar: if low <= E the rest exits at E.
  - After T1: exit all at the next open after any close below EMA(20).
  - Time stop: entry day = session 0. If the highs of sessions 1..10 never reached E + 2*ATR, sell at the open of session 11.
  - Sizing: min(1% of equity / (2*ATR), 20% of equity / price), equity marked at the signal close.
    Pending buy-stops count toward the 5-position cap. Nifty below its 200-day SMA blocks new entries only.
  - Slippage 0.15% each side on every fill. Statutory costs from costs.py. DP fee once per scrip per sell day.
  - Unadjusted corporate-action days (EVENTS): no signal from 3 sessions before to 14 sessions after; an open position
    is closed at the prior close and flagged event_void.
  - Holdings continue after a stock leaves the index; only new entries need membership.
"""
import os
import sys
import csv
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import costs

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "daily") + os.sep          # eod2 daily CSVs go here (see README)
MEM = os.path.join(HERE, "nifty50_membership_2016_2026.csv")  # point-in-time Nifty 50 members
OUT = os.path.join(HERE, "results") + os.sep
EVENTS = {"tmpv.csv": "2025-10-14", "shriramfin.csv": "2025-01-10",
          "powergrid.csv": "2023-09-12", "reliance.csv": "2023-07-20"}
START = "2016-01-01"
END = "2026-11-09"   # last session used in the video; set to None to run on all data

BASE = dict(capital=100000.0, risk=0.01, cap=0.20, max_pos=5, rsi_thr=20.0, stop_mult=2.0, tgt_mult=4.0,
            slip=0.0015, buf=0.001, gap_max=0.02, order_days=3, time_bars=10, idx_filter=True)


# ---------- indicators ----------
def wilder_rsi(c, n):
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    d = np.diff(c)
    g = np.where(d > 0, d, 0.0)
    l = np.where(d < 0, -d, 0.0)
    ag, al = g[:n].mean(), l[:n].mean()
    out[n] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(n, len(d)):
        ag = (ag * (n - 1) + g[i]) / n
        al = (al * (n - 1) + l[i]) / n
        out[i + 1] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def wilder_atr(h, l, c, n):
    pc = np.r_[np.nan, c[:-1]]
    tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    tr[0] = h[0] - l[0]
    out = np.full(len(c), np.nan)
    if len(c) < n:
        return out
    out[n - 1] = tr[:n].mean()
    for i in range(n, len(c)):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def ema_seeded(c, n):
    out = np.full(len(c), np.nan)
    if len(c) < n:
        return out
    out[n - 1] = c[:n].mean()
    a = 2.0 / (n + 1)
    for i in range(n, len(c)):
        out[i] = out[i - 1] + a * (c[i] - out[i - 1])
    return out


def read_bars(path):
    df = pd.read_csv(path, usecols=["Date", "Open", "High", "Low", "Close"], parse_dates=["Date"])
    df = df.dropna().drop_duplicates("Date").sort_values("Date").set_index("Date")
    return df[(df["Close"] > 0) & (df["High"] >= df["Low"])]


# ---------- data ----------
def prepare():
    ix = read_bars(DATA + "nifty 50.csv")["Close"]
    if END:
        ix = ix[ix.index <= pd.Timestamp(END)]
    cal = ix.index
    n = len(cal)
    ctx = dict(cal=cal, n=n, ix=ix.to_numpy(float))
    ctx["idx_ok"] = (ix > ix.rolling(200).mean()).to_numpy()
    ctx["start"] = int(cal.searchsorted(pd.Timestamp(START)))
    rows = list(csv.DictReader(open(MEM, newline="")))
    per, skipped = {}, []
    for r in rows:
        f = (r["eod2_file"] or "").strip()
        if not f or not os.path.exists(DATA + f):
            skipped.append((r["symbol"], r["member_from"], r["member_until_exclusive"]))
            continue
        s = pd.Timestamp(r["member_from"])
        e = pd.Timestamp(r["member_until_exclusive"]) if r["member_until_exclusive"].strip() else pd.Timestamp("2100-01-01")
        d = per.setdefault(f, dict(sym=r["symbol"], iv=[]))
        d["iv"].append((s, e))
    arr = {}
    for f, d in per.items():
        df = read_bars(DATA + f)
        o, h, l, c = (df[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
        cs = pd.Series(c, index=df.index)
        cols = dict(
            o=df["Open"], h=df["High"], l=df["Low"], c=df["Close"],
            sma50=cs.rolling(50).mean(), sma200=cs.rolling(200).mean(), ret126=cs / cs.shift(126) - 1,
            rsi=pd.Series(wilder_rsi(c, 3), index=df.index), atr=pd.Series(wilder_atr(h, l, c, 14), index=df.index),
            ema20=pd.Series(ema_seeded(c, 20), index=df.index))
        a = {k: v.reindex(cal).to_numpy(float) for k, v in cols.items()}
        mem = np.zeros(n, bool)
        for s, e in d["iv"]:
            mem |= (cal >= s) & (cal < e)
        a["member"] = mem
        a["sym"] = d["sym"]
        ok = np.ones(n, bool)
        a["ev"] = -1
        if f in EVENTS:
            ie = int(cal.searchsorted(pd.Timestamp(EVENTS[f])))
            a["ev"] = ie
            ok[max(ie - 3, 0): ie + 15] = False
        a["ev_ok"] = ok
        arr[f] = a
    ctx["arr"], ctx["skipped"] = arr, skipped
    return ctx


# ---------- engine ----------
def run(ctx, P, tag=None):
    cal, n, A, start = ctx["cal"], ctx["n"], ctx["arr"], ctx["start"]
    cand = {}
    with np.errstate(invalid="ignore"):
        for f, a in A.items():
            s = (a["member"] & (a["rsi"] < P["rsi_thr"]) & (a["c"] > a["sma200"]) & (a["sma50"] > a["sma200"])
                 & (a["ret126"] > 0) & np.isfinite(a["atr"]) & np.isfinite(a["h"]) & a["ev_ok"])
            if P["idx_filter"]:
                s &= ctx["idx_ok"]
            for i in np.nonzero(s)[0]:
                if start <= i < n - 1:
                    cand.setdefault(int(i), []).append((a["ret126"][i], f))

    cash = P["capital"]
    pos, pend, trades, legs = {}, [], [], []
    last_c = {}
    eq = np.full(n, np.nan)
    expo = np.zeros(n)
    slip = P["slip"]
    st = dict(cash=cash)

    def sell(f, p, i, q, raw, reason):
        if q <= 0:
            return
        px = raw * (1 - slip)
        val = q * px
        newday = i not in p["dp_days"]
        p["dp_days"].add(i)
        c = costs.sell_cost(val, dp=newday)
        st["cash"] += val - c
        p["stat"] += c
        p["slipc"] += q * raw * slip
        p["proceeds"] += val - c
        p["qty"] -= q
        p["reasons"].append(reason)
        legs.append(dict(file=f, sym=A[f]["sym"], date=str(cal[i].date()), qty=q, raw=round(raw, 2),
                         reason=reason, cost=round(c, 2)))
        if p["qty"] == 0:
            p["exit_i"] = i
            pnl = p["proceeds"] - p["buy_out"]
            trades.append(dict(file=f, sym=A[f]["sym"], signal=str(cal[p["sig_i"]].date()),
                               entry=str(cal[p["entry_i"]].date()), exit=str(cal[i].date()),
                               E=round(p["E"], 2), qty=p["qty0"], atr=round(p["atr"], 2), stop0=round(p["stop0"], 2),
                               t1=round(p["t1"], 2), bars=i - p["entry_i"], reasons="|".join(p["reasons"]),
                               pnl=round(pnl, 2), R=round(pnl / (p["qty0"] * P["stop_mult"] * p["atr"]), 3),
                               stat=round(p["stat"], 2), slip=round(p["slipc"], 2), t1_hit=p["t1_hit"]))
            del pos[f]

    for i in range(start, n):
        # 1. corporate-action days: void open positions at the prior close
        for f in list(pos):
            if A[f]["ev"] == i:
                sell(f, pos[f], i, pos[f]["qty"], last_c.get(f, pos[f]["E"]), "event_void")
        # 2. manage open positions (entered before today)
        for f in list(pos):
            p = pos[f]
            a = A[f]
            o, h, l, c = a["o"][i], a["h"][i], a["l"][i], a["c"][i]
            if not np.isfinite(o):
                continue
            if p["pending"]:
                sell(f, p, i, p["qty"], o, p["pending"])
                continue
            if o <= p["stop"]:
                sell(f, p, i, p["qty"], o, "gap_stop" if not p["t1_hit"] else "gap_be_stop")
                continue
            if l <= p["stop"]:
                sell(f, p, i, p["qty"], p["stop"], "stop" if not p["t1_hit"] else "be_stop")
                continue
            k = i - p["entry_i"]
            if not p["t1_hit"]:
                if h >= p["t1"]:
                    px = max(o, p["t1"])
                    sell(f, p, i, p["qty0"] // 2, px, "t1")
                    p["t1_hit"] = True
                    p["stop"] = p["E"]
                    if l <= p["E"]:  # worst case: the low came after the target
                        sell(f, p, i, p["qty"], p["E"], "be_stop_same_bar")
                        continue
                if k <= P["time_bars"]:
                    p["maxh"] = max(p["maxh"], h)
                if k == P["time_bars"] and not p["t1_hit"] and p["maxh"] < p["E"] + P["stop_mult"] * p["atr"]:
                    p["pending"] = "time"
            if f in pos and p["t1_hit"] and np.isfinite(c) and np.isfinite(a["ema20"][i]) and c < a["ema20"][i]:
                p["pending"] = "ema"
        # 3. fill pending buy-stops
        for od in list(pend):
            f = od["f"]
            a = A[f]
            o, h, l = a["o"][i], a["h"][i], a["l"][i]
            if i <= od["sig_i"]:
                continue
            if not np.isfinite(o):
                if i >= od["last_i"]:
                    pend.remove(od)
                continue
            trig = od["trig"]
            fill = None
            if o > trig * (1 + P["gap_max"]):
                pend.remove(od)
                continue
            if o >= trig:
                fill = o
            elif h >= trig:
                fill = trig
            if fill is None:
                if i >= od["last_i"]:
                    pend.remove(od)
                continue
            pend.remove(od)
            q = min(od["q"], int(P["cap"] * od["eq"] / fill))
            pxs = fill * (1 + slip)
            q = min(q, int(st["cash"] / (pxs * 1.0013)))
            while q > 0 and q * pxs + costs.buy_cost(q * pxs) > st["cash"]:
                q -= 1
            if q < 1:
                continue
            bc = costs.buy_cost(q * pxs)
            st["cash"] -= q * pxs + bc
            atr = od["atr"]
            p = dict(qty=q, qty0=q, entry_i=i, sig_i=od["sig_i"], E=fill, atr=atr, stop=fill - P["stop_mult"] * atr,
                     stop0=fill - P["stop_mult"] * atr, t1=fill + P["tgt_mult"] * atr, t1_hit=False, maxh=-1e18,
                     pending=None, buy_out=q * pxs + bc, proceeds=0.0, stat=bc, slipc=q * fill * slip,
                     dp_days=set(), reasons=[])
            pos[f] = p
            last_c[f] = fill
            if l <= p["stop"]:  # entry day: stop first
                sell(f, p, i, p["qty"], p["stop"], "stop_entry_day")
        # 4. mark to market
        v = 0.0
        for f, p in pos.items():
            c = A[f]["c"][i]
            if np.isfinite(c):
                last_c[f] = c
            v += p["qty"] * last_c.get(f, p["E"])
        e = st["cash"] + v
        eq[i] = e
        expo[i] = v / e if e > 0 else 0.0
        assert len(pos) <= P["max_pos"] and len(pos) + len(pend) <= P["max_pos"], (cal[i], len(pos), len(pend))
        assert st["cash"] > -1e-6, (cal[i], st["cash"])
        # 5. new signals after the close
        if i in cand and i < n - 1:
            free = P["max_pos"] - len(pos) - len(pend)
            held = set(pos) | {o["f"] for o in pend}
            for rr, f in sorted(cand[i], reverse=True):
                if free <= 0:
                    break
                if f in held:
                    continue
                a = A[f]
                atr, trig = a["atr"][i], a["h"][i] * (1 + P["buf"])
                q = int(min(P["risk"] * e / (P["stop_mult"] * atr), P["cap"] * e / trig))
                if q < 1:
                    continue
                pend.append(dict(f=f, trig=trig, atr=atr, q=q, eq=e, sig_i=i, last_i=i + P["order_days"]))
                free -= 1
    res = metrics(ctx, P, eq, expo, trades, st["cash"], pos, last_c)
    res["trades_df"], res["legs_df"], res["eq"] = pd.DataFrame(trades), pd.DataFrame(legs), eq
    res["open_positions"] = {A[f]["sym"]: p["qty"] for f, p in pos.items()}
    if tag:
        os.makedirs(OUT, exist_ok=True)
        res["trades_df"].to_csv(OUT + f"trades_{tag}.csv", index=False)
        res["legs_df"].to_csv(OUT + f"legs_{tag}.csv", index=False)
        pd.DataFrame(dict(date=cal[start:], equity=eq[start:], nifty=res["bench"][start:])).to_csv(
            OUT + f"equity_{tag}.csv", index=False)
    return res


def maxdd(x):
    x = np.asarray(x, float)
    return float((x / np.maximum.accumulate(x) - 1).min())


def bench_curve(ctx, P):
    ix, s = ctx["ix"], ctx["start"]
    units = (P["capital"] - costs.DP_SELL) / (ix[s] * (1 + 0.0012))
    b = np.full(ctx["n"], np.nan)
    b[s:] = units * ix[s:]
    return b


def metrics(ctx, P, eq, expo, trades, cash, pos, last_c):
    cal, s, n = ctx["cal"], ctx["start"], ctx["n"]
    yrs = (cal[n - 1] - cal[s]).days / 365.25
    b = bench_curve(ctx, P)
    b_final = b[n - 1] - costs.etf_sell_cost(b[n - 1])
    t = pd.DataFrame(trades)
    r = dict(tag="", capital=P["capital"], final=float(eq[n - 1]), cagr=float((eq[n - 1] / P["capital"]) ** (1 / yrs) - 1),
             maxdd=maxdd(eq[s:]), bench_final=float(b_final), bench_cagr=float((b_final / P["capital"]) ** (1 / yrs) - 1),
             bench_maxdd=maxdd(b[s:]), years=yrs, bench=b)
    if len(t):
        voided = t["reasons"].str.contains("event_void")
        tt = t[~voided]
        r.update(trades=len(t), voided=int(voided.sum()), win=float((tt["pnl"] > 0).mean()), avgR=float(tt["R"].mean()),
                 avg_bars=float(tt["bars"].mean()), stat=float(t["stat"].sum()), slip=float(t["slip"].sum()),
                 pnl=float(t["pnl"].sum()), exposure=float(np.nanmean(expo[s:])),
                 t1_rate=float(tt["t1_hit"].mean()), stopped=float(tt["reasons"].str.contains("stop").mean()))
    return r


def yearly(ctx, eq, b):
    cal, s, n = ctx["cal"], ctx["start"], ctx["n"]
    s_eq = pd.Series(eq[s:], index=cal[s:])
    s_b = pd.Series(b[s:], index=cal[s:])
    out = []
    for y in sorted(set(s_eq.index.year)):
        a, bb = s_eq[s_eq.index.year == y], s_b[s_b.index.year == y]
        prev_e = s_eq[s_eq.index.year == y - 1]
        base_e = prev_e.iloc[-1] if len(prev_e) else s_eq.iloc[0]
        base_b = s_b[s_b.index.year == y - 1].iloc[-1] if len(prev_e) else s_b.iloc[0]
        out.append((y, a.iloc[-1] / base_e - 1, bb.iloc[-1] / base_b - 1))
    return out


def fmt(r):
    return (f"{r['tag']:<22} final {r['final']:>10,.0f}  CAGR {r['cagr']*100:5.1f}%  maxDD {r['maxdd']*100:6.1f}%  "
            f"trades {r.get('trades',0):>4}  win {r.get('win',0)*100:4.1f}%  avgR {r.get('avgR',0):5.2f}  "
            f"stat {r.get('stat',0):>7,.0f}  slip {r.get('slip',0):>7,.0f}")


VARIANTS = [
    ("base", {}),
    ("slip 0", dict(slip=0.0)),
    ("slip 0.30%", dict(slip=0.003)),
    ("capital 10 lakh", dict(capital=1000000.0)),
    ("RSI<15", dict(rsi_thr=15.0)),
    ("RSI<25", dict(rsi_thr=25.0)),
    ("stop 2.5 ATR (T1 5)", dict(stop_mult=2.5, tgt_mult=5.0)),
    ("no Nifty filter", dict(idx_filter=False)),
]

if __name__ == "__main__":
    ctx = prepare()
    print("calendar", ctx["cal"][0].date(), "->", ctx["cal"][-1].date(), "start idx", ctx["start"], "stocks", len(ctx["arr"]))
    print("skipped (no price file):", ctx["skipped"])
    sens = len(sys.argv) > 1 and sys.argv[1] == "sens"
    for name, ov in (VARIANTS if sens else VARIANTS[:1]):
        P = dict(BASE, **ov)
        res = run(ctx, P, tag="base" if name == "base" else None)
        res["tag"] = name
        print(fmt(res))
        if name == "base":
            print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()
                              if k not in ("bench", "trades_df", "legs_df", "eq")}, default=str))
            for y, a, bb in yearly(ctx, res["eq"], res["bench"]):
                print(f"  {y}: strategy {a*100:6.1f}%   nifty {bb*100:6.1f}%")
