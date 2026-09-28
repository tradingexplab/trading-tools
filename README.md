# trading-tools

Small Python scripts behind the videos on [The Trading Experiment](https://www.youtube.com/@tradingexplab) YouTube channel.

Each script answers one question with arithmetic, not opinion. Every number shown on screen comes from running these files.

## Videos and their code

| Video | Question it answers | Code |
|---|---|---|
| [ETF Swing Trading Charges in Zerodha (What the Calculator hides)](https://www.youtube.com/watch?v=ygbnnFp2-bE&t=4s) | What do broker charges actually cost a small account, and what win rate does that force? | `costs.py` |
| [Can you actually trade with Rs. 10,000?](https://www.youtube.com/watch?v=NCi6GO_K8u0) | Can a position that still makes sense after costs exist on a ₹10,000 account at all? | `sizing.py` |
| [44 Moving Average Backtest: Does It Work After Costs?](https://youtu.be/u5874OUKqpM) | Does the 44 moving average strategy make money after charges? | `sma44/` |

## `costs.py` and `sizing.py`

### The setup these two scripts model

- ₹10,000 account
- Swing trading, cash segment, delivery only, no leverage
- Equity ETFs on Zerodha
- 1% of the account risked per trade
- ₹5,000 minimum position size

If your account, broker, or instrument is different, change the inputs and re-run. The outputs will change.

### `costs.py`

Calculates the full round-trip cost of one trade.

Costs come in two kinds:

- **Percentage charges** grow with trade size (STT, exchange charges, stamp duty, GST).
- **Flat charges** stay the same whatever the size (the DP charge on each sell).

On a small account the flat charge dominates. A fixed toll hurts more when the trade is small.

The script then works out the **break-even win rate** at different reward-to-risk targets. Costs cut every win and deepen every loss. So the real break-even is higher than the textbook figure.

Rates differ by instrument. The script keeps separate tiers for stocks, equity ETFs, and ETFs exempt from STT. The date the rates were last checked is stored in the file as `RATES_VERIFIED_ON`.

### `sizing.py`

Finds the range of stop distances where a trade is possible at all.

Three rules push against each other:

1. **Fixed rupee risk.** A wider stop means fewer shares.
2. **Capital cap.** A very tight stop asks for more money than the account has.
3. **Minimum position size.** A very wide stop makes the position too small to be worth the flat charge.

Only stops between those two edges produce a valid trade. For the setup above, that window is roughly **0.82% to 1.67%**. The script also reports which rule sets each edge.

## `sma44/` — 44 moving average backtest

Tests a popular Indian swing strategy, made famous by Siddharth Bhanushali, on daily data with Zerodha delivery charges included.

His rules are in words. Code needs numbers. **Every number below is my choice, not his.** Different numbers give different trades.

### Rules as tested

A daily candle is a signal when all four hold:

1. **Rising average.** The 44-day simple moving average is up at least 0.5% over the last 5 sessions.
2. **Touch.** The candle's low is within 1% of the average, above or below.
3. **Green candle.** Close is above open.
4. **First touch only.** It is the first such candle since price was last more than 1% above the average.

Then:

- **Entry** at the signal candle's high + ₹0.05. **Stop** at its low − ₹0.05.
- The buy order waits up to 3 sessions. If a session opens above the entry, the order is skipped.
- **Target** at 2× the risk in one test, 3× in the other.
- Gaps through the stop or target exit at the open. If one day hits both, the stop is assumed first.
- One open trade per stock. No time limit on trades.

### Test setup

- **Stocks:** all 50 Nifty 50 constituents as of 25 Sep 2026, plus the top 10 by weight as a subset.
- **Period:** signals from 1 Jan 2016 to 31 Aug 2026. Trades still open on 31 Aug 2026 close at that day's price.
- **Every signal taken.** No capital limit.
- **Costs:** Zerodha equity delivery charges, checked 25 Sep 2026, on ₹1,00,000 per trade. Round trip is ₹237.82 when the exit equals the entry.
- **Data:** daily prices from [EOD2](https://github.com/BennyThadikaran/eod2_data), split and bonus adjusted, as of 24 Sep 2026. Later copies of the data may differ slightly if a stock has a split or bonus after that date.

### Results, all 50 stocks

"Per ₹100 risked" means the average result of one trade, for every ₹100 between entry and stop.

| | 1:2 target | 1:3 target |
|---|---|---|
| Trades | 773 | 737 |
| Win rate | 38.2% | 30.7% |
| Break-even win rate before costs | 33.3% | 25% |
| Kept per ₹100 risked, before costs | ₹13.37 | ₹21.42 |
| Kept per ₹100 risked, after costs | ₹2.63 | ₹10.68 |
| Luck range (± 2 standard errors) | ± ₹10.72 | ± ₹13.88 |
| Worst losing streak | 15 | 19 |

Both after-cost results sit inside their luck range. **This test cannot show the strategy makes money after costs.** It also does not show a loss.

Full output for both stock sets is in `sma44/summary.txt`. Running the script writes a CSV log of every order.

### Limits

- Today's Nifty 50 are past winners. Stocks that dropped out are not tested, which flatters the result.
- Costs are statutory charges only. The bid-ask spread is not included.
- A few demergers are not adjusted in the data (TMPV, ADANIENT, GRASIM, RELIANCE). No trade in the results was affected by them.
- Daily candles cannot show whether the high or the low came first in a day.

### Run it

Needs Python 3 and pandas.

```powershell
git clone https://github.com/BennyThadikaran/eod2_data.git
git clone https://github.com/tradingexplab/trading-tools.git
cd trading-tools\sma44
pip install -r requirements.txt
python backtest.py --data ..\..\eod2_data\daily --out results_local
```

The script writes both trade logs and `summary.txt` into the `--out` folder.

The script prints a SHA-256 hash for each trade log. With the same data and pandas version, they should match:

- `trade_log_1to2.csv`: `4012416e4b1a299d402661039f9d9ef4836dcc6ed88f88d7f0fb6bdd8f5133eb`
- `trade_log_1to3.csv`: `7b4f9d847524edb0902fa3c0e1cd8a02e6a27310f40207466c8e8823fe61edf5`

## Run the other scripts

`costs.py` and `sizing.py` need only Python 3. No external packages.

```powershell
git clone https://github.com/tradingexplab/trading-tools.git
cd trading-tools
python costs.py
python sizing.py
```

To use your own numbers, edit the input values at the top of each file and run it again.

## Sources for the charges

- Zerodha charges page: https://zerodha.com/charges
- NSE's list of securities where STT does not apply

Charges change. Check them yourself before relying on any output.

## Disclaimer

I am not a SEBI-registered investment adviser. Nothing here is investment advice.

`costs.py` and `sizing.py` show whether a trade **can exist** on a small account. They say nothing about whether it **wins**.

The backtest describes the past. It is not a forecast.

## License

MIT