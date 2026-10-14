# India's 20 biggest IPOs on listing day

Data and code for the video "Do India's Biggest IPOs Actually Make Money? I Tested 20 Before Jio".

## Run it

```
python ipo_listing.py
```

You only need Python 3. No packages to install.

## What it tests

The 20 largest Indian IPOs by issue size, from Reliance Power (2008) to NSE (2026). Each one is tested three ways:

1. **Applied at the IPO price.** Buy at the retail price (after any retail discount). Sell at the listing-day close.
2. **Bought at the listing-day open.** Buy at the first traded price. Sell at the close.
3. **Weighted by allotment odds.** Way 1, multiplied by `min(1, 1 / retail subscription)`.

## Results

| Test | Average |
|---|---|
| Applied at IPO price | +9.8% (median +4.0%) |
| Bought at listing-day open | +0.1% |
| Weighted by allotment odds | ≈ +3.9% |

14 went up on day one. 6 went down.

## Limits

- No brokerage, taxes or other costs.
- The odds are rough. The real retail lottery works per application, not per share, so true odds differ.
- 20 IPOs is a small sample.
- NSE listed on BSE only, so its prices are BSE prices.
- Reliance Power's close is the BSE close. The NSE close wasn't found.
- ICICI Prudential AMC's open is calculated from its reported NSE listing gain.

## Data

`biggest_ipos.csv` has one row per IPO. Each row links its sources for prices (`source_listing`) and subscription (`source_subscription`).

---

⚠️ This is a test of a strategy, not a recommendation. A backtest shows what rules would have done on past data. It cannot tell you what they will do next. I'm not a registered advisor and nothing here is investment advice.