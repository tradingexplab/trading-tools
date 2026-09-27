"""44 SMA pullback backtest (long only, daily bars).

Usage:
    python backtest.py --data path/to/eod2_data/daily --out results

Writes, per target test (1:2 and 1:3):
    trade_log_1to2.csv / trade_log_1to3.csv   one row per order
    signals_1to2.csv   / signals_1to3.csv     one row per candle passing the rising, touch and green-candle checks
    summary.txt                               every reported metric
The SHA-256 of each trade log is printed so two data copies can be compared.
"""
import argparse
import hashlib
import math
import os
from datetime import date

import pandas as pd

# ---------------------------------------------------------------- parameters
SMA_LEN = 44
RISE_LOOKBACK = 5
RISE_MIN = 1.005          # SMA_t >= SMA_(t-5) * 1.005
TOUCH_BAND = 0.01         # |Low - SMA| / SMA <= 1%
BUFFER = 0.05             # rupees above high / below low
ORDER_SESSIONS = 3
POSITION = 100_000.0

LOAD_START = pd.Timestamp("2015-06-01")
SIGNAL_START = pd.Timestamp("2016-01-01")
TEST_END = pd.Timestamp("2026-08-31")

UNIVERSE = (
    "ADANIENT ADANIPORTS APOLLOHOSP ASIANPAINT AXISBANK BAJAJ-AUTO BAJFINANCE "
    "BAJAJFINSV BEL BHARTIARTL CIPLA COALINDIA DRREDDY EICHERMOT ETERNAL GRASIM "
    "HCLTECH HDFCBANK HDFCLIFE HINDALCO HINDUNILVR ICICIBANK ITC INFY INDIGO "
    "JSWSTEEL JIOFIN KOTAKBANK LT M&M MARUTI MAXHEALTH NTPC NESTLEIND ONGC "
    "POWERGRID RELIANCE SBILIFE SHRIRAMFIN SBIN SUNPHARMA TCS TATACONSUM TMPV "
    "TATASTEEL TECHM TITAN TRENT ULTRACEMCO WIPRO"
).split()
TOP10 = "HDFCBANK ICICIBANK RELIANCE BHARTIARTL LT SBIN INFY AXISBANK KOTAKBANK M&M".split()

DEMERGERS = {  # symbol: gap date (session 0)
    "TMPV": "2025-10-14",
    "ADANIENT": "2018-09-06",
    "GRASIM": "2017-07-19",
    "RELIANCE": "2023-07-20",
}

# Zerodha equity delivery, NSE (zerodha.com/charges, checked 25 Sep 2026)
STT = 0.001
TXN = 0.0000307
SEBI = 0.000001
GST = 0.18
STAMP_BUY = 0.00015
DP_SELL = 15.34


def r6(x):
    """Remove float noise before price comparisons."""
    return round(x, 6)


def charges(buy_value, sell_value):
    b_stt = STT * buy_value
    b_txn = TXN * buy_value
    b_sebi = SEBI * buy_value
    b_gst = GST * (b_txn + b_sebi)
    b_stamp = STAMP_BUY * buy_value
    s_stt = STT * sell_value
    s_txn = TXN * sell_value
    s_sebi = SEBI * sell_value
    s_gst = GST * (s_txn + s_sebi)
    s_dp = DP_SELL
    parts = dict(
        buy_stt=b_stt, buy_txn=b_txn, buy_sebi=b_sebi, buy_gst=b_gst, buy_stamp=b_stamp,
        sell_stt=s_stt, sell_txn=s_txn, sell_sebi=s_sebi, sell_gst=s_gst, sell_dp=s_dp,
    )
    parts["total_charges"] = sum(parts.values())
    return parts


