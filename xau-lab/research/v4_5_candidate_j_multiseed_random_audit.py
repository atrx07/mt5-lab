"""Experiment 47R: multi-seed random-window robustness audit for Candidate J.

Candidate J is frozen exactly as in Experiment 47. This script runs three new
deterministic random batches of real contiguous four-hour windows from the same
known historical-first80 and recent24h datasets. No tuning. No final20.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_microstate_v1_freeze as microstate
import v4_5_quote_flow_phase_controller as qflow
import v4_5_regime_portability as portability
import v4_5_router_v2_full_eval as full_eval
import v4_5_tick_tape_field_audit as tape

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-09-26-v4_5-candidate-j-multiseed-random-audit"

BATCHES = {
    "A": {"500ms": 20261001, "1s": 20261002},
    "B": {"500ms": 20261013, "1s": 20261014},
    "C": {"500ms": 20261027, "1s": 20261028},
}
WINDOWS_PER_BATCH = 40
WINDOW_HOURS = 4.0


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


def stats(rows: List[Dict], prefix: str) -> Dict:
    pnl = np.asarray([r[f"{prefix}_pnl"] for r in rows], dtype=float)
    tr = np.asarray([r[f"{prefix}_trades"] for r in rows], dtype=float)
    wi = np.asarray([r[f"{prefix}_wins"] for r in rows], dtype=float)
    return {
        "windows": int(len(rows)),
        "mean_pnl_inr": float(np.mean(pnl)),
        "median_pnl_inr": float(np.median(pnl)),
        "p05_pnl_inr": float(np.quantile(pnl, 0.05)),
        "p95_pnl_inr": float(np.quantile(pnl, 0.95)),
        "positive_window_fraction": float(np.mean(pnl > 0)),
        "total_trades": int(tr.sum()),
        "total_wins": int(wi.sum()),
        "aggregate_win_rate": float(wi.sum() / tr.sum()) if tr.sum() else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("canonical_csv", type=Path)
    ap.add_argument("recent_csv_or_gz", type=Path)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True, exist_ok=True)

    htape = tape.load_raw(a.canonical_csv, nrows=canonical.RESEARCH_ROWS)
    rtape = tape.load_raw(a.recent_csv_or_gz)
    hmicro = microstate.load_raw(a.canonical_csv, nrows=canonical.RESEARCH_ROWS)
    rmicro = microstate.load_raw(a.recent_csv_or_gz)

    hqcache: Dict = {}
    rqcache: Dict = {}
    hmcache: Dict = {}
    rmcache: Dict = {}

    result = {
        "schema": "xau-candidate-j-multiseed-random-audit-v1",
        "candidate_j_frozen_from": "Experiment 47",
        "batches": BATCHES,
        "windows_per_batch_per_grid": WINDOWS_PER_BATCH,
        "window_hours": WINDOW_HOURS,
        "external_data_used": False,
        "threshold_search": False,
        "known_data_only": True,
        "promotion_evidence": False,
        "final20_opened": False,
        "intervals": {},
    }

    all_rows: List[Dict] = []
    batch_summary_rows: List[Dict] = []
    parity_rows: List[Dict] = []

    for interval in ("500ms", "1s"):
        print(f"{interval}: building known feature grids", flush=True)
        h_arr, h_bounds = canonical.build_features(a.canonical_csv, interval)
        canonical.assert_baseline(
            canonical.run_strategy(h_arr, h_bounds, "v4_4"),
            interval, canonical.DEFAULT_GOLDEN,
        )
        h_ranges = full_eval.continuous_ranges(h_arr, autopsy.indices(h_arr, h_bounds))

        r_arr, _ = canonical.build_features(a.recent_csv_or_gz, interval)
        r_ranges = full_eval.continuous_ranges(r_arr, [(0, len(r_arr["t"]))])

        interval_batches = {}
        pooled: List[Dict] = []

        for batch_name, seed_map in BATCHES.items():
            seed = int(seed_map[interval])
            print(f"{interval}: batch {batch_name} seed={seed}", flush=True)
            rng = np.random.default_rng(seed)
            rows: List[Dict] = []

            for wid in range(WINDOWS_PER_BATCH):
                # Keep the same deliberately hostile 50/50 source balance as
                # Experiment 47 so only the random start times change.
                source = "historical7d" if wid % 2 == 0 else "recent24h"
                if source == "historical7d":
                    arr, ranges = h_arr, h_ranges
                    traw, mraw, qcache, mcache = htape, hmicro, hqcache, hmcache
                else:
                    arr, ranges = r_arr, r_ranges
                    traw, mraw, qcache, mcache = rtape, rmicro, rqcache, rmcache

                s, e, rid = full_eval.random_window_from_ranges(
                    arr, ranges, rng, WINDOW_HOURS
                )

                d = hbase.simulate(
                    arr, s, e, candidate_h=False, capture_trace=True
                )
                h = hbase.simulate(
                    arr, s, e, candidate_h=True,
                    raw=mraw, feature_cache=mcache,
                )
                j = qflow.simulate_overlay(
                    arr, s, e, variant="Candidate-J",
                    tape_raw=traw, micro_raw=mraw,
                    quote_cache=qcache, micro_cache=mcache,
                    capture_shadow_trace=True,
                )

                parity = j["shadow_trace"] == d["entry_trace"]
                parity_rows.append({
                    "interval": interval,
                    "batch": batch_name,
                    "window_id": wid,
                    "source": source,
                    "match": parity,
                    "candidate_d_entries": len(d["entry_trace"]),
                    "candidate_j_shadow_entries": len(j["shadow_trace"]),
                })
                if not parity:
                    raise RuntimeError(
                        f"shadow parity failed: {interval} batch={batch_name} window={wid}"
                    )

                row = {
                    "interval": interval,
                    "batch": batch_name,
                    "seed": seed,
                    "window_id": wid,
                    "source": source,
                    "source_range_id": rid,
                    "start_ts": float(arr["t"][s]),
                    "end_ts": float(arr["t"][e - 1]),
                    "D_pnl": d["terminal_equity_pnl_inr"],
                    "H_pnl": h["terminal_equity_pnl_inr"],
                    "J_pnl": j["terminal_equity_pnl_inr"],
                    "D_trades": d["trades"],
                    "H_trades": h["trades"],
                    "J_trades": j["trades"],
                    "D_wins": d["wins"],
                    "H_wins": h["wins"],
                    "J_wins": j["wins"],
                    "J_delayed_entries": j["delayed_entries"],
                    "J_skipped_entries": j["skipped_entries"],
                    "J_phase_exits": j["phase_exits"],
                }
                rows.append(row)
                pooled.append(row)
                all_rows.append(row)

            d_stats = stats(rows, "D")
            h_stats = stats(rows, "H")
            j_stats = stats(rows, "J")
            j_beats_d = float(np.mean([x["J_pnl"] > x["D_pnl"] for x in rows]))
            j_beats_h = float(np.mean([x["J_pnl"] > x["H_pnl"] for x in rows]))

            interval_batches[batch_name] = {
                "seed": seed,
                "D": d_stats,
                "H": h_stats,
                "J": j_stats,
                "J_beats_D_fraction": j_beats_d,
                "J_beats_H_fraction": j_beats_h,
                "shadow_parity": True,
            }
            for label, ss in (("D", d_stats), ("H", h_stats), ("J", j_stats)):
                batch_summary_rows.append({
                    "interval": interval,
                    "batch": batch_name,
                    "seed": seed,
                    "candidate": label,
                    **ss,
                    "J_beats_D_fraction": j_beats_d if label == "J" else "",
                    "J_beats_H_fraction": j_beats_h if label == "J" else "",
                })

        pooled_stats = {label: stats(pooled, label) for label in ("D", "H", "J")}
        pooled_beats_d = float(np.mean([x["J_pnl"] > x["D_pnl"] for x in pooled]))
        pooled_beats_h = float(np.mean([x["J_pnl"] > x["H_pnl"] for x in pooled]))

        result["intervals"][interval] = {
            "batches": interval_batches,
            "pooled_three_new_batches": {
                **pooled_stats,
                "J_beats_D_fraction": pooled_beats_d,
                "J_beats_H_fraction": pooled_beats_h,
                "shadow_parity": True,
            },
        }

    result["decision"] = (
        "Robustness audit only. Use these three independent random seeds to assess "
        "whether Experiment 47's random-window behavior persists. Candidate J remains "
        "frozen for Experiment 48 regardless of this known-data result."
    )

    write_csv(a.output / "window_results.csv", all_rows)
    write_csv(a.output / "batch_summary.csv", batch_summary_rows)
    write_csv(a.output / "baseline_shadow_parity.csv", parity_rows)
    (a.output / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
