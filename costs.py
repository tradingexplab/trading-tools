"""
costs.py - what trading costs actually do to a small account.

Change the numbers in CONFIG to match your own account, then run:

    python costs.py

No dependencies. Python 3.8+.

RATES VERIFIED: 2026-09-09, against Zerodha's published charges page
and Zerodha support "Is STT levied on exchange traded funds (ETFs)?".

Statutory rates change with government policy. Re-verify before
risking real money, and after every Union Budget.

WHY THIS FILE EXISTS
--------------------
The cost number should live in exactly one place. A rate copied into
several documents becomes several copies to maintain, and they drift
without announcing it. Anything that needs a cost figure should call
this module rather than restate the number.

The specific trap: applying stock delivery STT (0.1% buy + 0.1% sell)
to an ETF overstates the percentage component by roughly ten times.
"""

from dataclasses import dataclass

RATES_VERIFIED_ON = "2026-09-09"

# ---------------------------------------------------------------
# CONFIG - change these
# ---------------------------------------------------------------

CAPITAL = 10_000.0        # total account size, rupees
RISK_PCT = 0.01           # fraction of capital risked per trade
PRICE = 268.15          # entry price of the instrument (NIFTYBEES, 2026-09-09)
STOP_DISTANCE = 2.87      # entry minus stop, in rupees
MIN_NOTIONAL = 5_000.0    # smallest position worth taking
MAX_COST_RATIO = 0.20     # costs may not exceed this share of risk

INSTRUMENT = "etf_equity"  # see INSTRUMENTS below


# ---------------------------------------------------------------
# COST MODEL - Zerodha delivery (CNC)
# ---------------------------------------------------------------
#
# Two parts, always. One scales with position size. One does not.
#
# The part that varies by instrument is STT, and it varies a lot:
#
#   stock        0.1% on buy AND 0.1% on sell
#   equity ETF   nothing on buy, 0.001% on sell
#   some ETFs    nothing at all - gold, silver, liquid, gilt,
#                and most international ETFs
#
# NSE publishes an "STT Non-applicability report" under
# nseindia.com/all-reports. Check each ticker in your universe
# against it rather than assuming a tier.

STT_BUY = {"stock": 0.001, "etf_equity": 0.0, "etf_no_stt": 0.0}
STT_SELL = {"stock": 0.001, "etf_equity": 0.00001, "etf_no_stt": 0.0}

TXN_PER_LEG = 0.0000307   # NSE transaction charge, each leg
STAMP_BUY = 0.00015       # 0.015%, buy only
SEBI_PER_LEG = 10 / 1e7   # Rs 10 per crore
GST = 0.18                # on transaction + SEBI charges
DP_CHARGE = 15.34         # FLAT, on sell only - this is the whole story

INSTRUMENTS = tuple(STT_SELL)


def percentage_component(instrument: str = INSTRUMENT) -> float:
    """The part of cost that scales with position size, per rupee."""
    if instrument not in INSTRUMENTS:
        raise ValueError(f"instrument must be one of {INSTRUMENTS}")
    txn = TXN_PER_LEG * 2
    sebi = SEBI_PER_LEG * 2
    return (
        STT_BUY[instrument] + STT_SELL[instrument]
        + txn + STAMP_BUY + sebi
        + (txn + sebi) * GST
    )


def round_trip_cost(notional: float, instrument: str = INSTRUMENT) -> float:
    """Total cost to buy and later sell a position of this size."""
    return notional * percentage_component(instrument) + DP_CHARGE


# ---------------------------------------------------------------
# POSITION SIZING
# ---------------------------------------------------------------

@dataclass
class Position:
    shares: int
    notional: float
    cost: float
    price_risk: float      # shares x stop distance
    actual_risk: float     # price risk + costs
    cost_ratio: float      # costs as a share of actual risk


def size_position(price, stop_distance, risk_budget,
                  instrument: str = INSTRUMENT) -> Position:
    """
    Shares = (Risk - flat_fee) / (stop_distance + pct_cost_per_share)

    Both cost components live inside the formula. The flat fee comes
    out of the budget; the percentage cost is added to what each
    share effectively risks. Leave either out and the result
    overshoots your risk budget.
    """
    pct = percentage_component(instrument)
    shares = max(int((risk_budget - DP_CHARGE) / (stop_distance + pct * price)), 0)

    notional = shares * price
    cost = round_trip_cost(notional, instrument) if shares else 0.0
    price_risk = shares * stop_distance
    actual_risk = price_risk + cost
    ratio = cost / actual_risk if actual_risk else 0.0

    return Position(shares, notional, cost, price_risk, actual_risk, ratio)


# ---------------------------------------------------------------
# THE NUMBER THAT MATTERS
# ---------------------------------------------------------------

def breakeven_win_rate(r_multiple: float, pos: Position, stop_distance: float):
    """
    Break-even win rate AFTER costs.

    The naive answer is 1 / (1 + R). That answer is wrong, because
    costs are subtracted from every win AND added to every loss.
    The same rupee hits you twice.
    """
    gross_win = pos.shares * stop_distance * r_multiple
    net_win = gross_win - pos.cost
    net_loss = pos.price_risk + pos.cost

    naive = 1 / (1 + r_multiple)
    real = net_loss / (net_win + net_loss) if (net_win + net_loss) else 1.0

    return naive, real, net_win, net_loss


# ---------------------------------------------------------------
# STOP BAND - which setups are even worth taking
# ---------------------------------------------------------------

