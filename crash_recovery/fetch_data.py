"""Download the Nifty 50 daily file from EOD2, pinned to a fixed commit so results reproduce.

  python fetch_data.py

Saves to data/nifty 50.csv.
"""
import os
import urllib.parse
import urllib.request

COMMIT = "50b71b70235ec1ffae802e410f34e1c7f0a571fe"  # BennyThadikaran/eod2_data, 14 Oct 2026
NAME = "nifty 50.csv"

os.makedirs("data", exist_ok=True)
url = f"https://raw.githubusercontent.com/BennyThadikaran/eod2_data/{COMMIT}/daily/{urllib.parse.quote(NAME)}"
dest = os.path.join("data", NAME)
urllib.request.urlretrieve(url, dest)
print("saved", dest)
