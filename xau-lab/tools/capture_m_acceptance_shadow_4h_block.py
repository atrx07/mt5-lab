"""Capture one fresh 4-hour XAUUSD block for Experiment 58 acceptance discrimination.

READ ONLY. This script never sends broker orders and never evaluates strategy P&L.
It reuses the already battle-tested Candidate-J capture mechanics for continuity,
deduplication and exact MT5-history reconstruction, but writes an Experiment-58
manifest and a separate prospective dataset root.
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import capture_candidate_j_4h_block as capture_base
import live_shadow_candidate_j as shadow

SYMBOL = "XAUUSD"
DEFAULT_OUTPUT = ROOT / "data" / "prospective_m_acceptance_shadow"
DEFAULT_DIAG_OUTPUT = ROOT / "data" / "continuity_diagnostics"
EXPERIMENT_REF = "docs/experiments/2026-10-07/58-v4-5-m-acceptance-discrimination-shadow.md"
PLAN_REF = "docs/plans/V4_5_M_ACCEPTANCE_DISCRIMINATION_SHADOW.md"
RAW_COLUMNS = shadow.RAW_COLUMNS


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


def manifest_payload(
    *, args, session_id: str, warmup_path: Path, score_path: Path,
    score_start_host: datetime, score_start_msc: int,
    score_end_target_host: datetime, score_end_target_msc: int,
    complete: bool, stop_host: datetime | None, warmup_rows: int,
    score_rows: int, warmup_continuity_min: float,
    latest_score_tick_msc: int | None, score_rows_all: List[Dict],
    host_runtime_sec: float, hash_files: bool,
) -> Dict:
    score_start_broker = datetime.fromtimestamp(score_start_msc / 1000.0, timezone.utc)
    score_end_target_broker = datetime.fromtimestamp(score_end_target_msc / 1000.0, timezone.utc)
    latest_score_tick = (
        datetime.fromtimestamp(latest_score_tick_msc / 1000.0, timezone.utc).isoformat()
        if latest_score_tick_msc is not None else None
    )
    return {
        "schema": "xau-exp58-m-acceptance-shadow-block-v1",
        "dataset_id": session_id,
        "symbol": args.symbol,
        "mode": "read-only prospective discrimination capture",
        "used_by": [EXPERIMENT_REF, PLAN_REF],
        "candidate_m_reference_frozen": True,
        "candidate_m_reference": "Experiment 53 / frozen Candidate M",
        "strategy_pnl_evaluated_during_capture": False,
        "external_data_used": False,
        "final20_opened": False,
        "capture_mechanics_reused_from": "scripts/capture_candidate_j_4h_block.py",
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
            "valid_for_experiment58": bool(
                complete
                and warmup_continuity_min >= args.warmup_minutes
                and latest_score_tick_msc is not None
                and (score_end_target_msc - latest_score_tick_msc) / 1000.0 <= 5.0
            ),
        },
        "capture_quality": {
            "score_rows": score_rows,
            "score_max_raw_tick_gap_sec": capture_base.max_tick_gap_sec(score_rows_all),
            "score_gap_count_gt_5s": capture_base.gap_count(score_rows_all, 5.0),
            "latest_score_tick_mt5_reported_utc": latest_score_tick,
            "note": "Raw gaps are preserved. No synthetic ticks are created.",
        },
        "warmup": {
            "path": str(warmup_path), "rows": warmup_rows,
            "sha256": capture_base.sha256_file(warmup_path) if hash_files and warmup_path.exists() else None,
            "columns": RAW_COLUMNS,
        },
        "score": {
            "path": str(score_path), "rows": score_rows,
            "sha256": capture_base.sha256_file(score_path) if hash_files and score_path.exists() else None,
            "columns": RAW_COLUMNS,
        },
        "safety": safety_scan_source(),
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
    if args.duration_hours <= 0 or args.poll_sec <= 0:
        raise SystemExit("duration and poll interval must be positive")

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
        mt5.shutdown(); raise RuntimeError(f"symbol_info_tick failed: {mt5.last_error()}")

    broker_latest = datetime.fromtimestamp(float(latest.time_msc) / 1000.0, timezone.utc)
    request_start = broker_latest - timedelta(minutes=args.warmup_minutes + 10.0)
    request_end = broker_latest + timedelta(milliseconds=1)
    ticks = mt5.copy_ticks_range(args.symbol, request_start, request_end, mt5.COPY_TICKS_ALL)
    warmup_all = shadow.structured_ticks_to_rows(ticks)
    if len(warmup_all) < 2:
        mt5.shutdown(); raise RuntimeError("MT5 did not provide enough warmup ticks")

    trailing_min = capture_base.trailing_continuity_minutes(warmup_all)
    if trailing_min + 1e-9 < args.warmup_minutes:
        diag_ticks = mt5.copy_ticks_range(
            args.symbol, broker_latest - timedelta(hours=args.diagnostic_hours),
            request_end, mt5.COPY_TICKS_ALL,
        )
        diag = capture_base.write_continuity_diagnostics(
            shadow.structured_ticks_to_rows(diag_ticks),
            output_root=args.diagnostic_output_root, symbol=args.symbol,
            threshold_sec=args.continuity_gap_sec, required_minutes=args.warmup_minutes,
        )
        capture_base.print_continuity_diagnostics(diag)
        mt5.shutdown()
        raise RuntimeError(
            f"Warmup continuity insufficient: {trailing_min:.2f} min available, "
            f"{args.warmup_minutes:.2f} min required"
        )

    score_start_msc = int(warmup_all[-1]["_time_msc"])
    context_cutoff = score_start_msc - int(args.warmup_minutes * 60_000)
    warmup = [x for x in warmup_all if int(x["_time_msc"]) >= context_cutoff]
    capture_base.write_rows(warmup_path, capture_base.public_rows(warmup))

    boundary_rows = [x for x in warmup_all if int(x["_time_msc"]) == score_start_msc]
    boundary_signature_counts = Counter(x["_signature"] for x in boundary_rows)
    last_signature_counts = Counter(boundary_signature_counts)
    last_time_msc = score_start_msc

    duration_sec = args.duration_hours * 3600.0
    start_mono = time.monotonic(); end_mono = start_mono + duration_sec
    score_end_target_host = score_start_host + timedelta(seconds=duration_sec)
    score_end_target_msc = score_start_msc + int(duration_sec * 1000.0)
    score_rows_all: List[Dict] = []; score_rows = 0; latest_score_tick_msc: int | None = None
    last_manifest = last_print = 0.0; complete = False

    print("==========================================================")
    print(" EXPERIMENT 58 — M ACCEPTANCE SHADOW CAPTURE — READ ONLY")
    print("==========================================================")
    print("NO REAL ORDERS. NO STRATEGY P&L DURING CAPTURE.")
    print(f"Warmup continuity: PASS ({trailing_min:.1f} min)")
    print("Session:", session_id); print("Output :", session_dir.resolve())

    try:
        while True:
            now_mono = time.monotonic()
            if now_mono >= end_mono:
                recovered = capture_base.reconstruct_exact_score_window(
                    mt5, args.symbol, score_start_msc, score_end_target_msc, boundary_signature_counts,
                )
                if recovered:
                    tmp = score_path.with_suffix(".csv.tmp")
                    with tmp.open("w", newline="", encoding="utf-8") as fh:
                        w = csv.DictWriter(fh, fieldnames=RAW_COLUMNS); w.writeheader()
                        for row in capture_base.public_rows(recovered):
                            w.writerow({k: row[k] for k in RAW_COLUMNS})
                    os.replace(tmp, score_path)
                    score_rows_all = recovered; score_rows = len(recovered)
                    latest_score_tick_msc = max(int(x["_time_msc"]) for x in recovered)
                complete = bool(latest_score_tick_msc is not None and (score_end_target_msc - latest_score_tick_msc) / 1000.0 <= 5.0)
                break

            latest = mt5.symbol_info_tick(args.symbol)
            if latest is None or latest.time_msc <= 0:
                time.sleep(args.poll_sec); continue
            broker_now = datetime.fromtimestamp(float(latest.time_msc) / 1000.0, timezone.utc)
            fetch_start = datetime.fromtimestamp(max(0.0, last_time_msc / 1000.0 - args.fetch_lookback_sec), timezone.utc)
            ticks = mt5.copy_ticks_range(args.symbol, fetch_start, broker_now + timedelta(milliseconds=1), mt5.COPY_TICKS_ALL)
            fetched = shadow.structured_ticks_to_rows(ticks)
            new_rows, new_last_msc, new_counts = shadow.select_new_rows(fetched, last_time_msc, last_signature_counts)
            new_rows = [x for x in new_rows if int(x["_time_msc"]) >= score_start_msc]
            if new_rows:
                capture_base.write_rows(score_path, capture_base.public_rows(new_rows))
                score_rows_all.extend(new_rows); score_rows += len(new_rows)
                latest_score_tick_msc = max(int(x["_time_msc"]) for x in new_rows)
                last_time_msc = new_last_msc; last_signature_counts = new_counts

            elapsed = now_mono - start_mono
            if now_mono - last_manifest >= args.manifest_sec:
                capture_base.atomic_json(manifest_path, manifest_payload(
                    args=args, session_id=session_id, warmup_path=warmup_path, score_path=score_path,
                    score_start_host=score_start_host, score_start_msc=score_start_msc,
                    score_end_target_host=score_end_target_host, score_end_target_msc=score_end_target_msc,
                    complete=False, stop_host=None, warmup_rows=len(warmup), score_rows=score_rows,
                    warmup_continuity_min=trailing_min, latest_score_tick_msc=latest_score_tick_msc,
                    score_rows_all=score_rows_all, host_runtime_sec=elapsed, hash_files=False,
                )); last_manifest = now_mono
            if now_mono - last_print >= args.print_sec:
                remaining = max(0.0, end_mono - now_mono)
                print(f"{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z | elapsed={elapsed/3600:.2f}h | remaining={remaining/3600:.2f}h | ticks={score_rows:,}")
                last_print = now_mono
            time.sleep(args.poll_sec)
    except KeyboardInterrupt:
        print("\nStopped early; block will be marked INCOMPLETE.")
    finally:
        stop_host = datetime.now(timezone.utc); runtime = time.monotonic() - start_mono
        capture_base.atomic_json(manifest_path, manifest_payload(
            args=args, session_id=session_id, warmup_path=warmup_path, score_path=score_path,
            score_start_host=score_start_host, score_start_msc=score_start_msc,
            score_end_target_host=score_end_target_host, score_end_target_msc=score_end_target_msc,
            complete=complete, stop_host=stop_host, warmup_rows=len(warmup), score_rows=score_rows,
            warmup_continuity_min=trailing_min, latest_score_tick_msc=latest_score_tick_msc,
            score_rows_all=score_rows_all, host_runtime_sec=runtime, hash_files=True,
        )); mt5.shutdown()

    print("Block status:", "COMPLETE" if complete else "INCOMPLETE")
    print("Warmup :", warmup_path.resolve()); print("Score  :", score_path.resolve()); print("Manifest:", manifest_path.resolve())


if __name__ == "__main__":
    main()
