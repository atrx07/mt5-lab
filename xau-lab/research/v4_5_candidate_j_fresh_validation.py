"""Experiment 48: fresh MT5-only prospective validation for Candidate J.

This validator must only be run on a new snapshot captured after Experiment 47.
It compares frozen Candidate D, Candidate H and Candidate J unchanged.

No external market data. No parameter search. No final20 access.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_microstate_v1_freeze as microstate
import v4_5_quote_flow_phase_controller as qflow
import v4_5_tick_tape_field_audit as tape

KNOWN_RECENT_END = pd.Timestamp("2026-09-24T18:58:45.860000+00:00")
KNOWN_RECENT_SHA256 = "9243ac73c3d180417ff634fe9371a28939713a531c9ccfa63f919c94eb9a28b1"
KNOWN_CANONICAL_SHA256 = canonical.DATASET_SHA256
EXPERIMENT_REF = "docs/experiments/2026-09-26/48-v4-5-candidate-j-fresh-validation.md"
STRESS = (0.0, 0.05, 0.10, 0.20)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: List[Dict]):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: List[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def verify_fresh_snapshot(csv_path: Path, manifest_path: Path) -> Dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual_sha = sha256_file(csv_path)
    declared_sha = str(manifest.get("raw", {}).get("sha256", ""))
    if actual_sha != declared_sha:
        raise RuntimeError(f"fresh snapshot sha mismatch: {actual_sha} != {declared_sha}")
    if actual_sha in {KNOWN_RECENT_SHA256, KNOWN_CANONICAL_SHA256}:
        raise RuntimeError("snapshot is not fresh: hash matches an already-known dataset")

    first = pd.Timestamp(manifest["raw"]["first_timestamp_utc"])
    last = pd.Timestamp(manifest["raw"]["last_timestamp_utc"])
    if first <= KNOWN_RECENT_END:
        raise RuntimeError(
            f"fresh snapshot overlaps known recent window: first={first.isoformat()} "
            f"known_recent_end={KNOWN_RECENT_END.isoformat()}"
        )
    requested = float(manifest.get("source", {}).get("requested_window_hours", 0.0))
    if requested < 48.0:
        raise RuntimeError(f"prospective contract requires a 48-hour snapshot; manifest reports {requested}")
    if EXPERIMENT_REF not in manifest.get("used_by", []):
        raise RuntimeError(f"manifest used_by must include {EXPERIMENT_REF}")
    if str(manifest.get("source", {}).get("platform", "")).lower() != "metatrader 5":
        raise RuntimeError("fresh validation requires MT5 source")

    return {
        "sha256": actual_sha,
        "rows": int(manifest["raw"]["data_rows"]),
        "first_timestamp_utc": first.isoformat(),
        "last_timestamp_utc": last.isoformat(),
        "requested_window_hours": requested,
        "manifest_dataset_id": manifest.get("dataset_id"),
        "mt5_minus_host_clock_sec": manifest.get("source", {}).get("mt5_minus_host_clock_sec"),
    }


def compact(m: Dict) -> Dict:
    keys = (
        "pnl_inr", "terminal_unrealized_inr", "terminal_equity_pnl_inr",
        "open_position_at_end", "profit_factor", "trades", "wins", "win_rate",
        "max_drawdown_inr", "shadow_opportunities", "immediate_entries",
        "delayed_entries", "skipped_entries", "busy_skips",
        "phase_exits", "protected_pullbacks",
    )
    return {k: m[k] for k in keys if k in m}


def nonoverlap_blocks(arr: Dict[str, np.ndarray], hours: float = 4.0) -> List[Tuple[int, int, int]]:
    t = np.asarray(arr["t"], dtype=float)
    ss = np.asarray(arr["ss"])
    block_sec = hours * 3600.0
    out: List[Tuple[int, int, int]] = []
    block_id = 0
    for session in np.unique(ss):
        ids = np.flatnonzero(ss == session)
        if not len(ids):
            continue
        lo = int(ids[0])
        hi = int(ids[-1]) + 1
        s = lo
        while s < hi:
            target = float(t[s]) + block_sec
            if target > float(t[hi - 1]):
                break
            e = int(np.searchsorted(t, target, side="left"))
            e = min(max(e, s + 1), hi)
            if float(t[e - 1]) - float(t[s]) >= block_sec - 5.0:
                out.append((block_id, s, e))
                block_id += 1
            s = e
    return out


def block_summary(rows: List[Dict], prefix: str) -> Dict:
    pnl = np.asarray([r[f"{prefix}_pnl"] for r in rows], dtype=float)
    tr = np.asarray([r[f"{prefix}_trades"] for r in rows], dtype=float)
    wi = np.asarray([r[f"{prefix}_wins"] for r in rows], dtype=float)
    if not len(pnl):
        return {
            "blocks": 0, "mean_pnl_inr": math.nan, "median_pnl_inr": math.nan,
            "p05_pnl_inr": math.nan, "p95_pnl_inr": math.nan,
            "positive_block_fraction": math.nan,
            "total_trades": 0, "total_wins": 0, "aggregate_win_rate": math.nan,
        }
    return {
        "blocks": int(len(pnl)),
        "mean_pnl_inr": float(np.mean(pnl)),
        "median_pnl_inr": float(np.median(pnl)),
        "p05_pnl_inr": float(np.quantile(pnl, 0.05)),
        "p95_pnl_inr": float(np.quantile(pnl, 0.95)),
        "positive_block_fraction": float(np.mean(pnl > 0)),
        "total_trades": int(tr.sum()),
        "total_wins": int(wi.sum()),
        "aggregate_win_rate": float(wi.sum() / tr.sum()) if tr.sum() else 0.0,
    }


def run_one(
    arr: Dict[str, np.ndarray],
    start: int,
    end: int,
    *,
    label: str,
    traw: Dict[str, np.ndarray],
    mraw: Dict[str, np.ndarray],
    qcache: Dict,
    mcache: Dict,
    slip: float = 0.0,
    capture_trace: bool = False,
):
    if label == "D":
        return hbase.simulate(
            arr, start, end, candidate_h=False,
            extra_slippage_usd_per_side=slip,
            capture_trace=capture_trace,
        )
    if label == "H":
        return hbase.simulate(
            arr, start, end, candidate_h=True,
            raw=mraw, feature_cache=mcache,
            extra_slippage_usd_per_side=slip,
            capture_trace=capture_trace,
        )
    if label == "J":
        return qflow.simulate_overlay(
            arr, start, end, variant="Candidate-J",
            tape_raw=traw, micro_raw=mraw,
            quote_cache=qcache, micro_cache=mcache,
            extra_slippage_usd_per_side=slip,
            capture_shadow_trace=capture_trace,
        )
    raise ValueError(label)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fresh_csv", type=Path)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    evidence = verify_fresh_snapshot(a.fresh_csv, a.manifest)
    a.output.mkdir(parents=True, exist_ok=True)

    print("loading fresh MT5-only raw sources", flush=True)
    traw = tape.load_raw(a.fresh_csv)
    mraw = microstate.load_raw(a.fresh_csv)
    qcache: Dict = {}
    mcache: Dict = {}

    result = {
        "schema": "xau-candidate-j-fresh-validation-v1",
        "snapshot": evidence,
        "candidate_j_source": "Experiment 47 frozen unchanged",
        "external_data_used": False,
        "threshold_search": False,
        "final20_opened": False,
        "intervals": {},
    }
    block_rows: List[Dict] = []
    stress_rows: List[Dict] = []
    parity_rows: List[Dict] = []

    for interval in ("500ms", "1s"):
        print(f"{interval}: building fresh sampled features", flush=True)
        arr, _ = canonical.build_features(a.fresh_csv, interval)
        start, end = 0, len(arr["t"])

        d = run_one(arr, start, end, label="D", traw=traw, mraw=mraw, qcache=qcache, mcache=mcache, capture_trace=True)
        h = run_one(arr, start, end, label="H", traw=traw, mraw=mraw, qcache=qcache, mcache=mcache, capture_trace=True)
        j = run_one(arr, start, end, label="J", traw=traw, mraw=mraw, qcache=qcache, mcache=mcache, capture_trace=True)

        parity = j["shadow_trace"] == d["entry_trace"]
        parity_rows.append({
            "interval": interval,
            "match": parity,
            "candidate_d_entries": len(d["entry_trace"]),
            "candidate_j_shadow_entries": len(j["shadow_trace"]),
        })
        if not parity:
            raise RuntimeError(f"Candidate J baseline-shadow parity failed on fresh {interval}")

        blocks = nonoverlap_blocks(arr, 4.0)
        rows = []
        for bid, s, e in blocks:
            row = {
                "interval": interval,
                "block_id": bid,
                "start_ts": float(arr["t"][s]),
                "end_ts": float(arr["t"][e - 1]),
            }
            for label in ("D", "H", "J"):
                m = run_one(arr, s, e, label=label, traw=traw, mraw=mraw, qcache=qcache, mcache=mcache)
                row[f"{label}_pnl"] = m["terminal_equity_pnl_inr"]
                row[f"{label}_trades"] = m["trades"]
                row[f"{label}_wins"] = m["wins"]
            rows.append(row)
            block_rows.append(row)

        block_stats = {label: block_summary(rows, label) for label in ("D", "H", "J")}

        costs = []
        for slip in STRESS:
            row = {"interval": interval, "extra_slippage_usd_per_side": slip}
            for label in ("D", "H", "J"):
                m = run_one(
                    arr, start, end, label=label,
                    traw=traw, mraw=mraw, qcache=qcache, mcache=mcache,
                    slip=slip,
                )
                row[f"{label}_terminal_equity_pnl_inr"] = m["terminal_equity_pnl_inr"]
                row[f"{label}_trades"] = m["trades"]
                row[f"{label}_wins"] = m["wins"]
            costs.append(row)
            stress_rows.append(row)

        result["intervals"][interval] = {
            "whole": {"D": compact(d), "H": compact(h), "J": compact(j)},
            "nonoverlap_4h": block_stats,
            "cost_stress": costs,
        }

    gates = {}
    for interval in ("500ms", "1s"):
        x = result["intervals"][interval]
        jwhole = x["whole"]["J"]["terminal_equity_pnl_inr"]
        dwhole = x["whole"]["D"]["terminal_equity_pnl_inr"]
        jblocks = x["nonoverlap_4h"]["J"]
        stress_010 = next(z for z in x["cost_stress"] if abs(float(z["extra_slippage_usd_per_side"]) - 0.10) < 1e-12)
        gates[interval] = {
            "whole_j_positive": bool(jwhole > 0),
            "whole_j_ge_d": bool(jwhole >= dwhole),
            "block_mean_positive": bool(float(jblocks["mean_pnl_inr"]) > 0),
            "positive_block_fraction_ge_50pct": bool(float(jblocks["positive_block_fraction"]) >= 0.50),
            "stress_0_10_j_nonnegative": bool(float(stress_010["J_terminal_equity_pnl_inr"]) >= 0),
            "shadow_parity": True,
        }

    pass_all = all(all(v.values()) for v in gates.values())
    result["predeclared_gate"] = gates
    result["prospective_pass"] = bool(pass_all)
    result["decision"] = (
        "PASS prospective gate; eligible for next validation stage."
        if pass_all
        else "FAIL prospective gate; do not tune Candidate J on this snapshot and call it unseen again."
    )

    write_csv(a.output / "baseline_shadow_parity.csv", parity_rows)
    write_csv(a.output / "nonoverlap_4h_blocks.csv", block_rows)
    write_csv(a.output / "cost_stress.csv", stress_rows)
    (a.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
