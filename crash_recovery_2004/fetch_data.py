"""Download the Nifty 50 daily file from EOD2 (Feb 2012 onward), pinned to a fixed commit so results reproduce.

  python fetch_data.py

Saves to data/nifty 50.csv.

The 2003-2011 closes are not in that file. Download them from niftyindices.com
(Historical Data > Nifty 50 > Price Return, one CSV per year) and save them in data/
under their original names (NIFTY_50_Historical_PR_*.csv). See README.md.
"""
import os
import urllib.parse
import urllib.request

COMMIT = "04c645452ff4a214e3666fc265fdc3a56a5831c4"  # BennyThadikaran/eod2_data, prices to 23 Oct 2026
NAME = "nifty 50.csv"

os.makedirs("data", exist_ok=True)
url = f"https://raw.githubusercontent.com/BennyThadikaran/eod2_data/{COMMIT}/daily/{urllib.parse.quote(NAME)}"
dest = os.path.join("data", NAME)
urllib.request.urlretrieve(url, dest)
print("saved", dest)
