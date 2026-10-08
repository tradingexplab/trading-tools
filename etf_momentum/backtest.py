"""
ETF momentum rotation vs a Nifty + Gold 50/50 split, Indian ETFs, Oct 2016 - Sep 2026.

Usage:
    python backtest.py <path to EOD2 daily folder>

Data: daily CSVs from EOD2 (https://github.com/BennyThadikaran/eod2), one file per symbol
with Date and Close columns, plus "nifty 50.csv" used as the trading calendar.
Only closing prices are used.
"""
import sys
import numpy as np
import pandas as pd

# ---------------------------------------------------------------- settings
CAPITAL = 1_000_000
START = "2016-09-30"            # first month-end ranking date
LOOKBACKS = [21, 63, 126, 252]  # ~1, 3, 6, 12 months in trading days
VOL_WINDOW = 126                # ~6 months of daily returns
MIN_HISTORY = 252               # an ETF joins after 12 months of its own prices

UNIVERSE = ("goldbees silverbees niftybees juniorbees mid150bees bankbees psubnkbees pvtbanietf "
            "itbees pharmabees autobees fmcgietf metalietf oilietf morealty infrabees cpseetf "
            "consumbees hdfcsml250 alphaetf alpl30ietf mom30ietf lowvolietf").split()

# Zerodha delivery charges (statutory only; bid-ask spread not included)
EXCHANGE = 0.0000307   # NSE transaction charge
SEBI = 0.000001
GST = 0.18             # on exchange + SEBI charges
STAMP = 0.00015        # buy side
STT_SELL = 0.00001     # sell side, equity ETFs only
NO_STT = {"goldbees", "silverbees"}
DP = 15.34             # per sell, per symbol


def cost(symbol, side, value):
    c = (EXCHANGE + SEBI) * (1 + GST) * value
    if side == "buy":
        c += STAMP * value
    elif symbol not in NO_STT:
        c += STT_SELL * value
    return c


# ---------------------------------------------------------------- data
def load(folder):
    splits = pd.read_csv("splits.csv")
    cal = pd.read_csv(f"{folder}/nifty 50.csv", parse_dates=["Date"]).set_index("Date").index.sort_values()
    closes, first = {}, {}
    for s in UNIVERSE:
        c = pd.read_csv(f"{folder}/{s}.csv", parse_dates=["Date"]).set_index("Date").Close.sort_index()
        for _, row in splits[splits.symbol == s].iterrows():
            c[c.index < row.ex_date] = c[c.index < row.ex_date] / row.ratio
            if "history starts" in row.action:
                c = c[c.index >= row.ex_date]
        closes[s], first[s] = c, c.index[0]
    cal = cal[cal >= min(first.values())]
    traded = pd.DataFrame(closes).reindex(cal)   # NaN on days a symbol did not trade
    return cal, traded, traded.ffill(), first


class Market:
    def __init__(self, folder):
        self.cal, self.traded, self.px, self.first = load(folder)
        self.ret = self.px.pct_change()
        me = pd.Series(self.cal, index=self.cal).groupby([self.cal.year, self.cal.month]).last()
        self.month_ends = [d for d in me if pd.Timestamp(START) <= d < self.cal[-1]]

    def fill(self, s, day):
        """Next traded close on or after `day`."""
        t = self.traded[s].loc[day:].dropna()
        return t.iloc[0] if len(t) else self.px[s].iloc[-1]

    def eligible(self, i):
        n_before = (self.cal <= self.cal[i]).sum()
        return [s for s in UNIVERSE
                if n_before - (self.cal < self.first[s]).sum() > MIN_HISTORY and not np.isnan(self.px[s].iloc[i])]

    def scores(self, i):
        el = self.eligible(i)
        r = pd.DataFrame({k: self.px[el].iloc[i] / self.px[el].iloc[i - k] - 1 for k in LOOKBACKS})
        vol = self.ret[el].iloc[i - VOL_WINDOW + 1:i + 1].std()
        return r.mean(axis=1), vol


