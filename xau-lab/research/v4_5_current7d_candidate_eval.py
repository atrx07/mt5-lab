"""Run frozen V4.5 Candidates D, H, and J on the archived current-regime 7-day XAUUSD dataset.

This is an outcome-known development/diagnostic evaluation, not prospective validation.
No parameter search, no tuning, no external data, and no final20 access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict

import numpy as np

import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_candidate_j_stage1_staged_validation as stage1
import v4_5_microstate_v1_freeze as microstate
import v4_5_quote_flow_phase_controller as qflow
import v4_5_tick_tape_field_audit as tape

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "raw" / "xau_ticks_7d_current_2026-10-06.csv.gz"
DEFAULT_MANIFEST = ROOT / "data" / "manifests" / "xau_ticks_7d_2026-09-29_to_2026-10-06.json"
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-10-06-v4_5-current7d-candidate-eval"
STRESS = (0.05, 0.10, 0.20)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def common_metrics(m: Dict, active_hours: float) -> Dict:
    eq = float(m.get("terminal_equity_pnl_inr", m.get("pnl_inr", 0.0)))
    out = {
        "realized_pnl_inr": float(m.get("pnl_inr", 0.0)),
        "terminal_unrealized_inr": float(m.get("terminal_unrealized_inr", 0.0)),
        "terminal_equity_pnl_inr": eq,
        "profit_velocity_active_inr_per_hour": eq / active_hours if active_hours > 0 else 0.0,
        "open_position_at_end": bool(m.get("open_position_at_end", False)),
        "profit_factor": float(m.get("profit_factor", 0.0)),
        "trades": int(m.get("trades", 0)),
        "wins": int(m.get("wins", 0)),
        "losses": int(m.get("trades", 0)) - int(m.get("wins", 0)),
        "win_rate": float(m.get("win_rate", 0.0)),
        "max_drawdown_inr": float(m.get("max_drawdown_inr", 0.0)),
    }
    return out


def extra_metrics(label: str, m: Dict) -> Dict:
    if label == "H":
        return {
            "primary_flow_exits": int(m.get("primary_flow_exits", 0)),
            "ghost_releases": int(m.get("ghost_releases", 0)),
        }
    if label == "J":
        return {
            "shadow_opportunities": int(m.get("shadow_opportunities", 0)),
            "immediate_entries": int(m.get("immediate_entries", 0)),
            "delayed_entries": int(m.get("delayed_entries", 0)),
            "skipped_entries": int(m.get("skipped_entries", 0)),
            "busy_skips": int(m.get("busy_skips", 0)),
            "phase_exits": int(m.get("phase_exits", 0)),
            "protected_pullbacks": int(m.get("protected_pullbacks", 0)),
        }
    return {}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    expected_archive_sha = str(manifest["archive"]["sha256"]).lower()
    actual_archive_sha = sha256_file(args.dataset).lower()
    if actual_archive_sha != expected_archive_sha:
        raise RuntimeError(f"archive SHA mismatch: {actual_archive_sha} != {expected_archive_sha}")

    args.output.mkdir(parents=True, exist_ok=True)

    print("Loading full current-regime raw tape...", flush=True)
    traw = tape.load_raw(args.dataset)
    print("Loading full current-regime microstate raw tape...", flush=True)
    mraw = microstate.load_raw(args.dataset)

    raw_t = traw["t"]
    dt = np.diff(raw_t)
    # Same practical market-active convention used by the prospective capture:
    # long no-quote gaps do not count as active market time.
    active_hours = float(dt[(dt >= 0.0) & (dt < 60.0)].sum() / 3600.0)
    calendar_span_hours = float((raw_t[-1] - raw_t[0]) / 3600.0)

    result = {
        "schema": "xau-v4-5-current7d-candidate-eval-v1",
        "dataset": {
            "dataset_id": manifest["dataset_id"],
            "rows": int(manifest["raw"]["data_rows"]),
            "first_timestamp_utc": manifest["raw"]["first_timestamp_utc"],
            "last_timestamp_utc": manifest["raw"]["last_timestamp_utc"],
            "archive_sha256": actual_archive_sha,
            "calendar_span_hours": calendar_span_hours,
            "market_active_hours_gap_lt_60s": active_hours,
        },
        "status": "outcome-known development diagnostic",
        "candidates": ["D", "H", "J"],
        "final20_opened": False,
        "external_data_used": False,
        "threshold_search": False,
        "intervals": {},
    }

    for interval in ("500ms", "1s"):
        print(f"Building all-row features: {interval}", flush=True)
        arr = stage1.build_features_all_rows(args.dataset, interval)
        start, end = 0, len(arr["t"])
        qcache: Dict = {}
        mcache: Dict = {}

        print(f"Running D/H/J: {interval}", flush=True)
        d = hbase.simulate(arr, start, end, candidate_h=False, capture_trace=True)
        h = hbase.simulate(
            arr, start, end, candidate_h=True,
            raw=mraw, feature_cache=mcache, capture_trace=True,
        )
        j = qflow.simulate_overlay(
            arr, start, end, variant="Candidate-J",
            tape_raw=traw, micro_raw=mraw,
            quote_cache=qcache, micro_cache=mcache,
            capture_shadow_trace=True,
        )

        h_entry_parity = h.get("entry_trace") == d.get("entry_trace")
        j_shadow_parity = j.get("shadow_trace") == d.get("entry_trace")
        if not h_entry_parity:
            raise RuntimeError(f"Candidate H entry-path parity failed on {interval}")
        if not j_shadow_parity:
            raise RuntimeError(f"Candidate J baseline-shadow parity failed on {interval}")

        base = {}
        for label, m in (("D", d), ("H", h), ("J", j)):
            base[label] = {
                **common_metrics(m, active_hours),
                **extra_metrics(label, m),
            }

        stress = {}
        for slip in STRESS:
            print(f"Stress {interval} +${slip:.2f}/side", flush=True)
            sd = hbase.simulate(arr, start, end, candidate_h=False, extra_slippage_usd_per_side=slip)
            sh = hbase.simulate(
                arr, start, end, candidate_h=True,
                raw=mraw, feature_cache=mcache,
                extra_slippage_usd_per_side=slip,
            )
            sj = qflow.simulate_overlay(
                arr, start, end, variant="Candidate-J",
                tape_raw=traw, micro_raw=mraw,
                quote_cache=qcache, micro_cache=mcache,
                extra_slippage_usd_per_side=slip,
            )
            stress[f"{slip:.2f}"] = {
                "D_terminal_equity_pnl_inr": float(sd["terminal_equity_pnl_inr"]),
                "H_terminal_equity_pnl_inr": float(sh["terminal_equity_pnl_inr"]),
                "J_terminal_equity_pnl_inr": float(sj["terminal_equity_pnl_inr"]),
                "D_trades": int(sd["trades"]),
                "H_trades": int(sh["trades"]),
                "J_trades": int(sj["trades"]),
            }

        result["intervals"][interval] = {
            "sampled_rows": int(end - start),
            "path_parity": {
                "H_entries_equal_D": h_entry_parity,
                "J_shadow_equal_D": j_shadow_parity,
            },
            "base": base,
            "cost_stress_extra_slippage_usd_per_side": stress,
            "ranking_by_terminal_equity_pnl": sorted(
                ("D", "H", "J"),
                key=lambda label: base[label]["terminal_equity_pnl_inr"],
                reverse=True,
            ),
        }

        # Release the largest interval-specific structure before the next grid.
        del arr

    result["overall_note"] = (
        "This seven-day dataset was captured after Experiment 48 Stage-1 outcomes were known. "
        "These statistics are diagnostic/development evidence only and cannot promote a candidate."
    )

    out = args.output / "summary.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    print(f"Wrote {out}", flush=True)


if __name__ == "__main__":
    main()
