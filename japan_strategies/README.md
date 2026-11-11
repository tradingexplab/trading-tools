# Three Japanese chart methods on the Nifty 50, against holding

Candlestick patterns, Heikin-Ashi and Ichimoku, each written as exact rules and run on the Nifty 50 price index from 2004 to 23 Oct 2026, with Zerodha ETF charges, against buying once and holding.

## Rules

Everything is on daily bars. A signal on a day's close is traded at the next session's open. Long only, one position at a time.

**Candlestick patterns (five, pooled into one rule; a signal is any of the five)**

A "big" body is at least 0.25% of the close. "Downtrend before" means the close of the bar just before the pattern's first candle is below its 20-day simple average.

- Bullish engulfing: yesterday red, today green, today's open at or below yesterday's close, today's close at or above yesterday's open, both bodies big, downtrend before yesterday.
- Hammer: lower shadow at least 2x the body, upper shadow no more than the body, the body in the top third of the day's range, body big, downtrend before today.
- Morning star: day 1 red with a body of at least 0.5% of its close, day 2 body no more than 30% of day 1's body, day 3 green, big, closing above the midpoint of day 1's body, downtrend before day 1.
- Piercing line: day 1 red, day 2 green opening at or below day 1's close and closing above the midpoint of day 1's body but below day 1's open, both bodies big, downtrend before day 1.
- Three white soldiers: three green, big-bodied days, each closing in the top third of its range and above the previous close, each opening inside the previous day's body. No downtrend condition.
- Exit: sell at the open of the 6th session of the trade (the entry session is 1).

**Heikin-Ashi, N green candles (N = 2, 3, 4)**

HA close = (open + high + low + close) / 4. HA open = average of the previous HA open and HA close, starting from the first bar of 2003 (first HA open = (open + close) / 2). A candle is green if its HA close is above its HA open, red if below.

- Buy after N green HA candles in a row. Sell after a red one.

**Ichimoku, 9 / 26 / 52**

Tenkan = midpoint of the 9-day high and low. Kijun = the same over 26 days. Span A = (Tenkan + Kijun) / 2, drawn 26 bars ahead. Span B = the 52-day midpoint, drawn 26 bars ahead. The cloud at a bar is the one drawn there, so no future values are used.

- Buy when Tenkan crosses above Kijun (above today, at or below yesterday) and the close is above the top of the cloud.
- Sell when the close falls below the bottom of the cloud.

## Setup

- **Prices:** the Nifty 50 price index divided by 100, standing in for NIFTYBEES. Dividends are not included.
- **Money:** Rs 10,00,000 at the start of each period, whole units, all available cash in each trade, idle cash earns nothing.
- **Charges:** `costs.round_trip_cost()` at Zerodha equity-ETF statutory rates, charged in full when a trade is opened. The bid-ask spread is not included. The same 2026 rates are used for every year.
- **Periods:** earlier years 1 Jan 2004 to 31 Dec 2020, later years 1 Jan 2021 to 23 Oct 2026. Signals use the full history, and each period starts with no position.
- A position still open on a period's last day is sold at that close.

## Results

Earlier years (2004-2020)

| | Final value | Total | Per year | Worst fall | Trades | Up / down | Charges | Invested |
|---|---|---|---|---|---|---|---|---|
| **Hold** | Rs 74,33,822 | +643.4% | 12.5% | -59.9% | 1 | | Rs 250 | 100% |
| Candlestick patterns | Rs 4,15,373 | -58.5% | -5.0% | -67.8% | 103 | 50 / 53 | Rs 18,090 | 12% |
| Heikin-Ashi, 2 green | Rs 29,18,984 | +191.9% | 6.5% | -20.7% | 401 | 179 / 222 | Rs 1,83,713 | 47% |
| Heikin-Ashi, 3 green | Rs 14,71,417 | +47.1% | 2.3% | -32.7% | 337 | 137 / 200 | Rs 1,05,883 | 37% |
| Heikin-Ashi, 4 green | Rs 11,08,891 | +10.9% | 0.6% | -33.2% | 276 | 116 / 160 | Rs 74,533 | 29% |
| Ichimoku 9/26/52 | Rs 29,00,869 | +190.1% | 6.5% | -34.8% | 21 | 12 / 9 | Rs 10,428 | 37% |

