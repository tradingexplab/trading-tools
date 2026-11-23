---
name: india-trade-cost
description: Compute the round-trip cost (statutory, plus spread when known), break-even win rate, and viable stop range for a trade on Zerodha (NSE), using instrument-specific rate tiers. Use whenever the user asks what a trade costs, what win rate a strategy needs, whether an R-multiple target is achievable, how wide a stop must be to survive costs, or asks to check a position-sizing or expectancy calculation. Triggers on ETF, stock, delivery, CNC, intraday, MIS, brokerage, STT, DP charge, break-even, expectancy, R-multiple, position size.
---

# Indian Trade Cost & Break-Even

## The two errors this skill exists to prevent

**Error 1: one cost number for all instruments.** Stock delivery costs
roughly ten times what an equity ETF costs, because STT is 0.2% on stocks
(0.1% each side) and 0.001% on equity ETFs (sell side only). A single
"delivery cost %" silently applies the stock rate to an ETF trade and inflates
the required win rate.

**Error 2: percentage and flat costs folded together.** A flat ₹15.34 DP fee
and a 0.0235% percentage charge behave in opposite directions as position size
changes. Blend them into one "0.4% all-in" figure and the flat fee's dominance
at small size disappears from view — which is exactly where it matters most.

Both errors produce numbers that look reasonable. Neither announces itself.

---

## Step 0 — Ask the instrument first

**Before computing anything, if the instrument type is not already stated,
ask.** One question:

> Which of these — individual stock (delivery), equity ETF (Nifty/Sensex/
> sector/bank), non-STT ETF (gold, silver, liquid, gilt, most international),
> or intraday?

Do not infer it from context. Do not pick the middle tier as a hedge. The
whole cost model hinges on this one fact, and guessing it wrong invalidates
every downstream number.

Accept a tier only from an explicit statement by the user, or from a symbol
confirmed against NSE's STT non-applicability report. Otherwise ask. A
recognisable name is not confirmation.

---

## Rate table

**Verified on: 2026-11-21**
**Sources: zerodha.com/charges; Zerodha support article "Is STT levied on
ETFs?"; NSE STT non-applicability report dated 2026-11-20; NSE levies page
for stamp duty.**
**Applies to: Zerodha, NSE, resident individual, non-BSDA.**

If today's date is more than ~3 months past the verified-on date above, say so
before using these numbers, and offer to re-check the sources. STT and exchange
transaction rates change with budgets and exchange circulars.

### Per-side statutory components (equity segment, NSE)

| Component | Delivery | Intraday |
|---|---|---|
| Exchange transaction | 0.00307% each side | 0.00307% each side |
| SEBI turnover fee | 0.0001% each side (₹10/crore) | 0.0001% each side |
| Stamp duty | 0.015% buy side only* | 0.003% buy side only |
| GST | 18% on (brokerage + exchange + SEBI) | same |
| IPFT | negligible, ignore | same |

*ETF units bought on the exchange are treated here as a delivery-basis
transfer, which NSE's levies table charges at 0.015%. That table does not name
ETFs explicitly. The 0.005% rate applies to buying new mutual fund units
directly from a fund, not to exchange purchases. On ₹1 lakh the difference
between the two is ₹10.

### Tier table — round-trip cost

Percentage component is expressed as a share of **one-side notional** (the
position value), with both legs already summed. This is a close approximation:
the sell leg is slightly larger or smaller than the buy leg, which moves the
total by a few rupees at most on typical positions.

| Tier | Instruments | STT | **Percentage component** | **Flat component** |
|---|---|---|---|---|
| **A. Stock delivery** | Individual shares, CNC | 0.1% buy + 0.1% sell | **0.2225%** | **₹15.34** |
| **B. Equity ETF delivery** | Nifty/Sensex/sector/bank ETFs | 0% buy, 0.001% sell | **0.0235%** | **₹15.34** |
| **C. Non-STT ETF delivery** | Gold, silver, liquid, gilt, international | none | **0.0225%** | **₹15.34** |
| **D. Equity intraday** | Stocks or ETFs, MIS | 0.025% sell side | **see below** | **₹0** |

