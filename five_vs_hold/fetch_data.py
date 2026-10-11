"""
fetch_data.py - download every price file the backtest needs.

Source: the EOD2 data repository (github.com/BennyThadikaran/eod2_data), pinned to
one commit so every run sees exactly the same data.

Downloads into data/:
  * NIFTY50.csv     - Nifty 50 index daily open/high/low/close (used for signals)
  * NIFTYBEES.csv   - the ETF itself (used for every trade price)
  * the 83 ETFs on the ETF ki Dukan list (../etf_dukan/etf_list_2023-04-02.csv).
    Many were renamed after April 2023, so each symbol is matched by its ISIN.

Usage:  python fetch_data.py
"""
import csv, json, os, urllib.parse, urllib.request

COMMIT = "316b3be7872dd1aa889ac5d3cf0a77af1c34455b"
BASE = f"https://raw.githubusercontent.com/BennyThadikaran/eod2_data/{COMMIT}"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")
ETF_LIST = os.path.join(HERE, "..", "etf_dukan", "etf_list_2023-04-02.csv")


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def save(name, data):
    with open(os.path.join(OUT, name), "wb") as f:
        f.write(data)


def main():
    os.makedirs(OUT, exist_ok=True)
    save("NIFTY50.csv", get(f"{BASE}/daily/{urllib.parse.quote('nifty 50')}.csv"))
    save("NIFTYBEES.csv", get(f"{BASE}/daily/niftybees.csv"))
    print("NIFTY50, NIFTYBEES")

    with open(ETF_LIST, newline="", encoding="utf-8") as f:
        symbols = [row["symbol"] for row in csv.DictReader(f)]
    m = json.loads(get(f"{BASE}/isin_symbol_map.json"))
    sym2isin, isin2hist = m["sym2isin"], m["isin2hist"]
    missing = []
    for s in symbols:
        hist = isin2hist.get(sym2isin.get(s), []) if sym2isin.get(s) else []
        if not hist:
            missing.append(s)
            continue
        current = hist[-1]["symbol"]
        save(f"{s}.csv", get(f"{BASE}/daily/{urllib.parse.quote(current.lower())}.csv"))
    print(f"{len(symbols) - len(missing)} of {len(symbols)} ETF list files downloaded")
    if missing:
        print("not found:", ", ".join(missing))


if __name__ == "__main__":
    main()