Later years (2021 to 23 Oct 2026)

| | Final value | Total | Per year | Worst fall | Trades | Up / down | Charges | Invested |
|---|---|---|---|---|---|---|---|---|
| **Hold** | Rs 16,14,326 | +61.4% | 8.6% | -17.2% | 1 | | Rs 250 | 100% |
| Candlestick patterns | Rs 9,80,306 | -2.0% | -0.3% | -14.6% | 30 | 13 / 17 | Rs 7,799 | 10% |
| Heikin-Ashi, 2 green | Rs 11,96,263 | +19.6% | 3.1% | -10.8% | 142 | 65 / 77 | Rs 40,524 | 43% |
| Heikin-Ashi, 3 green | Rs 13,42,664 | +34.3% | 5.3% | -9.1% | 108 | 53 / 55 | Rs 33,127 | 33% |
| Heikin-Ashi, 4 green | Rs 13,00,201 | +30.0% | 4.7% | -7.5% | 83 | 44 / 39 | Rs 25,833 | 26% |
| Ichimoku 9/26/52 | Rs 9,59,438 | -4.1% | -0.7% | -14.0% | 11 | 4 / 7 | Rs 2,704 | 41% |

"Up / down" counts trades by profit after charges. "Invested" is the share of sessions with a position open at the close. Full output is in `results/summary.txt` after you run the script, with every trade in `results/trades_*.csv`.

## What this does and does not show

- **Holding won on total return in every row, in both periods.** Heikin-Ashi and Ichimoku had smaller falls, but they were in cash for roughly half of the sessions, so a smaller fall is partly just less time invested.
- **Candlestick patterns lost money in both periods.** In the earlier years most of the loss comes from trades entered in 2008 and 2020: leaving those out turns -58.5% into -7.2%. That describes this rule on this data, not why it happened.
- **The candlestick result depends on the exit day.** Selling at the open of the 5th session instead of the 6th gives -18.3% (earlier years) and -4.9% (later years). The 7th session gives -41.1% and +2.4%. Change `CANDLE_HOLD` at the top of `japan_test.py` to see it.
- **The Heikin-Ashi variant was chosen on the earlier years.** Among the three, 2 green returned the most there. The 3 and 4 green variants did better in the later years (+34.3% and +30.0% against +19.6%), and all three trailed holding. The later years were run for every variant, so they are a check on the rule, not an untouched sample.
- **Ichimoku has few trades** (21 and 11), so one trade can change the picture. The later-years result also depends on when the indicator starts: with 2020 history it is -4.1% (11 trades), and with the indicator started fresh on 1 Jan 2021 it is +0.3% (10 trades).
- **Heikin-Ashi depends on history before 2004.** It is calculated from the first bar of 2003. Starting the calculation on 1 Jan 2004 changes the earlier-years result to Rs 28,67,708.
- **The numbers in the rules are choices:** 0.25% body, 20-day average, 30% star body, 2/3 of the range, the 6-session exit, 9/26/52. Other numbers would give other results.
- **Data:** the index is price only (no dividends). The EOD2 file has no row for 20 Jun 2016, a real trading day. Some weekend special sessions count as sessions in the 6-session exit.

Past data only. A backtest shows what rules would have done, not what they will do. Nothing here is investment advice.

## Data

- **2003 to 20 Feb 2012:** yearly CSVs from niftyindices.com (Historical Data, Nifty 50, Price Return). Download the files for 2003 to 2012 and save them in `data/` under their original names (`NIFTY_50_Historical_PR_*.csv`).
- **21 Feb 2012 onward:** EOD2 daily data (github.com/BennyThadikaran/eod2_data), commit `04c645452ff4a214e3666fc265fdc3a56a5831c4`, prices to 23 Oct 2026. `fetch_data.py` downloads it.

On the 955 dates where the niftyindices files (late 2012, 2016, 2019, 2020) overlap the EOD2 file, the prices are identical.

## Run

```powershell
cd trading-tools\japan_strategies
pip install pandas numpy
python fetch_data.py
python japan_test.py
```

Writes `results/summary.txt` and `results/trades_*.csv`.
