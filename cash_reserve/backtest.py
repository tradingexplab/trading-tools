"""Cash-reserve test: 100% Nifty vs 80/20 vs 50/50 (Nifty / liquid fund).

  python backtest.py            (needs data/nifty50_tri.csv and data/eod2/, see README)
  python backtest.py --no-harvest

Rules
- Start capital Rs 10,00,000 on the first common date; equity = Nifty 50 total
  return index (price files + daily dividend yield), cash = NIFTY 1D Rate Index
  minus a 0.20%/yr expense ratio.
- Deploy: when the Nifty 50 price index closes 10% or more below its all-time
  closing high, move ALL cash into equity at the NEXT trading day's close.
- Refill: when the Nifty 50 price index closes at a new all-time high after a
  deploy, sell equity at the next day's close so that cash, after sale costs,
  tax and the cash-buy fee, equals the target weight of the pre-trade value.
- Between those events the weights drift; there is no other rebalancing.
- Costs (Zerodha, statutory, excl. spread, rates verified 2026-09-09):
  equity ETF buy 0.01874%, sell 0.00474% + Rs 15.34 DP;
  liquid ETF buy 0.01874%, sell 0.00374% + Rs 15.34 DP.
- Tax, today's rates applied to the whole period, deducted at each sale:
  equity held <=12 months 20%; >12 months 12.5% above Rs 1.25 lakh per
  financial year (FIFO lots); liquid gains at a flat 20% slab.
- Tax-gain harvesting, same for all three portfolios: on the last trading day
  of each financial year, sell long-term equity lots with gains up to that
  year's unused Rs 1.25 lakh exemption and buy back the same day (costs apply).
- Final value shown two ways: holding value, and value after selling everything
  on the last day (same tax and cost rules).
"""
import copy
import numpy as np
import pandas as pd

CAPITAL = 1_000_000
TRIGGER = 0.10
CASH_EXP = 0.0020
EQ_BUY, EQ_SELL = 0.0001874, 0.0000474
LQ_BUY, LQ_SELL = 0.0001874, 0.0000374
DP = 15.34
STCG, LTCG, LTCG_EXEMPT, SLAB = 0.20, 0.125, 125_000, 0.20


def load(tri_csv, eod2_dir):
    t = pd.read_csv(tri_csv, parse_dates=["Date"]).set_index("Date")
    hist = pd.read_csv(f"{eod2_dir}/nifty 50.csv", parse_dates=["Date"]).set_index("Date").Close
    seed_high = hist[hist.index < t.index[0]].max()
    c = pd.read_csv(f"{eod2_dir}/nifty 1d rate index.csv", parse_dates=["Date"]).set_index("Date").Close.dropna()
    c = c[~c.index.duplicated()].sort_index()
    # log-linear interpolation on calendar days; extend past the last point at the last 30-day rate
    x = (c.index - c.index[0]).days.values
    xs = (t.index - c.index[0]).days.values
    lc = np.log(c.values)
    rate = (lc[-1] - np.interp(x[-1] - 30, x, lc)) / 30
    lcs = np.interp(xs, x, lc)
    lcs = np.where(xs > x[-1], lc[-1] + (xs - x[-1]) * rate, lcs)
    cash = pd.Series(np.exp(lcs), index=t.index)
    days = t.index.to_series().diff().dt.days.fillna(0).values
    cash = cash * np.exp(-CASH_EXP * np.cumsum(days) / 365)
    return pd.DataFrame({"price": t.price, "tri": t.tri, "cash": cash}), seed_high, c.index[-1]


def fy(d):
    return d.year if d.month >= 4 else d.year - 1


