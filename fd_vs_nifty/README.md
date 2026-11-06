# FD vs Nifty after tax and inflation

The same ₹1,00,000 goes into a bank FD and into the Nifty 50. Tax is taken out of both, then inflation.

- Headline run: 1 Apr 2009 to 1 Apr 2026 (17 years)
- Also eight 10-year windows, starting each April from 2009 to 2016

## Run it

Nifty index closes are not included in this repo. Download them yourself, then build one file:

1. Download the yearly "Historical Index Data" CSVs for Nifty 50 from niftyindices.com (one file per year, 2009 to 2012 is enough for this test) into `data\niftyindices`. Keep the file names as downloaded (`NIFTY_50_Historical_PR_...csv`).
2. Clone eod2 (github.com/BennyThadikaran/eod2). Its Nifty 50 index file is `eod2_data\daily\nifty 50.csv` (it starts in Feb 2012 and has `Date` and `Close` columns). Copy it to `data\nifty_eod.csv`.
3. Build the combined file and run the test (PowerShell):

```powershell
python build_nifty.py data\niftyindices data\nifty_eod.csv data\nifty_close.csv
python fd_vs_nifty.py data\nifty_close.csv
```

The build step prints how many days overlap and any mismatches. Where both sources have a day, the niftyindices value is used.

Results are printed and also saved in `results\`.

## Rules

FD
- RBI table: 5 major banks, 3-5 year deposits (`rbi_fd_rates.csv`).
- Lower end of the range, March snapshot each year.
- The money is renewed at the new rate every year.

Tax
- 30% slab + 4% cess on the FD interest, paid every year.
- Today's tax rules are applied to every year. Cess is 4% throughout.

Nifty
- Nifty 50 price index. No dividends.
- 12.5% tax on gain above ₹1,25,000, once at sale.
- No cess, brokerage or fund costs.
- Tax relief on gains made before 31 Jan 2018 is not applied, so Nifty's tax is overstated.

Inflation
- RBI CPI, financial-year averages, so the numbers are approximate.
- 2009-10 to 2011-12: CPI for industrial workers. After that: CPI combined.
- 2025-26 is a mix of two CPI series.

## Limits

- The FD number is a model, not a real deposit's statement.
- The 17-year result is one run, and the 10-year windows overlap. This is not solid proof.

## Data

- RBI Handbook of Statistics on the Indian Economy 2025-26 (Tables 59 and 236)
- Nifty 50 index closes from niftyindices.com and eod2

Past data. Not investment advice.