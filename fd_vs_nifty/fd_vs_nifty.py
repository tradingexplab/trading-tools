"""FD vs Nifty after tax and inflation.

Same Rs 1,00,000 goes into a bank FD (renewed every year at that year's rate)
and into the Nifty 50. Tax is taken out of both, then inflation.

Usage:
    python fd_vs_nifty.py data/nifty_close.csv

Inputs:
    data/nifty_close.csv     date,close  (Nifty 50 index closes - see README)
    rbi_fd_rates.csv         RBI table: lower end of the 3-5 year deposit rate, per year
"""
import csv
import datetime as dt
import os
import sys

AMT = 100000.0
FD_TAX = 0.30 * 1.04      # 30% slab + 4% cess, on the interest, every year
LTCG = 0.125              # 12.5% on gain above the exemption, once at sale
EXEMPT = 125000

# CPI inflation by financial year start (percent):
# CPI-IW up to 2011-12, CPI Combined 2012-13 to 2024-25, a blend for 2025-26.
INFL = {2009: 12.4, 2010: 10.4, 2011: 8.4,
        2012: 9.9, 2013: 9.4, 2014: 5.9, 2015: 4.9, 2016: 4.5, 2017: 3.6,
        2018: 3.4, 2019: 4.8, 2020: 6.2, 2021: 5.5, 2022: 6.7, 2023: 5.4, 2024: 4.6}
INFL[2025] = (9 * 1.7 + 3 * 3.1) / 12   # Apr-Dec 2025 old base, Jan-Mar 2026 new base


def load(nifty_file, rates_file):
    close = {dt.date.fromisoformat(r['date']): float(r['close'])
             for r in csv.DictReader(open(nifty_file))}
    rates = {r['year_end_march']: float(r['td_3_5y_low'])
             for r in csv.DictReader(open(rates_file))}
    return close, rates


def run(close, rates, start_year, years):
    days = sorted(close)

    def first_on_or_after(d):
        return next(x for x in days if x >= d)

    buy = first_on_or_after(dt.date(start_year, 4, 1))
    sell = first_on_or_after(dt.date(start_year + years, 4, 1))

    # FD: the rate for each year is the one from the March just before it starts
    fd = fd_pre = AMT
    interest = tax_paid = 0.0
    used = []
    for k in range(years):
        label = f"{start_year + k - 1}-{str(start_year + k)[2:]}"
        r = rates[label] / 100
        used.append(rates[label])
        i = fd * r
        t = i * FD_TAX
        interest += i
        tax_paid += t
        fd += i - t
        fd_pre *= 1 + r

    # Nifty: price index only (no dividends), tax once at sale
    final = AMT * close[sell] / close[buy]
    nifty_tax = LTCG * max(0.0, final - AMT - EXEMPT)
    nifty = final - nifty_tax

    # inflation
    f = 1.0
    for k in range(years):
        f *= 1 + INFL[start_year + k] / 100

    return dict(buy=buy, sell=sell, years=years, fd_rates='/'.join(f'{u:g}' for u in used),
                fd_pretax=round(fd_pre), fd_interest=round(interest), fd_tax=round(tax_paid),
                fd_aftertax=round(fd), nifty_pretax=round(final), nifty_tax=round(nifty_tax),
                nifty_aftertax=round(nifty), cum_inflation_x=round(f, 3),
                fd_real=round(fd / f), nifty_real=round(nifty / f),
                winner='Nifty' if nifty > fd else 'FD')


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    close, rates = load(sys.argv[1], os.path.join(here, 'rbi_fd_rates.csv'))
    os.makedirs('results', exist_ok=True)

    print('Headline run: Apr 2009 to Apr 2026 (17 years)')
    h = run(close, rates, 2009, 17)
    for k, v in h.items():
        print(f'  {k}: {v}')

    print('\n10-year windows (start Apr 2009 ... Apr 2016)')
    rows = [run(close, rates, y, 10) for y in range(2009, 2017)]
    for r in rows:
        print(f"  {r['buy']} -> {r['sell']}  FD {r['fd_aftertax']:>7,}  Nifty {r['nifty_aftertax']:>7,}  "
              f"real FD {r['fd_real']:>7,}  real Nifty {r['nifty_real']:>7,}  {r['winner']}")

    with open('results/fd_vs_nifty_10y_windows.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open('results/fd_vs_nifty_17y.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(h))
        w.writeheader()
        w.writerow(h)
