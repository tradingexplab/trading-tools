"""
fetch_data.py - download every price file the backtest needs.

Source: the EOD2 data repository (github.com/BennyThadikaran/eod2_data), pinned to
two commits so every run sees exactly the same data:
  * HISTORY_COMMIT - full price history up to 25 Sep 2026.
  * LATEST_COMMIT  - used only to add the trading days after 25 Sep 2026 (up to 23 Oct 2026).
Later EOD2 snapshots trim the history of some ETFs, so the two are joined: history from the
first commit, then any rows dated after its last row from the second. Prices on the dates
both files share are identical.

Downloads into data/:
  * NIFTY50.csv     - Nifty 50 index daily open/high/low/close (used for signals)
  * NIFTYBEES.csv   - the ETF itself (used for every trade price)
  * the 83 ETFs on the ETF ki Dukan list (../etf_dukan/etf_list_2023-04-02.csv).
    Many were renamed after April 2023, so each symbol is matched by its ISIN.

Usage:  python fetch_data.py
"""
import csv, json, os, urllib.parse, urllib.request

HISTORY_COMMIT = "316b3be7872dd1aa889ac5d3cf0a77af1c34455b"
LATEST_COMMIT = "04c645452ff4a214e3666fc265fdc3a56a5831c4"
RAW = "https://raw.githubusercontent.com/BennyThadikaran/eod2_data"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")
ETF_LIST = os.path.join(HERE, "..", "etf_dukan", "etf_list_2023-04-02.csv")


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def save(name, data):
    with open(os.path.join(OUT, name), "wb") as f:
        f.write(data)


def join(old, new):
    """old file + the rows of the new file dated after old's last row (same header required)."""
    old_lines = old.decode("utf-8").splitlines()
    new_lines = new.decode("utf-8").splitlines()
    if old_lines[0] != new_lines[0]:
        raise ValueError("column headers differ between the two snapshots")
    last = old_lines[-1].split(",")[0]
    extra = [ln for ln in new_lines[1:] if ln.split(",")[0] > last]
    return ("\n".join(old_lines + extra) + "\n").encode("utf-8")


def fetch(path_old, path_new):
    """Download one daily file from both commits and join them."""
    return join(get(f"{RAW}/{HISTORY_COMMIT}/daily/{path_old}.csv"),
                get(f"{RAW}/{LATEST_COMMIT}/daily/{path_new}.csv"))


def current_symbol(commit_map, sym):
    isin = commit_map["sym2isin"].get(sym)
    hist = commit_map["isin2hist"].get(isin, []) if isin else []
    return hist[-1]["symbol"].lower() if hist else None


def main():
    os.makedirs(OUT, exist_ok=True)
    save("NIFTY50.csv", fetch(urllib.parse.quote("nifty 50"), urllib.parse.quote("nifty 50")))
    save("NIFTYBEES.csv", fetch("niftybees", "niftybees"))
    print("NIFTY50, NIFTYBEES")

    with open(ETF_LIST, newline="", encoding="utf-8") as f:
        symbols = [row["symbol"] for row in csv.DictReader(f)]
    map_old = json.loads(get(f"{RAW}/{HISTORY_COMMIT}/isin_symbol_map.json"))
    map_new = json.loads(get(f"{RAW}/{LATEST_COMMIT}/isin_symbol_map.json"))
    missing = []
    for s in symbols:
        a, b = current_symbol(map_old, s), current_symbol(map_new, s)
        if not a or not b:
            missing.append(s)
            continue
        save(f"{s}.csv", fetch(urllib.parse.quote(a), urllib.parse.quote(b)))
    print(f"{len(symbols) - len(missing)} of {len(symbols)} ETF list files downloaded")
    if missing:
        print("not found:", ", ".join(missing))


if __name__ == "__main__":
    main()
