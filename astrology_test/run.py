"""Do three astrology beliefs move the Nifty? Amavasya, Budh Vakri (Mercury retrograde)
and Jupiter in Ketu's nakshatras, tested on Nifty 50 data from 2004 to Nov 2026.

Run build_index.py and dates.py first (see README). Rules:
- Diwali Muhurat sessions are dropped (list below), and so are low-volume weekend test sessions.
- Amavasya: only Amavasyas that fall on a trading day count. Close-to-close returns.
  Version A: does Nifty fall that day? Version B: are moves bigger over the 4 trading days around it?
- Mercury retrograde: only completed periods count.
- Jupiter: counted per visit, per transit (retrograde re-entries merged), and with extra days after,
  at two crash thresholds, so every way of counting is visible.
- Rs 10 lakh story on NIFTYBEES closes with Zerodha equity ETF delivery charges.
  No tax, no spread. Idle cash earns 0% (6% shown as a sensitivity).
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
N = 10_000
HO = pd.Timestamp("2021-11-11")
START = pd.Timestamp("2004-01-01")
END = pd.Timestamp("2026-11-09")  # last day used in the video; newer data would change the numbers
PCT, FLAT = 0.000235, 15.34  # Zerodha equity ETF delivery, statutory only

MUHURAT = pd.to_datetime([
    "2004-11-12", "2005-11-01", "2006-10-21", "2007-11-09", "2008-10-28", "2009-10-17", "2010-11-05",
    "2011-10-26", "2012-11-13", "2013-11-03", "2014-10-23", "2015-11-11", "2016-10-30", "2017-10-19",
    "2018-11-07", "2019-10-27", "2020-11-14", "2021-11-04", "2022-10-24", "2023-11-12", "2024-11-01",
    "2025-10-21", "2026-11-08"])

IX_PATH = "data/nifty_index_2003_2026.csv"
NB_PATH = "data/eod2/niftybees.csv"


def raw(path):
    d = pd.read_csv(path, parse_dates=["Date"]).set_index("Date").sort_index()
    return d[["Close", "Volume"]]


IX_RAW, NB_RAW = raw(IX_PATH), raw(NB_PATH)


def ratio(df):
    return df.Volume / df.Volume.rolling(20, min_periods=5).median().shift(1)


R_IX, R_NB = ratio(IX_RAW), ratio(NB_RAW)


def clean(df):
    df = df.loc[START:END]
    r = R_IX.reindex(df.index).fillna(R_NB.reindex(df.index))
    weekend_test = (df.index.dayofweek >= 5) & (r < 0.35)
    drop = df.index.isin(MUHURAT) | weekend_test
    return df[~drop], df.index[drop]


def mdd(x):
    return (x / np.maximum.accumulate(x) - 1).min()


def amavasya(df, am):
    r = df.Close.pct_change().to_numpy()
    absr = np.abs(r)
    idx = df.index
    pos = np.where(idx.isin(am))[0]
    pos = pos[(pos >= 1)]
    out = {}
    for name, m in [("dev", idx < HO), ("hold", idx >= HO)]:
        pool = np.where(m)[0]; pool = pool[pool >= 1]
        e = pos[m[pos]]
        ev = r[e].mean()
        sims = np.array([r[RNG.choice(pool, len(e), replace=False)].mean() for _ in range(N)])
        pb = pool[(pool >= 3) & (pool < len(r) - 1)]
        eb = e[(e >= 3) & (e < len(r) - 1)]
        win = lambda s: absr[np.add.outer(s, np.arange(-2, 2))].mean()
        evb = win(eb)
        simb = np.array([win(RNG.choice(pb, len(eb), replace=False)) for _ in range(N)])
        dshare = (r[e] < 0).mean()
        dsims = np.array([(r[RNG.choice(pool, len(e), replace=False)] < 0).mean() for _ in range(N)])
        out[name] = dict(n=len(e), mean=100 * ev, p_down_low=(dsims <= dshare).mean(), p_down_high=(dsims >= dshare).mean(), all=100 * r[pool].mean(), median=100 * np.median(r[e]),
                         all_median=100 * np.median(r[pool]), down=100 * (r[e] < 0).mean(),
                         all_down=100 * (r[pool] < 0).mean(), p=(sims <= ev).mean(), p_high=(sims >= ev).mean(),
                         B=100 * evb, B_all=100 * absr[pb].mean(), B_n=len(eb), pB=(simb >= evb).mean())
    return pos, out


def mercury(df, per):
    c = df.Close
    r = c.pct_change().to_numpy()
    ins = np.zeros(len(c), bool)
    rets = []
    for _, p in per.iterrows():
        ins[(c.index >= p.start) & (c.index <= p.end)] = True
        s = c.loc[:p.start - pd.Timedelta(days=1)].iloc[-1]
        e = c.loc[:p.end].iloc[-1]
        rets.append(e / s - 1)
    rets = np.array(rets)
    out = dict(n=len(rets), fell=int((rets < 0).sum()), median=100 * np.median(rets),
               worst=100 * rets.min(), best=100 * rets.max(), in_frac=ins[1:].mean())
    for name, m in [("dev", c.index < HO), ("hold", c.index >= HO), ("all", c.index >= c.index[0])]:
        m = m.copy(); m[0] = False
        rr, ii = r[m], ins[m]
        ev = rr[ii].mean()
        sims = np.array([rr[np.roll(ii, k)].mean() for k in RNG.integers(1, len(rr), N)])
        out[name] = dict(inside=100 * ev, outside=100 * rr[~ii].mean(), p=(sims <= ev).mean(),
                         in_down=100 * (rr[ii] < 0).mean(), out_down=100 * (rr[~ii] < 0).mean())
    return out


def jupiter(df, per, extra=0, thr=0.20):
    c = df.Close
    arr, dates = c.to_numpy(), c.index
    rows, base = [], []
    for _, p in per.iterrows():
        end = p.end + pd.Timedelta(days=extra)
        seg = c.loc[p.start:end]
        rows.append(dict(nak=p.nak, start=p.start.date(), end=p.end.date(), ret=100 * (seg.iloc[-1] / seg.iloc[0] - 1),
                         maxfall=100 * mdd(seg.to_numpy()), peak=seg.idxmax().date(),
                         trough=seg.index[np.argmin(seg.to_numpy() / np.maximum.accumulate(seg.to_numpy()))].date()))
        L = (end - p.start).days
        endd = dates + pd.Timedelta(days=L)
        ok = endd <= dates[-1]
        ends = dates.searchsorted(endd, side="right") - 1
        base.append(np.mean([mdd(arr[i:ends[i] + 1]) <= -thr for i in np.where(ok)[0]]))
    res = pd.DataFrame(rows)
    res["base_%"] = 100 * np.array(base)
    k = int((res.maxfall <= -100 * thr).sum())
    dist = np.array([1.0])
    for q in base:
        dist = np.convolve(dist, [1 - q, q])
    return res, k, sum(base), dist[k:].sum()


def follower(df, exits, entries, cash=0.0, costs=True):
    cl, dts = df.Close.to_numpy(), df.index
    units, paid = 1e6 / cl[0], 0.0
    for x, e in zip(exits, entries):
        val = units * cl[x]
        cost = PCT * val + FLAT if costs else 0.0
        paid += cost
        units = (val - cost) * (1 + cash) ** ((dts[e] - dts[x]).days / 365.25) / cl[e]
    fin = units * cl[-1]
    if costs:
        fin -= PCT * fin + FLAT
    return fin, paid


def period_trades(idx, per):
    xs, es = [], []
    for _, p in per.iterrows():
        s = idx.searchsorted(p.start) - 1
        e = idx.searchsorted(p.end, side="right") - 1
        if s >= 0 and e > s:
            xs.append(s); es.append(e)
    return xs, es


if __name__ == "__main__":
    am = pd.read_csv("data/amavasya_dates.csv", parse_dates=["date"]).date
    merc = pd.read_csv("data/mercury_retrograde_periods.csv", parse_dates=["start", "end"])
    jv = pd.read_csv("data/jupiter_ketu_periods.csv", parse_dates=["start", "end"])
    ix, d_ix = clean(IX_RAW)
    nb, d_nb = clean(NB_RAW)
    last = min(ix.index[-1], nb.index[-1])
    merc = merc[(merc.start >= START) & (merc.end <= last)]
    jv = jv[(jv.start >= START) & (jv.end <= last)].reset_index(drop=True)
    # transits: merge visits of the same nakshatra less than 250 days apart
    tr = []
    for _, p in jv.iterrows():
        if tr and tr[-1]["nak"] == p.nak and (p.start - tr[-1]["end"]).days < 250:
            tr[-1]["end"] = p.end
        else:
            tr.append(dict(nak=p.nak, start=p.start, end=p.end))
    jt = pd.DataFrame(tr)

    print("Dropped (index):", [str(d.date()) for d in d_ix])
    print("Dropped (NIFTYBEES):", [str(d.date()) for d in d_nb])
    yrs = (nb.index[-1] - nb.index[0]).days / 365.25
    print(f"Window {nb.index[0].date()} - {nb.index[-1].date()} ({yrs:.2f} yrs)")

    print("\n== AMAVASYA (only Amavasyas on trading days) ==")
    for tag, df in [("index", ix), ("NIFTYBEES", nb)]:
        pos, o = amavasya(df, am)
        for k in ("dev", "hold"):
            v = o[k]
            print(f"{tag} {k}: n={v['n']} mean {v['mean']:+.3f}% vs all {v['all']:+.3f}% | median {v['median']:+.3f} vs {v['all_median']:+.3f}"
                  f" | down {v['down']:.1f}% vs {v['all_down']:.1f}% | p(random<=) {v['p']:.3f} p(random>=) {v['p_high']:.3f} | down-share luck low {v['p_down_low']:.3f} high {v['p_down_high']:.3f}"
                  f" || B {v['B']:.3f}% vs {v['B_all']:.3f}% p(random>=) {v['pB']:.3f}")
    am_on = am[am.isin(ix.index)]
    print("Amavasyas total in window:", int(((am >= START) & (am <= last)).sum()), " on trading days (index):", int(am.isin(ix.index).sum()))

    print("\n== MERCURY (completed periods) ==")
    for tag, df in [("index", ix), ("NIFTYBEES", nb)]:
        o = mercury(df, merc)
        print(f"{tag}: periods {o['n']} fell {o['fell']} median {o['median']:+.2f}% worst {o['worst']:.1f} best {o['best']:.1f} out {100*o['in_frac']:.1f}%")
        for k in ("dev", "hold", "all"):
            v = o[k]
            print(f"   {k}: inside {v['inside']:+.4f}% outside {v['outside']:+.4f}% p {v['p']:.3f} | down {v['in_down']:.1f}/{v['out_down']:.1f}")

    print("\n== JUPITER per visit (index) ==")
    res, k, exp, p = jupiter(ix, jv)
    print(res.round(2).to_string(index=False)); print(f"crashes {k}/{len(res)} expected {exp:.2f} p(>=k) {p:.3f}")
    res90, k90, exp90, p90 = jupiter(ix, jv, 90)
    print(f"+90d: {k90}/{len(res90)} expected {exp90:.2f} p(>=k) {p90:.3f}")
    print(res90[["start", "maxfall"]].round(1).to_string(index=False))
    print("\n== JUPITER per transit (index) ==")
    rt, kt, expt, pt = jupiter(ix, jt)
    print(rt.round(2).to_string(index=False)); print(f"crashes {kt}/{len(rt)} expected {expt:.2f} p(>=k) {pt:.3f}")

    print("\n== JUPITER sensitivity (index): all four counts, and the window/threshold around the one that passes ==")
    for nm, per in [("visit", jv), ("transit", jt)]:
        for ext in (0, 60, 90, 120):
            for thr in (0.20, 0.25):
                r_, k_, e_, p_ = jupiter(ix, per, ext, thr)
                print(f"   {nm:7s} +{ext:3d}d  crash>={int(thr*100)}%: {k_}/{len(r_)}  expected {e_:.2f}  luck p(>=k) {p_:.3f}")
    print("\n== RS 10 LAKH (NIFTYBEES) ==")
    H, _ = follower(nb, [], [])
    p_nb = np.where(nb.index.isin(am))[0]; p_nb = p_nb[p_nb >= 1]
    A, Ap = follower(nb, p_nb - 1, p_nb)
    A0, _ = follower(nb, p_nb - 1, p_nb, costs=False)
    rnb = nb.Close.pct_change().to_numpy()
    mx, me_ = period_trades(nb.index, merc)
    M, Mp = follower(nb, mx, me_)
    jx, je = period_trades(nb.index, jv)
    J, Jp = follower(nb, jx, je)
    tx, te = period_trades(nb.index, jt)
    T, Tp = follower(nb, tx, te)
    print(f"Holder            {H:,.0f}")
    for nm, v, paid, n, x_, e_ in [("Amavasya", A, Ap, len(p_nb), p_nb - 1, p_nb), ("Mercury", M, Mp, len(mx), mx, me_),
                                   ("Jupiter visits", J, Jp, len(jx), jx, je), ("Jupiter transits", T, Tp, len(tx), tx, te)]:
        c6, _ = follower(nb, x_, e_, cash=0.06)
        print(f"{nm:17s} {v:,.0f}  gap {(H-v)/1e5:.1f} L  trips {n}  charges paid {paid:,.0f} | cash@6%: {c6:,.0f} gap {(H-c6)/1e5:.1f} L")
    print(f"Amavasya zero-cost {A0:,.0f}: missed days {(H-A0)/1e5:.1f} L, charges incl. lost growth {(A0-A)/1e5:.1f} L;"
          f" up days {100*(rnb[p_nb]>0).mean():.1f}%  down {100*(rnb[p_nb]<0).mean():.1f}%  days/yr {len(p_nb)/yrs:.1f}")
    jt90 = jt.assign(end=jt.end + pd.Timedelta(days=90))
    jt90 = jt90[jt90.end <= nb.index[-1]]
    t9x, t9e = period_trades(nb.index, jt90)
    T9, _ = follower(nb, t9x, t9e)
    print(f"Jupiter transit+90d follower {T9:,.0f}  vs holder {(T9-H)/1e5:+.1f} L  trips {len(t9x)}")
    print(f"Mercury out of market {100*sum(e-x for x,e in zip(mx,me_))/(len(nb)-1):.1f}% of days")
    # biggest single Amavasya-day moves, NIFTYBEES vs index
    s = pd.Series(100 * rnb[p_nb], index=nb.index[p_nb]).sort_values()
    print("NIFTYBEES biggest Amavasya days:", s.head(3).round(2).to_dict(), s.tail(3).round(2).to_dict())
