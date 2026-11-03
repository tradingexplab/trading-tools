# Diwali Muhurat test: run it yourself

Question: does buying Nifty 50 on the Diwali Muhurat trading day beat buying on an ordinary day?

This is a test of a rule on past data. It is not a recommendation and not investment advice.

The price data is not in this repo. You download it from NSE (niftyindices.com) and from a public GitHub data repo, then build one file and run the test. Only Python 3 is needed. No packages to install.

## Step 1: Download the data

Make a folder named `data` next to these scripts, and put these files in it.

**A. From NSE (niftyindices.com), the Nifty 50 price index, one file per year.**

1. Open the Historical Data page on niftyindices.com (Reports, then Historical Data).
2. Choose index "NIFTY 50", type "Price Return", and set the dates from 1 Jan to 31 Dec of one year.
3. Download the CSV. Repeat for each of these years: 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2016, 2019, 2020.
4. Keep the file names as downloaded, for example `NIFTY_50_Historical_PR_01012004to31122004.csv`.

**B. For the other years (2013 to 2015, 2017, 2018, 2021 to now), one file from GitHub.**

Download this file and save it in `data` as `nifty 50.csv`:

https://raw.githubusercontent.com/BennyThadikaran/eod2_data/main/daily/nifty%2050.csv

Note: the numbers in the video came from exactly this mix of sources. If you instead download every year from niftyindices, small differences in a few days are possible, so your numbers may not match to the last decimal.

## Step 2: Build one price file

```
python build_series.py data
```

This writes `data/nifty_combined.csv` (columns: date, close). It prints a warning if a year is missing.

## Step 3: Run the test

```
python muhurat_test.py data/nifty_combined.csv results
```

It writes `results/summary.txt` and `results/muhurat_by_year.csv` and prints the summary. With the data above you should see 19 of 22 Muhurat entries positive after 365 days, a median of 9.32%, and the verdict "NO EVIDENCE OF LUCK".

## The rules (fixed before running)

1. Buy at the close on the Muhurat day. Sell at the close 365 calendar days later (next trading day if that day is closed).
2. Ordinary days are every Monday to Friday trading day, except Muhurat days.
3. Each Muhurat day is compared with ordinary days within 30 days either side.
4. Draw one ordinary day from each year's window (22 picks), repeat 10,000 times, take the median return of each draw. Muhurat counts as special only if its median is above the 95th percentile of those medians.
5. Price only. No dividends, brokerage or tax.
6. Only 22 Muhurat days exist, and the windows overlap. "No evidence" is not the same as "no effect".

## Change the rules

At the top of `muhurat_test.py` you can change `HOLD_DAYS`, `WINDOW_DAYS`, `DRAWS`, `PERCENTILE` and `SEED`, then run it again.

## Disclaimer

This is a test of a strategy, not a recommendation. A backtest shows what rules would have done on past data. It cannot tell you what they will do next. I'm not a registered advisor and nothing here is investment advice.
