# india-trade-cost — a Claude skill for Indian traders

A free Claude skill that works out the real cost of a trade on Zerodha (NSE):
STT, exchange charges, stamp duty, GST, SEBI fee and the DP charge. It then
tells you the win rate your strategy actually needs once those costs are
counted.

It exists because two easy mistakes make losing trades look profitable:

1. Using one cost number for every instrument. Stock delivery pays about ten
   times more STT than an equity ETF like NIFTYBEES.
2. Blending the flat ₹15.34 DP charge into a percentage. On small trades that
   flat fee is most of your cost, and a blended percentage hides it.

## What it does

- Asks which instrument you're trading (stock delivery, equity ETF, gold/silver/
  liquid ETF, or intraday) before computing anything.
- Shows cost as two parts: a percentage part and a flat part.
- Computes break-even win rate with costs, next to the zero-cost version, so
  you can see the gap.
- Flags when the flat DP fee dominates your cost.
- Labels results "statutory only, excludes spread" unless you give it the
  bid-ask spread.

It only calculates. It never says whether to buy or sell anything.

## Install

**Claude Code:** clone this repo, then from the `trading-tools` folder run:

Windows (PowerShell):
```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\skills" | Out-Null
Copy-Item -Recurse .\india-trade-cost-skill "$HOME\.claude\skills\india-trade-cost"
```

macOS / Linux:
```bash
mkdir -p ~/.claude/skills && cp -r india-trade-cost-skill ~/.claude/skills/india-trade-cost
```

**Claude desktop app:** download `SKILL.md` from this folder, then go to
**Plugins → Skills → Upload skill** and pick that file.

Then just ask, for example: *"I bought 150 Reliance shares at ₹1,324.40 and
sold at ₹1,339.70, delivery. What did it really cost me?"*

## Rates and sources

Rates were checked on **21 Nov 2026** against:

- [Zerodha charges page](https://zerodha.com/charges)
- [Zerodha: Is STT levied on ETFs?](https://support.zerodha.com/category/account-opening/charges-at-zerodha/statutory-and-exchange/articles/stt-etfs)
- NSE STT non-applicability report (dated 20 Nov 2026), from
  [NSE All Reports](https://www.nseindia.com/all-reports)
- [NSE levies page](https://www.nseindia.com/static/invest/first-time-investor-sebi-turnover-fees-stt-other-levies) (stamp duty)

Notes:

- An ETF is treated as STT-free only if its symbol appears in a recent NSE STT
  non-applicability report. The report changes, so check your symbol.
- Stamp duty on ETFs bought on the exchange is taken as NSE's delivery rate,
  0.015%. NSE's table doesn't name ETFs explicitly. The 0.005% rate is for
  buying new mutual fund units from the fund. On ₹1 lakh the difference is ₹10.
- Women as first demat holder get ₹0.25 off the CDSL part of the DP charge.
  The skill ignores this; it doesn't change any break-even result.
- Rates change with budgets and exchange circulars. If the checked date above
  is more than ~3 months old, re-check before relying on the numbers.

Spread is not included unless you provide it. Income tax is not included.

## Disclaimer

This is a calculator, not advice. I'm not a registered advisor, and nothing
here is a recommendation to buy or sell anything. Check every number against
the official sources before you trade.