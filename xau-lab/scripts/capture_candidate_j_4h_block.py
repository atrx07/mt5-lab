"""Capture one prospective Candidate-J 4-hour scored block with causal warmup.

This is a READ-ONLY MT5 market-data collector. It NEVER sends broker orders.

At launch:
  1. fetch >=90 minutes of prior XAUUSD MT5 ticks as causal warmup context;
  2. verify the trailing quote continuity really spans the requested warmup;
  3. freeze the score-start boundary at the latest broker tick;
  4. capture exactly four wall-clock hours of NEW ticks;
  5. auto-stop and write immutable per-file hashes + manifest.

The warmup is context only. The score window begins at launch, so the user's
laptop only needs to remain on for the four-hour scored block.

Candidate D/H/J evaluation is intentionally offline after capture.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import live_shadow_candidate_j as shadow

SYMBOL = "XAUUSD"
DEFAULT_OUTPUT = ROOT / "data" / "prospective_4h"
DEFAULT_DIAG_OUTPUT = ROOT / "data" / "continuity_diagnostics"
EXPERIMENT_REF = "docs/experiments/2026-09-26/48-v4-5-candidate-j-fresh-validation.md"

RAW_COLUMNS = shadow.RAW_COLUMNS


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, payload: Dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def safety_scan_source() -> Dict:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute):
            name = fn.attr.lower()
            if name == "order_send" or name.startswith("trade_"):
                forbidden.append({"line": getattr(node, "lineno", None), "call": fn.attr})
    if forbidden:
        raise RuntimeError(f"forbidden broker execution call in capture script: {forbidden}")
    return {
        "status": "PASS",
        "forbidden_calls_found": 0,
        "policy": "read-only MT5 market-data capture only",
    }


def write_rows(path: Path, rows: List[Dict]) -> None:
    if not rows:
        return
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RAW_COLUMNS)
        if not exists:
            w.writeheader()
        for row in rows:
            w.writerow({k: row[k] for k in RAW_COLUMNS})


def public_rows(rows: List[Dict]) -> List[Dict]:
    return [shadow.public_row(x) for x in rows]


def reconstruct_exact_score_window(mt5, symbol: str, start_msc: int, end_msc: int, boundary_counts: Counter):
    """Re-read the frozen score interval from MT5 history before finalizing.

    This makes laptop suspend harmless: the score boundary never moves and any
    locally missed ticks are recovered from the same broker archive.
    """
    start_dt = datetime.fromtimestamp(start_msc / 1000.0, timezone.utc)
    end_dt = datetime.fromtimestamp(end_msc / 1000.0, timezone.utc)
    ticks = mt5.copy_ticks_range(
        symbol,
        start_dt,
        end_dt + timedelta(milliseconds=2),
        mt5.COPY_TICKS_ALL,
    )
    fetched = shadow.structured_ticks_to_rows(ticks)
    rows, _, _ = shadow.select_new_rows(fetched, start_msc, boundary_counts)
    return [x for x in rows if start_msc <= int(x["_time_msc"]) <= end_msc]


def trailing_continuity_minutes(rows: List[Dict]) -> float:
    if len(rows) < 2:
        return 0.0
    times = [int(x["_time_msc"]) for x in rows]
    last_gap_idx = 0
    for i in range(1, len(times)):
        if times[i] - times[i - 1] > 5000:
            last_gap_idx = i
    return max(0.0, (times[-1] - times[last_gap_idx]) / 60000.0)


def continuity_gap_rows(rows: List[Dict], threshold_sec: float = 5.0) -> List[Dict]:
    """Return every raw tick gap strictly larger than threshold_sec."""
    if len(rows) < 2:
        return []
    out: List[Dict] = []
    latest_msc = int(rows[-1]["_time_msc"])
    prev = rows[0]
    for row in rows[1:]:
        a = int(prev["_time_msc"])
        b = int(row["_time_msc"])
        gap_sec = max(0.0, (b - a) / 1000.0)
        if gap_sec > threshold_sec:
            out.append({
                "gap_start_utc": datetime.fromtimestamp(a / 1000.0, timezone.utc).isoformat(),
                "gap_end_utc": datetime.fromtimestamp(b / 1000.0, timezone.utc).isoformat(),
                "gap_sec": gap_sec,
                "minutes_before_latest": max(0.0, (latest_msc - b) / 60000.0),
                "classification": "SESSION_OR_OUTAGE" if gap_sec >= 60.0 else "CONTINUITY_RESET",
            })
        prev = row
    return out


def write_continuity_diagnostics(
    rows: List[Dict],
    *,
    output_root: Path,
    symbol: str,
    threshold_sec: float,
    required_minutes: float,
) -> Dict:
    """Persist an outcome-blind MT5 quote-continuity diagnostic."""
    output_root.mkdir(parents=True, exist_ok=True)
    latest_msc = int(rows[-1]["_time_msc"]) if rows else 0
    gaps = continuity_gap_rows(rows, threshold_sec)
    continuity_min = trailing_continuity_minutes(rows)
    remaining_min = max(0.0, required_minutes - continuity_min)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    csv_path = output_root / f"{symbol}_{stamp}_gaps.csv"
    json_path = output_root / f"{symbol}_{stamp}_summary.json"

    fields = [
        "gap_start_utc", "gap_end_utc", "gap_sec",
        "minutes_before_latest", "classification",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(gaps)

    last_gap = gaps[-1] if gaps else None
    summary = {
        "schema": "xau-continuity-diagnostic-v1",
        "symbol": symbol,
        "threshold_sec": threshold_sec,
        "required_continuity_minutes": required_minutes,
        "current_continuity_minutes": continuity_min,
        "remaining_minutes": remaining_min,
        "latest_tick_utc": (
            datetime.fromtimestamp(latest_msc / 1000.0, timezone.utc).isoformat()
            if latest_msc else None
        ),
        "rows_examined": len(rows),
        "gap_count": len(gaps),
        "last_gap": last_gap,
        "gaps_csv": str(csv_path),
    }
    atomic_json(json_path, summary)
    return {**summary, "summary_json": str(json_path), "gaps": gaps}


def print_continuity_diagnostics(diag: Dict, *, max_recent: int = 10) -> None:
    print()
    print("==========================================================")
    print(" XAUUSD QUOTE-CONTINUITY DIAGNOSTIC")
    print("==========================================================")
    print(f"Current continuity : {diag['current_continuity_minutes']:.2f} min")
    print(f"Still required     : {diag['remaining_minutes']:.2f} min")
    print(f">5s gaps examined  : {diag['gap_count']}")
    if diag.get("last_gap"):
        g = diag["last_gap"]
        print(
            f"Last >5s gap       : {g['gap_sec']:.3f}s "
            f"({g['minutes_before_latest']:.2f} min before latest tick)"
        )
        print(f"Gap interval       : {g['gap_start_utc']} -> {g['gap_end_utc']}")
        print(f"Gap class          : {g['classification']}")
    else:
        print("Last >5s gap       : none in diagnostic lookback")

    gaps = diag.get("gaps") or []
    if gaps:
        print()
        print(f"Recent >5s gaps (latest {min(max_recent, len(gaps))}):")
        for g in gaps[-max_recent:]:
            print(
                f"  {g['gap_sec']:8.3f}s | {g['gap_end_utc']} | "
                f"{g['minutes_before_latest']:.2f} min ago | {g['classification']}"
            )
    print()
    print("All gaps CSV       :", diag["gaps_csv"])
    print("Summary JSON       :", diag["summary_json"])


def max_tick_gap_sec(rows: List[Dict]) -> float:
    if len(rows) < 2:
        return 0.0
    times = [int(x["_time_msc"]) for x in rows]
    return max((times[i] - times[i - 1]) / 1000.0 for i in range(1, len(times)))


def gap_count(rows: List[Dict], threshold_sec: float = 5.0) -> int:
    if len(rows) < 2:
        return 0
    times = [int(x["_time_msc"]) for x in rows]
    return sum(1 for i in range(1, len(times)) if times[i] - times[i - 1] > threshold_sec * 1000.0)


def manifest_payload(
    *,
    args,
    session_id: str,
    session_dir: Path,
    warmup_path: Path,
    score_path: Path,
    score_start_host: datetime,
    score_start_msc: int,
    score_end_target_host: datetime,
    score_end_target_msc: int,
    complete: bool,
    stop_host: datetime | None,
    warmup_rows: int,
    score_rows: int,
    warmup_continuity_min: float,
    latest_score_tick_msc: int | None,
    score_max_gap_sec: float,
    score_gap_count_5s: int,
    host_runtime_sec: float,
    hash_files: bool,
) -> Dict:
    score_start_broker = datetime.fromtimestamp(score_start_msc / 1000.0, timezone.utc)
    score_end_target_broker = datetime.fromtimestamp(score_end_target_msc / 1000.0, timezone.utc)
    latest_score_tick = (
        datetime.fromtimestamp(latest_score_tick_msc / 1000.0, timezone.utc).isoformat()
        if latest_score_tick_msc is not None
        else None
    )
    return {
        "schema": "xau-candidate-j-prospective-4h-block-v1",
        "dataset_id": session_id,
        "symbol": args.symbol,
        "mode": "read-only prospective block capture",
        "used_by": [EXPERIMENT_REF],
        "candidate_j_frozen": True,
        "external_data_used": False,
        "score_contract": {
            "warmup_minutes_requested": args.warmup_minutes,
            "warmup_trailing_continuity_minutes": warmup_continuity_min,
            "warmup_is_context_only": True,
            "score_duration_hours_requested": args.duration_hours,
            "score_start_host_utc": score_start_host.isoformat(),
            "score_start_mt5_reported_utc": score_start_broker.isoformat(),
            "score_end_target_host_utc": score_end_target_host.isoformat(),
            "score_end_target_mt5_reported_utc": score_end_target_broker.isoformat(),
            "score_stop_host_utc": stop_host.isoformat() if stop_host else None,
            "host_runtime_sec": host_runtime_sec,
            "complete": bool(complete),
            "valid_for_stage1": bool(
                complete
                and warmup_continuity_min >= args.warmup_minutes
                and latest_score_tick_msc is not None
                and (score_end_target_msc - latest_score_tick_msc) / 1000.0 <= 5.0
            ),
        },
        "capture_quality": {
            "score_rows": score_rows,
            "score_max_raw_tick_gap_sec": score_max_gap_sec,
            "score_gap_count_gt_5s": score_gap_count_5s,
            "latest_score_tick_mt5_reported_utc": latest_score_tick,
            "note": "Raw gaps are preserved; no synthetic ticks are created.",
        },
        "warmup": {
            "path": str(warmup_path),
            "rows": warmup_rows,
            "sha256": sha256_file(warmup_path) if hash_files and warmup_path.exists() else None,
            "columns": RAW_COLUMNS,
        },
        "score": {
            "path": str(score_path),
            "rows": score_rows,
            "sha256": sha256_file(score_path) if hash_files and score_path.exists() else None,
            "columns": RAW_COLUMNS,
        },
        "safety": safety_scan_source(),
        "final20_opened": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default=SYMBOL)
    ap.add_argument("--warmup-minutes", type=float, default=90.0)
    ap.add_argument("--duration-hours", type=float, default=4.0)
    ap.add_argument("--poll-sec", type=float, default=0.25)
    ap.add_argument("--fetch-lookback-sec", type=float, default=120.0)
    ap.add_argument("--manifest-sec", type=float, default=60.0)
    ap.add_argument("--print-sec", type=float, default=10.0)
    ap.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--diagnostic-output-root", type=Path, default=DEFAULT_DIAG_OUTPUT)
    ap.add_argument("--diagnostic-hours", type=float, default=24.0)
    ap.add_argument("--continuity-gap-sec", type=float, default=5.0)
    ap.add_argument("--session-id")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        print(json.dumps({"status": "PASS", "safety": safety_scan_source()}, indent=2))
        return

    if args.warmup_minutes < 30:
        raise SystemExit("--warmup-minutes must be >= 30")
    if args.duration_hours <= 0:
        raise SystemExit("--duration-hours must be > 0")
    if args.poll_sec <= 0:
        raise SystemExit("--poll-sec must be > 0")
    if args.diagnostic_hours <= 0:
        raise SystemExit("--diagnostic-hours must be > 0")
    if args.continuity_gap_sec <= 0:
        raise SystemExit("--continuity-gap-sec must be > 0")

    safety_scan_source()
    mt5 = shadow.live_import_mt5()
    shadow.mt5_connect(mt5, args.symbol)

    score_start_host = datetime.now(timezone.utc)
    session_id = args.session_id or score_start_host.strftime("%Y%m%dT%H%M%SZ")
    session_dir = args.output_root / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    warmup_path = session_dir / "warmup_ticks.csv"
    score_path = session_dir / "score_ticks.csv"
    manifest_path = session_dir / "block_manifest.json"

    latest = mt5.symbol_info_tick(args.symbol)
    if latest is None or latest.time_msc <= 0:
        mt5.shutdown()
        raise RuntimeError(f"symbol_info_tick failed: {mt5.last_error()}")

    # Request extra margin so the trailing-continuity test can still find a
    # full 90-minute causal context if the exact boundary is sparse.
    broker_latest = datetime.fromtimestamp(float(latest.time_msc) / 1000.0, timezone.utc)
    request_start = broker_latest - timedelta(minutes=args.warmup_minutes + 10.0)
    request_end = broker_latest + timedelta(milliseconds=1)
    ticks = mt5.copy_ticks_range(args.symbol, request_start, request_end, mt5.COPY_TICKS_ALL)
    warmup_all = shadow.structured_ticks_to_rows(ticks)
    if len(warmup_all) < 2:
        mt5.shutdown()
        raise RuntimeError("MT5 did not provide enough warmup ticks")

    trailing_min = trailing_continuity_minutes(warmup_all)
    if trailing_min + 1e-9 < args.warmup_minutes:
        # Pull a longer, outcome-blind history window so the user can see
        # exactly which >5s quote gaps reset the warmup clock.
        diag_start = broker_latest - timedelta(hours=args.diagnostic_hours)
        diag_ticks = mt5.copy_ticks_range(
            args.symbol,
            diag_start,
            request_end,
            mt5.COPY_TICKS_ALL,
        )
        diag_rows = shadow.structured_ticks_to_rows(diag_ticks)
        diag = write_continuity_diagnostics(
            diag_rows,
            output_root=args.diagnostic_output_root,
            symbol=args.symbol,
            threshold_sec=args.continuity_gap_sec,
            required_minutes=args.warmup_minutes,
        )
        print_continuity_diagnostics(diag)
        mt5.shutdown()
        raise RuntimeError(
            f"Warmup continuity insufficient: {trailing_min:.2f} min available, "
            f"{args.warmup_minutes:.2f} min required. "
            f"Need about {max(0.0, args.warmup_minutes - trailing_min):.2f} more "
            f"uninterrupted minutes. See continuity diagnostic above."
        )

    score_start_msc = int(warmup_all[-1]["_time_msc"])
    context_cutoff = score_start_msc - int(args.warmup_minutes * 60_000)
    warmup = [x for x in warmup_all if int(x["_time_msc"]) >= context_cutoff]
    write_rows(warmup_path, public_rows(warmup))

    # Seed overlap-dedup state from the boundary millisecond.
    boundary_rows = [x for x in warmup_all if int(x["_time_msc"]) == score_start_msc]
    boundary_signature_counts = Counter(x["_signature"] for x in boundary_rows)
    last_signature_counts = Counter(boundary_signature_counts)
    last_time_msc = score_start_msc

    duration_sec = args.duration_hours * 3600.0
    start_mono = time.monotonic()
    end_mono = start_mono + duration_sec
    score_end_target_host = score_start_host + timedelta(seconds=duration_sec)
    score_end_target_msc = score_start_msc + int(duration_sec * 1000.0)

    score_rows_all: List[Dict] = []
    score_rows = 0
    latest_score_tick_msc: int | None = None
    last_manifest = 0.0
    last_print = 0.0
    complete = False

    print("==========================================================")
    print(" CANDIDATE J PROSPECTIVE 4H BLOCK — READ ONLY")
    print("==========================================================")
    print("NO REAL ORDERS.")
    print(f"Warmup backfill: PASS ({trailing_min:.1f} min causal continuity)")
    print("Warmup is context only; scoring starts NOW.")
    print("Session:", session_id)
    print("Output :", session_dir.resolve())
    print(f"Auto-stop after {args.duration_hours:.2f} wall-clock hours.")
    print("You can stop the older 90-minute shadow process; this block is independently warmed.")

    try:
        while True:
            now_mono = time.monotonic()
            if now_mono >= end_mono:
                # Finalize from the exact frozen MT5 interval before declaring
                # success. This recovers ticks missed while Windows was asleep.
                recovered = reconstruct_exact_score_window(
                    mt5,
                    args.symbol,
                    score_start_msc,
                    score_end_target_msc,
                    boundary_signature_counts,
                )
                if recovered:
                    write_rows_tmp = score_path.with_suffix(".csv.tmp")
                    with write_rows_tmp.open("w", newline="", encoding="utf-8") as fh:
                        w = csv.DictWriter(fh, fieldnames=RAW_COLUMNS)
                        w.writeheader()
                        for row in public_rows(recovered):
                            w.writerow({k: row[k] for k in RAW_COLUMNS})
                    os.replace(write_rows_tmp, score_path)
                    score_rows_all = recovered
                    score_rows = len(recovered)
                    latest_score_tick_msc = max(int(x["_time_msc"]) for x in recovered)
                complete = bool(
                    latest_score_tick_msc is not None
                    and (score_end_target_msc - latest_score_tick_msc) / 1000.0 <= 5.0
                )
                break

            latest = mt5.symbol_info_tick(args.symbol)
            if latest is None or latest.time_msc <= 0:
                time.sleep(args.poll_sec)
                continue

            broker_now = datetime.fromtimestamp(float(latest.time_msc) / 1000.0, timezone.utc)
            fetch_start = datetime.fromtimestamp(
                max(0.0, last_time_msc / 1000.0 - args.fetch_lookback_sec),
                timezone.utc,
            )
            fetch_end = broker_now + timedelta(milliseconds=1)
            ticks = mt5.copy_ticks_range(args.symbol, fetch_start, fetch_end, mt5.COPY_TICKS_ALL)
            fetched = shadow.structured_ticks_to_rows(ticks)
            new_rows, new_last_msc, new_counts = shadow.select_new_rows(
                fetched, last_time_msc, last_signature_counts
            )

            # Score window is strictly after the frozen launch boundary.
            new_rows = [x for x in new_rows if int(x["_time_msc"]) >= score_start_msc]
            if new_rows:
                public = public_rows(new_rows)
                write_rows(score_path, public)
                score_rows_all.extend(new_rows)
                score_rows += len(new_rows)
                latest_score_tick_msc = max(int(x["_time_msc"]) for x in new_rows)
                last_time_msc = new_last_msc
                last_signature_counts = new_counts

            elapsed = now_mono - start_mono
            remaining = max(0.0, end_mono - now_mono)

            if now_mono - last_manifest >= args.manifest_sec:
                payload = manifest_payload(
                    args=args,
                    session_id=session_id,
                    session_dir=session_dir,
                    warmup_path=warmup_path,
                    score_path=score_path,
                    score_start_host=score_start_host,
                    score_start_msc=score_start_msc,
                    score_end_target_host=score_end_target_host,
                    score_end_target_msc=score_end_target_msc,
                    complete=False,
                    stop_host=None,
                    warmup_rows=len(warmup),
                    score_rows=score_rows,
                    warmup_continuity_min=trailing_min,
                    latest_score_tick_msc=latest_score_tick_msc,
                    score_max_gap_sec=max_tick_gap_sec(score_rows_all),
                    score_gap_count_5s=gap_count(score_rows_all, 5.0),
                    host_runtime_sec=elapsed,
                    hash_files=False,
                )
                atomic_json(manifest_path, payload)
                last_manifest = now_mono

            if now_mono - last_print >= args.print_sec:
                last_age = (
                    max(0.0, float(latest.time_msc - latest_score_tick_msc) / 1000.0)
                    if latest_score_tick_msc is not None
                    else float("nan")
                )
                print(
                    f"{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z | "
                    f"elapsed={elapsed/3600:.2f}h | remaining={remaining/3600:.2f}h | "
                    f"score_ticks={score_rows:,} | latest_age={last_age:.1f}s"
                )
                last_print = now_mono

            time.sleep(args.poll_sec)

    except KeyboardInterrupt:
        print("\nStopped early by user. This block will be marked INCOMPLETE.")
    finally:
        stop_host = datetime.now(timezone.utc)
        runtime = time.monotonic() - start_mono
        payload = manifest_payload(
            args=args,
            session_id=session_id,
            session_dir=session_dir,
            warmup_path=warmup_path,
            score_path=score_path,
            score_start_host=score_start_host,
            score_start_msc=score_start_msc,
            score_end_target_host=score_end_target_host,
            score_end_target_msc=score_end_target_msc,
            complete=complete,
            stop_host=stop_host,
            warmup_rows=len(warmup),
            score_rows=score_rows,
            warmup_continuity_min=trailing_min,
            latest_score_tick_msc=latest_score_tick_msc,
            score_max_gap_sec=max_tick_gap_sec(score_rows_all),
            score_gap_count_5s=gap_count(score_rows_all, 5.0),
            host_runtime_sec=runtime,
            hash_files=True,
        )
        atomic_json(manifest_path, payload)
        mt5.shutdown()

    print()
    print("Block status:", "COMPLETE ✅" if complete else "INCOMPLETE")
    print("Warmup :", warmup_path.resolve())
    print("Score  :", score_path.resolve())
    print("Manifest:", manifest_path.resolve())


if __name__ == "__main__":
    main()
