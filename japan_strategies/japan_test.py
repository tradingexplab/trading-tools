"""
japan_test.py - three Japanese chart methods on the Nifty 50, each against simply holding.

  * Candlestick patterns: bullish engulfing, hammer, morning star, piercing line and three white
    soldiers, pooled into one rule (a signal is any of the five).
  * Heikin-Ashi: buy after N green Heikin-Ashi candles in a row, sell after a red one. N = 2, 3, 4.
  * Ichimoku (9, 26, 52): buy when Tenkan crosses above Kijun while the close is above the cloud,
    sell when the close falls below the cloud.

Shared setup
  * Prices: the Nifty 50 price index divided by 100, standing in for NIFTYBEES. Dividends are not included.
    2003 to 20 Feb 2012 from niftyindices.com files, 21 Feb 2012 onward from EOD2 (see README.md).
  * Signals are computed on the full history; each period then starts with no position.
  * A signal on a day's close is traded at the next session's open. Whole units, all available cash,
    idle cash earns nothing. Start cash Rs 10,00,000.
  * Charges: costs.round_trip_cost() at Zerodha equity-ETF statutory rates, charged in full when a trade is
    opened. The bid-ask spread is not included.
  * A position still open on a period's last day is sold at that close.
  * Periods: earlier years 1 Jan 2004 - 31 Dec 2020, later years 1 Jan 2021 - 23 Oct 2026.

Usage:  python fetch_data.py   then   python japan_test.py
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import costs  # noqa: E402  (trading-tools/costs.py)

DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "results")
INSTRUMENT = "etf_equity"
START_CASH = 1_000_000.0
SPLICE = "2012-02-21"          # first date taken from the EOD2 file
PERIODS = {"Earlier years": ("2004-01-01", "2020-12-31"), "Later years": ("2021-01-01", "2026-10-23")}
CANDLE_HOLD = 5                # candlestick trades are sold at the open of the 6th session (entry session = 1)
BODY_MIN = 0.0025              # a "big" candle body is at least 0.25% of the close
DOWNTREND_AVG = 20             # "downtrend before": close below its 20-day simple average


def load_prices():
    frames = []
    for f in sorted(glob.glob(os.path.join(DATA, "NIFTY_50_Historical_PR_*.csv"))):
        d = pd.read_csv(f)
        d["Date"] = pd.to_datetime(d["Date"], format="%d %b %Y")
        frames.append(d[["Date", "Open", "High", "Low", "Close"]])
    old = pd.concat(frames).drop_duplicates("Date").sort_values("Date").set_index("Date")
    new = pd.read_csv(os.path.join(DATA, "nifty 50.csv"), parse_dates=["Date"])
    new = new[["Date", "Open", "High", "Low", "Close"]].drop_duplicates("Date").sort_values("Date").set_index("Date")
    return pd.concat([old[old.index < SPLICE], new[new.index >= SPLICE]]).sort_index()


# ----------------------------------------------------------------------------- signals
def candle_signal(px):
    O, H, L, C = (px[k] for k in ["Open", "High", "Low", "Close"])
    body = (C - O).abs()
    big = body >= BODY_MIN * C
    red, green = C < O, C > O
    down = C < C.rolling(DOWNTREND_AVG).mean()
    rng = (H - L).replace(0, np.nan)
    top, bottom = pd.concat([O, C], axis=1).max(axis=1), pd.concat([O, C], axis=1).min(axis=1)

    def before(k):                       # downtrend flag for the bar just before the first candle
        return down.shift(k + 1)

    engulfing = (red.shift(1) & green & (O <= C.shift(1)) & (C >= O.shift(1))
                 & big.shift(1) & big & before(1))
    hammer = (((bottom - L) >= 2 * body) & ((H - top) <= body) & (bottom >= L + (2 / 3) * rng)
              & big & before(0))
    morning_star = (red.shift(2) & (body.shift(2) >= 0.005 * C.shift(2)) & (body.shift(1) <= 0.3 * body.shift(2))
                    & green & big & (C > (O.shift(2) + C.shift(2)) / 2) & before(2))
    piercing = (red.shift(1) & green & (O <= C.shift(1)) & (C > (O.shift(1) + C.shift(1)) / 2) & (C < O.shift(1))
                & big.shift(1) & big & before(1))

    def soldier(k):
        return green.shift(k) & big.shift(k) & (C.shift(k) >= L.shift(k) + (2 / 3) * rng.shift(k))

    def opens_inside_previous_body(k):
        lo = pd.concat([O.shift(k + 1), C.shift(k + 1)], axis=1).min(axis=1)
        hi = pd.concat([O.shift(k + 1), C.shift(k + 1)], axis=1).max(axis=1)
        return (O.shift(k) >= lo) & (O.shift(k) <= hi)

    soldiers = (soldier(0) & soldier(1) & soldier(2) & (C > C.shift(1)) & (C.shift(1) > C.shift(2))
                & opens_inside_previous_body(0) & opens_inside_previous_body(1))
    pooled = pd.concat([s.fillna(False) for s in (engulfing, hammer, morning_star, piercing, soldiers)], axis=1).any(axis=1)
    return pooled.to_numpy()


def heikin_ashi_green(px):
    O, H, L, C = (px[k].to_numpy() for k in ["Open", "High", "Low", "Close"])
    ha_close = (O + H + L + C) / 4
    ha_open = np.empty(len(O))
    ha_open[0] = (O[0] + C[0]) / 2
    for i in range(1, len(O)):
        ha_open[i] = (ha_open[i - 1] + ha_close[i - 1]) / 2     # yesterday's Heikin-Ashi open and close
    return ha_close > ha_open, ha_close < ha_open


def ichimoku_lines(px, tenkan=9, kijun=26, senkou_b=52, shift=26):
    H, L = px["High"], px["Low"]

    def mid(n):
        return (H.rolling(n).max() + L.rolling(n).min()) / 2

    t, k = mid(tenkan), mid(kijun)
    span_a = ((t + k) / 2).shift(shift)          # the cloud drawn at a bar was computed `shift` bars earlier
    span_b = mid(senkou_b).shift(shift)
    return t.to_numpy(), k.to_numpy(), np.fmax(span_a, span_b).to_numpy(), np.fmin(span_a, span_b).to_numpy()


# ----------------------------------------------------------------------------- engine
class Backtest:
    def __init__(self, px):
        self.px = px
        self.idx = px.index
        self.open = (px["Open"] / 100).to_numpy()
        self.close = (px["Close"] / 100).to_numpy()

    def window(self, start, end):
        inside = (self.idx >= pd.Timestamp(start)) & (self.idx <= pd.Timestamp(end))
        first = int(np.argmax(inside))
        last = len(inside) - 1 - int(np.argmax(inside[::-1]))
        return first, last

    @staticmethod
    def units_for(cash, price):
        units = int(cash / price)
        while units > 0 and units * price + costs.round_trip_cost(units * price, INSTRUMENT) > cash:
            units -= 1
        return units

    def run(self, rule, first, last):
        """rule(i, entry_index_or_None) -> 'enter' | 'exit' | None, decided on day i's close, filled at day i+1's open."""
        cash, pos, pending = START_CASH, None, None
        equity, trades, invested = [], [], 0
        for i in range(first, last + 1):
            if pending == "enter" and pos is None:
                units = self.units_for(cash, self.open[i])
                if units:
                    fee = costs.round_trip_cost(units * self.open[i], INSTRUMENT)
                    cash -= units * self.open[i] + fee
                    pos = dict(units=units, entry=i, price=self.open[i], fee=fee)
            elif pending == "exit" and pos is not None:
                cash += pos["units"] * self.open[i]
                trades.append(self._trade(pos, i, self.open[i]))
                pos = None
            pending = None
            invested += pos is not None
            value = cash + (pos["units"] * self.close[i] if pos else 0.0)
            if i == last and pos is not None:
                cash += pos["units"] * self.close[i]
                trades.append(self._trade(pos, i, self.close[i]))
                pos, value = None, cash
            elif i < last:
                pending = rule(i, pos["entry"] if pos else None)
            equity.append(value)
        return np.array(equity), pd.DataFrame(trades), invested / (last - first + 1)

    def _trade(self, pos, exit_i, exit_price):
        return dict(entry=self.idx[pos["entry"]].date(), exit=self.idx[exit_i].date(),
                    entry_price=pos["price"], exit_price=exit_price, units=pos["units"], charges=pos["fee"],
                    profit=pos["units"] * (exit_price - pos["price"]) - pos["fee"])

    def hold(self, first, last):
        price = self.open[first]
        units = self.units_for(START_CASH, price)
        fee = costs.round_trip_cost(units * price, INSTRUMENT)
        equity = START_CASH - units * price - fee + units * self.close[first:last + 1]
        return equity, pd.DataFrame([dict(charges=fee, profit=units * (self.close[last] - price) - fee)])


def summarise(equity, trades, share, years):
    peak = np.maximum.accumulate(equity)
    return dict(final=equity[-1], total=(equity[-1] / START_CASH - 1) * 100,
                per_year=((equity[-1] / START_CASH) ** (1 / years) - 1) * 100,
                worst_fall=((equity / peak) - 1).min() * 100, trades=len(trades),
                up=int((trades.profit > 0).sum()), down=int((trades.profit <= 0).sum()),
                charges=trades.charges.sum(), invested=share * 100)


def main():
    px = load_prices()
    bt = Backtest(px)
    candle = candle_signal(px)
    green, red = heikin_ashi_green(px)
    t, k, cloud_top, cloud_bottom = ichimoku_lines(px)
    close = px["Close"].to_numpy()

    def candle_rule(i, entry):
        if entry is None:
            return "enter" if candle[i] else None
        return "exit" if i == entry + CANDLE_HOLD - 1 else None

    def heikin_ashi_rule(n):
        def rule(i, entry):
            if entry is None:
                return "enter" if i >= n - 1 and green[i - n + 1:i + 1].all() else None
            return "exit" if red[i] else None
        return rule

    def ichimoku_rule(i, entry):
        if entry is None:
            ok = i >= 1 and not np.isnan(cloud_top[i]) and not np.isnan(k[i - 1])
            return "enter" if ok and t[i] > k[i] and t[i - 1] <= k[i - 1] and close[i] > cloud_top[i] else None
        return "exit" if not np.isnan(cloud_bottom[i]) and close[i] < cloud_bottom[i] else None

    strategies = [("Candlestick patterns (5, pooled)", candle_rule),
                  ("Heikin-Ashi, 2 green", heikin_ashi_rule(2)),
                  ("Heikin-Ashi, 3 green", heikin_ashi_rule(3)),
                  ("Heikin-Ashi, 4 green", heikin_ashi_rule(4)),
                  ("Ichimoku 9/26/52", ichimoku_rule)]

    os.makedirs(OUT, exist_ok=True)
    lines = [f"Nifty 50 {px.index.min().date()} to {px.index.max().date()}, {len(px)} sessions. Start cash Rs {START_CASH:,.0f}.", ""]
    for period, (start, end) in PERIODS.items():
        first, last = bt.window(start, end)
        years = (bt.idx[last] - bt.idx[first]).days / 365.25
        lines.append(f"{period}: {bt.idx[first].date()} to {bt.idx[last].date()}")
        lines.append(f"{'':34s}{'final (Rs)':>13s}{'total':>9s}{'per year':>9s}{'worst fall':>11s}{'trades':>8s}{'up/down':>10s}{'charges':>10s}{'invested':>9s}")
        eq, tr = bt.hold(first, last)
        s = summarise(eq, tr.assign(profit=tr.profit), 1.0, years)
        lines.append(f"{'Hold':34s}{s['final']:13,.0f}{s['total']:8.1f}%{s['per_year']:8.1f}%{s['worst_fall']:10.1f}%{1:8d}{'-':>10s}{s['charges']:10,.0f}{'100%':>9s}")
        for name, rule in strategies:
            eq, tr, share = bt.run(rule, first, last)
            s = summarise(eq, tr, share, years)
            lines.append(f"{name:34s}{s['final']:13,.0f}{s['total']:8.1f}%{s['per_year']:8.1f}%{s['worst_fall']:10.1f}%{s['trades']:8d}"
                         f"{str(s['up']) + '/' + str(s['down']):>10s}{s['charges']:10,.0f}{s['invested']:8.0f}%")
            slug = name.lower().replace(" ", "_").replace(",", "").replace("(", "").replace(")", "").replace("/", "-")
            tr.to_csv(os.path.join(OUT, f"trades_{period.split()[0].lower()}_{slug}.csv"), index=False)
        lines.append("")
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(OUT, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
