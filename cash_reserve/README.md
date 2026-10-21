# Keep 20% cash for the crash? (cash_reserve)

Three ways to hold ₹10 lakh of Nifty 50 from 23 June 2016 to 19 October 2026:

- **All in:** 100% Nifty 50, never touched.
- **20% cash:** 80% Nifty, 20% in a liquid fund waiting for a crash.
- **50% cash:** 50% Nifty, 50% in a liquid fund.

Video: https://youtu.be/ikbQF5kG-D4

## Results

| | All in | 20% cash | 50% cash |
|---|---|---|---|
| Value if held (19 Oct 2026) | ₹31.51L | ₹30.99L | ₹29.37L |
| Value after selling everything and paying tax | ₹30.24L | ₹30.49L | ₹29.37L |
| Yearly return after selling | 11.32% | 11.41% | 11.00% |
| Worst fall (Jan → Mar 2020) | −38.3% | −36.0% | −32.6% |
| Times the cash went in / was refilled | – | 8 / 7 | 8 / 7 |

- Every one of the 8 times the cash went in, Nifty fell further afterwards (see `results/after_cash_went_in.csv`). In 6 of the 8 the extra fall was under 7%; March 2020 was −27.2%.
- With the yearly tax-free gain booking turned off (`--no-harvest`), the all-in investor ends with ₹28.99L after selling, ₹1.25 lakh less.

## The rules

- **Equity:** Nifty 50 total return index (price plus reinvested dividends), rebuilt from the daily price and dividend yield.
- **Cash:** NIFTY 1D Rate Index, minus a 0.20% a year expense ratio.
- **Cash goes in:** when the Nifty 50 price index closes 10% or more below its highest close so far, all cash goes into Nifty at the next trading day's close.
- **Cash refilled:** when Nifty closes at a new high after that, enough Nifty is sold at the next day's close to bring cash back to 20% (or 50%), after costs and tax.
- **No other rebalancing.**
- **Costs:** Zerodha statutory charges for ETF delivery, including ₹15.34 per sell. Bid-ask spread not included.
- **Tax (today's rules, applied to all 10 years):** equity held 12 months or less 20%; longer 12.5% on gains above ₹1.25 lakh per financial year; liquid fund gains 20%.
- **Yearly gain booking, same for all three:** on the last trading day of each financial year, long-term gains up to that year's unused ₹1.25 lakh are booked and the units bought back the same day.

## Run it yourself

You need Python 3 with pandas and numpy (`pip install pandas numpy`).

1. **Price and dividend-yield files.** On niftyindices.com → Reports → Historical Data, download NIFTY 50 for 23 Jun 2016 to today, one year per file:
   - the price index files → put them in `data/price/`
   - the P/E, P/B & Div Yield files → put them in `data/yield/`
2. **EOD2 files** (Nifty 50 history for the starting high, and the 1D Rate Index):
   ```
   python fetch_eod2.py
   ```
3. **Build the total return index:**
   ```
   python build_tri.py
   ```
4. **Run the backtest:**
   ```
   python backtest.py
   python backtest.py --no-harvest --out results_noharvest
   ```

Results go to `results/`: `summary.csv`, `daily_values.csv`, the trade lists `events_cash_20.csv` and `events_cash_50.csv`, and `after_cash_went_in.csv`.

Change any rule at the top of `backtest.py` (trigger, expense ratio, costs, tax rates) and run it again.

## Limits

- Today's tax rules are applied to the whole period. Before 2018 these gains weren't taxed, and the tax-free limit was lower before 2024.
- One 10-year stretch. A different start date could change a result this close.
- The test starts with Nifty already 8.1% below its 2015 high, so the cash went in on the second day.
- The total return index is rebuilt from the published daily dividend yield, not the official index. The rebuilt index grows 1.40% a year faster than the price index; the average yield was 1.26%.
- 8 trading days have no published yield; the previous day's value is used.

⚠️ This is a test of a strategy, not a recommendation. A backtest shows what rules would have done on past data. It cannot tell you what they will do next. I'm not a registered advisor and nothing here is investment advice.
