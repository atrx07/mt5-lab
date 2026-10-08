#!/usr/bin/env python3
"""Fetch MCX bhavcopy (daily OHLCV+OI) via the official JSON endpoint.

Endpoint: GET https://www.mcxindia.com/market-data/bhavcopy/GetCommoditywiseBhavCopy
Params  : Symbol, Expiry (e.g. 30NOV2026), FromDate/ToDate (dd/mm/yyyy),
          InstrumentName=FUTCOM

Critical: MCX sits behind Akamai bot protection. A bare script UA gets
HTTP 403 "Access Denied". A full browser header profile (below) gets
HTTP 200. If Akamai starts refusing again, fall back to the live-browser
route documented in docs/plans/00-lab-bootstrap.md Phase 1.

GOLDPETAL expiries are month-end (31OCT2026, 30NOV2026, ...); GOLD (1 kg)
expiries are on the 5th (05DEC2026, 05FEB2027, ...).

Usage:
  python tools/fetch_bhavcopy.py --symbol GOLDPETAL --from 08/10/2025 --to 07/10/2026
  python tools/fetch_bhavcopy.py --symbol GOLDGUINEA --from 08/10/2025 --to 07/10/2026

Output: data/raw/bhavcopy_<SYMBOL>_<from>_<to>.json  (raw endpoint responses)
Then curate with tools/curate_bhavcopy.py into the canonical CSV.
"""

import argparse
import calendar
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date

BASE = "https://www.mcxindia.com/market-data/bhavcopy/GetCommoditywiseBhavCopy"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.mcxindia.com/market-data/bhavcopy",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def month_end_expiries(from_y: int, from_m: int, to_y: int, to_m: int) -> list[str]:
    """Expiry strings like 31OCT2026 for month-end contracts (Petal/Guinea)."""
    out, y, m = [], from_y, from_m
    while (y, m) <= (to_y, to_m):
        last = calendar.monthrange(y, m)[1]
        out.append(f"{last:02d}{MONTHS[m-1]}{y}")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def fetch(symbol: str, expiry: str, fr: str, to: str) -> list[dict]:
    params = urllib.parse.urlencode({
        "Symbol": symbol, "Expiry": expiry,
        "FromDate": fr, "ToDate": to, "InstrumentName": "FUTCOM"})
    req = urllib.request.Request(BASE + "?" + params, headers=HEADERS)
    raw = urllib.request.urlopen(req, timeout=30).read()
    data = json.loads(raw)
    return data.get("Data") or []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--from", dest="fr", required=True, help="dd/mm/yyyy")
    ap.add_argument("--to", dest="to", required=True, help="dd/mm/yyyy")
    ap.add_argument("--sleep", type=float, default=1.0)
    a = ap.parse_args()

    fd = tuple(int(x) for x in a.fr.split("/")[::-1])  # yyyy, mm, dd
    td = tuple(int(x) for x in a.to.split("/")[::-1])
    expiries = month_end_expiries(fd[0], fd[1], td[0], td[1])

    all_rows: dict[str, dict] = {}
    for exp in expiries:
        try:
            rows = fetch(a.symbol, exp, a.fr, a.to)
        except Exception as e:
            print(f"  {exp}: FAILED {type(e).__name__} {str(e)[:100]}")
            time.sleep(a.sleep)
            continue
        print(f"  {exp}: {len(rows)} rows")
        for r in rows:
            key = (r.get("DateDisplay"), r.get("ExpiryDate"))
            all_rows[key] = r
        time.sleep(a.sleep)

    rows = sorted(all_rows.values(), key=lambda r: (r.get("DateDisplay"), r.get("ExpiryDate")))
    tag = f"{a.fr.replace('/', '')}_{a.to.replace('/', '')}"
    out = f"data/raw/bhavcopy_{a.symbol}_{tag}.json"
    os.makedirs("data/raw", exist_ok=True)
    with open(out, "w") as f:
        json.dump(rows, f)
    print(f"total unique rows: {len(rows)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
