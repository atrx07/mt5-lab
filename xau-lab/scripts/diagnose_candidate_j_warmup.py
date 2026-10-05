"""Read-only diagnostic for Candidate-J 4h-block warmup readiness.

Runs independently of the scorer so even very-early failures (for example,
MT5 returning fewer than two warmup ticks) still produce useful diagnostics.
No broker orders are sent.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import live_shadow_candidate_j as shadow


def trailing_continuity_minutes(rows, gap_sec: float) -> float:
    if len(rows) < 2:
        return 0.0
    times = [int(x["_time_msc"]) for x in rows]
    last_gap_idx = 0
    for i in range(1, len(times)):
        if (times[i] - times[i - 1]) / 1000.0 > gap_sec:
            last_gap_idx = i
    return max(0.0, (times[-1] - times[last_gap_idx]) / 60000.0)


def gaps(rows, threshold_sec: float):
    out = []
    if len(rows) < 2:
        return out
    latest = int(rows[-1]["_time_msc"])
    prev = rows[0]
    for row in rows[1:]:
        a = int(prev["_time_msc"])
        b = int(row["_time_msc"])
        dt = max(0.0, (b - a) / 1000.0)
        if dt > threshold_sec:
            out.append({
                "gap_start_utc": datetime.fromtimestamp(a / 1000.0, timezone.utc).isoformat(),
                "gap_end_utc": datetime.fromtimestamp(b / 1000.0, timezone.utc).isoformat(),
                "gap_sec": dt,
                "minutes_before_latest": max(0.0, (latest - b) / 60000.0),
                "classification": "SESSION_OR_OUTAGE" if dt >= 60.0 else "CONTINUITY_RESET",
            })
        prev = row
    return out


def count_since(rows, latest_msc: int, minutes: float) -> int:
    cutoff = latest_msc - int(minutes * 60_000)
    return sum(int(x["_time_msc"]) >= cutoff for x in rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="XAUUSD")
    ap.add_argument("--required-minutes", type=float, default=90.0)
    ap.add_argument("--lookback-hours", type=float, default=24.0)
    ap.add_argument("--gap-sec", type=float, default=5.0)
    args = ap.parse_args()

    mt5 = shadow.live_import_mt5()
    shadow.mt5_connect(mt5, args.symbol)
    try:
        tick = mt5.symbol_info_tick(args.symbol)
        if tick is None or tick.time_msc <= 0:
            raise RuntimeError(f"symbol_info_tick failed: {mt5.last_error()}")

        latest_msc = int(tick.time_msc)
        latest_dt = datetime.fromtimestamp(latest_msc / 1000.0, timezone.utc)
        start_dt = latest_dt - timedelta(hours=args.lookback_hours)
        arr = mt5.copy_ticks_range(
            args.symbol,
            start_dt,
            latest_dt + timedelta(milliseconds=1),
            mt5.COPY_TICKS_ALL,
        )
        rows = shadow.structured_ticks_to_rows(arr)
    finally:
        mt5.shutdown()

    gs = gaps(rows, args.gap_sec)
    cont = trailing_continuity_minutes(rows, args.gap_sec)
    remaining = max(0.0, args.required_minutes - cont)

    print()
    print("==========================================================")
    print(" XAUUSD WARMUP READINESS DIAGNOSTIC")
    print("==========================================================")
    print(f"Latest MT5 tick    : {latest_dt.isoformat()}")
    print(f"24h ticks returned : {len(rows):,}")

    if rows:
        print(f"Ticks last 10 min  : {count_since(rows, latest_msc, 10):,}")
        print(f"Ticks last 30 min  : {count_since(rows, latest_msc, 30):,}")
        print(f"Ticks last 90 min  : {count_since(rows, latest_msc, 90):,}")
    else:
        print("Ticks last 10 min  : 0")
        print("Ticks last 30 min  : 0")
        print("Ticks last 90 min  : 0")

    print(f"Current continuity : {cont:.2f} min")
    print(f"Still required     : {remaining:.2f} min")
    print(f">{args.gap_sec:g}s gaps          : {len(gs)}")

    if len(rows) < 2:
        print()
        print("Diagnosis           : MT5 returned fewer than two historical ticks in the")
        print("                      diagnostic window. This usually means the symbol has")
        print("                      only just resumed quoting, the broker history cache")
        print("                      has not populated yet, or the feed/session is inactive.")
    elif gs:
        g = gs[-1]
        print(f"Last >{args.gap_sec:g}s gap       : {g['gap_sec']:.3f}s ({g['minutes_before_latest']:.2f} min ago)")
        print(f"Gap interval        : {g['gap_start_utc']} -> {g['gap_end_utc']}")
        print(f"Gap class           : {g['classification']}")
        print()
        print(f"Recent >{args.gap_sec:g}s gaps:")
        for g in gs[-10:]:
            print(
                f"  {g['gap_sec']:8.3f}s | {g['gap_end_utc']} | "
                f"{g['minutes_before_latest']:.2f} min ago | {g['classification']}"
            )
    else:
        print(f"Last >{args.gap_sec:g}s gap       : none in lookback")

    if cont >= args.required_minutes:
        print("\nWarmup readiness   : PASS")
    else:
        print(f"\nWarmup readiness   : WAIT ~{remaining:.2f} more uninterrupted min")


if __name__ == "__main__":
    main()
