"""Frozen Experiment-58 causal feature/label schema for Candidate-M entries."""
from __future__ import annotations

import math
from typing import Dict

import numpy as np

import v4_5_microstate_v1_freeze as microstate

HORIZONS = (2.0, 5.0, 10.0, 30.0, 60.0, 120.0)
SCHEMA = "xau-exp58-m-acceptance-discrimination-v1"
PLAN_REF = "docs/plans/V4_5_M_ACCEPTANCE_DISCRIMINATION_SHADOW.md"


def value(arr: Dict[str, np.ndarray], key: str, i: int) -> float:
    if key not in arr:
        return math.nan
    try:
        return float(arr[key][i])
    except Exception:
        return math.nan


def safe_div(a: float, b: float) -> float:
    return float(a / b) if math.isfinite(a) and math.isfinite(b) and abs(b) > 1e-12 else math.nan


def prior_value(t: np.ndarray, x: np.ndarray, i: int, seconds: float) -> float:
    j = int(np.searchsorted(t, float(t[i]) - seconds, side="left"))
    j = min(max(0, j), i)
    return float(x[j])


def crossing_count(values: np.ndarray, threshold: float) -> int:
    if len(values) < 2:
        return 0
    signs = np.sign(values - threshold)
    signs[signs == 0] = 1
    return int(np.sum(signs[1:] != signs[:-1]))


def future_labels(arr: Dict[str, np.ndarray], i: int, side: int, entry_px: float) -> Dict:
    t = np.asarray(arr["t"], float)
    bid = np.asarray(arr["bid"], float)
    ask = np.asarray(arr["ask"], float)
    mid = np.asarray(arr["mid"], float)
    out: Dict = {}
    for horizon in HORIZONS:
        target = float(t[i]) + horizon
        end = min(max(i + 1, int(np.searchsorted(t, target, side="right"))), len(t))
        mids = mid[i:end]
        exits = bid[i:end] if side == 1 else ask[i:end]
        exec_move = exits - entry_px if side == 1 else entry_px - exits
        mid_move = side * (mids - float(mid[i]))
        segment_t = t[i:end]
        continuity_ok = bool(len(segment_t) < 2 or float(np.max(np.diff(segment_t))) <= 5.0)
        suffix = str(int(horizon))
        out[f"label_complete_{suffix}s"] = bool(float(t[-1]) >= target and continuity_ok)
        out[f"label_observed_sec_{suffix}s"] = float(t[end - 1] - t[i])
        out[f"label_exec_mfe_usd_{suffix}s"] = float(np.max(exec_move))
        out[f"label_exec_mae_usd_{suffix}s"] = float(np.min(exec_move))
        out[f"label_exec_end_move_usd_{suffix}s"] = float(exec_move[-1])
        out[f"label_mid_mfe_usd_{suffix}s"] = float(np.max(mid_move))
        out[f"label_mid_mae_usd_{suffix}s"] = float(np.min(mid_move))
        out[f"label_mid_end_move_usd_{suffix}s"] = float(mid_move[-1])
    return out


def entry_feature_row(
    arr: Dict[str, np.ndarray], i: int, side: int, *, arm_time: float,
    arm_anchor: float, arm_spread: float, accept_since: float,
    arm_qacc: float, arm_mid: float, acceptance_timer_resets: int,
    flow_feat: Dict[str, float], entry_px: float,
) -> Dict:
    t = np.asarray(arr["t"], float)
    mid = np.asarray(arr["mid"], float)
    spread = value(arr, "spread", i)
    r60 = value(arr, "range60", i)
    r300 = value(arr, "range300", i)
    qacc = value(arr, "qacc", i)
    ts = float(t[i])

    lo5 = int(np.searchsorted(t, ts - 5.0, side="left"))
    dir_anchor = side * (mid[lo5:i + 1] - arm_anchor)
    lo_accept = int(np.searchsorted(t, accept_since, side="left"))
    accept_margin = side * (mid[lo_accept:i + 1] - arm_anchor) - arm_spread

    row = {
        "schema": SCHEMA, "entry_ts": ts,
        "side": "BUY" if side == 1 else "SELL", "side_int": int(side),
        "entry_px": float(entry_px),
        "feature_arm_age_sec": float(ts - arm_time),
        "feature_accept_age_sec": float(ts - accept_since),
        "feature_arm_anchor": float(arm_anchor),
        "feature_arm_spread_usd": float(arm_spread),
        "feature_entry_spread_usd": spread,
        "feature_spread_over_arm_spread": safe_div(spread, arm_spread),
        "feature_range60_usd": r60, "feature_range300_usd": r300,
        "feature_spread_over_range60": safe_div(spread, r60),
        "feature_accept_distance_usd": float(side * (mid[i] - arm_anchor)),
        "feature_accept_distance_arm_spreads": safe_div(float(side * (mid[i] - arm_anchor)), arm_spread),
        "feature_accept_excess_usd": float(side * (mid[i] - arm_anchor) - arm_spread),
        "feature_accept_excess_arm_spreads": safe_div(float(side * (mid[i] - arm_anchor) - arm_spread), arm_spread),
        "feature_accept_min_excess_usd": float(np.min(accept_margin)),
        "feature_accept_mean_excess_usd": float(np.mean(accept_margin)),
        "feature_accept_max_excess_usd": float(np.max(accept_margin)),
        "feature_anchor_crosses_5s": crossing_count(dir_anchor, 0.0),
        "feature_accept_level_crosses_5s": crossing_count(dir_anchor, arm_spread),
        "feature_qacc": qacc, "feature_qacc_at_arm": arm_qacc,
        "feature_qacc_delta_from_arm": qacc - arm_qacc if math.isfinite(qacc) and math.isfinite(arm_qacc) else math.nan,
        "feature_dir_mid_from_arm_usd": float(side * (mid[i] - arm_mid)),
        "feature_dir_mid_move_2s_sampled": float(side * (mid[i] - prior_value(t, mid, i, 2.0))),
        "feature_dir_mid_move_5s_sampled": float(side * (mid[i] - prior_value(t, mid, i, 5.0))),
        "feature_dir_mid_move_10s_sampled": float(side * (mid[i] - prior_value(t, mid, i, 10.0))),
        "feature_acceptance_timer_resets_since_arm": int(acceptance_timer_resets),
    }
    for key in ("m10", "m30", "m60", "m300", "m1800"):
        x = value(arr, key, i)
        row[f"feature_{key}_usd"] = x
        row[f"feature_dir_{key}_usd"] = float(side * x) if math.isfinite(x) else math.nan
    row["feature_dir_m10_over_range60"] = safe_div(side * value(arr, "m10", i), r60)
    row["feature_dir_m30_over_range60"] = safe_div(side * value(arr, "m30", i), r60)
    row["feature_dir_m60_over_range60"] = safe_div(side * value(arr, "m60", i), r60)
    row["feature_dir_m300_over_range300"] = safe_div(side * value(arr, "m300", i), r300)
    for key in microstate.FEATURES:
        row[f"feature_micro_{key}"] = float(flow_feat.get(key, math.nan))
    return row
