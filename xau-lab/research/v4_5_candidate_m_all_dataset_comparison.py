"""Experiment 54: rerun frozen Candidate M across every currently archived non-sealed dataset.

This is a comparison/diagnostic only. Candidate M was already rejected unchanged in
Experiment 53, so this script must not tune or promote it. The canonical seven-day
final20 remains sealed.

Compared candidates: D, H, M.
Data:
- canonical historical seven-day archive, first80 only;
- frozen recent-24h archive;
- current seven-day archive;
- all six archived Experiment-48 Stage-1 blocks, individually and pooled.

Normal fills and +$0.10 adverse slippage per side are reported for the three raw
archives. Stage-1 blocks are rerun at normal fills to preserve their frozen scoring
contract.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Dict, List

import numpy as np

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_candidate_l_normalized_resumption as lbase
import v4_5_candidate_m_pullback_acceptance as mbase
import v4_5_microstate_v1_freeze as microstate
from v4_5_candidate_j_stage1_staged_validation import build_features_all_rows, inspect_block, make_combined_csv

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "xau_ticks_7d.csv"
RECENT = ROOT / "data" / "raw" / "xau_ticks_recent_24h_2026-09-24.csv.gz"
RECENT_MANIFEST = ROOT / "data" / "manifests" / "xau_ticks_recent_24h_2026-09-24.json"
CURRENT = ROOT / "data" / "raw" / "xau_ticks_7d_current_2026-10-06.csv.gz"
CURRENT_MANIFEST = ROOT / "data" / "manifests" / "xau_ticks_7d_2026-09-29_to_2026-10-06.json"
BLOCK_ROOT = ROOT / "data" / "prospective_restored"
OUT = ROOT / "results" / "simulations" / "2026-10-06-v4_5-candidate-m-all-dataset-comparison"
STRESS = (0.0, 0.10)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_gzip_payload(path: Path) -> str:
    h = hashlib.sha256()
    with gzip.open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_archive(path: Path, manifest_path: Path) -> Dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive = manifest["archive"]
    raw = manifest["raw"]
    got_archive = sha256_file(path)
    if got_archive != archive["sha256"]:
        raise RuntimeError(f"archive SHA mismatch {path.name}: {got_archive} != {archive['sha256']}")
    got_raw = sha256_gzip_payload(path)
    if got_raw != raw["sha256"]:
        raise RuntimeError(f"raw SHA mismatch {path.name}: {got_raw} != {raw['sha256']}")
    return manifest


def write_csv(path: Path, rows: List[Dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def normalize_continuous(label: str, m: Dict) -> Dict:
    return {
        "candidate": label,
        "pnl_inr": float(m["terminal_equity_pnl_inr"]),
        "realized_pnl_inr": float(m["pnl_inr"]),
        "terminal_unrealized_inr": float(m.get("terminal_unrealized_inr", 0.0)),
        "trades": int(m["trades"]),
        "wins": int(m["wins"]),
        "win_rate": float(m["win_rate"]),
        "profit_factor": float(m["profit_factor"]),
        "max_drawdown_inr": float(m["max_drawdown_inr"]),
        "open_position_at_end": bool(m.get("open_position_at_end", False)),
    }


def evaluate_continuous(path: Path, interval: str, slip: float) -> Dict[str, Dict]:
    arr = build_features_all_rows(path, interval)
    raw = microstate.load_raw(path)
    cache = {}
    d = hbase.simulate(arr, 0, len(arr["t"]), candidate_h=False, extra_slippage_usd_per_side=slip)
    h = hbase.simulate(arr, 0, len(arr["t"]), candidate_h=True, raw=raw, feature_cache=cache, extra_slippage_usd_per_side=slip)
    m = mbase.simulate_m(arr, 0, len(arr["t"]), raw=raw, cache=cache, extra_slippage_usd_per_side=slip)
    return {"D": normalize_continuous("D", d), "H": normalize_continuous("H", h), "M": normalize_continuous("M", m)}


def evaluate_historical(interval: str, slip: float) -> Dict[str, Dict]:
    arr, bounds = canonical.build_features(HISTORICAL, interval)
    v44 = canonical.run_strategy(arr, bounds, "v4_4")
    canonical.assert_baseline(v44, interval, canonical.DEFAULT_GOLDEN)
    ranges = autopsy.indices(arr, bounds)
    raw = microstate.load_raw(HISTORICAL, nrows=canonical.RESEARCH_ROWS)
    cache = {}
    dseg = [hbase.simulate(arr, s, e, candidate_h=False, extra_slippage_usd_per_side=slip) for s, e in ranges]
    hseg = [hbase.simulate(arr, s, e, candidate_h=True, raw=raw, feature_cache=cache, extra_slippage_usd_per_side=slip) for s, e in ranges]
    mseg = [mbase.simulate_m(arr, s, e, raw=raw, cache=cache, extra_slippage_usd_per_side=slip) for s, e in ranges]
    ds = hbase.summarize(dseg); hs = hbase.summarize(hseg); ms = mbase.compounded(mseg)
    def n(label: str, x: Dict) -> Dict:
        return {
            "candidate": label,
            "pnl_inr": float(x["compounded_pnl_inr"]),
            "trades": int(x["trades"]),
            "wins": int(x["wins"]),
            "win_rate": float(x["win_rate"]),
            "max_drawdown_inr": float(x["max_segment_drawdown_inr"]),
            "profit_factor": None,
            "pnl_semantics": "five-segment reset/compound first80",
        }
    return {"D": n("D", ds), "H": n("H", hs), "M": n("M", ms)}


def eval_stage1(interval: str, root: Path) -> tuple[List[Dict], Dict]:
    rows: List[Dict] = []
    with tempfile.TemporaryDirectory(prefix="candidate-m-all-data-") as td:
        temp = Path(td)
        for session_dir in sorted(p for p in root.iterdir() if p.is_dir() and (p / "block_manifest.json").exists()):
            block = inspect_block(session_dir)
            combined = make_combined_csv(block, temp)
            arr = build_features_all_rows(combined, interval)
            raw = microstate.load_raw(combined)
            cache = {}
            s = int(np.searchsorted(arr["t"], block["start"].timestamp(), side="left"))
            e = int(np.searchsorted(arr["t"], block["end"].timestamp(), side="right"))
            d = hbase.simulate(arr, s, e, candidate_h=False)
            h = hbase.simulate(arr, s, e, candidate_h=True, raw=raw, feature_cache=cache)
            m = mbase.simulate_m(arr, s, e, raw=raw, cache=cache)
            row = {"session": session_dir.name, "interval": interval}
            for label, x in (("D", d), ("H", h), ("M", m)):
                row[f"{label}_pnl_inr"] = float(x["terminal_equity_pnl_inr"])
                row[f"{label}_trades"] = int(x["trades"])
                row[f"{label}_wins"] = int(x["wins"])
                row[f"{label}_win_rate"] = float(x["win_rate"])
                row[f"{label}_max_dd_inr"] = float(x["max_drawdown_inr"])
            rows.append(row)
    pooled = {}
    for label in ("D", "H", "M"):
        tr = sum(r[f"{label}_trades"] for r in rows)
        wi = sum(r[f"{label}_wins"] for r in rows)
        pooled[label] = {
            "pnl_inr": float(sum(r[f"{label}_pnl_inr"] for r in rows)),
            "trades": int(tr),
            "wins": int(wi),
            "win_rate": float(wi / tr) if tr else 0.0,
            "positive_blocks": int(sum(r[f"{label}_pnl_inr"] > 0 for r in rows)),
            "blocks": len(rows),
            "worst_block_pnl_inr": float(min(r[f"{label}_pnl_inr"] for r in rows)),
            "best_block_pnl_inr": float(max(r[f"{label}_pnl_inr"] for r in rows)),
        }
    return rows, pooled


def pct_delta(m: float, comparator: float) -> float | None:
    if abs(comparator) < 1e-12:
        return None
    # For negative comparators, positive means M loses less / improves P&L.
    return float((m - comparator) / abs(comparator) * 100.0)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--blocks", type=Path, default=BLOCK_ROOT)
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)

    historical_digest = canonical.verify_dataset(HISTORICAL)
    recent_manifest = verify_archive(RECENT, RECENT_MANIFEST)
    current_manifest = lbase.verify_current(CURRENT, CURRENT_MANIFEST)

    summary = {
        "schema": "xau-v4-5-candidate-m-all-known-datasets-v1",
        "status": "rerun comparison; Candidate M remains rejected and unchanged",
        "strategy_changed": False,
        "threshold_search": False,
        "final20_opened": False,
        "historical_raw_sha256": historical_digest,
        "recent_dataset_id": recent_manifest["dataset_id"],
        "current_dataset_id": current_manifest["dataset_id"],
        "datasets": {},
        "stage1": {},
        "notes": [
            "Historical seven-day uses only canonical first80. Final20 remains sealed.",
            "Current seven-day substantially overlaps five of the six Stage-1 blocks; do not sum them as independent evidence.",
            "P&L semantics differ: historical first80 uses five reset segments compounded; recent/current are continuous fresh-Rs500 terminal-equity windows; Stage-1 is six fresh-Rs500 four-hour blocks pooled additively.",
        ],
    }
    flat_rows: List[Dict] = []
    block_rows: List[Dict] = []

    for interval in ("500ms", "1s"):
        print(f"=== {interval} ===", flush=True)
        for slip in STRESS:
            print(f"historical first80 slip={slip}", flush=True)
            hist = evaluate_historical(interval, slip)
            print(f"recent24h slip={slip}", flush=True)
            recent = evaluate_continuous(RECENT, interval, slip)
            print(f"current7d slip={slip}", flush=True)
            current = evaluate_continuous(CURRENT, interval, slip)
            for dataset, result in (("historical_first80", hist), ("recent24h", recent), ("current7d", current)):
                key = f"{dataset}|{interval}|slip={slip:.2f}"
                summary["datasets"][key] = result
                for label in ("D", "H", "M"):
                    x = result[label]
                    row = {
                        "dataset": dataset, "interval": interval, "slip_usd_per_side": slip,
                        "candidate": label, "pnl_inr": x["pnl_inr"], "trades": x["trades"],
                        "wins": x["wins"], "win_rate": x["win_rate"],
                        "profit_factor": x.get("profit_factor"), "max_drawdown_inr": x["max_drawdown_inr"],
                    }
                    flat_rows.append(row)
                result["M_vs_D_pnl_delta_inr"] = float(result["M"]["pnl_inr"] - result["D"]["pnl_inr"])
                result["M_vs_H_pnl_delta_inr"] = float(result["M"]["pnl_inr"] - result["H"]["pnl_inr"])
                result["M_vs_D_relative_pct"] = pct_delta(result["M"]["pnl_inr"], result["D"]["pnl_inr"])
                result["M_vs_H_relative_pct"] = pct_delta(result["M"]["pnl_inr"], result["H"]["pnl_inr"])

        print("Stage1 blocks", flush=True)
        br, pooled = eval_stage1(interval, a.blocks)
        block_rows.extend(br)
        summary["stage1"][interval] = {"blocks": br, "pooled": pooled}
        pooled["M_vs_D_pnl_delta_inr"] = float(pooled["M"]["pnl_inr"] - pooled["D"]["pnl_inr"])
        pooled["M_vs_H_pnl_delta_inr"] = float(pooled["M"]["pnl_inr"] - pooled["H"]["pnl_inr"])

    write_csv(a.out / "dataset_candidate_comparison.csv", flat_rows)
    write_csv(a.out / "stage1_block_comparison.csv", block_rows)
    (a.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