def stop_band(price, capital, risk_budget, min_notional, max_cost_ratio,
              instrument: str = INSTRUMENT):
    """
    Scan stop distances and find the window where a setup passes
    every check. Also reports WHICH check bounds each end — the
    binding constraint is often not the one the rule was written for.

    Returns (lo, hi, why_lo, why_hi) as fractions of price.
    """
    valid = []
    steps = int(price * 0.08 * 100)  # scan up to 8% of price, paisa steps

    for i in range(1, steps):
        sd = i / 100
        pos = size_position(price, sd, risk_budget, instrument)
        fails = []
        if pos.shares == 0:
            fails.append("no shares")
        else:
            if pos.notional > capital:
                fails.append("over capital")
            if pos.notional < min_notional:
                fails.append("under min size")
            if pos.cost_ratio > max_cost_ratio:
                fails.append("cost ceiling")
        if not fails:
            valid.append(sd)

    if not valid:
        return None, None, None, None

    lo, hi = min(valid), max(valid)

    def why(sd, direction):
        probe = size_position(price, sd + direction * 0.01, risk_budget, instrument)
        if probe.shares == 0:
            return "no shares"
        if probe.notional > capital:
            return "capital cap"
        if probe.notional < min_notional:
            return "minimum position size"
        if probe.cost_ratio > max_cost_ratio:
            return "cost ceiling"
        return "scan edge"

    return lo / price, hi / price, why(lo, -1), why(hi, +1)


# ---------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------

def main():
    risk_budget = CAPITAL * RISK_PCT
    pct = percentage_component()

    print()
    print("=" * 62)
    print(f"  COST MODEL   instrument: {INSTRUMENT}   rates as of {RATES_VERIFIED_ON}")
    print("=" * 62)
    print(f"  Round trip = {pct * 100:.4f}% of notional  +  Rs {DP_CHARGE:.2f} flat")
    print()
    print("  Percentage component by instrument, same rates:")
    for name in INSTRUMENTS:
        print(f"    {name:<12} {percentage_component(name) * 100:>8.4f}%")
    print()
    print("  Using stock rates on an ETF overstates the percentage")
    print("  part by roughly ten times.")
    print()
    print("  What each part costs at different position sizes:")
    print(f"    {'Notional':>10}{'Flat':>10}{'Pct part':>11}{'Flat share':>13}")
    for n in (2_000, 5_000, 9_000, 25_000, 100_000):
        flat_share = DP_CHARGE / (DP_CHARGE + n * pct) * 100
        print(f"    {n:>10,}{DP_CHARGE:>10.2f}{n * pct:>11.2f}{flat_share:>12.0f}%")
    print()
    print("  The flat fee is most of the cost until the account is large.")

    pos = size_position(PRICE, STOP_DISTANCE, risk_budget)

    print()
    print("=" * 62)
    print("  YOUR POSITION")
    print("=" * 62)
    print(f"  Capital          Rs {CAPITAL:,.0f}")
    print(f"  Risk budget      Rs {risk_budget:,.2f}  ({RISK_PCT * 100:.0f}%)")
    print(f"  Price            Rs {PRICE:,.2f}")
    print(f"  Stop distance    Rs {STOP_DISTANCE:,.2f}  ({STOP_DISTANCE / PRICE * 100:.2f}% of price)")
    print()
    print(f"  Shares           {pos.shares}")
    print(f"  Notional         Rs {pos.notional:,.2f}")
    print(f"  Round-trip cost  Rs {pos.cost:,.2f}")
    print(f"  Price risk (1R)  Rs {pos.price_risk:,.2f}")
    print(f"  Actual risk      Rs {pos.actual_risk:,.2f}")
    print(f"  Cost / risk      {pos.cost_ratio * 100:.1f}%", end="")
    print("   <-- over ceiling" if pos.cost_ratio > MAX_COST_RATIO else "   OK")

    print()
    print("=" * 62)
    print("  BREAK-EVEN WIN RATE")
    print("=" * 62)
    print(f"  {'Target':<8}{'Net win':>11}{'Net loss':>11}{'Naive':>9}{'Real':>9}{'Gap':>8}")
    print("  " + "-" * 54)
    for r in (1.5, 2.0, 2.5, 3.0, 4.0):
        naive, real, nw, nl = breakeven_win_rate(r, pos, STOP_DISTANCE)
        print(f"  {r:<8.1f}{nw:>11,.0f}{nl:>11,.0f}"
              f"{naive * 100:>8.0f}%{real * 100:>8.0f}%{(real - naive) * 100:>7.0f}pp")
    print()
    print("  'Naive' ignores costs. 'Real' is the bar you must clear.")
    print("  Test your strategy against the Real column.")

    lo, hi, why_lo, why_hi = stop_band(
        PRICE, CAPITAL, risk_budget, MIN_NOTIONAL, MAX_COST_RATIO)

    print()
    print("=" * 62)
    print("  WHICH SETUPS ARE WORTH TAKING")
    print("=" * 62)
    if lo is None:
        print("  No stop distance passes every check at this account size.")
        print("  Either the cost ceiling or the minimum size has to move.")
    else:
        print(f"  Stop must be between {lo * 100:.2f}% and {hi * 100:.2f}% of entry price.")
        print(f"  At Rs {PRICE:,.0f} that is Rs {lo * PRICE:.2f} to Rs {hi * PRICE:.2f}.")
        print(f"  Window width: {(hi - lo) * 100:.2f} percentage points.")
        print()
        print(f"  Tight end bounded by: {why_lo}")
        print(f"  Wide end bounded by:  {why_hi}")
        print()
        print("  Read those two lines. The binding constraint is not")
        print("  always the one you assumed when you wrote the rule.")
        print()
        print("  Outside this band, skip the setup. One comparison, no maths.")
    print()


if __name__ == "__main__":
    main()