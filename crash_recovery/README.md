# Nifty crash recovery times

How long did each Nifty 50 fall of 13% or more, since 2016, take to get back to its old high?

## Definitions

All on daily closes of the Nifty 50 price index (dividends not included, so real investors got back to even a little sooner).

- **Old high:** the highest close before the fall.
- **Fall:** a close at least 13% below the old high.
- **Clock:** starts on the first close 13% below the old high. The wait from the old high itself is reported too.
- **Recovered:** the first close at or above the old high.
- **Counted:** falls whose first −13% close is on or after 1 Jan 2016.

The script repeats the count at 10%, 15% and 20% to check the result doesn't depend on the 13% line.

## Data

EOD2 daily data (github.com/BennyThadikaran/eod2_data), commit `50b71b70235ec1ffae802e410f34e1c7f0a571fe`, prices to 13 Oct 2026. The file starts in Feb 2012; Nifty passed its 2010 high in 2014, so every old high used from 2016 on is a true all-time high.

Only four falls since 2016 have fully recovered. That is a very small sample: it describes what happened, not what will happen next.

## Run

```
python fetch_data.py
python recovery.py
```

Writes `results/falls.csv` and `results/summary.txt`.

Past data only. Nothing here is investment advice.
