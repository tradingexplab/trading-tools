"""
sizing.py — what stop distances a given account can actually trade.

The inverse of costs.py. That one asks "given this trade, what win rate do I
need?". This one asks "given this account, which setups are even sizeable?".

The key fact, and the thing that is easy to get wrong: position size is not a
free choice. Once the risk budget and the stop distance are fixed, the notional
follows. From the sizing formula

    shares = (risk - flat) / (stop_distance + pct * price)

and stop_pct = stop_distance / price, the price cancels:

    notional = (risk - flat) / (stop_pct + pct)

So a tighter stop forces a LARGER position, and a wider stop forces a smaller
one. That is what bounds the band at both ends:

    tight end  <- notional would exceed the capital you have
    wide  end  <- notional would fall under your minimum position size

The cost ceiling (cost as a share of risk) does not bind anywhere inside the
band. With a fixed rupee risk budget the flat fee sits against the same rupees
regardless of stop width, so the ratio barely moves. It is kept as a tripwire.

Rates are equity ETF delivery on Zerodha. Verify before trusting:
https://zerodha.com/charges
"""

CAPITAL       = 10_000.0
RISK_PCT      = 0.01
MIN_POSITION  = 5_000.0
COST_TRIPWIRE = 0.20        # flag if cost exceeds this share of actual risk

FLAT_COST     = 15.34       # DP charge, per sell, any size
PCT_COST      = 0.000235    # round-trip percentage fees (0.0235%)

ATR_MULTIPLE  = 0.5         # trigger candle must be >= this x ATR(14)


def notional_for(stop_pct, capital=CAPITAL, risk_pct=RISK_PCT):
    """Notional the sizing formula produces at this stop distance."""
    return (capital * risk_pct - FLAT_COST) / (stop_pct + PCT_COST)


def band(capital=CAPITAL, risk_pct=RISK_PCT, min_position=MIN_POSITION):
    """(tight, wide) stop percentages, before integer-share rounding."""
    budget = capital * risk_pct - FLAT_COST
    if budget <= 0:
        return None
    tight = budget / capital - PCT_COST
    wide = budget / min_position - PCT_COST
    return (tight, wide) if tight < wide else None


def size(stop_pct, price, capital=CAPITAL, risk_pct=RISK_PCT):
    """Actual sized trade at a real price, with integer shares."""
    budget = capital * risk_pct - FLAT_COST
    stop_distance = stop_pct * price
    shares = int(budget / (stop_distance + PCT_COST * price))
    notional = shares * price
    cost = FLAT_COST + PCT_COST * notional
    risk = shares * stop_distance + cost
    return {
        "shares": shares,
        "notional": notional,
        "cost": cost,
        "risk": risk,
        "cost_ratio": cost / risk if risk else 0.0,
    }


def max_atr_pct(capital=CAPITAL, **kw):
    """
    Widest daily range that still admits a valid setup.

    The trigger candle must be at least ATR_MULTIPLE x ATR, and the stop is
    that candle's range. So the candle floor and the band ceiling collide at:

        ATR% = wide_end / ATR_MULTIPLE
    """
    b = band(capital=capital, **kw)
    return None if b is None else b[1] / ATR_MULTIPLE


if __name__ == "__main__":
    PRICE = 280.0

    print(f"account        Rs {CAPITAL:,.0f}")
    print(f"risk budget    Rs {CAPITAL * RISK_PCT:,.2f}   "
          f"(Rs {CAPITAL * RISK_PCT - FLAT_COST:,.2f} after the flat fee)")
    print(f"min position   Rs {MIN_POSITION:,.0f}")
    print(f"test price     Rs {PRICE:,.2f}")
    print()

    b = band()
    if not b:
        print("no valid band on this account")
        raise SystemExit

    print(f"{'stop %':>8}  {'notional':>10}  {'shares':>7}  "
          f"{'cost':>7}  {'risk':>7}  {'cost/risk':>9}  verdict")
    print("-" * 70)
    s = 0.0070
    while s <= 0.0190:
        r = size(s, PRICE)
        if r["notional"] > CAPITAL:
            verdict = "over capital"
        elif r["notional"] < MIN_POSITION:
            verdict = "under min size"
        else:
            verdict = "VALID"
            if r["cost_ratio"] > COST_TRIPWIRE:
                verdict += "  (tripwire)"
        print(f"{s:>7.2%}  Rs {r['notional']:>8,.0f}  {r['shares']:>7}  "
              f"Rs {r['cost']:>5.2f}  Rs {r['risk']:>5.2f}  "
              f"{r['cost_ratio']:>9.1%}  {verdict}")
        s += 0.0005

    print()
    print(f"band, before share rounding   {b[0]:.2%} - {b[1]:.2%}")

    lo = hi = None
    s = 0.0050
    while s <= 0.0300:
        r = size(s, PRICE)
        if MIN_POSITION <= r["notional"] <= CAPITAL:
            lo = s if lo is None else lo
            hi = s
        s += 0.0001
    print(f"band at Rs {PRICE:,.0f}, integer shares   {lo:.2%} - {hi:.2%}")
    print(f"widest ATR% that still admits a setup   {max_atr_pct():.2%}")
    print()

    print("scaling")
    print(f"{'capital':>10}  {'band':>18}  {'slots':>6}")
    for cap in (10_000.0, 12_000.0, 16_000.0, 25_000.0):
        bb = band(capital=cap)
        if bb is None:
            print(f"Rs {cap:>7,.0f}  {'no valid band':>18}")
            continue
        # slots must use the smallest notional the band actually produces,
        # not MIN_POSITION -- integer shares overshoot it.
        smallest = min(size(x / 10000, PRICE, capital=cap)["notional"]
                       for x in range(int(bb[0] * 10000) + 1,
                                      int(bb[1] * 10000) + 1)
                       if size(x / 10000, PRICE, capital=cap)["notional"] >= MIN_POSITION)
        slots = int(cap // smallest)
        print(f"Rs {cap:>7,.0f}  {bb[0]:>7.2%} - {bb[1]:<7.2%}  {slots:>6}"
              f"   (smallest position Rs {smallest:,.0f})")

    print()
    print("Excludes the bid-ask spread, which is real and unprinted.")