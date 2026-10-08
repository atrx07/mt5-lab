#!/usr/bin/env python3
"""Curate raw MCX bhavcopy JSON into the canonical lab CSV.

Input : data/raw/bhavcopy_<SYMBOL>_<range>.json  (raw endpoint responses)
Output: data/raw/gold_<symbol>_bhavcopy_<first>_<last>.csv.gz
        + data/manifests/gold_<symbol>_bhavcopy_<first>_<last>.json

Canonical columns: date, contract, expiry, open, high, low, close,
                   prev_close, volume, oi
Prices: Rs per gram for GOLDPETAL; Rs per 8 g contract for GOLDGUINEA
        (see contract notes; per-gram normalization happens in analysis).

Usage:
  python tools/curate_bhavcopy.py data/raw/bhavcopy_GOLDPETAL_08102025_07102026.json
"""

import csv
import gzip
import hashlib
import json
import os
import sys
from datetime import datetime


def parse_dt(s: str) -> str:
    return datetime.strptime(s.strip(), "%d %b %Y").strftime("%Y-%m-%d")


def main() -> int:
    src = sys.argv[1]
    rows = json.load(open(src))
    sym = os.path.basename(src).split("_")[1]

    out_rows = []
    for r in rows:
        try:
            out_rows.append(dict(
                date=parse_dt(r["DateDisplay"]),
                contract=r["Symbol"].strip(),
                expiry=r["ExpiryDate"].strip(),
                open=float(r["Open"]), high=float(r["High"]),
                low=float(r["Low"]), close=float(r["Close"]),
                prev_close=float(r.get("PreviousClose") or 0),
                volume=int(float(r.get("Volume") or 0)),
                oi=int(float(r.get("OpenInterest") or 0)),
            ))
        except (KeyError, ValueError, TypeError) as e:
            print(f"  skip ({e}): {str(r)[:120]}")
    out_rows.sort(key=lambda r: (r["date"], r["expiry"]))
    # dedupe
    seen, clean = set(), []
    for r in out_rows:
        k = (r["date"], r["contract"], r["expiry"])
        if k not in seen:
            seen.add(k)
            clean.append(r)

    first, last = clean[0]["date"], clean[-1]["date"]
    out = f"data/raw/gold_{sym}_bhavcopy_{first}_{last}.csv.gz"
    with gzip.open(out, "wt") as f:
        w = csv.DictWriter(f, fieldnames=list(clean[0].keys()))
        w.writeheader()
        w.writerows(clean)

    sha = hashlib.sha256(open(out, "rb").read()).hexdigest()
    manifest = dict(
        schema="mcx-bhavcopy-v1", instrument="GOLD", contract_symbol=sym,
        source="MCX official bhavcopy endpoint "
               "(GET /market-data/bhavcopy/GetCommoditywiseBhavCopy), "
               "browser header profile (Akamai bypass)",
        input=src, input_rows=len(rows), output=out, output_rows=len(clean),
        sha256=sha, first=first, last=last,
        unique_dates=len({r["date"] for r in clean}),
        provenance="Public exchange data. Daily bars only — no bid/ask, no "
                   "intraday path. Valid for daily-bar experiments and pipeline "
                   "validation; NOT valid for tick-level strategy research.",
    )
    mp = out.replace("data/raw/", "data/manifests/").replace(".csv.gz", ".json")
    json.dump(manifest, open(mp, "w"), indent=2)
    print(f"{sym}: {len(clean)} rows, {manifest['unique_dates']} dates, {first}..{last}")
    print(f"  -> {out}\n  -> {mp}")
    # latest close for cost-model calibration:
    latest = max(clean, key=lambda r: r["date"])
    print(f"  latest close: {latest['close']} on {latest['date']} ({latest['expiry']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
