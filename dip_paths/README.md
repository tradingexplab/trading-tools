# Buy the dip, spread it out, or wait? Every 10% Nifty fall since 2002

Three ways to invest ₹1,00,000 after Nifty 50 falls 10%, tested on every such fall in NIFTYBEES since 2002, with Zerodha charges included.

| Path | What it does |
|---|---|
| **Buy now** | Buys NIFTYBEES the day after the fall. |
| **Spread 6 months** | Parks the money in a liquid fund and moves 1/6 into NIFTYBEES every 21 trading days. |
| **Wait for 50 DMA** | Parks the money in a liquid fund and buys NIFTYBEES the day after the close crosses back above its 50-day average. |

## Results (16 falls, 2002–2024)

| | Buy now | Spread 6 months | Wait for 50 DMA |
|---|---|---|---|
| Best of the three | 8 | 7 | 1 |
| Median 12-month return | 8.9% | 11.4% | 5.5% |
| Average 12-month return | 17.3% | 13.7% | 15.1% |
| Losing years | 3 | 5 | 6 |
| Average worst dip below ₹1,00,000 | 13.8% | 10.9% | 12.1% |
| Worst dip below ₹1,00,000 | 48.3% | 47.3% | 49.0% |

- Buy now vs Spread 6 months, head to head: **8–8**.
- Wait for 50 DMA vs Buy now: **lost 13, won 2, tied 1**.

Per-fall numbers are in `results.csv`. In it, `A` = Buy now, `B` = Spread 6 months, `C` = Wait for 50 DMA. `_ret` is the 12-month return and `_dd` is the worst dip below ₹1,00,000, both as fractions (0.089 = 8.9%). `next_12m_low` is NIFTYBEES' lowest close in the year after the fall, relative to the fall day. `C_entry` is the day Wait for 50 DMA bought.

## Rules

- **Data:** NIFTYBEES daily closes from EOD2. Prices before 19 Dec 2019 are divided by 10 to adjust for the 1:10 unit split on that date.
- **A fall:** the close is 10% or more below its highest close so far.
- **One fall, one event:** a new fall only counts after a new closing high.
- **Fills:** every trade fills at the next day's close. Opens aren't used, because NIFTYBEES opens in this data carry stray pre-open auction prints.
- **Cash:** money waiting in the liquid fund earns a fixed 6% a year. LIQUIDBEES' own price stays near ₹1,000 because it pays its return as extra units, so its price alone would show 0%.
- **Window:** every path is measured for 252 trading days from the day of the fall, then everything is sold at that day's close.
- **Worst dip:** the lowest value of the whole ₹1,00,000, cash included, during the window.
- **Units:** fractional units are allowed.

## Costs (Zerodha, NSE delivery)

| Charge | Rate |
|---|---|
| STT, NIFTYBEES | 0.001%, sell side only |
| STT, liquid fund | none |
| Exchange transaction charge | 0.00307% each side |
| SEBI fee | 0.0001% each side |
| GST | 18% on exchange and SEBI charges |
| Stamp duty | 0.015%, buy side |
| DP charge | ₹15.34 per scrip per sell day |

Check these against [zerodha.com/charges](https://zerodha.com/charges) and Zerodha's [ETF STT article](https://support.zerodha.com/category/account-opening/charges-at-zerodha/articles/stt-etfs) before relying on them. Rates change.

## Limits

- **16 falls is a small sample.** A few big years move the averages a lot.
- **Dividends are left out.** NIFTYBEES dividends would add a little to every path, and more to the paths that held longer.
- **The current fall isn't included.** It started in March 2026 and doesn't have a full year of results yet.
- **The data starts in January 2002.** The first "highest close so far" is a high within this data, not an all-time high.

## Run it yourself

You need Python 3 and pandas. In PowerShell:

```powershell
pip install pandas
Invoke-WebRequest https://raw.githubusercontent.com/BennyThadikaran/eod2_data/main/daily/niftybees.csv -OutFile niftybees.csv
python backtest.py niftybees.csv
```

This downloads only the NIFTYBEES file. The full EOD2 data repo holds thousands of files, so cloning it isn't needed.

This prints a table for each fall and the summary above, and writes `results.csv`. To test a different rule, change the constants at the top of `backtest.py`: `DROP` (fall size), `WINDOW` (days held), `N_INST` and `STEP` (instalments), or `CASH_RATE` (liquid fund return).

---

⚠️ This is a test of a strategy, not a recommendation. A backtest shows what rules would have done on past data. It cannot tell you what they will do next. I'm not a registered advisor and nothing here is investment advice.