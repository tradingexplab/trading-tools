# Nifty crash recovery times, since 2004

How long did each Nifty 50 fall of 13% or more, since 2004, take to get back to its old high?

## Definitions

All on daily closes of the Nifty 50 price index (dividends not included, so real investors got back to even a little sooner).

- **Old high:** the highest close so far, tracked from the first row of data (Jan 2003).
- **Fall:** a close at least 13% below the old high.
- **Clock:** starts on the first close 13% below the old high. The wait from the old high itself is reported too.
- **Recovered:** the first close at or above the old high.
- **Counted:** falls whose first −13% close is on or after 1 Jan 2004.

Nifty's Feb 2000 high (about 1,756) was passed in Dec 2003, so every old high behind a counted fall is a true all-time high.

The script repeats the count at 10%, 15% and 20% to check the result doesn't depend on the 13% line.

## Results (13% line)

| Old high | First −13% close | Bottom | Back at old high | Days from the line |
|---|---|---|---|---|
| 14 Jan 2004 | 18 Mar 2004 | −29.9% | 2 Dec 2004 | 259 |
| 4 Oct 2005 | 28 Oct 2005 | −13.0% | 25 Nov 2005 | 28 |
| 10 May 2006 | 19 May 2006 | −29.9% | 30 Oct 2006 | 164 |
| 7 Feb 2007 | 5 Mar 2007 | −15.3% | 21 May 2007 | 77 |
| 8 Jan 2008 | 21 Jan 2008 | −59.9% | 5 Nov 2010 | 1,019 |
| 5 Nov 2010 | 1 Feb 2011 | −28.0% | 3 Nov 2013 | 1,006 |
| 3 Mar 2015 | 24 Aug 2015 | −22.5% | 14 Mar 2017 | 568 |
| 28 Aug 2018 | 23 Oct 2018 | −14.6% | 16 Apr 2019 | 175 |
| 14 Jan 2020 | 9 Mar 2020 | −38.4% | 9 Nov 2020 | 245 |
| 18 Oct 2021 | 7 Mar 2022 | −17.2% | 24 Nov 2022 | 262 |
| 26 Sep 2024 | 21 Feb 2025 | −15.8% | 2 Jan 2026 | 315 |
| 2 Jan 2026 | 23 Mar 2026 | −15.6% so far | not yet | open |

Twelve falls, eleven recovered. The eleven waits run from 28 to 1,019 days, with a median of 259. Eight of the eleven recovered within 365 days. The two Nov 2010 and Nov 2013 recoveries were closes on Diwali Muhurat sessions.

The same test at 10%, 15% and 20% gives medians of 193, 245 and 319.5 days, and a longest wait of about 1,020 days at every line. Full output is in `results/summary.txt` after you run the script.

## Data

- **2003–2011:** yearly CSVs from niftyindices.com (Historical Data, Nifty 50, Price Return). Download them and save them in `data/` under their original names (`NIFTY_50_Historical_PR_*.csv`).
- **Feb 2012 onward:** EOD2 daily data (github.com/BennyThadikaran/eod2_data), commit `04c645452ff4a214e3666fc265fdc3a56a5831c4`, prices to 23 Oct 2026. `fetch_data.py` downloads it.

The EOD2 file has no rows for Jan–Feb 2012. No fall starts, ends or reaches its low in that gap, and the script prints a note about it.

The open fall is measured to the last row of the data (23 Oct 2026).

## Limits

Twelve falls is a small sample. It describes what happened, not what will happen next. The 13% line is a choice.

## Run

```powershell
cd trading-tools\crash_recovery_2004
pip install pandas
python fetch_data.py
python recovery.py
```

Writes `results/falls.csv` and `results/summary.txt`.

Past data only. Nothing here is investment advice.
