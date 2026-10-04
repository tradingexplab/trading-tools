# ETF ki Dukan (version 1) backtest

A backtest of the ETF ki Dukan method on its original list of 83 ETFs, dated 2 April 2023.
Test period: 3 April 2023 to 25 September 2026. Zerodha delivery charges included.

## Results

| | ₹2 lakh | ₹10,000 |
|---|---|---|
| Strategy, per year | 9.9% | −0.8% |
| Holding NIFTYBEES, per year | 9.8% | 9.7% |
| Worst fall, strategy | −10.4% | −12.9% |
| Sales / losing after charges | 291 / 0 | 269 / 168 |
| Still held at the end / below cost | 29 / 27 | 26 / 26 |

With ₹2 lakh, holding all 83 ETFs equally made 21.0% a year, and the 68 without gold and silver made 17.8%.

## Rules

As stated in the strategy's videos:

1. Each day, rank the ETFs by how far the close sits below its 20-day average. Look at the top 3.
2. Buy one ETF a day, sized at capital ÷ 60. Prefer the best-ranked top-3 ETF you don't hold.
3. If you hold all three, buy more of the best-ranked one whose price is more than 2.5% below its last purchase. Otherwise skip the day.
4. Sell at a 6% profit over average cost.

Where the videos are silent, this test uses the plain reading: trades at the close, every ETF at +6% sells that day, the buy size stays fixed, whole units (minimum one), no cap on adding, and a buy is skipped if cash runs short.

## Data

Daily prices come from the [EOD2 data repository](https://github.com/BennyThadikaran/eod2_data), pinned to commit `316b3be7`. 45 of the 83 ETFs were renamed after April 2023; `fetch_data.py` matches each one by its ISIN. Ten 1:10 splits are adjusted in the code.

Charges are statutory only (exchange, SEBI, GST, stamp duty, STT and the ₹15.34 DP charge per sale). The bid-ask spread is not included. Equity-ETF rates are applied to every ETF, which overstates gold, silver and international ETF charges by 0.001% of each sale.

## Run it

```
pip install pandas numpy
python fetch_data.py
python etf_dukan_v1.py
```

Results are printed and saved under `results/`.

This is a test of a strategy, not a recommendation. A backtest shows what rules would have done on past data. It cannot tell you what they will do next. Nothing here is investment advice.
