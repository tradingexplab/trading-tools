# Zerodha NSE delivery costs, resident individual, non-BSDA.
# Rates verified 2026-09-09 and re-checked 2026-11-10 via zerodha.com/charges and /charge-list. Statutory only: spread and slippage are NOT here.
# All three backtests take their charges from this file.

STT_BUY = 0.001        # stock delivery
STT_SELL = 0.001       # stock delivery
ETF_STT_SELL = 0.00001  # equity ETF delivery, sell side only
EXCH = 0.0000307       # NSE transaction charge, each side
SEBI = 0.000001        # SEBI turnover fee, each side
STAMP_BUY = 0.00015    # buy side only (ETF unit rate unconfirmed; immaterial at benchmark size)
GST = 0.18             # on exchange + SEBI (brokerage is zero for delivery)
DP_SELL = 15.34        # flat, per scrip per sell day


def buy_cost(value):
    """Tier A (stock delivery) buy leg."""
    return value * (STT_BUY + EXCH + SEBI + STAMP_BUY + GST * (EXCH + SEBI))


def sell_cost(value, dp=True):
    """Tier A (stock delivery) sell leg. dp=False for a second sale of the same scrip on the same day."""
    return value * (STT_SELL + EXCH + SEBI + GST * (EXCH + SEBI)) + (DP_SELL if dp else 0.0)


def etf_buy_cost(value):
    """Tier B (equity ETF delivery) buy leg, used only for the hold-Nifty comparison."""
    return value * (EXCH + SEBI + STAMP_BUY + GST * (EXCH + SEBI))


def etf_sell_cost(value, dp=True):
    return value * (ETF_STT_SELL + EXCH + SEBI + GST * (EXCH + SEBI)) + (DP_SELL if dp else 0.0)


if __name__ == "__main__":
    v = 100000.0
    rt = (buy_cost(v) + sell_cost(v, dp=False)) / v
    print(f"Tier A round-trip percentage component: {rt*100:.4f}%  (expect 0.2225%)")
    assert abs(rt - 0.002225) < 0.000002