# ---------------------------------------------------------------- strategies
def momentum(m, hold, exit_rank, vol_adjusted):
    """Rank on each month-end close, trade at the next day's close.
    Sell holdings that fall below exit_rank; refill empty slots from the top of the ranking."""
    cash, units, trades = CAPITAL, {}, 0
    signals = {m.cal.get_loc(d) for d in m.month_ends}
    equity = {}
    for i, d in enumerate(m.cal):
        if i - 1 in signals:
            score, vol = m.scores(i - 1)
            key = score / vol if vol_adjusted else score
            order = pd.DataFrame({"k": key, "v": vol}).sort_values(["k", "v"], ascending=[False, True]).index.tolist()
            rank = {s: n + 1 for n, s in enumerate(order)}
            sold = 0
            for s in [s for s in units if rank.get(s, 999) > exit_rank]:
                v = units.pop(s) * m.fill(s, d)
                cash += v - cost(s, "sell", v); trades += 1; sold += 1
            cash -= DP * sold
            buys = [s for s in order if s not in units][:hold - len(units)]
            if buys:
                budget = cash / len(buys)
                for s in buys:
                    p = m.fill(s, d)
                    q = int(budget / (p * (1 + STAMP + 0.0001)))
                    if q > 0:
                        cash -= q * p + cost(s, "buy", q * p); units[s] = q; trades += 1
        if d >= m.month_ends[0]:
            equity[d] = cash + sum(q * m.px[s].iloc[i] for s, q in units.items())
    return pd.Series(equity), trades


def nifty_gold(m, nifty_weight=0.5):
    """Hold Nifty BeES and Gold BeES; reset to target weights after the last trading day of each September."""
    w = {"niftybees": nifty_weight, "goldbees": 1 - nifty_weight}
    cash, units, trades = CAPITAL, {}, 0
    sept = {m.cal.get_loc(d) for d in m.month_ends if d.month == 9}
    first = min(sept)
    equity = {}
    for i, d in enumerate(m.cal):
        if i - 1 in sept:
            value = cash + sum(q * m.px[s].iloc[i] for s, q in units.items())
            for s in list(units):                     # trim overweight first
                target = int(value * w[s] / m.px[s].iloc[i])
                if target < units[s]:
                    v = (units[s] - target) * m.fill(s, d)
                    cash += v - cost(s, "sell", v) - DP; units[s] = target; trades += 1
            for s in w:                                # then top up
                p = m.fill(s, d)
                target = int(min(value * w[s], cash + units.get(s, 0) * p) / (p * 1.0002))
                add = target - units.get(s, 0)
                if add > 0 and add * p * 1.0002 <= cash:
                    cash -= add * p + cost(s, "buy", add * p); units[s] = units.get(s, 0) + add; trades += 1
        if i > first:
            equity[d] = cash + sum(q * m.px[s].iloc[i] for s, q in units.items())
    return pd.Series(equity), trades


def buy_and_hold(m, s):
    d = m.cal[m.cal.get_loc(m.month_ends[0]) + 1]
    p = m.fill(s, d); q = int(CAPITAL / (p * 1.0002))
    return CAPITAL - q * p - cost(s, "buy", q * p) + q * m.px[s].loc[d:], 1


# ---------------------------------------------------------------- report
def stats(e):
    years = (e.index[-1] - e.index[0]).days / 365.25
    return (e.iloc[-1] / CAPITAL) ** (1 / years) - 1, (e / e.cummax() - 1).min(), e.iloc[-1]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    m = Market(sys.argv[1])
    runs = {
        "Momentum, top 2 (exit below rank 5)": momentum(m, 2, 5, False),
        "Momentum, top 6 (vol-adjusted, exit below rank 8)": momentum(m, 6, 8, True),
        "Nifty + Gold 50/50, reset yearly": nifty_gold(m, 0.5),
        "Nifty + Gold 70/30, reset yearly": nifty_gold(m, 0.7),
        "Gold BeES, buy and hold": buy_and_hold(m, "goldbees"),
        "Nifty BeES, buy and hold": buy_and_hold(m, "niftybees"),
    }
    print(f"{'Strategy':52s} {'CAGR':>7s} {'Worst fall':>11s} {'Final':>12s} {'Trades':>7s}")
    for name, (e, t) in runs.items():
        cagr, dd, final = stats(e)
        print(f"{name:52s} {cagr*100:6.1f}% {dd*100:10.1f}% {final:12,.0f} {t:7d}")
