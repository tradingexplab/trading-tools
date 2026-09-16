# trading-tools

Small Python scripts behind the videos on [The Trading Experiment](https://www.youtube.com/@tradingexplab) YouTube channel.

Each script answers one question with arithmetic, not opinion. Every number shown on screen comes from running these files.

## The setup these scripts model

- ₹10,000 account
- Swing trading, cash segment, delivery only, no leverage
- Equity ETFs on Zerodha
- 1% of the account risked per trade
- ₹5,000 minimum position size

If your account, broker, or instrument is different, change the inputs and re-run. The outputs will change.

## Videos and their code

| Video | Question it answers | Script |
|---|---|---|
| [Zerodha's calculator has no ETF option. It costs me 10x.](https://www.youtube.com/watch?v=ygbnnFp2-bE&t=4s) | What do broker charges actually cost a small account, and what win rate does that force? | `costs.py` |
| [Swing Trading ETFs with Rs. 10,000: Position Sizing and Cost Breakdown](https://www.youtube.com/watch?v=NCi6GO_K8u0) | Can a position that still makes sense after costs exist on a ₹10,000 account at all? | `sizing.py` |

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

## Run it

Requires Python 3. No external packages.

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

These scripts show whether a trade **can exist** on a small account. They say nothing about whether it **wins**.

## License

MIT