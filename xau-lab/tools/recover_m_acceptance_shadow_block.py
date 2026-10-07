"""Recover an interrupted Experiment-58 block from the same MT5 broker history.

READ ONLY. The frozen score start/end are never moved. This utility replaces an
incomplete local score capture with the exact original four-wall-clock-hour MT5
history, preserving real quote gaps and the pre-recovery CSV for provenance.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import capture_candidate_j_4h_block as capture_base
import live_shadow_candidate_j as shadow

DEFAULT_ROOT = ROOT / "data" / "prospective_m_acceptance_shadow"
RAW_COLUMNS = shadow.RAW_COLUMNS
EXPECTED_SCHEMA = "xau-exp58-m-acceptance-shadow-block-v1"


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


def write_atomic_csv(path: Path, rows: List[Dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RAW_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row[k] for k in RAW_COLUMNS})
    os.replace(tmp, path)


def safety_scan_source() -> Dict:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    forbidden = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            name = node.func.attr.lower()
            if name == "order_send" or name.startswith("trade_"):
                forbidden.append({"line": getattr(node, "lineno", None), "call": node.func.attr})
    if forbidden:
        raise RuntimeError(f"forbidden broker execution call: {forbidden}")
    return {
        "status": "PASS",
        "forbidden_calls_found": 0,
        "policy": "read-only MT5 exact-window historical recovery only",
    }


def csv_boundary_counts(path: Path, start_msc: int) -> Counter:
    if not path.exists():
        return Counter()
    df = pd.read_csv(path)
    out = Counter()
    for _, row in df.iterrows():
        tmsc = int(pd.Timestamp(row["timestamp_utc"]).timestamp() * 1000)
        if tmsc != start_msc:
            continue
        sig = (
            float(row["bid"]), float(row["ask"]), float(row.get("last", 0.0)),
            float(row.get("volume", 0.0)), int(row.get("flags", 0)),
            float(row.get("volume_real", 0.0)),
        )
        out[sig] += 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("session_id")
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--end-tolerance-sec", type=float, default=5.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        print(json.dumps({"status": "PASS", "safety": safety_scan_source()}, indent=2))
        return

    safety_scan_source()
    session_dir = args.root / args.session_id
    manifest_path = session_dir / "block_manifest.json"
    warmup_path = session_dir / "warmup_ticks.csv"
    score_path = session_dir / "score_ticks.csv"
    backup_path = session_dir / "score_ticks.pre_recovery.csv"

    if not manifest_path.exists():
        raise SystemExit(f"manifest not found: {manifest_path}")
    if not warmup_path.exists():
        raise SystemExit(f"warmup not found: {warmup_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != EXPECTED_SCHEMA:
        raise RuntimeError(f"unexpected manifest schema: {manifest.get('schema')}")
    if manifest.get("candidate_m_reference_frozen") is not True:
        raise RuntimeError("candidate_m_reference_frozen is not true")
    if manifest.get("external_data_used") is not False or manifest.get("final20_opened") is not False:
        raise RuntimeError("invalid Experiment-58 provenance flags")

    contract = manifest["score_contract"]
    start_dt = pd.Timestamp(contract["score_start_mt5_reported_utc"]).to_pydatetime()
    end_dt = pd.Timestamp(contract["score_end_target_mt5_reported_utc"]).to_pydatetime()
    if end_dt <= start_dt:
        raise RuntimeError("invalid frozen score interval")
    start_msc = int(start_dt.timestamp() * 1000)
    end_msc = int(end_dt.timestamp() * 1000)
    symbol = str(manifest.get("symbol", "XAUUSD"))

    original = {"existed": score_path.exists(), "rows": 0, "sha256": None}
    if score_path.exists():
        original["rows"] = max(0, sum(1 for _ in score_path.open("r", encoding="utf-8")) - 1)
        original["sha256"] = sha256_file(score_path)
        if not backup_path.exists():
            shutil.copy2(score_path, backup_path)

    mt5 = shadow.live_import_mt5()
    shadow.mt5_connect(mt5, symbol)
    try:
        latest = mt5.symbol_info_tick(symbol)
        if latest is None or latest.time_msc <= 0:
            raise RuntimeError(f"symbol_info_tick failed: {mt5.last_error()}")
        latest_msc = int(latest.time_msc)
        if latest_msc < end_msc:
            missing_sec = (end_msc - latest_msc) / 1000.0
            raise RuntimeError(
                f"Frozen Experiment-58 endpoint has not passed in broker time yet. "
                f"Retry after about {missing_sec/60.0:.1f} more min of broker time."
            )
        ticks = mt5.copy_ticks_range(
            symbol,
            start_dt,
            end_dt + timedelta(milliseconds=2),
            mt5.COPY_TICKS_ALL,
        )
        fetched = shadow.structured_ticks_to_rows(ticks)
    finally:
        mt5.shutdown()

    if len(fetched) < 2:
        raise RuntimeError("MT5 returned insufficient history for the frozen score window")

    boundary_counts = csv_boundary_counts(warmup_path, start_msc)
    recovered_all, _, _ = shadow.select_new_rows(fetched, start_msc, boundary_counts)
    recovered = [x for x in recovered_all if start_msc <= int(x["_time_msc"]) <= end_msc]
    if len(recovered) < 2:
        raise RuntimeError("recovered exact score interval is empty")

    first_msc = min(int(x["_time_msc"]) for x in recovered)
    last_msc = max(int(x["_time_msc"]) for x in recovered)
    end_lag_sec = max(0.0, (end_msc - last_msc) / 1000.0)
    if end_lag_sec > args.end_tolerance_sec:
        raise RuntimeError(
            f"Broker history still does not cover the frozen endpoint closely enough: "
            f"last tick is {end_lag_sec:.3f}s before target (tolerance {args.end_tolerance_sec:.3f}s)."
        )

    public = [shadow.public_row(x) for x in recovered]
    write_atomic_csv(score_path, public)
    max_gap = capture_base.max_tick_gap_sec(recovered)
    gap_count = capture_base.gap_count(recovered, 5.0)
    warmup_ok = float(contract.get("warmup_trailing_continuity_minutes", 0.0)) >= float(contract.get("warmup_minutes_requested", 30.0))

    contract["complete"] = True
    contract["valid_for_experiment58"] = bool(warmup_ok and end_lag_sec <= args.end_tolerance_sec)
    contract["recovered_exact_frozen_wall_clock_window"] = True
    contract["recovery_changed_score_start"] = False
    contract["recovery_changed_score_end"] = False

    manifest["capture_quality"] = {
        **manifest.get("capture_quality", {}),
        "score_rows": len(public),
        "score_max_raw_tick_gap_sec": max_gap,
        "score_gap_count_gt_5s": gap_count,
        "first_score_tick_mt5_reported_utc": public[0]["timestamp_utc"],
        "latest_score_tick_mt5_reported_utc": public[-1]["timestamp_utc"],
        "reconstructed_from_same_mt5_history": True,
        "note": "Exact frozen four-wall-clock-hour interval reconstructed from same MT5 broker history; real quote gaps preserved.",
    }
    manifest["score"] = {
        **manifest.get("score", {}),
        "path": str(score_path),
        "rows": len(public),
        "sha256": sha256_file(score_path),
        "columns": RAW_COLUMNS,
    }
    manifest["recovery"] = {
        "performed_host_utc": datetime.now(timezone.utc).isoformat(),
        "reason": "collector blocked during MT5 terminal restart and was stopped cleanly",
        "same_mt5_broker_history": True,
        "frozen_score_start_preserved": True,
        "frozen_score_end_preserved": True,
        "window_basis": "original four wall-clock hours",
        "pre_recovery_capture": {
            **original,
            "backup_path": str(backup_path) if backup_path.exists() else None,
            "backup_sha256": sha256_file(backup_path) if backup_path.exists() else None,
        },
        "recovered_score_rows": len(public),
        "recovered_score_sha256": sha256_file(score_path),
        "first_recovered_tick_lag_sec": max(0.0, (first_msc - start_msc) / 1000.0),
        "end_lag_sec": end_lag_sec,
        "safety": safety_scan_source(),
    }
    atomic_json(manifest_path, manifest)

    print("==========================================================")
    print(" EXPERIMENT 58 EXACT-WINDOW RECOVERY — PASS")
    print("==========================================================")
    print("Session:", args.session_id)
    print("Frozen start:", start_dt.isoformat())
    print("Frozen end  :", end_dt.isoformat())
    print("Recovered score rows:", f"{len(public):,}")
    print("Max raw tick gap:", f"{max_gap:.3f}s")
    print(">5s raw gaps:", gap_count)
    print("End lag:", f"{end_lag_sec:.3f}s")
    print("Experiment-58 valid:", contract["valid_for_experiment58"])
    print("Score:", score_path.resolve())
    print("Manifest:", manifest_path.resolve())
    if backup_path.exists():
        print("Pre-recovery partial capture:", backup_path.resolve())


if __name__ == "__main__":
    main()
