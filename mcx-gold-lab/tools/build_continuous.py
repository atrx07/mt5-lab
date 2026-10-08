#!/usr/bin/env python3
"""Build a continuous daily series from curated MCX bhavcopy archives.

Input : data/raw/gold_<contract>_bhavcopy_<range>.csv.gz  (one row per
        contract-day: date, contract, open, high, low, close, volume, oi)
Output: data/raw/gold_<contract>_continuous_<range>.csv.gz
        (columns: date, open, high, low, close, volume, oi, contract, rolled,
         limit_day)

Method: for each date keep the NEAREST-expiry contract with volume > 0
(front-month rule). `rolled` marks the first bar of a new contract.
`limit_day` marks |close - prev_close|/prev_close >= 9% or high == low.

Rollover in the harness closes at old close and reopens at new open, paying
both legs — the roll cost is explicit, never smoothed away.

Usage:
  python tools/build_continuous.py data/raw/gold_GOLDPETAL_bhavcopy_*.csv.gz
"""

import csv
import gzip
import hashlib
import json
import os
import sys
from datetime import datetime


def parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d", "%d%b%Y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"unparseable date: {s!r}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src = sys.argv[1]
    rows = []
    opener = gzip.open if src.endswith(".gz") else open
    with opener(src, "rt") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    # normalize
    norm = []
    for r in rows:
        try:
            norm.append(dict(
                date=parse_dt(r["date"]).strftime("%Y-%m-%d"),
                contract=r["contract"].strip(),
                expiry=parse_dt(r.get("expiry", r["date"])),
                open=float(r["open"]), high=float(r["high"]),
                low=float(r["low"]), close=float(r["close"]),
                volume=int(float(r.get("volume", 0) or 0)),
                oi=int(float(r.get("oi", 0) or 0)),
            ))
        except (KeyError, ValueError) as e:
            print(f"  skip row ({e}): {r}")
    # front-month per date: nearest expiry with volume > 0
    by_date: dict[str, list] = {}
    for r in norm:
        by_date.setdefault(r["date"], []).append(r)
    series = []
    for date in sorted(by_date):
        cands = [r for r in by_date[date] if r["volume"] > 0] or by_date[date]
        pick = min(cands, key=lambda r: r["expiry"])
        series.append(pick)

    out_rows = []
    prev_expiry, prev_close = None, None
    for r in series:
        rolled = prev_expiry is not None and r["expiry"] != prev_expiry
        limit = False
        if prev_close:
            chg = abs(r["close"] - prev_close) / prev_close
            limit = chg >= 0.09 or r["high"] == r["low"]
        out_rows.append(dict(date=r["date"], open=r["open"], high=r["high"],
                             low=r["low"], close=r["close"], volume=r["volume"],
                             oi=r["oi"], contract=r["contract"],
                             expiry=r["expiry"].strftime("%d%b%Y").upper(),
                             rolled=int(rolled), limit_day=int(limit)))
        prev_expiry, prev_close = r["expiry"], r["close"]

    base = os.path.basename(src)
    name = base.replace("_bhavcopy_", "_continuous_").replace(".csv.gz", ".csv")
    if "_bhavcopy_" not in base:
        name = base.replace(".csv.gz", "_continuous.csv").replace(".csv", "_continuous.csv")
    out_path = os.path.join(os.path.dirname(src), name + ".gz")
    with gzip.open(out_path, "wt") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    sha = hashlib.sha256(open(out_path, "rb").read()).hexdigest()
    manifest = dict(schema="mcx-continuous-v1", instrument="GOLD",
                    source="MCX bhavcopy curation", input=src, output=out_path,
                    sha256=sha, bars=len(out_rows),
                    first=out_rows[0]["date"], last=out_rows[-1]["date"],
                    rolls=sum(r["rolled"] for r in out_rows),
                    limit_days=sum(r["limit_day"] for r in out_rows))
    mp = out_path.replace("raw/", "manifests/").replace(".csv.gz", ".json")
    os.makedirs(os.path.dirname(mp), exist_ok=True)
    json.dump(manifest, open(mp, "w"), indent=2)
    print(f"continuous series: {len(out_rows)} bars, "
          f"{manifest['rolls']} rolls, {manifest['limit_days']} limit days")
    print(f"  -> {out_path}\n  -> {mp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