def load(data_dir, sym):
    df = pd.read_csv(os.path.join(data_dir, f"{sym.lower()}.csv"), parse_dates=["Date"])
    df = df[(df.Date >= LOAD_START) & (df.Date <= TEST_END)]
    df = df[["Date", "Open", "High", "Low", "Close"]].sort_values("Date").reset_index(drop=True)
    df["SMA"] = df.Close.rolling(SMA_LEN).mean()
    df["SMA_prev"] = df.SMA.shift(RISE_LOOKBACK)
    return df


def run_stock(sym, df, mult):
    orders, signals = [], []
    visit_active = False      # inside a visit (an away day has occurred)
    visit_used = False        # a candle in this visit already passed the entry checks
    order = None              # waiting order
    trade = None              # open trade
    last = len(df) - 1

    def close_order(o, reason, i):
        o.update(status="no_fill", reason=reason, end_date=df.Date[i].date())
        orders.append(o)

    def close_trade(t, i, price, etype):
        t.update(exit_date=df.Date[i].date(), exit_price=price, exit_type=etype,
                 holding=i - t["_fill_i"] + 1)
        orders.append(t)

    for i in range(len(df)):
        o_, h, l, c = df.Open[i], df.High[i], df.Low[i], df.Close[i]

        # ---------------- intraday: open trade exits (days after fill)
        if trade is not None:
            st, tg = trade["stop"], trade["target"]
            if r6(o_) <= st:
                close_trade(trade, i, o_, "gap_stop"); trade = None
            elif r6(o_) >= tg:
                close_trade(trade, i, o_, "gap_target"); trade = None
            elif r6(l) <= st:
                close_trade(trade, i, st, "stop"); trade = None
            elif r6(h) >= tg:
                close_trade(trade, i, tg, "target"); trade = None

        # ---------------- intraday: waiting order
        if order is not None:
            order["_sessions"] += 1
            e, st = order["entry"], order["stop"]
            filled = False
            if r6(o_) > e:
                close_order(order, "gap", i); order = None
            elif r6(o_) <= st:
                close_order(order, "cancelled", i); order = None
            elif r6(h) >= e:
                filled = True
            elif r6(l) <= st:
                close_order(order, "cancelled", i); order = None
            elif order["_sessions"] >= ORDER_SESSIONS:
                close_order(order, "expired", i); order = None

            if filled:
                trade = order; order = None
                trade.update(status="filled", reason="", fill_date=df.Date[i].date(), _fill_i=i)
                # fill-day exits: stop wins
                if r6(l) <= trade["stop"]:
                    close_trade(trade, i, trade["stop"], "stop"); trade = None
                elif r6(h) >= trade["target"]:
                    close_trade(trade, i, trade["target"], "target"); trade = None

        # ---------------- end of test: close open trade at the close
        if i == last and trade is not None:
            close_trade(trade, i, c, "end_of_test"); trade = None

        # ---------------- close: signal detection
        sma, sma_prev = df.SMA[i], df.SMA_prev[i]
        if math.isnan(sma):
            continue
        if l > sma * (1 + TOUCH_BAND):          # away day
            visit_active, visit_used = True, False
            continue
        if not visit_active or math.isnan(sma_prev):
            continue
        rising = sma >= sma_prev * RISE_MIN
        touch = abs(l - sma) / sma <= TOUCH_BAND
        bullish = c > o_
        if not (rising and touch and bullish):
            continue
        if visit_used:
            continue                            # not the first signal in this visit
        visit_used = True
        d = df.Date[i]
        rec = dict(symbol=sym, signal_date=d.date(), open=o_, high=h, low=l, close=c,
                   sma=round(sma, 4), sma_5_ago=round(sma_prev, 4))
        if d < SIGNAL_START:
            rec["outcome"] = "pre_window_blocks_visit"
            signals.append(rec)
            continue
        if trade is not None:
            rec["outcome"] = "ignored_trade_open"
            signals.append(rec)
            continue
        if order is not None:
            close_order(order, "replaced", i); order = None
        rec["outcome"] = "order_placed"
        signals.append(rec)
        entry = round(h + BUFFER, 2)
        stop = round(l - BUFFER, 2)
        R = r6(entry - stop)
        order = dict(symbol=sym, test=f"1:{mult}", signal_date=d.date(),
                     sig_open=o_, sig_high=h, sig_low=l, sig_close=c, sig_sma=round(sma, 4),
                     entry=entry, stop=stop, R=R, target=r6(entry + mult * R),
                     _sessions=0, _signal_i=i)

    if order is not None:
        order.update(status="no_fill", reason="end_of_test", end_date=df.Date[last].date())
        orders.append(order)
    return orders, signals


