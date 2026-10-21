"""Download the two EOD2 files this test uses, pinned to a fixed commit so results reproduce.

  python fetch_eod2.py

Saves to data/eod2/.
"""
import os
import urllib.parse
import urllib.request

COMMIT = "50b71b70235ec1ffae802e410f34e1c7f0a571fe"  # BennyThadikaran/eod2_data, 14 Oct 2026
FILES = ["nifty 50.csv", "nifty 1d rate index.csv"]
OUT = os.path.join("data", "eod2")

os.makedirs(OUT, exist_ok=True)
for name in FILES:
    url = f"https://raw.githubusercontent.com/BennyThadikaran/eod2_data/{COMMIT}/daily/{urllib.parse.quote(name)}"
    dest = os.path.join(OUT, name)
    urllib.request.urlretrieve(url, dest)
    print("saved", dest)
