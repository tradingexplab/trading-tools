# 5 popular strategies vs doing nothing

Ten years of Indian market data, one shared setup, and one opponent: buying NIFTYBEES once and never touching it.

## Results (₹10 lakh start, after Zerodha charges, Oct 2016 – Sep 2026)

| Strategy | Final value | Per year | Worst fall | Trades |
|---|---|---|---|---|
| Momentum rotation, top 2 ([`etf_momentum/`](../etf_momentum/)) | — | 15.9% | −37.7% | 70 |
| **Hold NIFTYBEES (doing nothing)** | **₹29.6 lakh** | **11.5%** | **−36.3%** | **1** |
| ETF ki Dukan | ₹23.0 lakh | 8.7% | −35.2% | 683 sales |
| Supertrend 10, 3 | ₹21.9 lakh | 8.2% | −13.5% | 39 |
| Golden cross, EMA 50/200 | ₹19.5 lakh | 6.9% | −27.8% | 8 |
| 44 moving average pullback, 1:2 | ₹10.6 lakh | 0.6% | −2.2% | 7 |

Four of the five lost to doing nothing. Momentum beat it, with a deeper worst fall, and from an ETF list chosen with hindsight.

With ₹10,000 instead of ₹10 lakh, ETF ki Dukan falls to 1.8% a year: the flat ₹15.34 charge on every sale eats most of its small profits. The other results barely move.

## The shared setup

- **Window:** 3 Oct 2016 to 25 Sep 2026.
- **Signals** come from the Nifty 50 index ÷ 100. NIFTYBEES' own opening, high and low prices contain stray pre-open auction prints; the index does not.
- **Every trade** uses the real NIFTYBEES closing price on the next trading day after the signal. The 1:10 unit split of 19 Dec 2019 is adjusted.
- **Money:** whole units, all available cash per trade, idle cash earns nothing.
- **Charges:** Zerodha delivery, statutory only (exchange, SEBI, GST, stamp duty, STT, and ₹15.34 DP charge per sale). The bid-ask spread is not included.
- Positions still open on the last day are sold at that day's close, charges included.

## The strategies

| Strategy | Rule as tested |
|---|---|
| 44 moving average | Buy the bounce when price dips to a rising 44-day average; stop below the signal candle, target at 2× the risk. Full rules in [`sma44/`](../sma44/). |
| Golden cross | Hold while the 50-day exponential average is above the 200-day one; cash otherwise. |
| Supertrend | Settings 10 and 3. Hold while it is green; sell to cash when it turns red. Long only. |
| ETF ki Dukan | Version 1 on its own 83-ETF list, code unchanged from [`etf_dukan/`](../etf_dukan/). |
| Momentum rotation | Monthly ranking, hold the top 2, sell below rank 5. Code and rules in [`etf_momentum/`](../etf_momentum/). |

## Limits

- **One 10-year window.** A different decade could change the order.
- **Hindsight in two ETF lists.** ETF ki Dukan's list is dated April 2023; only 32 of its 83 ETFs existed in Oct 2016. The momentum universe was also picked knowing which ETFs exist today.
- **Before tax.** Strategies that trade often create short-term gains, taxed at higher rates.
- **One instrument for four strategies.** Most of these rules were made for stocks; here they run on the simplest thing an Indian investor can buy.
- **Index data:** the video used daily Nifty 50 files from niftyindices.com. This code downloads the same index from EOD2 so it runs without manual steps. EOD2 lacks seven special trading sessions, which moves the golden cross result from 6.91% to 6.94% a year. Every other number is identical.

## Run it

Needs Python 3 with pandas and numpy. Run from this folder, in PowerShell:

```powershell
git clone https://github.com/tradingexplab/trading-tools.git
cd trading-tools\five_vs_hold
pip install pandas numpy
python fetch_data.py
python backtest.py
```

`fetch_data.py` downloads prices from a pinned EOD2 commit, so every run sees the same data. `backtest.py` prints results at ₹10 lakh and ₹10,000 and writes every trade to `results/`.

This is a test of a strategy, not a recommendation. A backtest shows what rules would have done on past data. It cannot tell you what they will do next. Nothing here is investment advice.
