"""Listing-day returns of India's 20 biggest IPOs, tested three ways.

1. Applied at the IPO price (retail price, after any retail discount),
   sold at the listing-day close.
2. Bought at the listing-day open, sold at the close.
3. Way 1, weighted by a rough chance of getting shares:
   min(1, 1 / retail subscription).

No costs or taxes included. Run: python ipo_listing.py
"""
import csv
from pathlib import Path
from statistics import mean, median

rows = list(csv.DictReader(open(Path(__file__).with_name("biggest_ipos.csv"), encoding="utf-8")))


def num(r, k):
    return float(r[k])


def applied(r):
    return 100 * (num(r, "listing_close") / num(r, "retail_price") - 1)


def bought_at_open(r):
    return 100 * (num(r, "listing_close") / num(r, "listing_open") - 1)


def odds(r):
    # Rough: the real retail lottery works per application, not per share.
    return min(1.0, 1.0 / num(r, "retail_subscription_x"))


print(f"{'Company':<26}{'Applied':>9}{'At open':>9}{'Retail x':>10}{'Odds':>7}")
for r in sorted(rows, key=applied, reverse=True):
    print(f"{r['company']:<26}{applied(r):>+8.1f}%{bought_at_open(r):>+8.1f}%"
          f"{num(r, 'retail_subscription_x'):>9.2f}x{odds(r):>7.0%}")

a = [applied(r) for r in rows]
print()
print(f"Up / down on day one:        {sum(x > 0 for x in a)} / {sum(x < 0 for x in a)}")
print(f"Applied at IPO price:        {mean(a):+.1f}% average, {median(a):+.1f}% median")
print(f"Bought at listing-day open:  {mean(bought_at_open(r) for r in rows):+.1f}% average")
print(f"Weighted by allotment odds:  {mean(applied(r) * odds(r) for r in rows):+.1f}% average (rough)")

top3 = sorted(rows, key=applied, reverse=True)[:3]
easy = [r for r in rows if num(r, "retail_subscription_x") < 1]
print()
print(f"Top 3 gainers:               {mean(applied(r) for r in top3):+.1f}% average, "
      f"{mean(odds(r) for r in top3):.0%} average odds")
print(f"Retail not fully subscribed: {mean(applied(r) for r in easy):+.1f}% average ({len(easy)} IPOs)")