class Book:
    def __init__(self):
        self.eq_lots = []          # [units, cost_per_unit, date]
        self.lq_lots = []
        self.costs = 0.0
        self.tax = 0.0
        self.ltcg_used = {}

    def buy(self, kind, rupees, px, d):
        fee = rupees * (EQ_BUY if kind == "eq" else LQ_BUY)
        self.costs += fee
        units = (rupees - fee) / px
        (self.eq_lots if kind == "eq" else self.lq_lots).append([units, px, d])

    def sell(self, kind, rupees_gross, px, d):
        """Sell enough units to raise rupees_gross (before cost/tax); FIFO. Returns net cash."""
        lots = self.eq_lots if kind == "eq" else self.lq_lots
        need = rupees_gross / px
        st = lt = 0.0
        while need > 1e-12 and lots:
            u, cpx, bd = lots[0]
            take = min(u, need)
            gain = take * (px - cpx)
            if kind == "eq" and (d - bd).days > 365:
                lt += gain
            else:
                st += gain
            lots[0][0] -= take
            need -= take
            if lots[0][0] <= 1e-12:
                lots.pop(0)
        gross = rupees_gross - need * px
        fee = gross * (EQ_SELL if kind == "eq" else LQ_SELL) + DP
        self.costs += fee
        tax = 0.0
        if kind == "eq":
            tax += max(st, 0) * STCG
            y = fy(d)
            room = max(LTCG_EXEMPT - self.ltcg_used.get(y, 0.0), 0)
            ltg = max(lt, 0)
            self.ltcg_used[y] = self.ltcg_used.get(y, 0.0) + ltg
            tax += max(ltg - room, 0) * LTCG
        else:
            tax += max(st, 0) * SLAB
        self.tax += tax
        return gross - fee - tax

    def harvest(self, px, d):
        """Book long-term equity gains up to this FY's unused exemption, buy back same day."""
        y = fy(d)
        room = max(LTCG_EXEMPT - self.ltcg_used.get(y, 0.0), 0)
        sold_units = 0.0
        for lot in self.eq_lots:
            if room <= 1e-6:
                break
            u, cpx, bd = lot
            if (d - bd).days <= 365 or px <= cpx:
                continue
            take = min(u, room / (px - cpx))
            room -= take * (px - cpx)
            lot[0] -= take
            sold_units += take
        if sold_units <= 0:
            return 0.0
        self.eq_lots = [l for l in self.eq_lots if l[0] > 1e-12]
        gain = (LTCG_EXEMPT - self.ltcg_used.get(y, 0.0)) - room
        self.ltcg_used[y] = self.ltcg_used.get(y, 0.0) + gain
        gross = sold_units * px
        fee = gross * EQ_SELL + DP
        self.costs += fee
        self.buy("eq", gross - fee, px, d)
        return gain

    def value(self, eqpx, lqpx):
        return sum(u for u, *_ in self.eq_lots) * eqpx + sum(u for u, *_ in self.lq_lots) * lqpx

    def units(self, kind):
        return sum(u for u, *_ in (self.eq_lots if kind == "eq" else self.lq_lots))