def enrich(o):
    if o["status"] != "filled":
        return o
    qty = POSITION / o["entry"]
    sell_value = qty * o["exit_price"]
    ch = charges(POSITION, sell_value)
    gross = sell_value - POSITION
    net = gross - ch["total_charges"]
    o.update(qty=qty, buy_value=POSITION, sell_value=sell_value, **ch,
             gross_result=gross, net_result=net,
             gross_R=(o["exit_price"] - o["entry"]) / o["R"],
             net_R=net / (qty * o["R"]),
             gross_pct=(o["exit_price"] - o["entry"]) / o["entry"],
             net_pct=net / POSITION)
    return o


COLS = ["symbol", "test", "signal_date", "sig_open", "sig_high", "sig_low", "sig_close", "sig_sma",
        "entry", "stop", "R", "target", "status", "reason", "end_date", "fill_date",
        "exit_date", "exit_price", "exit_type", "holding", "qty", "buy_value", "sell_value",
        "buy_stt", "buy_txn", "buy_sebi", "buy_gst", "buy_stamp",
        "sell_stt", "sell_txn", "sell_sebi", "sell_gst", "sell_dp", "total_charges",
        "gross_result", "net_result", "gross_R", "net_R", "gross_pct", "net_pct"]


def worst_streak(tr):
    tr = tr.sort_values(["exit_date", "symbol"])
    best = cur = 0
    for v in tr.net_result:
        cur = cur + 1 if v <= 0 else 0
        best = max(best, cur)
    return best


def block(stats, x):
    n = len(x)
    if n == 0:
        return "n=0"
    return (f"n={n}  win%={100*(x.net_result > 0).mean():.2f}  avgR={x.net_R.mean():.4f}  "
            f"(gross win%={100*(x.gross_result > 0).mean():.2f}  gross avgR={x.gross_R.mean():.4f})")


