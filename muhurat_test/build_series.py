"""Build data/nifty_combined.csv (columns: date, close) from the files you downloaded.

Usage:  python3 build_series.py data

Reads every .csv file in the folder you give it and recognises two layouts by their header:
  1. niftyindices.com files (columns: Index Name, Date, Open, High, Low, Close; dates like "31 Dec 2004").
     The file name does not matter.
  2. The eod2_data file "nifty 50.csv" (columns: Date, Open, High, Low, Close, ...; dates like 2012-02-21).
     Used only for dates that the niftyindices files do not cover.

If a date is in both, the niftyindices value is used.
"""
import csv, datetime as dt, glob, os, sys

OUTPUT = "nifty_combined.csv"


def read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        head = [h.strip().strip('"') for h in (reader.fieldnames or [])]
        rows = [{(k or "").strip().strip('"'): (v or "").strip() for k, v in r.items()} for r in reader]
    return head, rows


def main(folder):
    nse, eod2 = {}, {}
    for path in sorted(glob.glob(os.path.join(folder, "*.csv"))):
        name = os.path.basename(path)
        if name.lower() == OUTPUT:
            continue
        head, rows = read_rows(path)
        if "Index Name" in head and "Date" in head and "Close" in head:
            n = 0
            for r in rows:
                if not r["Date"]:
                    continue
                day = dt.datetime.strptime(r["Date"], "%d %b %Y").date()
                nse[day] = float(r["Close"]); n += 1
            print(f"niftyindices file: {name} ({n} days)")
        elif "Date" in head and "Close" in head:
            n = 0
            for r in rows:
                if not r["Date"]:
                    continue
                eod2[dt.date.fromisoformat(r["Date"])] = float(r["Close"]); n += 1
            print(f"eod2 file: {name} ({n} days)")
        else:
            print(f"skipped (not a price file): {name}")

    if not nse:
        print("WARNING: no niftyindices files were recognised in", folder)
    rows = dict(eod2)
    rows.update(nse)          # niftyindices wins when both have a date
    if not rows:
        sys.exit(f"No data found in {folder}. See README.md, step 1.")

    days = sorted(rows)
    out = os.path.join(folder, OUTPUT)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "close"])
        for d in days:
            w.writerow([d.isoformat(), rows[d]])
    print(f"wrote {out}: {len(days)} days, {days[0]} to {days[-1]}")

    for a, b in zip(days, days[1:]):
        if (b - a).days > 5:
            print(f"WARNING: gap of {(b - a).days} days between {a} and {b}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 build_series.py data")
    main(sys.argv[1])