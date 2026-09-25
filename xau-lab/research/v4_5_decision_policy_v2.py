"""Experiment 39: Decision Policy v2.

Structural changes from Experiment 38:
  * learn entry timing across complete cooldown-free signal episodes;
  * add causal trajectory-delta features to exit state;
  * predict 30-second incremental continuation value;
  * require two consecutive non-positive exit predictions;
  * compare one fixed +1R / 50%-MFE profit ratchet.

No model/threshold/hyperparameter search is performed. Known data are diagnostic
only and final20 remains sealed.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_decision_policy_v1 as v1
import v4_5_independent_opportunity_atlas as atlasmod
import v4_5_microstate_v1_freeze as microstate
import v4_5_regime_portability as portability
import v4_5_router_v2 as router
import v4_5_state_v2_freeze as state_v2

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_V1_DIR = ROOT / "results" / "simulations" / "2026-09-25-v4_5-decision-policy-v1"
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-09-25-v4_5-decision-policy-v2"

ENTRY_CHECKPOINT_SEC = 2.0
EXIT_FORWARD_SEC = 30.0
EXIT_NEGATIVE_CONFIRMATIONS = 2
RATCHET_TRIGGER_R = 1.0
RATCHET_RETAIN_FRACTION = 0.50

ENGINES = (1, 2, 3, 4)
ENGINE_NAMES = router.ENGINE_NAMES
MODEL_PARAMS = dict(v1.MODEL_PARAMS)

EPISODE_FEATURES = (
    "episode_age_sec",
    "episode_checkpoint_index",
    "simultaneous_engine_count",
    "same_side_engine_count",
)
ENTRY_FEATURE_NAMES = (
    list(v1.ENTRY_CONT_FEATURES)
    + [f"engine_{name}" for name in v1.ENGINES]
    + ["interval_1s"]
    + list(EPISODE_FEATURES)
)

SEQUENCE_FEATURES = (
    "move_delta_5",
    "move_delta_15",
    "move_delta_30",
    "pnl_velocity_15_inr_per_sec",
    "mfe_growth_15",
    "mfe_growth_30",
    "giveback_delta_5",
    "giveback_delta_15",
    "giveback_speed_15_usd_per_sec",
    "dir_mid_move2_delta_5",
    "dir_mid_move2_delta_15",
    "dir_event_imb2_delta_5",
    "dir_event_imb2_delta_15",
    "event_rate_accel_delta_15",
    "spread_rel10_delta_15",
    "activity_rel_delta_15",
    "flow_align10_delta_15",
)
EXIT_FEATURE_NAMES = list(v1.EXIT_FEATURE_NAMES) + list(SEQUENCE_FEATURES)


def write_csv(path: Path, rows: List[Dict]):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: List[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def engine_max_hold(engine: int, highopen: bool) -> float:
    cfg = canonical.burst_config("v4_5_b")
    if engine == 4:
        return float(cfg[12])
    if engine == 2 and highopen:
        return 1200.0
    if engine == 1 and not highopen:
        return 1800.0
    return 900.0


def simulate_exact_entry(
    arr: Dict[str, np.ndarray],
    start: int,
    end: int,
    engine: int,
    side: int,
) -> Dict:
    """Fixed-size independent counterfactual using Candidate-D lifecycle."""
    t, bid, ask = arr["t"], arr["bid"], arr["ask"]
    m30, m300 = arr["m30"], arr["m300"]
    r300, er60 = arr["range300"], arr["er60"]
    cfg = canonical.burst_config("v4_5_b")

    entry = float(ask[start] if side == 1 else bid[start])
    oz0 = float(atlasmod.fixed_oz(entry))
    oz = oz0
    ptime = float(t[start])
    peak = 0.0
    trough = 0.0
    partial = 0.0
    partial_done = 0
    failure_since = -1e30
    highopen = bool(
        np.isfinite(r300[start])
        and np.isfinite(er60[start])
        and r300[start] >= 5.0
        and er60[start] >= 0.03
    )

    for i in range(start + 1, end):
        ts = float(t[i])
        move = float((bid[i] - entry) if side == 1 else (entry - ask[i]))
        held = ts - ptime
        peak = max(peak, move)
        trough = min(trough, move)

        if engine == 3 and partial_done == 0 and move >= 5.5:
            closeoz = oz * 0.75
            partial += move * closeoz * canonical.INR_PER_USD
            oz -= closeoz
            partial_done = 1

        reason = 0
        rev = 1
        trig = -1.0
        gb = 0.0
        tp = 12.0
        maxhold = engine_max_hold(engine, highopen)

        if engine == 3:
            tp = 10.0
            trig = 4.0
            gb = 2.0
        elif engine == 4:
            tp = float(cfg[11])
            trig = float(cfg[15])
            gb = float(cfg[16])
            rev = 0
        elif engine == 1 and highopen:
            tp = 25.0
            rev = 0
        elif engine == 2 and highopen:
            tp = 8.0
            trig = 12.0
            gb = 3.0
            rev = 0
        elif engine == 1:
            tp = 21.0

        if move <= -4.0:
            reason = 1
        elif move >= tp:
            reason = 2
        if reason == 0 and trig > 0 and peak >= trig and move <= peak - gb:
            reason = 3
        if reason == 0 and engine == 3 and held >= 45.0 and peak < 0.75:
            reason = 4
        if reason == 0 and engine == 4 and held >= cfg[13] and peak < cfg[14]:
            reason = 4

        if engine == 4 and not np.isfinite(m30[i]):
            failure_since = -1e30
        if reason == 0 and engine == 4 and np.isfinite(m30[i]):
            failure = (side == 1 and m30[i] <= 0) or (side == -1 and m30[i] >= 0)
            if failure:
                if failure_since < -1e20:
                    failure_since = ts
                if ts - failure_since >= 1.0:
                    reason = 5
            else:
                failure_since = -1e30

        if reason == 0 and rev == 1 and np.isfinite(m300[i]):
            if (side == 1 and m300[i] <= 0) or (side == -1 and m300[i] >= 0):
                reason = 5
        if reason == 0 and held >= maxhold:
            reason = 7

        if reason:
            pnl = move * oz * canonical.INR_PER_USD + partial
            return {
                "counterfactual_pnl_inr": float(pnl),
                "counterfactual_hold_sec": float(held),
                "counterfactual_mfe_usd": float(peak),
                "counterfactual_mae_usd": float(trough),
                "counterfactual_exit_reason": atlasmod.REASONS.get(reason, str(reason)),
                "censored": False,
            }

    j = end - 1
    if j <= start:
        return {
            "counterfactual_pnl_inr": 0.0,
            "counterfactual_hold_sec": 0.0,
            "counterfactual_mfe_usd": peak,
            "counterfactual_mae_usd": trough,
            "counterfactual_exit_reason": "terminal_mark",
            "censored": True,
        }
    move = float((bid[j] - entry) if side == 1 else (entry - ask[j]))
    peak = max(peak, move)
    trough = min(trough, move)
    pnl = move * oz * canonical.INR_PER_USD + partial
    return {
        "counterfactual_pnl_inr": float(pnl),
        "counterfactual_hold_sec": float(t[j] - ptime),
        "counterfactual_mfe_usd": float(peak),
        "counterfactual_mae_usd": float(trough),
        "counterfactual_exit_reason": "terminal_mark",
        "censored": True,
    }


def signal_episode_checkpoints(
    arr: Dict[str, np.ndarray],
    ranges: List[Tuple[int, int]],
    interval: str,
    window: str,
) -> List[Dict]:
    rows: List[Dict] = []
    episode_counter = 0

    for sid, (start, end) in enumerate(ranges):
        active: Dict[int, Dict] = {}
        prev_ss = None
        cont = 0.0
        fake_last = {1: -1e30, 2: -1e30, 3: -1e30, 4: -1e30}

        for i in range(start, end):
            ts = float(arr["t"][i])
            ss = int(arr["ss"][i])
            if prev_ss is None or ss != prev_ss:
                active.clear()
                cont = ts
                prev_ss = ss

            candidates = router.signal_candidates(arr, i, cont, fake_last)
            cmap = {int(e): int(side) for e, side in candidates}
            same_side_count = {
                side: sum(1 for _, s in candidates if int(s) == side)
                for side in (-1, 1)
            }

            for engine in ENGINES:
                side = cmap.get(engine)
                if side is None:
                    active.pop(engine, None)
                    continue

                cur = active.get(engine)
                if cur is None or int(cur["side"]) != side:
                    episode_counter += 1
                    cur = {
                        "episode_id": f"{window}|{interval}|{sid}|{engine}|{episode_counter}",
                        "side": side,
                        "start_ts": ts,
                        "last_checkpoint_ts": -1e30,
                        "checkpoint_index": 0,
                    }
                    active[engine] = cur

                if (
                    cur["checkpoint_index"] == 0
                    or ts - float(cur["last_checkpoint_ts"]) >= ENTRY_CHECKPOINT_SEC
                ):
                    rows.append({
                        "window": window,
                        "interval": interval,
                        "segment_id": sid,
                        "engine_id": engine,
                        "engine": ENGINE_NAMES[engine],
                        "side": "BUY" if side == 1 else "SELL",
                        "side_sign": side,
                        "episode_id": cur["episode_id"],
                        "episode_start_ts": float(cur["start_ts"]),
                        "episode_age_sec": float(ts - float(cur["start_ts"])),
                        "episode_checkpoint_index": int(cur["checkpoint_index"]),
                        "simultaneous_engine_count": int(len(candidates)),
                        "same_side_engine_count": int(same_side_count.get(side, 0)),
                        "entry_index": int(i),
                        "entry_ts": ts,
                        "segment_end_index": int(end),
                    })
                    cur["last_checkpoint_ts"] = ts
                    cur["checkpoint_index"] += 1
    return rows


def build_entry_episode_dataset(
    canonical_csv: Path,
    recent_csv: Path,
    hraw: Dict[str, np.ndarray],
    rraw: Dict[str, np.ndarray],
) -> pd.DataFrame:
    rows: List[Dict] = []
    by_window: Dict[str, List[Dict]] = {"historical7d": [], "recent24h": []}

    for interval in v1.INTERVALS:
        h_arr, h_bounds = canonical.build_features(canonical_csv, interval)
        h_ranges = autopsy.indices(h_arr, h_bounds)
        hrows = signal_episode_checkpoints(h_arr, h_ranges, interval, "historical7d")
        print(f"{interval}: historical episode checkpoints {len(hrows)}", flush=True)
        for r in hrows:
            r.update(
                simulate_exact_entry(
                    h_arr,
                    int(r["entry_index"]),
                    int(r["segment_end_index"]),
                    int(r["engine_id"]),
                    int(r["side_sign"]),
                )
            )
        by_window["historical7d"].extend(hrows)

        r_arr, _ = canonical.build_features(recent_csv, interval)
        r_ranges = [(0, len(r_arr["t"]))]
        rrows = signal_episode_checkpoints(r_arr, r_ranges, interval, "recent24h")
        print(f"{interval}: recent episode checkpoints {len(rrows)}", flush=True)
        for r in rrows:
            r.update(
                simulate_exact_entry(
                    r_arr,
                    int(r["entry_index"]),
                    int(r["segment_end_index"]),
                    int(r["engine_id"]),
                    int(r["side_sign"]),
                )
            )
        by_window["recent24h"].extend(rrows)

    for window, path, raw in (
        ("historical7d", canonical_csv, hraw),
        ("recent24h", recent_csv, rraw),
    ):
        base = by_window[window]
        print(f"enriching {window} entry episode states: {len(base)}", flush=True)
        enriched = state_v2.overlay(path, base, window)
        for row in enriched:
            row.update(
                microstate.features_at(
                    raw, float(row["entry_ts"]), int(row["side_sign"])
                )
            )
            rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        cens = df["censored"].astype(str).str.lower().eq("true")
        df = df.loc[~cens].copy()
        df["segment_id"] = pd.to_numeric(df.segment_id).astype(int)
    return df


def make_entry_matrix(df: pd.DataFrame) -> np.ndarray:
    blocks = [
        pd.to_numeric(df[col], errors="coerce").to_numpy(float)[:, None]
        for col in v1.ENTRY_CONT_FEATURES
    ]
    eng = df.engine.astype(str).to_numpy()
    for name in v1.ENGINES:
        blocks.append((eng == name).astype(float)[:, None])
    blocks.append((df.interval.astype(str).to_numpy() == "1s").astype(float)[:, None])
    for col in EPISODE_FEATURES:
        blocks.append(pd.to_numeric(df[col], errors="coerce").to_numpy(float)[:, None])
    return np.hstack(blocks)


def episode_weights(df: pd.DataFrame) -> np.ndarray:
    counts = df.groupby("episode_id")["episode_id"].transform("count").to_numpy(float)
    return np.divide(1.0, counts, out=np.ones_like(counts), where=counts > 0)


def fit_entry(train: pd.DataFrame):
    x = make_entry_matrix(train)
    y = pd.to_numeric(train.counterfactual_pnl_inr, errors="coerce").to_numpy(float)
    model = HistGradientBoostingRegressor(**MODEL_PARAMS)
    model.fit(x, y, sample_weight=episode_weights(train))
    return model


def entry_walkforward(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for fold, train_segments, test_segments in v1.fold_specs():
        train = df[
            (df.window == "historical7d") & (df.segment_id.isin(train_segments))
        ]
        test = df[
            (df.window == "historical7d") & (df.segment_id.isin(test_segments))
        ]
        if train.empty or test.empty:
            continue
        model = fit_entry(train)
        pred = model.predict(make_entry_matrix(test))
        for row, p in zip(test.to_dict("records"), pred):
            out.append({
                "label": "historical_walkforward",
                "fold": fold,
                "episode_id": row["episode_id"],
                "window": row["window"],
                "interval": row["interval"],
                "segment_id": int(row["segment_id"]),
                "engine": row["engine"],
                "side": row["side"],
                "entry_ts": float(row["entry_ts"]),
                "episode_age_sec": float(row["episode_age_sec"]),
                "episode_checkpoint_index": int(row["episode_checkpoint_index"]),
                "actual_pnl_inr": float(row["counterfactual_pnl_inr"]),
                "predicted_entry_ev_inr": float(p),
            })

    train = df[df.window == "historical7d"]
    test = df[df.window == "recent24h"]
    model = fit_entry(train)
    pred = model.predict(make_entry_matrix(test))
    for row, p in zip(test.to_dict("records"), pred):
        out.append({
            "label": "recent_after_first80",
            "fold": "whole_recent",
            "episode_id": row["episode_id"],
            "window": row["window"],
            "interval": row["interval"],
            "segment_id": int(row["segment_id"]),
            "engine": row["engine"],
            "side": row["side"],
            "entry_ts": float(row["entry_ts"]),
            "episode_age_sec": float(row["episode_age_sec"]),
            "episode_checkpoint_index": int(row["episode_checkpoint_index"]),
            "actual_pnl_inr": float(row["counterfactual_pnl_inr"]),
            "predicted_entry_ev_inr": float(p),
        })
    return pd.DataFrame(out)


def episode_policy(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if pred.empty:
        return pd.DataFrame(rows)
    for (label, episode_id), g in pred.groupby(["label", "episode_id"], sort=True):
        g = g.sort_values(["episode_age_sec", "entry_ts"])
        onset = g.iloc[0]
        q = g[g.predicted_entry_ev_inr > 0]
        chosen = q.iloc[0] if len(q) else None
        rows.append({
            "label": label,
            "episode_id": episode_id,
            "window": onset.window,
            "interval": onset.interval,
            "segment_id": int(onset.segment_id),
            "engine": onset.engine,
            "side": onset.side,
            "onset_pnl_inr": float(onset.actual_pnl_inr),
            "onset_entry_ts": float(onset.entry_ts),
            "policy_action": "TAKE" if chosen is not None else "SKIP",
            "policy_entry_ts": float(chosen.entry_ts) if chosen is not None else math.nan,
            "policy_wait_sec": float(chosen.episode_age_sec) if chosen is not None else math.nan,
            "policy_predicted_ev_inr": float(chosen.predicted_entry_ev_inr) if chosen is not None else 0.0,
            "policy_pnl_inr": float(chosen.actual_pnl_inr) if chosen is not None else 0.0,
            "episode_checkpoints": int(len(g)),
        })
    return pd.DataFrame(rows)


def episode_policy_metrics(policy: pd.DataFrame) -> List[Dict]:
    out = []
    if policy.empty:
        return out
    for (label, interval), g in policy.groupby(["label", "interval"], sort=True):
        base = pd.to_numeric(g.onset_pnl_inr).to_numpy(float)
        pp = pd.to_numeric(g.policy_pnl_inr).to_numpy(float)
        take = g.policy_action.eq("TAKE").to_numpy()
        waits = pd.to_numeric(g.policy_wait_sec, errors="coerce").to_numpy(float)
        out.append({
            "label": label,
            "interval": interval,
            "episodes": len(g),
            "onset_entry_pnl_inr": float(base.sum()),
            "episode_policy_pnl_inr": float(pp.sum()),
            "delta_policy_vs_onset_inr": float((pp - base).sum()),
            "taken_episodes": int(take.sum()),
            "episode_retention": float(take.mean()) if len(take) else 0.0,
            "onset_win_rate": float(np.mean(base > 0)) if len(base) else 0.0,
            "policy_taken_win_rate": float(np.mean(pp[take] > 0)) if take.any() else 0.0,
            "median_wait_sec_taken": float(np.nanmedian(waits[take])) if take.any() else math.nan,
        })
    return out


def nearest_previous(g: pd.DataFrame, i: int, seconds: float):
    cur = float(g.iloc[i].hold_sec)
    q = g.iloc[:i]
    q = q[pd.to_numeric(q.hold_sec) <= cur - seconds]
    return q.iloc[-1] if len(q) else None


def add_exit_sequence_features(snapshots: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, g in snapshots.groupby("trade_id", sort=False):
        g = g.sort_values("hold_sec").reset_index(drop=True)
        for i in range(len(g)):
            row = g.iloc[i].to_dict()
            p5 = nearest_previous(g, i, 5.0)
            p15 = nearest_previous(g, i, 15.0)
            p30 = nearest_previous(g, i, 30.0)

            def delta(col, prev):
                if prev is None:
                    return math.nan
                a = float(row.get(col, math.nan))
                b = float(prev.get(col, math.nan))
                return a - b if math.isfinite(a) and math.isfinite(b) else math.nan

            row.update({
                "move_delta_5": delta("current_move_usd", p5),
                "move_delta_15": delta("current_move_usd", p15),
                "move_delta_30": delta("current_move_usd", p30),
                "pnl_velocity_15_inr_per_sec": (
                    delta("current_mark_equity_pnl_inr", p15) / 15.0
                    if p15 is not None
                    else math.nan
                ),
                "mfe_growth_15": delta("mfe_usd_live", p15),
                "mfe_growth_30": delta("mfe_usd_live", p30),
                "giveback_delta_5": delta("giveback_usd", p5),
                "giveback_delta_15": delta("giveback_usd", p15),
                "giveback_speed_15_usd_per_sec": (
                    delta("giveback_usd", p15) / 15.0
                    if p15 is not None
                    else math.nan
                ),
                "dir_mid_move2_delta_5": delta("dir_mid_move2", p5),
                "dir_mid_move2_delta_15": delta("dir_mid_move2", p15),
                "dir_event_imb2_delta_5": delta("dir_event_imb2", p5),
                "dir_event_imb2_delta_15": delta("dir_event_imb2", p15),
                "event_rate_accel_delta_15": delta("event_rate_accel_2_10", p15),
                "spread_rel10_delta_15": delta("spread_rel10", p15),
                "activity_rel_delta_15": delta("activity_rel", p15),
                "flow_align10_delta_15": delta("flow_align10", p15),
            })

            cur_hold = float(row["hold_sec"])
            future = g[pd.to_numeric(g.hold_sec) >= cur_hold + EXIT_FORWARD_SEC]
            if len(future):
                future_equity = float(future.iloc[0].current_mark_equity_pnl_inr)
            else:
                future_equity = float(row["legacy_final_pnl_inr"])
            row["forward_30s_value_inr"] = (
                future_equity - float(row["current_mark_equity_pnl_inr"])
            )
            rows.append(row)
    return pd.DataFrame(rows)


def make_exit_matrix(df: pd.DataFrame) -> np.ndarray:
    base = v1.make_matrix(df, exit_model=True)
    seq = np.hstack([
        pd.to_numeric(df[col], errors="coerce").to_numpy(float)[:, None]
        for col in SEQUENCE_FEATURES
    ])
    return np.hstack([base, seq])


def fit_exit(train: pd.DataFrame):
    x = make_exit_matrix(train)
    y = pd.to_numeric(train.forward_30s_value_inr, errors="coerce").to_numpy(float)
    model = HistGradientBoostingRegressor(**MODEL_PARAMS)
    model.fit(x, y, sample_weight=v1.exit_weights(train))
    return model


def exit_walkforward(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for fold, train_segments, test_segments in v1.fold_specs():
        train = df[
            (df.window == "historical7d") & (df.segment_id.isin(train_segments))
        ]
        test = df[
            (df.window == "historical7d") & (df.segment_id.isin(test_segments))
        ]
        if train.empty or test.empty:
            continue
        model = fit_exit(train)
        pred = model.predict(make_exit_matrix(test))
        for row, p in zip(test.to_dict("records"), pred):
            rows.append({
                "label": "historical_walkforward",
                "fold": fold,
                "trade_id": row["trade_id"],
                "window": row["window"],
                "interval": row["interval"],
                "segment_id": int(row["segment_id"]),
                "engine": row["engine"],
                "side": row["side"],
                "hold_sec": float(row["hold_sec"]),
                "snapshot_ts": float(row["snapshot_ts"]),
                "current_mark_equity_pnl_inr": float(row["current_mark_equity_pnl_inr"]),
                "legacy_final_pnl_inr": float(row["legacy_final_pnl_inr"]),
                "forward_30s_value_inr": float(row["forward_30s_value_inr"]),
                "predicted_forward_30s_ev_inr": float(p),
                "current_r": float(row["current_r"]),
                "mfe_r": float(row["mfe_r"]),
                "giveback_r": float(row["giveback_r"]),
            })

    train = df[df.window == "historical7d"]
    test = df[df.window == "recent24h"]
    model = fit_exit(train)
    pred = model.predict(make_exit_matrix(test))
    for row, p in zip(test.to_dict("records"), pred):
        rows.append({
            "label": "recent_after_first80",
            "fold": "whole_recent",
            "trade_id": row["trade_id"],
            "window": row["window"],
            "interval": row["interval"],
            "segment_id": int(row["segment_id"]),
            "engine": row["engine"],
            "side": row["side"],
            "hold_sec": float(row["hold_sec"]),
            "snapshot_ts": float(row["snapshot_ts"]),
            "current_mark_equity_pnl_inr": float(row["current_mark_equity_pnl_inr"]),
            "legacy_final_pnl_inr": float(row["legacy_final_pnl_inr"]),
            "forward_30s_value_inr": float(row["forward_30s_value_inr"]),
            "predicted_forward_30s_ev_inr": float(p),
            "current_r": float(row["current_r"]),
            "mfe_r": float(row["mfe_r"]),
            "giveback_r": float(row["giveback_r"]),
        })
    return pd.DataFrame(rows)


def exit_prediction_metrics(pred: pd.DataFrame) -> List[Dict]:
    out = []
    if pred.empty:
        return out
    for (label, interval), g in pred.groupby(["label", "interval"], sort=True):
        y = pd.to_numeric(g.forward_30s_value_inr).to_numpy(float)
        p = pd.to_numeric(g.predicted_forward_30s_ev_inr).to_numpy(float)
        out.append({
            "label": label,
            "interval": interval,
            "snapshots": len(g),
            "pearson": v1.corr(p, y),
            "spearman": v1.spearman(p, y),
            "sign_accuracy": float(np.mean((p > 0) == (y > 0))),
            "predicted_positive_fraction": float(np.mean(p > 0)),
            "actual_forward_value_sum_inr": float(y.sum()),
        })
    return out


def confirmed_exit_policy(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if pred.empty:
        return pd.DataFrame(rows)
    for (label, tid), g in pred.groupby(["label", "trade_id"], sort=True):
        g = g.sort_values("hold_sec")
        neg = 0
        chosen = None
        for _, row in g.iterrows():
            if float(row.predicted_forward_30s_ev_inr) <= 0:
                neg += 1
            else:
                neg = 0
            if neg >= EXIT_NEGATIVE_CONFIRMATIONS:
                chosen = row
                break
        first = g.iloc[0]
        baseline = float(first.legacy_final_pnl_inr)
        policy = float(chosen.current_mark_equity_pnl_inr) if chosen is not None else baseline
        rows.append({
            "label": label,
            "trade_id": tid,
            "window": first.window,
            "interval": first.interval,
            "segment_id": int(first.segment_id),
            "engine": first.engine,
            "side": first.side,
            "legacy_pnl_inr": baseline,
            "policy_pnl_inr": policy,
            "delta_inr": policy - baseline,
            "model_exit": chosen is not None,
            "model_exit_hold_sec": float(chosen.hold_sec) if chosen is not None else math.nan,
        })
    return pd.DataFrame(rows)


def ratchet_policy(
    snapshots: pd.DataFrame,
    represented: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    if represented.empty:
        return pd.DataFrame(rows)
    labels = {
        tid: str(represented.loc[represented.trade_id == tid, "label"].iloc[0])
        for tid in represented.trade_id.unique()
    }
    for tid, label in labels.items():
        g = snapshots[snapshots.trade_id == tid].sort_values("hold_sec")
        if g.empty:
            continue
        first = g.iloc[0]
        q = g[
            (pd.to_numeric(g.mfe_r) >= RATCHET_TRIGGER_R)
            & (
                pd.to_numeric(g.current_r)
                <= RATCHET_RETAIN_FRACTION * pd.to_numeric(g.mfe_r)
            )
        ]
        chosen = q.iloc[0] if len(q) else None
        baseline = float(first.legacy_final_pnl_inr)
        policy = float(chosen.current_mark_equity_pnl_inr) if chosen is not None else baseline
        rows.append({
            "label": label,
            "trade_id": tid,
            "window": first.window,
            "interval": first.interval,
            "segment_id": int(first.segment_id),
            "engine": first.engine,
            "side": first.side,
            "legacy_pnl_inr": baseline,
            "policy_pnl_inr": policy,
            "delta_inr": policy - baseline,
            "ratchet_exit": chosen is not None,
            "ratchet_exit_hold_sec": float(chosen.hold_sec) if chosen is not None else math.nan,
        })
    return pd.DataFrame(rows)


def policy_metrics(df: pd.DataFrame, action_col: str, prefix: str) -> List[Dict]:
    out = []
    if df.empty:
        return out
    for (label, interval), g in df.groupby(["label", "interval"], sort=True):
        base = pd.to_numeric(g.legacy_pnl_inr).to_numpy(float)
        pp = pd.to_numeric(g.policy_pnl_inr).to_numpy(float)
        delta = pp - base
        act = g[action_col].astype(bool).to_numpy()
        out.append({
            "policy": prefix,
            "label": label,
            "interval": interval,
            "trades": len(g),
            "legacy_pnl_inr": float(base.sum()),
            "policy_pnl_inr": float(pp.sum()),
            "delta_inr": float(delta.sum()),
            "policy_exits": int(act.sum()),
            "policy_exit_fraction": float(act.mean()) if len(act) else 0.0,
            "improved_trades": int((delta > 1e-9).sum()),
            "harmed_trades": int((delta < -1e-9).sum()),
            "avoided_loss_or_giveback_inr": float(delta[delta > 0].sum()),
            "false_early_exit_cost_inr": float(-delta[delta < 0].sum()),
            "legacy_win_rate": float(np.mean(base > 0)),
            "policy_win_rate": float(np.mean(pp > 0)),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("canonical_csv", type=Path)
    ap.add_argument("recent_csv_or_gz", type=Path)
    ap.add_argument("--v1-dir", type=Path, default=DEFAULT_V1_DIR)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True, exist_ok=True)

    print("loading raw causal sources", flush=True)
    hraw = microstate.load_raw(a.canonical_csv, nrows=canonical.RESEARCH_ROWS)
    rraw = microstate.load_raw(a.recent_csv_or_gz)

    print("building cooldown-free signal episode dataset", flush=True)
    episodes = build_entry_episode_dataset(
        a.canonical_csv, a.recent_csv_or_gz, hraw, rraw
    )
    print(f"usable episode checkpoints: {len(episodes)}", flush=True)

    print("entry timing walk-forward", flush=True)
    entry_pred = entry_walkforward(episodes)
    entry_policy_df = episode_policy(entry_pred)
    entry_metrics = episode_policy_metrics(entry_policy_df)

    print("loading and enriching v1 exit snapshots", flush=True)
    snapshots = pd.read_csv(a.v1_dir / "exit_snapshots.csv")
    snapshots["segment_id"] = pd.to_numeric(snapshots.segment_id).astype(int)
    seq = add_exit_sequence_features(snapshots)
    print(f"exit sequence rows: {len(seq)}", flush=True)

    print("short-horizon exit walk-forward", flush=True)
    exit_pred = exit_walkforward(seq)
    exit_pred_metrics = exit_prediction_metrics(exit_pred)
    exit_policy_df = confirmed_exit_policy(exit_pred)
    exit_metrics = policy_metrics(exit_policy_df, "model_exit", "confirmed_30s_model")

    ratchet_df = ratchet_policy(seq, exit_pred)
    ratchet_metrics = policy_metrics(ratchet_df, "ratchet_exit", "mfe_50pct_ratchet")

    write_csv(a.output / "entry_episode_dataset.csv", episodes.to_dict("records"))
    write_csv(a.output / "entry_episode_predictions.csv", entry_pred.to_dict("records"))
    write_csv(a.output / "entry_episode_policy.csv", entry_policy_df.to_dict("records"))
    write_csv(a.output / "entry_episode_policy_metrics.csv", entry_metrics)
    write_csv(a.output / "exit_sequence_dataset.csv", seq.to_dict("records"))
    write_csv(a.output / "exit_v2_predictions.csv", exit_pred.to_dict("records"))
    write_csv(a.output / "exit_v2_prediction_metrics.csv", exit_pred_metrics)
    write_csv(a.output / "exit_v2_policy.csv", exit_policy_df.to_dict("records"))
    write_csv(a.output / "exit_v2_policy_metrics.csv", exit_metrics)
    write_csv(a.output / "profit_ratchet_policy.csv", ratchet_df.to_dict("records"))
    write_csv(a.output / "profit_ratchet_metrics.csv", ratchet_metrics)

    result = {
        "schema": "xau-decision-policy-v2-diagnostic",
        "strategy_changed": False,
        "candidate_created": False,
        "model_search_performed": False,
        "threshold_search_performed": False,
        "feature_selection_performed": False,
        "model": "HistGradientBoostingRegressor",
        "model_params": MODEL_PARAMS,
        "entry_checkpoint_sec": ENTRY_CHECKPOINT_SEC,
        "entry_target": "counterfactual fixed-size Candidate-D-lifecycle pnl_inr at each cooldown-free signal-episode checkpoint",
        "entry_boundary": "predicted EV > 0; first positive checkpoint in episode",
        "entry_features": ENTRY_FEATURE_NAMES,
        "exit_checkpoint_sec": v1.CHECKPOINT_SEC,
        "exit_forward_sec": EXIT_FORWARD_SEC,
        "exit_negative_confirmations": EXIT_NEGATIVE_CONFIRMATIONS,
        "exit_target": "30-second-or-legacy-exit incremental mark-equity value",
        "exit_features": EXIT_FEATURE_NAMES,
        "ratchet": {
            "trigger_mfe_r": RATCHET_TRIGGER_R,
            "retain_fraction_of_mfe": RATCHET_RETAIN_FRACTION,
            "checkpoint_sec": v1.CHECKPOINT_SEC,
            "threshold_search": False,
        },
        "historical_folds": "expanding segments 0->1, 0-1->2, 0-2->3, 0-3->4",
        "recent_transfer": "train all historical first80, predict recent24h",
        "final20_opened": False,
        "promotion_evidence": False,
        "entry_episode_rows": int(len(episodes)),
        "entry_episodes": int(episodes.episode_id.nunique()) if len(episodes) else 0,
        "entry_policy_metrics": entry_metrics,
        "exit_sequence_rows": int(len(seq)),
        "exit_prediction_metrics": exit_pred_metrics,
        "exit_policy_metrics": exit_metrics,
        "ratchet_metrics": ratchet_metrics,
        "decision": (
            "Diagnostic only. A future full shared-slot Candidate F requires a separately "
            "frozen experiment and genuinely new non-overlapping validation for promotion."
        ),
    }
    (a.output / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