The flat ₹15.34 is the DP charge: ₹3.50 CDSL + ₹9.50 Zerodha + ₹2.34 GST, per
scrip, on the sell side.

**Tier D percentage component** depends on where brokerage lands:

- Brokerage is `min(0.03% × leg value, ₹20)` **per leg**.
- The hinge is at **₹66,667 per leg**. Below it you pay the percentage; above
  it you pay the flat ₹20.
- Below the hinge: **0.1063%** of notional, flat component ₹0.
- Above the hinge: 0.0355% of notional + ₹47.20 flat (₹40 brokerage + GST).

No DP charge on intraday — nothing is debited from the demat account.

### Tier boundary cautions

- **Silver, gold, liquid and international ETFs**: confirmed in NSE's STT
  non-applicability report dated 2026-11-20 (for example SILVERBEES,
  GOLDBEES, LIQUIDBEES, MON100) — Tier C. NIFTYBEES is not in the report —
  Tier B.
- **Re-check anyway.** NSE reissues the report daily and securities move on
  and off it. It lists individual securities, so a symbol you have not checked
  in a recent report is unconfirmed, even if others in its category are listed.
- **Some liquid ETFs have a different DP charge** at Zerodha. Check before
  applying ₹15.34 to them.
- **BTST** on ETFs pays delivery STT (0.001%), not intraday STT.
- **DP charge is per scrip per day, on the sell side, regardless of quantity.**
  Selling two scrips the same day costs ₹30.68, not ₹15.34.
- **Women as first holder** get ₹0.25 off the CDSL part of the DP charge.
  Immaterial for break-even maths.
- **The DP charge does not appear in Zerodha's brokerage calculator output**
  or on the contract note, because the depository levies it, not the exchange.
  It shows up later in the ledger. A cost estimate taken from the calculator is
  therefore short by ₹15.34 per sell, which at small position size is most of
  the true cost. Never treat calculator output as complete for delivery trades.

---

## Step 1 — Compute cost as two named parts

Always write it this way:

```
Percentage component: <rate>% × ₹<notional> = ₹<x>
Flat component:       ₹<y>
Total round trip:     ₹<x+y>
```

Never collapse these into a single blended percentage. If the user asks for
"the cost as a %", give the two parts first, then the blend, and note that the
blend is only valid at that one position size.

---

## Step 1b — Spread is a cost, and often a large one

The tier table is statutory only. Spread is not in it, and for ETFs it is
comparable in size to everything that is.

You cross the spread **once per round trip**, not twice: you buy at the ask and
sell at the bid, so you give up half a spread on each leg and one full spread
in total.

At Tier B, statutory percentage cost is 0.0235%. A five-paisa spread on a ₹280
ETF is 0.018% round trip — roughly as large as every tax and fee combined.

Ask for the typical spread. If it isn't available, label the output
**"statutory only, excludes spread"** rather than calling it true round-trip
cost.

---

## Step 2 — Break-even win rate, in its real form

**Use this:**

```
p = net_loss / (net_win + net_loss)

where  net_win  = gross_target − cost
       net_loss = gross_stop   + cost
```

Costs subtract from the win **and** add to the loss. That double action is why
the naive formula is wrong.

**Do not use `p = 1 / (1 + R)`.** That formula assumes zero cost. At a 3R
target it says 25%. On a ₹10,000 Tier B position with 1R = ₹100, the real
answer is 29.4%. A strategy tested against 25% passes; against 29.4% it may
not. That gap is the trap.

State both numbers, with the position size they belong to:

> At ₹10,000 notional, 1R = ₹100 — naive (zero-cost): 25.0%. With costs:
> 29.4%. Gap: 4.4 points.

The gap is not a constant. It grows as position size falls, because the flat
fee is a larger share of a smaller R.

---

## Step 3 — The mandatory check (do not skip)

After any cost or break-even computation, state these two lines:

1. **Cost as a share of 1R:** `total_cost / gross_stop_in_rupees` as a percent.
2. **Flat fee share of total cost:** `flat / total` as a percent.

Then, if the flat component is more than half of total cost, **say so
explicitly**:

> The ₹15.34 DP fee is 87% of your total cost. At this size you are not paying
> a percentage cost — you are paying a fixed toll. Doubling position size
> roughly halves cost as a share of R.

This is the line that catches sizing errors before they reach a plan.

---

## Step 4 — Report which constraint binds

When asked for a viable stop distance, a position size, or a range of any
kind, **do not report only the number. Report what bounds each end.**

**Which end is bounded by what depends on the sizing model. Compute both;
never assume.**

**Fixed-notional sizing** (position value roughly constant): a tighter stop
makes 1R small in rupees, so the flat fee grows as a share of R. Cost binds the
tight end. Capital binds the wide end.

**Fixed-risk sizing** (rupee risk constant, shares derived): a tighter stop
buys more shares. 1R is unchanged, so cost drag is unchanged. Cost binds
neither end. Capital binds the tight end; a minimum-position rule, if the user
has one, binds the wide end.

State the sizing model before reporting a band. Then walk each end outward one
step and report which check fails first, and name which one is actually
active:

> Binding constraint: your minimum position rule, not cost. Cost never binds
> under fixed-risk sizing. Loosening a cost ceiling buys you nothing.

Assuming the wrong end binds leads to optimising the wrong variable.

**Distinguish arithmetic bounds from chosen bounds.** A capital cap is
arithmetic. A minimum position size is a preference the user chose and can
change. Say which is which — they respond differently to a larger account.

---

## Step 5 — Required precision scales with what the number decides

Do not chase precision on a component that cannot move any decision. Do not
wave away imprecision on one that can.

The test: express the uncertainty in rupees, then compare it to the smallest
gap it would have to close to flip a decision.

Worked instance: suppose one rate is uncertain by 0.01% of notional. On a
₹10,000 position that is ₹1. Beside a ₹15.34 flat fee and a break-even gap of
several points, ₹1 cannot move anything, so the question can be dropped. On a
₹50 lakh position the same uncertainty is ₹500, and it may be worth resolving.

**Say the rule out loud when you apply it**, especially when dropping a
question you raised earlier. Otherwise it reads as an unexplained reversal.

---

## Verify before relying on it

Any number from this skill that is going into a public post or a live-money
decision should be checked against the primary sources first: Zerodha's
charges page, Zerodha's ETF STT support article, and NSE's STT
non-applicability report. All are public, no account needed.

---

## Worked example

**Input:** Equity ETF, delivery. Notional ₹10,000. 1R = ₹100. Target 3R.

```
Tier B (equity ETF delivery) — statutory only, excludes spread

Percentage component: 0.0235% × ₹10,000 = ₹2.35
Flat component:       ₹15.34
Total round trip:     ₹17.69

Gross stop   = ₹100.00  (1R)
Gross target = ₹300.00  (3R)

net_win  = 300.00 − 17.69 = ₹282.31
net_loss = 100.00 + 17.69 = ₹117.69

p = 117.69 / (282.31 + 117.69) = 117.69 / 400 = 29.4%
```

**Check:**
- Cost as share of 1R: 17.69 / 100 = **17.7%**
- Flat fee share of cost: 15.34 / 17.69 = **86.7%**
- Flat fee dominates. This is a fixed-toll regime, not a percentage regime.

**Comparison:** naive `1/(1+3)` = 25.0%. Real = 29.4%. **4.4 points understated.**

**Same position at 2R:** real 39.2% vs naive 33.3%.

**If this were Tier A (stock delivery)** at the same size: percentage component
₹22.25, total ₹37.59, 3R break-even 34.4%. The instrument tier alone moves the
required win rate by 5.0 points — and more at larger size, where the
percentage component dominates.

---

## Output discipline

- Lead with the number asked for.
- Show the two cost parts, always — and label output "statutory only, excludes
  spread" when spread is unknown.
- Show the check lines from Step 3, always.
- Name the binding constraint whenever a range was requested.
- State the verified-on date whenever quoting a rate.
- If any input is missing — instrument, notional, stop distance — ask instead
  of assuming a default.
- This skill calculates costs. It does not say whether to buy or sell anything.
