"""Backtest of Gemini 4 Argon's 20/50 EMA pullback strategy.

Signal at the close of day t (all must hold):
  Nifty close > its 50 EMA and the 50 EMA > its value 5 sessions ago (blocks new entries only).
  Stock: close > EMA50, EMA20 > EMA50, EMA20 and EMA50 each above their value 5 sessions ago.
  Swing high = most recent highest high of the last 10 sessions (incl. t); it is 3..6 sessions before t.
  Pullback candles = sessions after the swing-high day up to t-1 (2..5). Window W = pullback + trigger day.
  Zone: some day in W has low <= 1.01*EMA20 that day; every close in W is above that day's EMA50.
  Volume contraction: at least one red (close<open) pullback candle; their mean volume < SMA20(volume) ending t-1.
  RSI(14, Wilder): min over pullback days >= 40 and RSI on day t-1 <= 55.
  Trigger day: close > EMA20, volume >= 1.2 * SMA20(volume) ending t-1, and one of engulfing / hammer / piercing.
Entry: next open; skipped if open > 1.015 * signal close or if stop >= entry.
Stop = max(lowest low over W, entry - 1.5*ATR14(signal day)). R = entry - stop. T1 = E+1.5R (sell int(q/2)), stop to E.
Remaining half: exit at E+3R, or next open after any close below EMA20. Time stop: entry day = session 0; if T1 not hit
by the close of session 10, sell at that close. Stop first within a bar; gaps fill at the open. After T1, worst case:
if the low <= E on the same bar the rest exits at E.
Sizing: floor(1% of equity at signal close / R); limited by cash (and optionally by cap*equity/E). Max 3 positions.
Ranking: highest trigger-day volume ratio. Costs/slippage/universe/events as in backtest.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import backtest as B
import costs

BASE = dict(capital=100000.0, risk=0.01, max_pos=3, cap=None, slip=0.0015, gap_skip=0.015, atr_stop=1.5,
            t1_r=1.5, t3_r=3.0, time_bars=10, idx_filter=True, vol_mult=1.2, rsi_lo=40.0, rsi_hi=55.0, pattern_any=False)


def prepare():
    ctx = B.prepare()
    n, cal = ctx["n"], ctx["cal"]
    ixs = ctx["ix"]
    e50 = B.ema_seeded(ixs, 50)
    ok = np.zeros(n, bool)
    with np.errstate(invalid="ignore"):
        ok[5:] = (ixs[5:] > e50[5:]) & (e50[5:] > e50[:-5])
    ctx["idx_ok2"] = ok
    for f, a in ctx["arr"].items():
        df = pd.read_csv(B.DATA + f, usecols=["Date", "Open", "High", "Low", "Close", "Volume"], parse_dates=["Date"])
        df = df.dropna(subset=["Open", "High", "Low", "Close"]).drop_duplicates("Date").sort_values("Date").set_index("Date")
        df = df[(df["Close"] > 0) & (df["High"] >= df["Low"])]
        c = df["Close"].to_numpy(float)
        vs = df["Volume"].astype(float)
        a["ema50"] = pd.Series(B.ema_seeded(c, 50), index=df.index).reindex(cal).to_numpy(float)
        a["rsi14"] = pd.Series(B.wilder_rsi(c, 14), index=df.index).reindex(cal).to_numpy(float)
        a["v"] = vs.reindex(cal).to_numpy(float)
        a["vsma"] = vs.rolling(20).mean().shift(1).reindex(cal).to_numpy(float)
    return ctx


def signals(ctx, P):
    n, A, start = ctx["n"], ctx["arr"], ctx["start"]
    cand, counts = {}, dict(base=0, window=0, final=0)
    for f, a in A.items():
        o, h, l, c, v = a["o"], a["h"], a["l"], a["c"], a["v"]
        e20, e50, rsi, atr, vsma = a["ema20"], a["ema50"], a["rsi14"], a["atr"], a["vsma"]
        with np.errstate(invalid="ignore"):
            base = (a["member"] & a["ev_ok"] & (c > e50) & (e20 > e50) & (c > e20) & (vsma > 0) & (v >= P["vol_mult"] * vsma)
                    & np.isfinite(atr) & np.isfinite(rsi))
            e20r = np.zeros(n, bool)
            e50r = np.zeros(n, bool)
            e20r[5:] = e20[5:] > e20[:-5]
            e50r[5:] = e50[5:] > e50[:-5]
            base &= e20r & e50r
            if P["idx_filter"]:
                base &= ctx["idx_ok2"]
        for t in np.nonzero(base)[0]:
            t = int(t)
            if t < start or t >= n - 1 or t < 12:
                continue
            counts["base"] += 1
            w = h[t - 9:t + 1]
            if not np.all(np.isfinite(w)):
                continue
            s = t - int(np.argmax(w[::-1]))
            if not 3 <= t - s <= 6:
                continue
            counts["window"] += 1
            pb = slice(s + 1, t)
            W = slice(s + 1, t + 1)
            if not (np.all(np.isfinite(o[W])) and np.all(np.isfinite(l[W])) and np.all(np.isfinite(c[W]))
                    and np.all(np.isfinite(e20[W])) and np.all(np.isfinite(e50[W])) and np.all(np.isfinite(rsi[pb]))
                    and np.all(np.isfinite(v[pb]))):
                continue
            if not np.any(l[W] <= 1.01 * e20[W]) or not np.all(c[W] > e50[W]):
                continue
            red = c[pb] < o[pb]
            if not red.any() or not (v[pb][red].mean() < vsma[t]):
                continue
            if not (rsi[pb].min() >= P["rsi_lo"] and rsi[t - 1] <= P["rsi_hi"]):
                continue
            body = abs(c[t] - o[t])
            lower = min(o[t], c[t]) - l[t]
            upper = h[t] - max(o[t], c[t])
            engulf = c[t - 1] < o[t - 1] and c[t] > o[t] and o[t] <= c[t - 1] and c[t] >= o[t - 1]
            hammer = (h[t] > l[t]) and lower >= 2 * body and upper <= body
            pierce = (c[t - 1] < o[t - 1] and c[t] > o[t] and o[t] < c[t - 1]
                      and c[t] > (o[t - 1] + c[t - 1]) / 2 and c[t] < o[t - 1])
            if P["pattern_any"]:
                engulf = engulf or c[t] > o[t]
            if not (engulf or hammer or pierce):
                continue
            counts["final"] += 1
            cand.setdefault(t, []).append((v[t] / vsma[t], f, float(l[W].min()), float(atr[t]), float(c[t]),
                                           "E" if engulf else ("H" if hammer else "P")))
    return cand, counts


def run(ctx, P, tag=None):
    cal, n, A, start = ctx["cal"], ctx["n"], ctx["arr"], ctx["start"]
    cand, counts = signals(ctx, P)
    st = dict(cash=P["capital"], gap=0, stopge=0, cashbind=0, noslot=0)
    pos, trades, legs, last_c, queue = {}, [], [], {}, []
    eq = np.full(n, np.nan)
    expo = np.zeros(n)
    slip = P["slip"]

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
                               qty=p["qty0"], atr=round(p["atr"], 2), stop0=round(p["stop0"], 2), t1=round(p["t1"], 2),
                               t3=round(p["t3"], 2), bars=i - p["entry_i"], reasons="|".join(p["reasons"]),
                               pnl=round(pnl, 2), R=round(pnl / (p["qty0"] * (p["E"] - p["stop0"])), 3),
                               stat=round(p["stat"], 2), slip=round(p["slipc"], 2), t1_hit=p["t1_hit"],
                               notional_pct=round(p["qty0"] * p["E"] / p["eq_sig"] * 100, 1),
                               stop_pct=round((p["E"] - p["stop0"]) / p["E"] * 100, 2), pattern=p["pattern"]))
            del pos[f]

    def manage(f, p, i, entry_day):
        a = A[f]
        o, h, l, c = a["o"][i], a["h"][i], a["l"][i], a["c"][i]
        if not np.isfinite(o):
            return
        if not entry_day:
            if p["pending"]:
                sell(f, p, i, p["qty"], o, p["pending"])
                return
            if o <= p["stop"]:
                sell(f, p, i, p["qty"], o, "gap_be_stop" if p["t1_hit"] else "gap_stop")
                return
        if l <= p["stop"]:
            sell(f, p, i, p["qty"], p["stop"], "be_stop" if p["t1_hit"] else "stop")
            return
        if not p["t1_hit"] and h >= p["t1"]:
            px = p["t1"] if entry_day else max(o, p["t1"])
            sell(f, p, i, p["qty0"] // 2, px, "t1")
            p["t1_hit"] = True
            p["stop"] = p["E"]
            if l <= p["E"]:
                sell(f, p, i, p["qty"], p["E"], "be_same_bar")
                return
        if p["t1_hit"] and h >= p["t3"]:
            px = p["t3"] if entry_day else max(o, p["t3"])
            sell(f, p, i, p["qty"], px, "t3")
            return
        if p["t1_hit"]:
            if np.isfinite(c) and np.isfinite(a["ema20"][i]) and c < a["ema20"][i]:
                p["pending"] = "ema"
        elif i - p["entry_i"] >= P["time_bars"] and np.isfinite(c):
            sell(f, p, i, p["qty"], c, "time")

    for i in range(start, n):
        for f in list(pos):
            if A[f]["ev"] == i:
                sell(f, pos[f], i, pos[f]["qty"], last_c.get(f, pos[f]["E"]), "event_void")
        for f in list(pos):
            if pos[f]["entry_i"] < i:
                manage(f, pos[f], i, False)
        # execute entries queued at the previous close
        for (ratio, f, wick, atr, sc, pat, eq_sig, sig_i) in queue:
            if f in pos or len(pos) >= P["max_pos"]:
                continue
            a = A[f]
            o = a["o"][i]
            if not np.isfinite(o):
                continue
            if o > sc * (1 + P["gap_skip"]):
                st["gap"] += 1
                continue
            E = o
            stop = max(wick, E - P["atr_stop"] * atr)
            if stop >= E:
                st["stopge"] += 1
                continue
            R = E - stop
            q = int(P["risk"] * eq_sig / R)
            if P["cap"]:
                q = min(q, int(P["cap"] * eq_sig / E))
            pxs = E * (1 + slip)
            aff = int(st["cash"] / (pxs * 1.0013))
            if aff < q:
                st["cashbind"] += 1
                q = aff
            while q > 0 and q * pxs + costs.buy_cost(q * pxs) > st["cash"]:
                q -= 1
            if q < 1:
                continue
            bc = costs.buy_cost(q * pxs)
            st["cash"] -= q * pxs + bc
            p = dict(qty=q, qty0=q, entry_i=i, sig_i=sig_i, E=E, atr=atr, stop=stop, stop0=stop, t1=E + P["t1_r"] * R,
                     t3=E + P["t3_r"] * R, t1_hit=False, pending=None, buy_out=q * pxs + bc, proceeds=0.0, stat=bc,
                     slipc=q * E * slip, dp_days=set(), reasons=[], eq_sig=eq_sig, pattern=pat)
            pos[f] = p
            last_c[f] = E
            manage(f, p, i, True)
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
            free = P["max_pos"] - len(pos)
            held = set(pos)
            cl = sorted([x for x in cand[i] if x[1] not in held], reverse=True)
            if len(cl) > max(free, 0):
                st["noslot"] += len(cl) - max(free, 0)
            for (ratio, f, wick, atr, sc, pat) in cl[:max(free, 0)]:
                queue.append((ratio, f, wick, atr, sc, pat, e, i))
    res = B.metrics(ctx, P, eq, expo, trades, st["cash"], pos, last_c)
    res.update(counts=counts, st={k: v for k, v in st.items() if k != "cash"})
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
    ("argon base (cash only)", {}, "argon_base"),
    ("argon cap 33%", dict(cap=0.33), "argon_cap33"),
    ("slip 0", dict(slip=0.0), None),
    ("slip 0.30%", dict(slip=0.003), None),
    ("capital 10 lakh", dict(capital=1000000.0), None),
    ("no Nifty filter", dict(idx_filter=False), None),
    ("volume >= 1.0x", dict(vol_mult=1.0), None),
    ("RSI band 35-60", dict(rsi_lo=35.0, rsi_hi=60.0), None),
    ("any green trigger candle", dict(pattern_any=True), None),
    ("any green + vol 1.0x + no Nifty", dict(pattern_any=True, vol_mult=1.0, idx_filter=False), None),
]

if __name__ == "__main__":
    ctx = prepare()
    sens = len(sys.argv) > 1 and sys.argv[1] == "sens"
    for name, ov, tag in (VARIANTS if sens else VARIANTS[:2]):
        P = dict(BASE, **ov)
        r = run(ctx, P, tag=tag)
        r["tag"] = name
        print(B.fmt(r))
        print("   signals", r["counts"], "| skips", r["st"], "| exposure", round(r.get("exposure", 0) * 100, 1), "% | t1_rate",
              round(r.get("t1_rate", 0) * 100, 1), "% | open at end", r["open_positions"])
        if tag in ("argon_base", "argon_cap33") and len(r["trades_df"]):
            t = r["trades_df"]
            print("   avg notional % of equity", round(t.notional_pct.mean(), 1), " avg stop %", round(t.stop_pct.mean(), 2),
                  " patterns", t.pattern.value_counts().to_dict(), " exits", t.reasons.str.split("|").explode().value_counts().to_dict())
            print("   bench", round(r["bench_final"]), f"CAGR {r['bench_cagr']*100:.1f}% maxDD {r['bench_maxdd']*100:.1f}%")
            for y, a_, b_ in B.yearly(ctx, r["eq"], r["bench"]):
                print(f"     {y}: strategy {a_*100:6.1f}%   nifty {b_*100:6.1f}%")
