# ETF Momentum vs Nifty + Gold

A 10-year backtest (Oct 2016 – Sep 2026) on Indian ETFs, comparing a monthly momentum rotation with a simple Nifty + Gold split reset once a year.

## Results (₹10 lakh start, before tax)

| Strategy | CAGR | Worst fall | Trades |
| --- | --- | --- | --- |
| Momentum, top 2 | 15.9% | -37.7% | 70 |
| Momentum, top 6 (volatility-adjusted) | 15.6% | -36.7% | 132 |
| Nifty + Gold 50/50, reset yearly | 14.8% | -20.6% | 20 |
| Nifty + Gold 70/30, reset yearly | 13.7% | -25.6% | 20 |
| Gold BeES, buy and hold | 16.0% | -24.4% | 1 |
| Nifty BeES, buy and hold | 11.5% | -36.3% | 1 |

## Rules

The momentum rules tested here are a version of a popular ETF rotation approach shared in the Indian investing community, not my own invention.

**Momentum**
- Universe: 23 Indian ETFs (sectors, factors, broad market, gold, silver). International ETFs excluded.
- An ETF becomes eligible after 12 months of its own price history. No index data is used to fill gaps.
- Score = average of the 1, 3, 6 and 12-month returns.
- Top 2: hold the top 2 equally. Sell a holding only when it falls below rank 5.
- Top 6: rank by score ÷ volatility (standard deviation of daily returns, last 6 months). Hold the top 6. Sell below rank 8.
- Ties go to the lower-volatility ETF.
- A sold holding is replaced by the best-ranked ETF not already held, using only that sale's money.

**Nifty + Gold**
- Half in NIFTYBEES, half in GOLDBEES (or 70/30). Reset to target weights once a year, after the last trading day of September.

**Both**
- Decisions use the last trading day's close. Trades fill at the next day's close (or the next close the ETF actually traded).
- Zerodha delivery charges included: exchange, SEBI, GST, stamp duty, STT on equity ETF sells, and ₹15.34 DP charge per sell.
- Bid-ask spread not included. Idle cash earns nothing. All results are before tax.

## Data

Daily closes from [EOD2](https://github.com/BennyThadikaran/eod2). The data is not included here.

EOD2 does not adjust ETF unit splits. `splits.csv` lists every split in the universe, each checked against NSE corporate-action filings, and the script adjusts earlier prices by the stated ratio.

## Run it

Requires Python 3 with pandas and numpy. In PowerShell:

```powershell
pip install pandas numpy
python backtest.py "C:\path\to\eod2\src\eod2_data\daily"
```

Run it from this folder so the script can find `splits.csv`.

## Limits

- One 10-year window. A different decade could change the order.
- Gold had an unusually strong decade, which helps every gold-heavy result.
- The momentum score's details (how the four lookbacks combine, the volatility window) are choices. Scoring by average rank instead of average return moves top 2 to about 20.5% a year, so treat any single number with caution.
- Before tax. Monthly rotation creates mostly short-term gains.

A backtest shows what rules would have done on past data. It cannot tell you what they will do next. This is not investment advice.
