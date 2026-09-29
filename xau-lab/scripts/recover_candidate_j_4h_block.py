"""Repair a frozen prospective 4-hour block from MT5 tick history.

Use this only when the block boundary was frozen before outcomes were viewed but
the local collector was suspended/disconnected and therefore missed raw ticks.

The repair DOES NOT move the score window. It re-downloads the exact original
score interval from the same MT5/broker history, preserves the pre-repair local
capture, and rewrites score_ticks.csv deterministically.

READ ONLY: no broker execution APIs are called.
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

import live_shadow_candidate_j as shadow

DEFAULT_ROOT = ROOT / "data" / "prospective_4h"
RAW_COLUMNS = shadow.RAW_COLUMNS


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
        "policy": "read-only MT5 historical tick recovery only",
    }


def read_csv_rows(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    df = pd.read_csv(path)
    if df.empty:
        return []
    return df.to_dict("records")


def csv_last_boundary_counts(warmup_path: Path, start_msc: int) -> Counter:
    rows = read_csv_rows(warmup_path)
    counts = Counter()
    for row in rows:
        ts = pd.Timestamp(row["timestamp_utc"])
        tmsc = int(ts.timestamp() * 1000)
        if tmsc != start_msc:
            continue
        sig = (
            float(row["bid"]),
            float(row["ask"]),
            float(row.get("last", 0.0)),
            float(row.get("volume", 0.0)),
            int(row.get("flags", 0)),
            float(row.get("volume_real", 0.0)),
        )
        counts[sig] += 1
    return counts


def write_atomic_csv(path: Path, rows: List[Dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RAW_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row[k] for k in RAW_COLUMNS})
    os.replace(tmp, path)


def gap_stats(rows: List[Dict]) -> Dict:
    if len(rows) < 2:
        return {"max_gap_sec": 0.0, "gap_count_gt_5s": 0}
    t = [int(pd.Timestamp(r["timestamp_utc"]).timestamp() * 1000) for r in rows]
    gaps = [(t[i] - t[i - 1]) / 1000.0 for i in range(1, len(t))]
    return {
        "max_gap_sec": max(gaps),
        "gap_count_gt_5s": sum(g > 5.0 for g in gaps),
    }


def atomic_json(path: Path, payload: Dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("session_id", help="e.g. 20260928T150531Z")
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
        raise SystemExit(f"warmup file not found: {warmup_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = manifest["score_contract"]
    symbol = str(manifest.get("symbol", "XAUUSD"))
    start_dt = pd.Timestamp(contract["score_start_mt5_reported_utc"]).to_pydatetime()
    duration_hours = float(contract["score_duration_hours_requested"])
    target_dt = start_dt + timedelta(hours=duration_hours)
    start_msc = int(start_dt.timestamp() * 1000)
    target_msc = int(target_dt.timestamp() * 1000)

    original = {
        "existed": score_path.exists(),
        "rows": 0,
        "sha256": None,
    }
    if score_path.exists():
        original["rows"] = max(0, sum(1 for _ in score_path.open("r", encoding="utf-8")) - 1)
        original["sha256"] = sha256_file(score_path)
        if not backup_path.exists():
            shutil.copy2(score_path, backup_path)

    mt5 = shadow.live_import_mt5()
    shadow.mt5_connect(mt5, symbol)
    try:
        # Request the exact frozen score interval with a tiny end margin. The
        # filter below enforces the original boundary regardless of MT5 inclusivity.
        ticks = mt5.copy_ticks_range(
            symbol,
            start_dt,
            target_dt + timedelta(milliseconds=2),
            mt5.COPY_TICKS_ALL,
        )
        fetched = shadow.structured_ticks_to_rows(ticks)
    finally:
        mt5.shutdown()

    if len(fetched) < 2:
        raise RuntimeError("MT5 did not return enough ticks for the frozen score interval")

    boundary_counts = csv_last_boundary_counts(warmup_path, start_msc)
    recovered, _, _ = shadow.select_new_rows(fetched, start_msc, boundary_counts)
    recovered = [x for x in recovered if start_msc <= int(x["_time_msc"]) <= target_msc]
    public = [shadow.public_row(x) for x in recovered]
    if len(public) < 2:
        raise RuntimeError("recovered score interval is empty after boundary filtering")

    first_msc = int(pd.Timestamp(public[0]["timestamp_utc"]).timestamp() * 1000)
    last_msc = int(pd.Timestamp(public[-1]["timestamp_utc"]).timestamp() * 1000)
    start_lag_sec = max(0.0, (first_msc - start_msc) / 1000.0)
    end_lag_sec = max(0.0, (target_msc - last_msc) / 1000.0)
    coverage_sec = max(0.0, (last_msc - start_msc) / 1000.0)

    if end_lag_sec > args.end_tolerance_sec:
        raise RuntimeError(
            f"Broker history does not yet cover the frozen block end: "
            f"last tick is {end_lag_sec:.3f}s before target"
        )

    write_atomic_csv(score_path, public)
    stats = gap_stats(public)

    manifest["schema"] = "xau-candidate-j-prospective-4h-block-v2"
    manifest["score_contract"]["score_end_target_mt5_reported_utc"] = target_dt.isoformat()
    manifest["score_contract"]["broker_coverage_sec"] = coverage_sec
    manifest["score_contract"]["score_start_lag_sec"] = start_lag_sec
    manifest["score_contract"]["score_end_lag_sec"] = end_lag_sec
    manifest["score_contract"]["complete"] = True
    manifest["score_contract"]["valid_for_stage1"] = bool(
        float(contract["warmup_trailing_continuity_minutes"])
        >= float(contract["warmup_minutes_requested"])
        and end_lag_sec <= args.end_tolerance_sec
    )
    manifest["capture_quality"] = {
        **manifest.get("capture_quality", {}),
        "score_rows": len(public),
        "score_max_raw_tick_gap_sec": stats["max_gap_sec"],
        "score_gap_count_gt_5s": stats["gap_count_gt_5s"],
        "first_score_tick_mt5_reported_utc": public[0]["timestamp_utc"],
        "latest_score_tick_mt5_reported_utc": public[-1]["timestamp_utc"],
        "reconstructed_from_same_mt5_history": True,
        "note": (
            "Exact predeclared score interval reconstructed from the same MT5/broker "
            "history after a local suspend gap; no score boundary was moved."
        ),
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
        "reason": "local collector suspended before frozen block end",
        "score_window_changed": False,
        "same_mt5_broker_history": True,
        "pre_recovery_capture": {
            **original,
            "backup_path": str(backup_path) if backup_path.exists() else None,
            "backup_sha256": sha256_file(backup_path) if backup_path.exists() else None,
        },
        "recovered_score_rows": len(public),
        "recovered_score_sha256": sha256_file(score_path),
        "safety": safety_scan_source(),
    }
    atomic_json(manifest_path, manifest)

    print("==========================================================")
    print(" CANDIDATE J 4H BLOCK RECOVERY — PASS")
    print("==========================================================")
    print("Session:", args.session_id)
    print("Frozen window:", start_dt.isoformat(), "->", target_dt.isoformat())
    print("Recovered score rows:", f"{len(public):,}")
    print("End lag:", f"{end_lag_sec:.3f}s")
    print("Max raw tick gap:", f"{stats['max_gap_sec']:.3f}s")
    print("Stage-1 valid:", manifest["score_contract"]["valid_for_stage1"])
    print("Score:", score_path.resolve())
    print("Manifest:", manifest_path.resolve())
    if backup_path.exists():
        print("Original capture preserved:", backup_path.resolve())


if __name__ == "__main__":
    main()
