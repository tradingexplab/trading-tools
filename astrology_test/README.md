# Do astrology beliefs move the Nifty?

Tests three popular beliefs on Nifty 50 data from 1 Jan 2004 to 9 Nov 2026:

1. **Amavasya:** does Nifty fall on Amavasya? Do moves get bigger in the 4 trading days around it?
2. **Budh Vakri (Mercury retrograde):** does Nifty fall while Mercury is retrograde?
3. **Jupiter in Ketu's nakshatras (Ashwini, Magha, Mula):** does a 20%+ crash come while Jupiter is there?

It also runs a ₹10 lakh simulation on NIFTYBEES: one holder who never sells, and one follower per belief who sells before the "bad" time and buys back after.

## 1. Get the data

Download these yourself and put them in the folders shown:

| File | Where to get it | Put it in |
|---|---|---|
| NIFTY 50 price index (not Total Returns), one file per year, 2003 to 2012 | niftyindices.com/reports/historical-data (Reports → Historical Data, pick NIFTY 50, one year per download). Files are named like `NIFTY_50_Historical_PR_01012003to31122003.csv` | `data/niftyindices/` |
| `nifty 50.csv` | github.com/BennyThadikaran/eod2_data, folder `daily/` | `data/eod2/` |
| `niftybees.csv` | same EOD2 repo, folder `daily/` | `data/eod2/` |

## 2. Install

```
pip install pandas numpy pyswisseph
```

## 3. Run

```
python build_index.py
python dates.py
python run.py
```

- `build_index.py` joins the niftyindices files (2003 to Feb 2012) with the EOD2 index file (Feb 2012 onward) into `data/nifty_index_2003_2026.csv`, and checks that the two sources agree where they overlap.
- `dates.py` computes the event dates with the Swiss Ephemeris and writes three files into `data/`.
- `run.py` runs every test and prints the results.

Random comparisons use a fixed seed, so you should get the same numbers. Luck figures can move by a point or so if you change the seed.

## The rules

- **Data:** Nifty 50 price index (no dividends) for the tests; NIFTYBEES closing prices for the ₹10 lakh simulation. Diwali Muhurat sessions (2004–2026) and low-volume weekend test sessions are removed.
- **Amavasya day:** the date whose New Delhi sunrise falls inside the Amavasya tithi. Only Amavasyas that fall on a trading day count. Returns are close to close.
- **Mercury retrograde:** Mercury's longitude speed is below zero at 3:30 pm IST. Only completed periods count.
- **Jupiter:** sidereal position (Lahiri ayanamsa) at noon IST. Counted four ways: inside each visit, inside each transit (retrograde re-entries merged), and each of those plus 90 days after. Crash = a fall of 20% or more from a high to a low. The script also prints the same counts with 60 and 120 extra days and a 25% crash line.
- **"Worked":** the belief's result is more extreme than 95% of 10,000 random comparisons (random days for Amavasya, shifted calendars for Mercury). For Jupiter, "luck" is the chance of seeing that many crashes in windows of the same length picked at random from 2004–2026.
- **₹10 lakh simulation:** followers sell at the close before the "bad" time and buy back at its last close. Zerodha equity ETF delivery charges (0.0235% of value + ₹15.34 per round trip). No tax, no spread. Idle cash earns 0%; the script also shows 6%.

## Limits

- Past data only. It cannot say what happens next.
- Jupiter has only 5 transits (8 visits) since 2004, too few to prove or disprove anything.
- Today's charges are applied to every year, and tax is left out. Followers who sell often would pay short-term tax on each sale.
- Only the nakshatra condition is tested for Jupiter, not other conditions astrologers add.

⚠️ This is a test of a strategy, not a recommendation. A backtest shows what rules would have done on past data. It cannot tell you what they will do next. I'm not a registered advisor and nothing here is investment advice.
