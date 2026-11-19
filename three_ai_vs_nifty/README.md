# 3 AI strategies vs holding Nifty

Three AI chatbots were asked the same question in a fresh chat:

> Give me the best swing trading strategy for Nifty 50 stocks on daily candles, long only. Write the exact entry, stop-loss and exit rules, with a number for every rule.

Each answer was turned into code and backtested on ₹1,00,000 from January 2016 to 9 November 2026, then compared with simply holding Nifty.

| File | Strategy |
|---|---|
| `backtest.py` | Fable 5.2: buy a short pullback (RSI(3) below 20) in an uptrend |
| `backtest_astra.py` | GPT-6 Astra: 20-day breakout with an ATR trailing stop |
| `backtest_argon.py` | Gemini 4 Argon: 20/50 EMA pullback with a bullish trigger candle |
| `costs.py` | Zerodha delivery charges used by all three |

The exact rules for each strategy are written at the top of its file.

## What you need

1. **Python 3.10+** with `numpy` and `pandas`:
   ```powershell
   pip install numpy pandas
   ```
2. **Daily price data.** The CSV files from the free [eod2](https://github.com/BennyThadikaran/eod2) project (data repo: [eod2_data](https://github.com/BennyThadikaran/eod2_data)). Copy the `daily` folder so that this path exists:
   ```
   three_ai_vs_nifty\data\daily\nifty 50.csv
   three_ai_vs_nifty\data\daily\reliance.csv
   ...
   ```
3. **`nifty50_membership_2016_2026.csv`** (in this folder). It lists which stocks were in the Nifty 50 and when, so each year only uses that year's actual members. Columns: `symbol, eod2_file, member_from, member_until_exclusive`.

## Run it

From inside this folder:

```powershell
python backtest.py          # Fable 5.2
python backtest_astra.py    # GPT-6 Astra
python backtest_argon.py    # Gemini 4 Argon
```

Each prints its result next to holding Nifty, and writes trade lists and the daily equity curve to `results\`.

Add `sens` to also run the sensitivity checks (zero slippage, 0.30% slippage, ₹10,00,000 capital and other variations):

```powershell
python backtest.py sens
```

`END` at the top of `backtest.py` is set to `2026-11-09`, the last day used in the video. Set it to `None` to include newer data.

## Which data version gives which numbers

The video was made on eod2 data as of 9 November 2026 (eod2_data commit `d23d835`). On 14 November eod2 fixed a bug that had left a few trading days (mostly Muhurat and special sessions) out of most stock files. So your result depends on which copy you use:

| | eod2 data of 9 Nov 2026 (as in the video) | eod2 data after the 14 Nov fix |
|---|---|---|
| Fable 5.2 | ₹77,630 · 426 trades | ₹76,969 · 432 trades |
| GPT-6 Astra | ₹76,573 · 518 trades | ₹71,725 · 520 trades |
| Gemini 4 Argon | ₹99,985 · 24 trades | ₹99,985 · 24 trades |
| Holding Nifty | ₹3,14,049 | ₹3,14,049 |

To reproduce the video exactly, check out that commit of [eod2_data](https://github.com/BennyThadikaran/eod2_data):

```powershell
git clone https://github.com/BennyThadikaran/eod2_data
cd eod2_data
git checkout d23d835
```

With either version, none of the three beats holding Nifty.

## How it was tested

- Signals use the day's close; orders fill on the following sessions as each file describes.
- Zerodha delivery charges (rates checked 10 November 2026) plus 0.15% slippage on every buy and sell. The slippage figure is an assumption.
- Holding Nifty is charged like an ETF, with no slippage.
- Prices only. No dividends on either side.

## Limits

- One prompt and one answer per AI. The same prompt can give a completely different answer.
- Argon and Astra searched the web before answering; Fable did not.
- Some rules had no number (for example how to calculate RSI, or what price to buy at on a gap). Those values were chosen when writing the code, so this tests one reading of each answer.
- Not tested: the earnings-date filter and sector cap (no historical data), the drawdown pause, and Argon's swing-high target and buy-stop option.
- No price data for HDFC, LTIM, CAIRN, Tata Motors DVR, Tata Motors before 2024, and Samman Capital 2017–2019. Some survivorship bias remains.
- Trades around unadjusted split or demerger days are skipped: Reliance 2023, Power Grid 2023, Shriram Finance 2025, Tata Motors 2025.
- This tests these rules, not AI in general.

⚠️ This is a test of a strategy, not a recommendation. A backtest shows what rules would have done on past data. It cannot tell you what they will do next. I'm not a registered advisor and nothing here is investment advice.