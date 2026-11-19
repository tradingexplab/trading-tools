"""Backtest of GPT-6 Astra's 20-day breakout strategy.

Signal at the close of day t (all must hold):
  Nifty close > its 200-day SMA; stock close > SMA50 > SMA200; close > highest high of the preceding 20 sessions;
  close <= SMA50 + 3*ATR14 (Wilder, seeded by the mean of the first 14 true ranges).
Entry: next session's raw open E, only if signal_close - 0.5*A <= E <= signal_close + 0.5*A (A = signal-day ATR14).
Rank: 63-session return (close/close[-63]-1) highest first, ties by symbol. Signals queued for the next open count
toward the 5 positions. Skip any that fail; no sector cap (dropped).
Stop S0 = E - 2A, 1R = 2A. After every close (including entry day): stop = max(stop, highest close since entry - 3*ATR14),
active from the next session. Stop-first within a bar; gap below the stop exits at the open; otherwise exit at the stop.
Exits at the next open: close < SMA20, or Nifty close < its 200-day SMA, or after 40 completed sessions
(entry day = session 1, exit at session 41's open). These take priority over an intraday stop.
Sizing: floor(min(0.5% * equity / 2A, 20% * equity / E, cash-affordable incl. buy charges)), equity marked at the
signal-day close. Slippage 0.15% each side, statutory costs from costs.py, DP fee once per scrip per sell day.
Held stocks that leave the index are held to their normal exit. Corporate-action days voided as in backtest.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import backtest as B
import costs

BASE = dict(capital=100000.0, risk=0.005, cap=0.20, max_pos=5, slip=0.0015, brk=20, band=0.5, stop_mult=2.0,
            trail_mult=3.0, stretch=3.0, time_sessions=40, idx_filter=True)


def prepare():
    ctx = B.prepare()
    cal = ctx["cal"]
    for f, a in ctx["arr"].items():
        df = B.read_bars(B.DATA + f)
        c, h = df["Close"], df["High"]
        a["sma20"] = c.rolling(20).mean().reindex(cal).to_numpy(float)
        a["ret63"] = (c / c.shift(63) - 1).reindex(cal).to_numpy(float)
        for n in (10, 20, 55):
            a[f"hh{n}"] = h.rolling(n).max().shift(1).reindex(cal).to_numpy(float)
    return ctx


def signals(ctx, P):
    n, A, start = ctx["n"], ctx["arr"], ctx["start"]
    cand = {}
    for f, a in A.items():
        with np.errstate(invalid="ignore"):
            s = (a["member"] & a["ev_ok"] & (a["c"] > a["sma50"]) & (a["sma50"] > a["sma200"]) & (a["c"] > a[f"hh{P['brk']}"])
                 & (a["c"] <= a["sma50"] + P["stretch"] * a["atr"]) & np.isfinite(a["atr"]) & np.isfinite(a["ret63"]))
            if P["idx_filter"]:
                s &= ctx["idx_ok"]
        for i in np.nonzero(s)[0]:
            if start <= i < n - 1:
                cand.setdefault(int(i), []).append((-a["ret63"][i], a["sym"], f, float(a["atr"][i]), float(a["c"][i])))
    return cand


def run(ctx, P, tag=None):
    cal, n, A, start = ctx["cal"], ctx["n"], ctx["arr"], ctx["start"]
    cand = signals(ctx, P)
    st = dict(cash=P["capital"], band_fail=0, cash_bind=0, cap_bind=0, noslot=0, signals=sum(len(v) for v in cand.values()))
    pos, trades, legs, last_c, queue = {}, [], [], {}, []
    eq = np.full(n, np.nan)
    expo = np.zeros(n)
    slip = P["slip"]
    mkt_ok = ctx["idx_ok"] if P["idx_filter"] else np.ones(n, bool)

    def sell(f, p, i, q, raw, reason):
        if q <= 0:
            return
        px = raw * (1 - slip)
        val = q * px
        newday = i not in p["dp_days"]
        p["dp_days"].add(i)
        cst = costs.sell_cost(val, dp=newday)
        st["cash"] += val - cst
        p["stat"] += cst
        p["slipc"] += q * raw * slip
        p["proceeds"] += val - cst
        p["qty"] -= q
        p["reasons"].append(reason)
        legs.append(dict(file=f, sym=A[f]["sym"], date=str(cal[i].date()), qty=q, raw=round(raw, 2), reason=reason,
                         cost=round(cst, 2)))
        if p["qty"] == 0:
            pnl = p["proceeds"] - p["buy_out"]
            trades.append(dict(file=f, sym=A[f]["sym"], signal=str(cal[p["sig_i"]].date()),
                               entry=str(cal[p["entry_i"]].date()), exit=str(cal[i].date()), E=round(p["E"], 2),
                               qty=p["qty0"], atr=round(p["atr"], 2), stop0=round(p["stop0"], 2), bars=i - p["entry_i"],
                               reasons="|".join(p["reasons"]), pnl=round(pnl, 2),
                               R=round(pnl / (p["qty0"] * P["stop_mult"] * p["atr"]), 3), stat=round(p["stat"], 2),
                               slip=round(p["slipc"], 2), t1_hit=pnl > 0,
                               notional_pct=round(p["qty0"] * p["E"] / p["eq_sig"] * 100, 1),
                               stop_pct=round(P["stop_mult"] * p["atr"] / p["E"] * 100, 2)))
            del pos[f]

    def eod(f, p, i):
        a = A[f]
        c = a["c"][i]
        if not np.isfinite(c):
            return
        p["hc"] = max(p["hc"], c)
        if np.isfinite(a["atr"][i]):
            p["stop"] = max(p["stop"], p["hc"] - P["trail_mult"] * a["atr"][i])
        if not mkt_ok[i]:
            p["exit_open"] = "market"
        elif np.isfinite(a["sma20"][i]) and c < a["sma20"][i]:
            p["exit_open"] = "trend"

    for i in range(start, n):
        for f in list(pos):
            if A[f]["ev"] == i:
                sell(f, pos[f], i, pos[f]["qty"], last_c.get(f, pos[f]["E"]), "event_void")
        for f in list(pos):
            p = pos[f]
            if p["entry_i"] >= i:
                continue
            a = A[f]
            o, l = a["o"][i], a["l"][i]
            if not np.isfinite(o):
                continue
            if i - p["entry_i"] >= P["time_sessions"] and not p["exit_open"]:
                p["exit_open"] = "time"
            if p["exit_open"]:
                sell(f, p, i, p["qty"], o, p["exit_open"])
            elif o <= p["stop"]:
                sell(f, p, i, p["qty"], o, "gap_stop")
            elif l <= p["stop"]:
                sell(f, p, i, p["qty"], p["stop"], "stop")
            if f in pos:
                eod(f, p, i)
        for (negr, sym, f, atr, sc, eq_sig, sig_i) in queue:
            if f in pos or len(pos) >= P["max_pos"]:
                continue
            a = A[f]
            o = a["o"][i]
            if not np.isfinite(o):
                continue
            if not (sc - P["band"] * atr <= o <= sc + P["band"] * atr):
                st["band_fail"] += 1
                continue
            E = o
            risk_q = P["risk"] * eq_sig / (P["stop_mult"] * atr)
            cap_q = P["cap"] * eq_sig / E
            q = int(min(risk_q, cap_q))
            if cap_q < risk_q:
                st["cap_bind"] += 1
            pxs = E * (1 + slip)
            aff = int(st["cash"] / (pxs * 1.0013))
            if aff < q:
                st["cash_bind"] += 1
                q = aff
            while q > 0 and q * pxs + costs.buy_cost(q * pxs) > st["cash"]:
                q -= 1
            if q < 1:
                continue
            bc = costs.buy_cost(q * pxs)
            st["cash"] -= q * pxs + bc
            p = dict(qty=q, qty0=q, entry_i=i, sig_i=sig_i, E=E, atr=atr, stop=E - P["stop_mult"] * atr,
                     stop0=E - P["stop_mult"] * atr, hc=-1e18, exit_open=None, buy_out=q * pxs + bc, proceeds=0.0,
                     stat=bc, slipc=q * E * slip, dp_days=set(), reasons=[], eq_sig=eq_sig)
            pos[f] = p
            last_c[f] = E
            if a["l"][i] <= p["stop"]:
                sell(f, p, i, p["qty"], p["stop"], "stop_entry_day")
            else:
                eod(f, p, i)
        queue = []
        v = 0.0
        for f, p in pos.items():
            c = A[f]["c"][i]
            if np.isfinite(c):
                last_c[f] = c
            v += p["qty"] * last_c.get(f, p["E"])
        e = st["cash"] + v
        eq[i] = e
        expo[i] = v / e if e > 0 else 0.0
        assert len(pos) <= P["max_pos"], (cal[i], len(pos))
        assert st["cash"] > -1e-6, (cal[i], st["cash"])
        if i in cand and i < n - 1:
            free = max(P["max_pos"] - len(pos), 0)
            held = set(pos)
            cl = sorted(x for x in cand[i] if x[2] not in held)
            if len(cl) > free:
                st["noslot"] += len(cl) - free
            for (negr, sym, f, atr, sc) in cl[:free]:
                queue.append((negr, sym, f, atr, sc, e, i))
    res = B.metrics(ctx, P, eq, expo, trades, st["cash"], pos, last_c)
    res["st"] = {k: v for k, v in st.items() if k != "cash"}
    res["trades_df"], res["legs_df"], res["eq"] = pd.DataFrame(trades), pd.DataFrame(legs), eq
    res["open_positions"] = {A[f]["sym"]: p["qty"] for f, p in pos.items()}
    if tag:
        os.makedirs(B.OUT, exist_ok=True)
        res["trades_df"].to_csv(B.OUT + f"trades_{tag}.csv", index=False)
        res["legs_df"].to_csv(B.OUT + f"legs_{tag}.csv", index=False)
        pd.DataFrame(dict(date=cal[start:], equity=eq[start:], nifty=res["bench"][start:])).to_csv(
            B.OUT + f"equity_{tag}.csv", index=False)
    return res


VARIANTS = [
    ("astra base", {}, "astra_base"),
    ("slip 0", dict(slip=0.0), None),
    ("slip 0.30%", dict(slip=0.003), None),
    ("capital 10 lakh", dict(capital=1000000.0), None),
    ("no Nifty filter/exit", dict(idx_filter=False), None),
    ("breakout 10 days", dict(brk=10), None),
    ("breakout 55 days", dict(brk=55), None),
    ("trail 4 x ATR", dict(trail_mult=4.0), None),
    ("risk 1%", dict(risk=0.01), None),
]

if __name__ == "__main__":
    ctx = prepare()
    sens = len(sys.argv) > 1 and sys.argv[1] == "sens"
    for name, ov, tag in (VARIANTS if sens else VARIANTS[:1]):
        P = dict(BASE, **ov)
        r = run(ctx, P, tag=tag)
        r["tag"] = name
        print(B.fmt(r))
        print("   ", r["st"], "| exposure", round(r.get("exposure", 0) * 100, 1), "% | avg bars", round(r.get("avg_bars", 0), 1),
              "| open at end", r["open_positions"])
        if tag == "astra_base" and len(r["trades_df"]):
            t = r["trades_df"]
            print("   avg notional % of equity", round(t.notional_pct.mean(), 1), " avg stop %", round(t.stop_pct.mean(), 2),
                  " exits", t.reasons.str.split("|").explode().value_counts().to_dict())
            print("   bench", round(r["bench_final"]), f"CAGR {r['bench_cagr']*100:.1f}% maxDD {r['bench_maxdd']*100:.1f}%")
            for y, a_, b_ in B.yearly(ctx, r["eq"], r["bench"]):
                print(f"     {y}: strategy {a_*100:6.1f}%   nifty {b_*100:6.1f}%")
