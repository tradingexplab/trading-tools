"""
fetch_data.py - download daily prices for the 83 ETFs in etf_list_2023-04-02.csv.

Source: the EOD2 data repository (github.com/BennyThadikaran/eod2_data), pinned to
one commit so every run sees the same data. Many ETFs were renamed after April 2023
(for example ICICINIFTY is now NIFTYIETF). Each 2023 symbol is matched to its ISIN,
which never changes, and the ISIN's latest symbol is downloaded. Files are saved
under data/ with the 2023 symbol as the file name.

Usage:  python fetch_data.py
"""
import csv, json, os, urllib.parse, urllib.request

COMMIT = "316b3be7872dd1aa889ac5d3cf0a77af1c34455b"
BASE = f"https://raw.githubusercontent.com/BennyThadikaran/eod2_data/{COMMIT}"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(HERE, "etf_list_2023-04-02.csv"), newline="", encoding="utf-8") as f:
        symbols = [row["symbol"] for row in csv.DictReader(f)]
    m = json.loads(get(f"{BASE}/isin_symbol_map.json"))
    sym2isin, isin2hist = m["sym2isin"], m["isin2hist"]
    missing = []
    for s in symbols:
        isin = sym2isin.get(s)
        hist = isin2hist.get(isin, []) if isin else []
        if not hist:
            missing.append(s)
            continue
        current = hist[-1]["symbol"]
        data = get(f"{BASE}/daily/{urllib.parse.quote(current.lower())}.csv")
        with open(os.path.join(OUT, f"{s}.csv"), "wb") as f:
            f.write(data)
        note = "" if current == s else f"  (now {current})"
        print(f"{s}{note}")
    print(f"\n{len(symbols) - len(missing)} of {len(symbols)} downloaded")
    if missing:
        print("not found:", ", ".join(missing))


if __name__ == "__main__":
    main()