def run(df, seed_high, cash_w):
    b = Book()
    d0 = df.index[0]
    b.buy("eq", CAPITAL * (1 - cash_w), df.tri.iloc[0], d0)
    if cash_w > 0:
        b.buy("lq", CAPITAL * cash_w, df.cash.iloc[0], d0)
    high = max(seed_high, df.price.iloc[0])
    deployed = False
    pending = None
    events, vals, harvests = [], [], []
    for i, (d, r) in enumerate(df.iterrows()):
        if pending and cash_w > 0:
            act, sig = pending
            if act == "deploy":
                lqv = b.units("lq") * r.cash
                net = b.sell("lq", lqv, r.cash, d)
                b.buy("eq", net, r.tri, d)
                deployed = True
            else:  # refill
                tot = b.value(r.tri, r.cash)
                deficit = max(tot * cash_w - b.units("lq") * r.cash, 0)
                # size the sale so cash AFTER sale costs, tax and the cash-buy fee equals the target
                need = deficit
                for _ in range(30):
                    trial = copy.deepcopy(b)
                    got = trial.sell("eq", need, r.tri, d) * (1 - LQ_BUY)
                    if got <= 0:
                        break
                    need *= deficit / got
                net = b.sell("eq", need, r.tri, d)
                b.buy("lq", net, r.cash, d)
                deployed = False
            events.append({"signal": sig.date(), "trade": d.date(), "action": act,
                           "nifty": r.price, "value_after": round(b.value(r.tri, r.cash))})
            pending = None
        if i < len(df) - 1 and fy(df.index[i + 1]) != fy(d):
            booked = b.harvest(r.tri, d)
            if booked > 0:
                harvests.append((d.date(), round(booked)))
        newhigh = r.price > high
        high = max(high, r.price)
        if cash_w > 0 and i < len(df) - 1:
            if not deployed and r.price <= high * (1 - TRIGGER):
                pending = ("deploy", d)
            elif deployed and newhigh:
                pending = ("refill", d)
        vals.append(b.value(r.tri, r.cash))
    v = pd.Series(vals, index=df.index)
    last = df.iloc[-1]
    hold = v.iloc[-1]
    costs_before, tax_before = b.costs, b.tax
    exit_cash = 0.0
    if b.units("eq") > 0:
        exit_cash += b.sell("eq", b.units("eq") * last.tri, last.tri, df.index[-1])
    if b.units("lq") > 0:
        exit_cash += b.sell("lq", b.units("lq") * last.cash, last.cash, df.index[-1])
    yrs = (df.index[-1] - d0).days / 365.25
    dd = (v / v.cummax() - 1).min()
    return {
        "cash_weight": cash_w,
        "final_holding_value": round(hold),
        "final_after_exit": round(exit_cash),
        "cagr_after_exit_pct": round(((exit_cash / CAPITAL) ** (1 / yrs) - 1) * 100, 2),
        "max_drawdown_pct": round(dd * 100, 1),
        "deploys": sum(e["action"] == "deploy" for e in events),
        "refills": sum(e["action"] == "refill" for e in events),
        "costs_during": round(costs_before),
        "tax_during": round(tax_before),
        "tax_total_incl_exit": round(b.tax),
        "harvest_years": len(harvests),
        "gains_harvested": sum(h[1] for h in harvests),
    }, events, v


if __name__ == "__main__":
    import argparse, os
    ap = argparse.ArgumentParser(description="20% / 50% cash reserve vs fully invested, Nifty 50, 2016-2026")
    ap.add_argument("--tri", default=os.path.join("data", "nifty50_tri.csv"))
    ap.add_argument("--eod2", default=os.path.join("data", "eod2"))
    ap.add_argument("--out", default="results")
    ap.add_argument("--no-harvest", action="store_true", help="turn off the yearly tax-free gain booking")
    a = ap.parse_args()
    if a.no_harvest:
        Book.harvest = lambda self, px, d: 0.0
    os.makedirs(a.out, exist_ok=True)
    df, seed_high, cash_last = load(a.tri, a.eod2)
    print(f"period {df.index[0].date()} to {df.index[-1].date()}, highest close before start {seed_high}, "
          f"cash index data ends {cash_last.date()}")
    rows, curves = [], {}
    for w in (0.0, 0.2, 0.5):
        s, ev, v = run(df, seed_high, w)
        rows.append(s)
        curves[f"cash_{int(w*100)}"] = v
        if ev:
            pd.DataFrame(ev).to_csv(os.path.join(a.out, f"events_cash_{int(w*100)}.csv"), index=False)
        if w == 0.2:
            # how much further Nifty fell after each time the cash went in (until the next refill)
            dep = [e for e in ev if e["action"] == "deploy"]
            ref = [e for e in ev if e["action"] == "refill"]
            ft = []
            for i, e in enumerate(dep):
                end = pd.Timestamp(ref[i]["trade"]) if i < len(ref) else df.index[-1]
                seg = df.price[(df.index >= pd.Timestamp(e["trade"])) & (df.index <= end)]
                ft.append({"cash_in": e["trade"], "nifty_close": e["nifty"], "lowest_after": seg.min(),
                           "lowest_date": seg.idxmin().date(), "further_fall_pct": round((seg.min() / e["nifty"] - 1) * 100, 1)})
            pd.DataFrame(ft).to_csv(os.path.join(a.out, "after_cash_went_in.csv"), index=False)
    summ = pd.DataFrame(rows)
    summ.to_csv(os.path.join(a.out, "summary.csv"), index=False)
    pd.DataFrame(curves).to_csv(os.path.join(a.out, "daily_values.csv"))
    pd.set_option("display.width", 200)
    print(summ.T)