def report(label, orders, signals, trading_days):
    L = []
    p = L.append
    sg = signals[signals.outcome != "pre_window_blocks_visit"]
    tr = orders[orders.status == "filled"].copy()
    nf = orders[orders.status == "no_fill"]
    p(f"=== {label} ===")
    p("Funnel")
    p(f"  signal candles: {len(sg)}  (ignored, trade open: {(sg.outcome == 'ignored_trade_open').sum()})")
    p(f"  orders placed:  {len(orders)}")
    p(f"  fills:          {len(tr)}")
    p(f"  no_fills:       {len(nf)}  " + ", ".join(
        f"{r}={(nf.reason == r).sum()}" for r in ["gap", "cancelled", "expired", "replaced", "end_of_test"]))
    if len(tr) == 0:
        p(""); return "\n".join(L)
    n = len(tr)
    p("Per trade")
    p(f"  before costs: win%={100*(tr.gross_result > 0).mean():.2f}  avgR={tr.gross_R.mean():.4f}  "
      f"avg%={100*tr.gross_pct.mean():.4f}")
    p(f"  after costs:  win%={100*(tr.net_result > 0).mean():.2f}  avgR={tr.net_R.mean():.4f}  "
      f"avg%={100*tr.net_pct.mean():.4f}")
    se = tr.net_R.std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
    p(f"  SE of net avgR (sample sd / sqrt n): {se:.4f}")
    p(f"Total net result: Rs {tr.net_result.sum():,.2f}  (over {n} trades at Rs 1,00,000 each)")
    p(f"Holding period (sessions): median={tr.holding.median():.1f}  longest={int(tr.holding.max())}")
    p(f"Worst losing streak (after costs): {worst_streak(tr)}")
    p("Exit types: " + ", ".join(f"{e}={(tr.exit_type == e).sum()}"
                                 for e in ["stop", "target", "gap_stop", "gap_target", "end_of_test"]))
    eot = tr[tr.exit_type == "end_of_test"]
    p(f"End-of-test trades: {len(eot)}")
    p(f"  with:    {block(None, tr)}")
    p(f"  without: {block(None, tr[tr.exit_type != 'end_of_test'])}")
    # demergers
    tot = 0
    parts = []
    for sym, gd in DEMERGERS.items():
        t = tr[tr.symbol == sym]
        if t.empty:
            parts.append(f"{sym}: 0"); continue
        gd = pd.Timestamp(gd)
        days = trading_days[sym]
        g_idx = days.searchsorted(gd)
        win_end = days[min(g_idx + 44, len(days) - 1)]
        fd = pd.to_datetime(t.fill_date); ed = pd.to_datetime(t.exit_date); sd = pd.to_datetime(t.signal_date)
        across = (fd < gd) & (ed >= gd)
        after = (sd > gd) & (sd <= win_end)
        k = int((across | after).sum())
        tot += k
        parts.append(f"{sym}: {k} (open across {int(across.sum())}, signalled in sessions 1-44 {int(after.sum())})")
    p(f"Demerger-affected filled trades: {tot}  [" + "; ".join(parts) + "]")
    p("Per stock (trades, net win%):")
    g = tr.groupby("symbol").agg(trades=("net_result", "size"),
                                 win=("net_result", lambda v: 100 * (v > 0).mean()))
    g = g.sort_values("trades", ascending=False)
    p("  " + "; ".join(f"{s} {int(r.trades)} ({r.win:.0f}%)" for s, r in g.iterrows()))
    p("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    rt = charges(POSITION, POSITION)["total_charges"]
    out = [f"Round trip on Rs 1,00,000 at exit = entry: Rs {rt:.2f}", ""]

    data = {s: load(a.data, s) for s in UNIVERSE}
    trading_days = {s: pd.DatetimeIndex(d.Date) for s, d in data.items()}
    out.append("First possible signal date per stock (SMA and SMA 5 sessions ago both exist):")
    firsts = {s: d.Date[d.SMA_prev.first_valid_index()].date() for s, d in data.items()}
    late = {s: v for s, v in firsts.items() if v > date(2016, 1, 1)}
    out.append("  late entrants: " + ", ".join(f"{s} {v}" for s, v in sorted(late.items(), key=lambda x: x[1])))
    out.append("")

    for mult in (2, 3):
        all_o, all_s = [], []
        for s in UNIVERSE:
            o, sg = run_stock(s, data[s], mult)
            all_o += [enrich(x) for x in o]
            all_s += sg
        od = pd.DataFrame(all_o)
        od = od[[c for c in COLS if c in od.columns]].sort_values(["symbol", "signal_date"])
        sd = pd.DataFrame(all_s).sort_values(["symbol", "signal_date"])
        tag = f"1to{mult}"
        lp = os.path.join(a.out, f"trade_log_{tag}.csv")
        od.to_csv(lp, index=False, float_format="%.6f", lineterminator="\n")
        sd.to_csv(os.path.join(a.out, f"signals_{tag}.csv"), index=False, float_format="%.6f", lineterminator="\n")
        with open(lp, "rb") as f:
            out.append(f"trade_log_{tag}.csv sha256 {hashlib.sha256(f.read()).hexdigest()}")
        out.append(report(f"1:{mult} - all 50", od, sd, trading_days))
        out.append(report(f"1:{mult} - top 10", od[od.symbol.isin(TOP10)], sd[sd.symbol.isin(TOP10)],
                          trading_days))

    text = "\n".join(out)
    with open(os.path.join(a.out, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()