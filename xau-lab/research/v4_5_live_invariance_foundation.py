"""Experiment 50: outcome-blind live-invariance foundation for Candidate L.

The goal is to understand which market/execution quantities remain meaningful
across the original research regime, the current seven-day regime, and the six
now-outcome-known prospective blocks. This script intentionally does NOT load
trade P&L/outcome labels and does not choose/tune a strategy threshold.

Final20 is never read: the canonical historical source is capped by the frozen
RESEARCH_ROWS first-80% boundary.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
from v4_5_candidate_j_stage1_staged_validation import (
    build_features_all_rows,
    inspect_block,
    make_combined_csv,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OLD = ROOT / "xau_ticks_7d.csv"
DEFAULT_NEW = ROOT / "data" / "raw" / "xau_ticks_7d_current_2026-10-06.csv.gz"
DEFAULT_BLOCKS = ROOT / "data" / "prospective_restored"
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-10-06-v4_5-live-invariance-foundation"
ENGINE_NAMES = {1: "PRIMARY", 2: "SECONDARY", 3: "MICRO", 4: "BURST"}

STATE_KEYS = (
    "spread",
    "range60",
    "range300",
    "er60",
    "qacc",
    "spread_over_range60",
    "spread_over_stop4",
    "abs_m60_over_range60",
    "abs_m300_over_range300",
    "abs_m10_over_range60",
    "abs_m30_over_range60",
)

QUANTILES = (0.01, 0.05, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 0.999)


def write_csv(path: Path, rows: List[Dict]) -> None:
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


def safe_div(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    out = np.full(len(a), np.nan, dtype=float)
    mask = np.isfinite(a) & np.isfinite(b) & (np.abs(b) > 1e-12)
    out[mask] = a[mask] / b[mask]
    return out


def qstats(values: Iterable[float]) -> Dict[str, float]:
    x = np.asarray(list(values) if not isinstance(values, np.ndarray) else values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"count": 0}
    out: Dict[str, float] = {
        "count": int(len(x)),
        "mean": float(np.mean(x)),
        "std": float(np.std(x)),
        "min": float(np.min(x)),
        "max": float(np.max(x)),
    }
    for q in QUANTILES:
        label = f"p{q*100:g}".replace(".", "_")
        out[label] = float(np.quantile(x, q))
    return out


def active_hours(t: np.ndarray, *, max_gap: float = 60.0) -> float:
    if len(t) < 2:
        return 0.0
    d = np.diff(t.astype(float))
    return float(d[(d > 0) & (d < max_gap)].sum() / 3600.0)


def derived_state(arr: Dict[str, np.ndarray], start: int, end: int) -> Dict[str, np.ndarray]:
    spread = np.asarray(arr["spread"][start:end], float)
    r60 = np.asarray(arr["range60"][start:end], float)
    r300 = np.asarray(arr["range300"][start:end], float)
    m10 = np.asarray(arr["m10"][start:end], float)
    m30 = np.asarray(arr["m30"][start:end], float)
    m60 = np.asarray(arr["m60"][start:end], float)
    m300 = np.asarray(arr["m300"][start:end], float)
    er60 = np.asarray(arr["er60"][start:end], float)
    qacc = np.asarray(arr["qacc"][start:end], float)
    return {
        "spread": spread,
        "range60": r60,
        "range300": r300,
        "er60": er60,
        "qacc": qacc,
        "spread_over_range60": safe_div(spread, r60),
        "spread_over_stop4": spread / 4.0,
        "abs_m60_over_range60": safe_div(np.abs(m60), r60),
        "abs_m300_over_range300": safe_div(np.abs(m300), r300),
        "abs_m10_over_range60": safe_div(np.abs(m10), r60),
        "abs_m30_over_range60": safe_div(np.abs(m30), r60),
    }


def horizon_agreement(arr: Dict[str, np.ndarray], start: int, end: int) -> float:
    m60 = np.asarray(arr["m60"][start:end], float)
    m300 = np.asarray(arr["m300"][start:end], float)
    m1800 = np.asarray(arr["m1800"][start:end], float)
    finite = np.isfinite(m60) & np.isfinite(m300) & np.isfinite(m1800)
    nonzero = finite & (np.abs(m60) > 1e-12) & (np.abs(m300) > 1e-12) & (np.abs(m1800) > 1e-12)
    if not np.any(nonzero):
        return math.nan
    s60 = np.sign(m60[nonzero]); s300 = np.sign(m300[nonzero]); s1800 = np.sign(m1800[nonzero])
    return float(np.mean((s60 == s300) & (s300 == s1800)))


def state_summary(source: str, interval: str, arr: Dict[str, np.ndarray], start: int, end: int) -> Tuple[Dict, List[Dict]]:
    state = derived_state(arr, start, end)
    t = np.asarray(arr["t"][start:end], float)
    spread = state["spread"]
    r60 = state["range60"]

    row = {
        "source": source,
        "interval": interval,
        "sampled_rows": int(end - start),
        "active_hours_gap_lt_60s": active_hours(t),
        "horizon_60_300_1800_sign_agreement": horizon_agreement(arr, start, end),
        "pass_global_spread_cap_0_30": float(np.mean(spread <= 0.30)) if len(spread) else math.nan,
        "pass_burst_spread_cap_0_28": float(np.mean(spread <= 0.28)) if len(spread) else math.nan,
        "pass_cost_budget_spread_le_10pct_stop4": float(np.mean(spread <= 0.40)) if len(spread) else math.nan,
        "pass_micro_relative_spread_gate": float(np.mean(np.isfinite(r60) & (r60 > 0) & (spread <= 0.25 * r60))) if len(spread) else math.nan,
        "pass_burst_relative_spread_gate": float(np.mean(np.isfinite(r60) & (r60 > 0) & (spread <= 0.18 * r60))) if len(spread) else math.nan,
    }
    dist_rows: List[Dict] = []
    for key in STATE_KEYS:
        stats = qstats(state[key])
        dist_rows.append({"source": source, "interval": interval, "scope": "all_sampled_rows", "metric": key, **stats})
    return row, dist_rows


def entry_rows_for_trace(source: str, interval: str, arr: Dict[str, np.ndarray], traces: List[Tuple[float, int, int]]) -> List[Dict]:
    out: List[Dict] = []
    t = np.asarray(arr["t"], float)
    for ts, engine, side in traces:
        i = int(np.searchsorted(t, float(ts), side="left"))
        if i >= len(t) or abs(float(t[i]) - float(ts)) > 1e-6:
            i = int(np.searchsorted(t, float(ts), side="right") - 1)
        if i < 0 or i >= len(t):
            continue
        r60 = float(arr["range60"][i]); r300 = float(arr["range300"][i]); spread = float(arr["spread"][i])
        m10 = float(arr["m10"][i]); m30 = float(arr["m30"][i]); m60 = float(arr["m60"][i]); m300 = float(arr["m300"][i]); m1800 = float(arr["m1800"][i])
        def ratio(v, d):
            return float(v / d) if math.isfinite(v) and math.isfinite(d) and abs(d) > 1e-12 else math.nan
        dir60 = side * m60 if math.isfinite(m60) else math.nan
        dir300 = side * m300 if math.isfinite(m300) else math.nan
        dir1800 = side * m1800 if math.isfinite(m1800) else math.nan
        agree = bool(dir60 > 0 and dir300 > 0 and dir1800 > 0) if all(math.isfinite(x) for x in (dir60, dir300, dir1800)) else False
        out.append({
            "source": source,
            "interval": interval,
            "entry_ts": float(ts),
            "engine": ENGINE_NAMES.get(int(engine), str(engine)),
            "side": "BUY" if int(side) == 1 else "SELL",
            "spread": spread,
            "range60": r60,
            "range300": r300,
            "spread_over_range60": ratio(spread, r60),
            "spread_over_stop4": spread / 4.0,
            "dir_m10_over_range60": ratio(side * m10, r60),
            "dir_m30_over_range60": ratio(side * m30, r60),
            "dir_m60_over_range60": ratio(dir60, r60),
            "dir_m300_over_range300": ratio(dir300, r300),
            "er60": float(arr["er60"][i]),
            "qacc": float(arr["qacc"][i]),
            "all_60_300_1800_aligned": agree,
        })
    return out


def entry_summary(rows: List[Dict]) -> List[Dict]:
    if not rows:
        return []
    df = pd.DataFrame(rows)
    out: List[Dict] = []
    metrics = (
        "spread", "range60", "range300", "spread_over_range60", "spread_over_stop4",
        "dir_m10_over_range60", "dir_m30_over_range60", "dir_m60_over_range60",
        "dir_m300_over_range300", "er60", "qacc",
    )
    for (source, interval, engine), g in df.groupby(["source", "interval", "engine"], sort=False):
        base = {
            "source": source,
            "interval": interval,
            "engine": engine,
            "entries": int(len(g)),
            "aligned_60_300_1800_fraction": float(g["all_60_300_1800_aligned"].mean()),
        }
        for metric in metrics:
            stats = qstats(pd.to_numeric(g[metric], errors="coerce").to_numpy(float))
            for k, v in stats.items():
                base[f"{metric}_{k}"] = v
        out.append(base)
    return out


def four_hour_windows(source: str, interval: str, arr: Dict[str, np.ndarray], start: int, end: int) -> List[Dict]:
    t = np.asarray(arr["t"][start:end], float)
    if not len(t):
        return []
    dt = pd.to_datetime(t, unit="s", utc=True)
    bucket = dt.floor("4h")
    state = derived_state(arr, start, end)
    df = pd.DataFrame({"bucket": bucket, "t": t})
    for key in ("spread", "range60", "spread_over_range60", "spread_over_stop4", "abs_m60_over_range60", "abs_m300_over_range300", "er60", "qacc"):
        df[key] = state[key]
    out: List[Dict] = []
    for b, g in df.groupby("bucket", sort=True):
        tt = g["t"].to_numpy(float)
        ah = active_hours(tt)
        if ah < 0.5:
            continue
        row = {"source": source, "interval": interval, "window_start": b.isoformat(), "sampled_rows": int(len(g)), "active_hours": ah}
        for key in ("spread", "range60", "spread_over_range60", "spread_over_stop4", "abs_m60_over_range60", "abs_m300_over_range300", "er60", "qacc"):
            x = pd.to_numeric(g[key], errors="coerce").to_numpy(float)
            x = x[np.isfinite(x)]
            row[f"{key}_median"] = float(np.median(x)) if len(x) else math.nan
            row[f"{key}_p90"] = float(np.quantile(x, 0.90)) if len(x) else math.nan
        out.append(row)
    return out


def raw_spread_stats(path: Path, *, nrows: int | None = None) -> Dict[str, float]:
    d = pd.read_csv(path, nrows=nrows, usecols=["spread"])
    return qstats(pd.to_numeric(d["spread"], errors="coerce").to_numpy(float))


def historical_traces(arr: Dict[str, np.ndarray], bounds, interval: str) -> List[Tuple[float, int, int]]:
    traces: List[Tuple[float, int, int]] = []
    for start, end in autopsy.indices(arr, bounds):
        m = hbase.simulate(arr, start, end, candidate_h=False, capture_trace=True)
        traces.extend(m.get("entry_trace") or [])
    return traces


def whole_trace(arr: Dict[str, np.ndarray], start: int, end: int) -> List[Tuple[float, int, int]]:
    m = hbase.simulate(arr, start, end, candidate_h=False, capture_trace=True)
    return list(m.get("entry_trace") or [])


def process_dataset(source: str, path: Path, interval: str, *, historical: bool) -> Tuple[Dict, List[Dict], List[Dict], List[Dict]]:
    if historical:
        arr, bounds = canonical.build_features(path, interval)
        start, end = 0, len(arr["t"])
        traces = historical_traces(arr, bounds, interval)
    else:
        arr = build_features_all_rows(path, interval)
        start, end = 0, len(arr["t"])
        traces = whole_trace(arr, start, end)
    state_row, dist = state_summary(source, interval, arr, start, end)
    entries = entry_rows_for_trace(source, interval, arr, traces)
    windows = four_hour_windows(source, interval, arr, start, end)
    state_row["candidate_d_entries"] = int(len(entries))
    return state_row, dist, entries, windows


def process_block(session_dir: Path, interval: str, temp_dir: Path) -> Tuple[Dict, List[Dict], List[Dict], List[Dict]]:
    block = inspect_block(session_dir)
    combined = make_combined_csv(block, temp_dir)
    arr = build_features_all_rows(combined, interval)
    start_ts = block["start"].timestamp(); end_ts = block["end"].timestamp()
    start = int(np.searchsorted(arr["t"], start_ts, side="left"))
    end = int(np.searchsorted(arr["t"], end_ts, side="right"))
    source = f"stage1:{session_dir.name}"
    traces = whole_trace(arr, start, end)
    state_row, dist = state_summary(source, interval, arr, start, end)
    entries = entry_rows_for_trace(source, interval, arr, traces)
    windows = four_hour_windows(source, interval, arr, start, end)
    state_row["candidate_d_entries"] = int(len(entries))
    return state_row, dist, entries, windows


def source_comparison(state_rows: List[Dict], dist_rows: List[Dict]) -> Dict:
    summary: Dict = {"gate_pressure": {}, "median_drift": {}}
    for row in state_rows:
        key = f"{row['source']}|{row['interval']}"
        summary["gate_pressure"][key] = {
            k: row[k] for k in row
            if k.startswith("pass_") or k in ("candidate_d_entries", "horizon_60_300_1800_sign_agreement", "active_hours_gap_lt_60s")
        }
    df = pd.DataFrame(dist_rows)
    med_col = "p50"
    if med_col in df.columns:
        for interval in sorted(df.interval.unique()):
            for metric in STATE_KEYS:
                g = df[(df.interval == interval) & (df.metric == metric)]
                vals = {str(r.source): float(getattr(r, med_col)) for r in g.itertuples() if math.isfinite(float(getattr(r, med_col)))}
                if vals:
                    summary["median_drift"][f"{interval}|{metric}"] = vals
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--historical", type=Path, default=DEFAULT_OLD)
    ap.add_argument("--current", type=Path, default=DEFAULT_NEW)
    ap.add_argument("--prospective-root", type=Path, default=DEFAULT_BLOCKS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    a.output.mkdir(parents=True, exist_ok=True)
    state_rows: List[Dict] = []
    dist_rows: List[Dict] = []
    entry_rows: List[Dict] = []
    window_rows: List[Dict] = []

    raw_summary = {
        "historical_first80_raw_spread": raw_spread_stats(a.historical, nrows=canonical.RESEARCH_ROWS),
        "current7d_raw_spread": raw_spread_stats(a.current),
    }

    for interval in ("500ms", "1s"):
        print(f"{interval}: historical first80", flush=True)
        s, d, e, w = process_dataset("historical_first80", a.historical, interval, historical=True)
        state_rows.append(s); dist_rows.extend(d); entry_rows.extend(e); window_rows.extend(w)

        print(f"{interval}: current7d", flush=True)
        s, d, e, w = process_dataset("current7d", a.current, interval, historical=False)
        state_rows.append(s); dist_rows.extend(d); entry_rows.extend(e); window_rows.extend(w)

        with tempfile.TemporaryDirectory(prefix="xau-invariance-") as td:
            temp = Path(td)
            for session_dir in sorted(p for p in a.prospective_root.iterdir() if p.is_dir()):
                if not (session_dir / "block_manifest.json").exists():
                    continue
                print(f"{interval}: {session_dir.name}", flush=True)
                s, d, e, w = process_block(session_dir, interval, temp)
                state_rows.append(s); dist_rows.extend(d); entry_rows.extend(e); window_rows.extend(w)

    e_summary = entry_summary(entry_rows)
    comparison = source_comparison(state_rows, dist_rows)

    write_csv(a.output / "state_source_summary.csv", state_rows)
    write_csv(a.output / "state_distributions.csv", dist_rows)
    write_csv(a.output / "candidate_d_entry_states.csv", entry_rows)
    write_csv(a.output / "candidate_d_entry_state_summary.csv", e_summary)
    write_csv(a.output / "four_hour_state_windows.csv", window_rows)

    summary = {
        "schema": "xau-v4-5-live-invariance-foundation-v1",
        "status": "outcome-blind representation/execution diagnostic",
        "pnl_labels_loaded": False,
        "strategy_changed": False,
        "threshold_search": False,
        "final20_opened": False,
        "historical_rows_cap": int(canonical.RESEARCH_ROWS),
        "raw_spread": raw_summary,
        "sources": state_rows,
        "comparison": comparison,
        "candidate_d_entry_state_groups": len(e_summary),
        "four_hour_state_windows": len(window_rows),
        "interpretation_rule": "Use this only to design causal/live-computable structure. Do not select a threshold by past P&L.",
    }
    (a.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
