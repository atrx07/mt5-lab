"""Experiment 38: Decision Policy v1 foundation.

Two fixed nonlinear diagnostics are evaluated with chronological walk-forward
discipline:

1) entry expected value / engine ownership;
2) in-trade continuation expected value / exit timing.

This experiment does not modify or promote Candidate D. It creates out-of-
sample policy evidence that may justify a later frozen Candidate F.

The model class, features, targets, 5-second checkpoint cadence and zero
decision boundaries are frozen in docs/plans/V4_5_DECISION_POLICY_V1.md.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

import canonical_replay as canonical
import v4_5_independent_opportunity_atlas as atlasmod
import v4_5_microstate_v1_freeze as microstate
import v4_5_regime_portability as portability
import v4_5_state_v2_freeze as state_v2

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATLAS = (
    ROOT / "results" / "simulations" /
    "2026-09-25-v4_5-independent-opportunity-atlas" / "shadow_opportunities.csv"
)
DEFAULT_OUT = (
    ROOT / "results" / "simulations" /
    "2026-09-25-v4_5-decision-policy-v1"
)

SEED = 20260925
CHECKPOINT_SEC = 5.0
ENGINES = ("PRIMARY", "SECONDARY", "MICRO", "BURST")
INTERVALS = ("500ms", "1s")
ENGINE_PRIORITY = {e: i for i, e in enumerate(ENGINES)}

MODEL_PARAMS = {
    "loss": "squared_error",
    "learning_rate": 0.05,
    "max_iter": 160,
    "max_leaf_nodes": 7,
    "min_samples_leaf": 20,
    "l2_regularization": 1.0,
    "random_state": SEED,
}

ENTRY_CONT_FEATURES = tuple(state_v2.FEATURES) + tuple(microstate.FEATURES)
DYNAMIC_EXIT_FEATURES = (
    "hold_sec",
    "current_move_usd",
    "current_r",
    "mfe_usd_live",
    "mae_usd_live",
    "mfe_r",
    "mae_r",
    "giveback_usd",
    "giveback_r",
    "mfe_capture_ratio",
    "time_since_mfe_sec",
    "partial_done",
)
ENTRY_FEATURE_NAMES = (
    list(ENTRY_CONT_FEATURES)
    + [f"engine_{e}" for e in ENGINES]
    + ["interval_1s"]
)
EXIT_FEATURE_NAMES = ENTRY_FEATURE_NAMES + list(DYNAMIC_EXIT_FEATURES)


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


def realized(df: pd.DataFrame) -> pd.DataFrame:
    censored = df["censored"].astype(str).str.lower().eq("true")
    return df.loc[~censored].copy()


def trade_id(row: Dict) -> str:
    return (
        f'{row["window"]}|{row["interval"]}|{int(row["segment_id"])}|'
        f'{row["engine"]}|{row["side"]}|{float(row["entry_ts"]):.6f}'
    )


def corr(a, b) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ok = np.isfinite(a) & np.isfinite(b)
    a = a[ok]
    b = b[ok]
    if len(a) < 3 or np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return math.nan
    return float(np.corrcoef(a, b)[0, 1])


def spearman(a, b) -> float:
    q = pd.DataFrame({"a": a, "b": b}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(q) < 3:
        return math.nan
    return float(q["a"].rank(method="average").corr(q["b"].rank(method="average")))


def make_matrix(df: pd.DataFrame, *, exit_model: bool) -> np.ndarray:
    cols = list(ENTRY_CONT_FEATURES)
    if exit_model:
        cols += list(DYNAMIC_EXIT_FEATURES)
    blocks = []
    for col in cols:
        blocks.append(pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)[:, None])
    eng = df["engine"].astype(str).to_numpy()
    for name in ENGINES:
        blocks.append((eng == name).astype(float)[:, None])
    blocks.append((df["interval"].astype(str).to_numpy() == "1s").astype(float)[:, None])
    return np.hstack(blocks)


def fit_model(train: pd.DataFrame, target: str, *, exit_model: bool, weights=None):
    x = make_matrix(train, exit_model=exit_model)
    y = pd.to_numeric(train[target], errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(y)
    if weights is not None:
        weights = np.asarray(weights, dtype=float)[ok]
    model = HistGradientBoostingRegressor(**MODEL_PARAMS)
    model.fit(x[ok], y[ok], sample_weight=weights)
    return model


def predict(model, df: pd.DataFrame, *, exit_model: bool) -> np.ndarray:
    return model.predict(make_matrix(df, exit_model=exit_model))


def enrich_entries(
    atlas: pd.DataFrame,
    historical_raw: Dict[str, np.ndarray],
    recent_raw: Dict[str, np.ndarray],
) -> pd.DataFrame:
    rows = []
    for rec in atlas.to_dict("records"):
        raw = historical_raw if rec["window"] == "historical7d" else recent_raw
        z = dict(rec)
        z["trade_id"] = trade_id(z)
        z.update(microstate.features_at(raw, float(z["entry_ts"]), int(z["side_sign"])))
        rows.append(z)
    return pd.DataFrame(rows)


def build_sampled_arrays(canonical_csv: Path, recent_csv: Path):
    arrays = {}
    for interval in INTERVALS:
        h, _ = canonical.build_features(canonical_csv, interval)
        r, _ = canonical.build_features(recent_csv, interval)
        arrays[("historical7d", interval)] = h
        arrays[("recent24h", interval)] = r
    return arrays


def live_mark_path(arr: Dict[str, np.ndarray], row: Dict):
    s = int(row["entry_index"])
    e = int(row["exit_index"])
    side = int(row["side_sign"])
    engine = str(row["engine"])
    if e <= s:
        return None

    entry = float(arr["ask"][s] if side == 1 else arr["bid"][s])
    oz0 = float(atlasmod.fixed_oz(entry))
    sl = slice(s, e + 1)
    if side == 1:
        moves = arr["bid"][sl].astype(float) - entry
    else:
        moves = entry - arr["ask"][sl].astype(float)
    tt = arr["t"][sl].astype(float)
    peak = np.maximum.accumulate(moves)
    trough = np.minimum.accumulate(moves)

    if engine == "MICRO":
        hit = np.flatnonzero(moves >= 5.5)
        partial_k = int(hit[0]) if len(hit) else None
    else:
        partial_k = None

    current_pnl = np.empty(len(moves), dtype=float)
    if partial_k is None:
        current_pnl[:] = moves * oz0 * canonical.INR_PER_USD
        partial_flags = np.zeros(len(moves), dtype=float)
    else:
        trigger_move = float(moves[partial_k])
        realized_part = trigger_move * (oz0 * 0.75) * canonical.INR_PER_USD
        current_pnl[:partial_k] = moves[:partial_k] * oz0 * canonical.INR_PER_USD
        current_pnl[partial_k:] = (
            realized_part + moves[partial_k:] * (oz0 * 0.25) * canonical.INR_PER_USD
        )
        partial_flags = np.zeros(len(moves), dtype=float)
        partial_flags[partial_k:] = 1.0

    peak_idx = np.empty(len(moves), dtype=np.int64)
    best_i = 0
    for i in range(len(moves)):
        if moves[i] >= moves[best_i]:
            best_i = i
        peak_idx[i] = best_i

    return {
        "entry": entry,
        "oz0": oz0,
        "t": tt,
        "moves": moves,
        "peak": peak,
        "trough": trough,
        "current_pnl": current_pnl,
        "partial": partial_flags,
        "peak_idx": peak_idx,
    }


def build_exit_snapshot_metadata(
    atlas: pd.DataFrame,
    sampled: Dict[Tuple[str, str], Dict[str, np.ndarray]],
) -> List[Dict]:
    rows: List[Dict] = []
    for rec in atlas.to_dict("records"):
        arr = sampled[(rec["window"], rec["interval"])]
        path = live_mark_path(arr, rec)
        if path is None:
            continue

        t = path["t"]
        if len(t) < 2:
            continue
        final_pnl = float(rec["pnl_inr"])
        final_ts = float(rec["exit_ts"])
        target_times = np.arange(float(rec["entry_ts"]) + CHECKPOINT_SEC, final_ts, CHECKPOINT_SEC)
        if not len(target_times):
            continue

        local_idx = np.searchsorted(t, target_times, side="left")
        local_idx = np.unique(local_idx[(local_idx > 0) & (local_idx < len(t) - 1)])
        tid = trade_id(rec)

        for k in local_idx:
            ts = float(t[k])
            cur_move = float(path["moves"][k])
            live_mfe = float(path["peak"][k])
            live_mae = float(path["trough"][k])
            giveback = float(live_mfe - cur_move)
            capture = (
                float(cur_move / live_mfe)
                if live_mfe > 1e-9
                else (1.0 if cur_move >= 0 else 0.0)
            )
            future_moves = path["moves"][k:]
            current_pnl = float(path["current_pnl"][k])
            rows.append({
                "window": rec["window"],
                "interval": rec["interval"],
                "segment_id": int(rec["segment_id"]),
                "engine": rec["engine"],
                "side": rec["side"],
                "side_sign": int(rec["side_sign"]),
                "trade_id": tid,
                "trade_entry_ts": float(rec["entry_ts"]),
                # state_v2.overlay intentionally evaluates the timestamp in entry_ts.
                "entry_ts": ts,
                "snapshot_ts": ts,
                "hold_sec": float(ts - float(rec["entry_ts"])),
                "current_move_usd": cur_move,
                "current_r": cur_move / 4.0,
                "mfe_usd_live": live_mfe,
                "mae_usd_live": live_mae,
                "mfe_r": live_mfe / 4.0,
                "mae_r": live_mae / 4.0,
                "giveback_usd": giveback,
                "giveback_r": giveback / 4.0,
                "mfe_capture_ratio": capture,
                "time_since_mfe_sec": float(ts - float(t[int(path["peak_idx"][k])])),
                "partial_done": float(path["partial"][k]),
                "current_mark_equity_pnl_inr": current_pnl,
                "legacy_final_pnl_inr": final_pnl,
                "continuation_value_inr": final_pnl - current_pnl,
                "future_best_additional_usd": float(np.max(future_moves) - cur_move),
                "future_worst_additional_usd": float(np.min(future_moves) - cur_move),
                "legacy_mfe_usd": float(rec["mfe_usd"]),
                "legacy_mae_usd": float(rec["mae_usd"]),
                "legacy_exit_reason": rec["exit_reason"],
                "initial_oz": float(path["oz0"]),
            })
    return rows


def enrich_exit_snapshots(
    metadata: List[Dict],
    canonical_csv: Path,
    recent_csv: Path,
    historical_raw: Dict[str, np.ndarray],
    recent_raw: Dict[str, np.ndarray],
) -> pd.DataFrame:
    out = []
    for window, path, raw in (
        ("historical7d", canonical_csv, historical_raw),
        ("recent24h", recent_csv, recent_raw),
    ):
        sub = [r for r in metadata if r["window"] == window]
        if not sub:
            continue
        # state-v2 is evaluated at each snapshot timestamp using only past raw events.
        enriched = state_v2.overlay(path, sub, window)
        for row in enriched:
            row.update(
                microstate.features_at(
                    raw, float(row["snapshot_ts"]), int(row["side_sign"])
                )
            )
            out.append(row)
    return pd.DataFrame(out)


def fold_specs():
    for test_seg in (1, 2, 3, 4):
        yield f"hist_seg{test_seg}", list(range(test_seg)), [test_seg]


def entry_walkforward(entries: pd.DataFrame):
    preds: List[Dict] = []
    for label, train_segments, test_segments in fold_specs():
        train = entries[
            (entries.window == "historical7d")
            & (entries.segment_id.isin(train_segments))
        ].copy()
        test = entries[
            (entries.window == "historical7d")
            & (entries.segment_id.isin(test_segments))
        ].copy()
        if train.empty or test.empty:
            continue
        model = fit_model(train, "pnl_inr", exit_model=False)
        pp = predict(model, test, exit_model=False)
        for row, p in zip(test.to_dict("records"), pp):
            preds.append({
                "label": "historical_walkforward",
                "fold": label,
                "trade_id": row["trade_id"],
                "window": row["window"],
                "interval": row["interval"],
                "segment_id": int(row["segment_id"]),
                "engine": row["engine"],
                "side": row["side"],
                "entry_ts": float(row["entry_ts"]),
                "actual_pnl_inr": float(row["pnl_inr"]),
                "mfe_usd": float(row["mfe_usd"]),
                "mae_usd": float(row["mae_usd"]),
                "predicted_entry_ev_inr": float(p),
                "take": bool(p > 0.0),
            })

    train = entries[entries.window == "historical7d"].copy()
    test = entries[entries.window == "recent24h"].copy()
    model = fit_model(train, "pnl_inr", exit_model=False)
    pp = predict(model, test, exit_model=False)
    for row, p in zip(test.to_dict("records"), pp):
        preds.append({
            "label": "recent_after_first80",
            "fold": "whole_recent",
            "trade_id": row["trade_id"],
            "window": row["window"],
            "interval": row["interval"],
            "segment_id": int(row["segment_id"]),
            "engine": row["engine"],
            "side": row["side"],
            "entry_ts": float(row["entry_ts"]),
            "actual_pnl_inr": float(row["pnl_inr"]),
            "mfe_usd": float(row["mfe_usd"]),
            "mae_usd": float(row["mae_usd"]),
            "predicted_entry_ev_inr": float(p),
            "take": bool(p > 0.0),
        })
    return pd.DataFrame(preds)


def exit_weights(train: pd.DataFrame) -> np.ndarray:
    counts = train.groupby("trade_id")["trade_id"].transform("count").to_numpy(dtype=float)
    return np.divide(1.0, counts, out=np.ones_like(counts), where=counts > 0)


def exit_walkforward(snapshots: pd.DataFrame):
    preds: List[Dict] = []
    for label, train_segments, test_segments in fold_specs():
        train = snapshots[
            (snapshots.window == "historical7d")
            & (snapshots.segment_id.isin(train_segments))
        ].copy()
        test = snapshots[
            (snapshots.window == "historical7d")
            & (snapshots.segment_id.isin(test_segments))
        ].copy()
        if train.empty or test.empty:
            continue
        model = fit_model(
            train,
            "continuation_value_inr",
            exit_model=True,
            weights=exit_weights(train),
        )
        pp = predict(model, test, exit_model=True)
        for row, p in zip(test.to_dict("records"), pp):
            preds.append({
                "label": "historical_walkforward",
                "fold": label,
                "trade_id": row["trade_id"],
                "window": row["window"],
                "interval": row["interval"],
                "segment_id": int(row["segment_id"]),
                "engine": row["engine"],
                "side": row["side"],
                "snapshot_ts": float(row["snapshot_ts"]),
                "hold_sec": float(row["hold_sec"]),
                "current_mark_equity_pnl_inr": float(row["current_mark_equity_pnl_inr"]),
                "legacy_final_pnl_inr": float(row["legacy_final_pnl_inr"]),
                "continuation_value_inr": float(row["continuation_value_inr"]),
                "predicted_continuation_ev_inr": float(p),
                "hold": bool(p > 0.0),
                "mfe_usd_live": float(row["mfe_usd_live"]),
                "giveback_usd": float(row["giveback_usd"]),
            })

    train = snapshots[snapshots.window == "historical7d"].copy()
    test = snapshots[snapshots.window == "recent24h"].copy()
    model = fit_model(
        train,
        "continuation_value_inr",
        exit_model=True,
        weights=exit_weights(train),
    )
    pp = predict(model, test, exit_model=True)
    for row, p in zip(test.to_dict("records"), pp):
        preds.append({
            "label": "recent_after_first80",
            "fold": "whole_recent",
            "trade_id": row["trade_id"],
            "window": row["window"],
            "interval": row["interval"],
            "segment_id": int(row["segment_id"]),
            "engine": row["engine"],
            "side": row["side"],
            "snapshot_ts": float(row["snapshot_ts"]),
            "hold_sec": float(row["hold_sec"]),
            "current_mark_equity_pnl_inr": float(row["current_mark_equity_pnl_inr"]),
            "legacy_final_pnl_inr": float(row["legacy_final_pnl_inr"]),
            "continuation_value_inr": float(row["continuation_value_inr"]),
            "predicted_continuation_ev_inr": float(p),
            "hold": bool(p > 0.0),
            "mfe_usd_live": float(row["mfe_usd_live"]),
            "giveback_usd": float(row["giveback_usd"]),
        })
    return pd.DataFrame(preds)


def prediction_metrics(df: pd.DataFrame, target: str, pred: str, decision_col: str, kind: str):
    out = []
    if df.empty:
        return out
    for (label, interval), g in df.groupby(["label", "interval"], sort=True):
        y = pd.to_numeric(g[target], errors="coerce").to_numpy(dtype=float)
        p = pd.to_numeric(g[pred], errors="coerce").to_numpy(dtype=float)
        keep = g[decision_col].astype(bool).to_numpy()
        row = {
            "kind": kind,
            "label": label,
            "interval": interval,
            "rows": int(len(g)),
            "pearson": corr(p, y),
            "spearman": spearman(p, y),
            "sign_accuracy": float(np.mean((p > 0) == (y > 0))) if len(g) else 0.0,
            "predicted_positive_fraction": float(np.mean(keep)) if len(g) else 0.0,
            "actual_target_sum": float(np.sum(y)),
            "predicted_positive_actual_target_sum": float(np.sum(y[keep])) if keep.any() else 0.0,
            "predicted_nonpositive_actual_target_sum": float(np.sum(y[~keep])) if (~keep).any() else 0.0,
        }
        if kind == "entry":
            actual = pd.to_numeric(g["actual_pnl_inr"], errors="coerce").to_numpy(float)
            row.update({
                "baseline_all_opportunity_pnl_inr": float(actual.sum()),
                "policy_take_pnl_inr": float(actual[keep].sum()) if keep.any() else 0.0,
                "policy_delta_inr": float(actual[keep].sum() - actual.sum()) if keep.any() else float(-actual.sum()),
                "taken_win_rate": float(np.mean(actual[keep] > 0)) if keep.any() else 0.0,
                "trade_retention": float(np.mean(keep)),
            })
        out.append(row)
    return out


def per_engine_entry(entry_pred: pd.DataFrame) -> List[Dict]:
    out = []
    if entry_pred.empty:
        return out
    for (label, interval, engine), g in entry_pred.groupby(
        ["label", "interval", "engine"], sort=True
    ):
        actual = pd.to_numeric(g.actual_pnl_inr).to_numpy(float)
        pred = pd.to_numeric(g.predicted_entry_ev_inr).to_numpy(float)
        keep = pred > 0
        out.append({
            "label": label,
            "interval": interval,
            "engine": engine,
            "opportunities": len(g),
            "baseline_pnl_inr": float(actual.sum()),
            "taken": int(keep.sum()),
            "retention": float(keep.mean()) if len(keep) else 0.0,
            "taken_pnl_inr": float(actual[keep].sum()) if keep.any() else 0.0,
            "skipped_pnl_inr": float(actual[~keep].sum()) if (~keep).any() else 0.0,
            "taken_win_rate": float(np.mean(actual[keep] > 0)) if keep.any() else 0.0,
            "prediction_spearman": spearman(pred, actual),
        })
    return out


def ownership_diagnostic(entry_pred: pd.DataFrame) -> List[Dict]:
    rows = []
    if entry_pred.empty:
        return rows
    # Exact-timestamp only: this mirrors actual same-tick competition and avoids
    # inventing a clustering tolerance after seeing outcomes.
    for (label, interval, ts), g in entry_pred.groupby(
        ["label", "interval", "entry_ts"], sort=True
    ):
        if len(g) < 2:
            continue
        legacy = g.sort_values(
            "engine", key=lambda s: s.map(ENGINE_PRIORITY)
        ).iloc[0]
        q = g[g.predicted_entry_ev_inr > 0]
        chosen = q.sort_values("predicted_entry_ev_inr", ascending=False).iloc[0] if len(q) else None
        rows.append({
            "label": label,
            "interval": interval,
            "entry_ts": float(ts),
            "engines": "|".join(g.engine.astype(str)),
            "legacy_engine": legacy.engine,
            "legacy_actual_pnl_inr": float(legacy.actual_pnl_inr),
            "policy_engine": chosen.engine if chosen is not None else "HOLD",
            "policy_predicted_ev_inr": float(chosen.predicted_entry_ev_inr) if chosen is not None else 0.0,
            "policy_actual_pnl_inr": float(chosen.actual_pnl_inr) if chosen is not None else 0.0,
            "delta_policy_vs_legacy_inr": (
                float(chosen.actual_pnl_inr) - float(legacy.actual_pnl_inr)
                if chosen is not None
                else -float(legacy.actual_pnl_inr)
            ),
        })
    return rows


def build_exit_trade_policy(
    atlas: pd.DataFrame,
    exit_pred: pd.DataFrame,
) -> pd.DataFrame:
    atlas_map = {trade_id(r): r for r in atlas.to_dict("records")}
    out = []
    if exit_pred.empty:
        return pd.DataFrame(out)

    represented = set(exit_pred.trade_id.astype(str))
    labels = {
        tid: str(exit_pred.loc[exit_pred.trade_id == tid, "label"].iloc[0])
        for tid in represented
    }

    for tid in sorted(represented):
        base = atlas_map[tid]
        g = exit_pred[exit_pred.trade_id == tid].sort_values("hold_sec")
        exit_rows = g[~g["hold"].astype(bool)]
        if len(exit_rows):
            chosen = exit_rows.iloc[0]
            policy_pnl = float(chosen.current_mark_equity_pnl_inr)
            model_exit = True
            exit_hold = float(chosen.hold_sec)
            pred_ev = float(chosen.predicted_continuation_ev_inr)
        else:
            policy_pnl = float(base["pnl_inr"])
            model_exit = False
            exit_hold = float(base["hold_sec"])
            pred_ev = float(g.predicted_continuation_ev_inr.iloc[-1]) if len(g) else math.nan

        baseline = float(base["pnl_inr"])
        delta = policy_pnl - baseline
        oz0 = atlasmod.fixed_oz(
            float("nan")
        )
        # Do not reconstruct entry price here; normalized MFE capture is supplied
        # from the actual fixed-size scale: pnl / (mfe * initial_oz * INR) is
        # computed later only when initial_oz is available in snapshots.
        out.append({
            "label": labels[tid],
            "trade_id": tid,
            "window": base["window"],
            "interval": base["interval"],
            "segment_id": int(base["segment_id"]),
            "engine": base["engine"],
            "side": base["side"],
            "entry_ts": float(base["entry_ts"]),
            "baseline_pnl_inr": baseline,
            "policy_exit_pnl_inr": policy_pnl,
            "delta_exit_vs_legacy_inr": delta,
            "model_exit": model_exit,
            "model_exit_hold_sec": exit_hold,
            "first_exit_predicted_continuation_ev_inr": pred_ev,
            "legacy_mfe_usd": float(base["mfe_usd"]),
            "legacy_mae_usd": float(base["mae_usd"]),
            "legacy_exit_reason": base["exit_reason"],
        })
    return pd.DataFrame(out)


def exit_policy_metrics(policy: pd.DataFrame) -> List[Dict]:
    out = []
    if policy.empty:
        return out
    for (label, interval), g in policy.groupby(["label", "interval"], sort=True):
        base = pd.to_numeric(g.baseline_pnl_inr).to_numpy(float)
        pp = pd.to_numeric(g.policy_exit_pnl_inr).to_numpy(float)
        delta = pp - base
        ex = g.model_exit.astype(bool).to_numpy()
        out.append({
            "label": label,
            "interval": interval,
            "trades": len(g),
            "legacy_pnl_inr": float(base.sum()),
            "exit_policy_pnl_inr": float(pp.sum()),
            "delta_exit_vs_legacy_inr": float(delta.sum()),
            "model_exits": int(ex.sum()),
            "model_exit_fraction": float(ex.mean()) if len(ex) else 0.0,
            "improved_trades": int((delta > 1e-9).sum()),
            "harmed_trades": int((delta < -1e-9).sum()),
            "unchanged_trades": int((np.abs(delta) <= 1e-9).sum()),
            "avoided_loss_or_giveback_inr": float(delta[delta > 0].sum()),
            "false_early_exit_cost_inr": float(-delta[delta < 0].sum()),
            "legacy_win_rate": float(np.mean(base > 0)) if len(base) else 0.0,
            "policy_win_rate": float(np.mean(pp > 0)) if len(pp) else 0.0,
        })
    return out


def per_engine_exit(policy: pd.DataFrame) -> List[Dict]:
    out = []
    if policy.empty:
        return out
    for (label, interval, engine), g in policy.groupby(
        ["label", "interval", "engine"], sort=True
    ):
        base = pd.to_numeric(g.baseline_pnl_inr).to_numpy(float)
        pp = pd.to_numeric(g.policy_exit_pnl_inr).to_numpy(float)
        out.append({
            "label": label,
            "interval": interval,
            "engine": engine,
            "trades": len(g),
            "legacy_pnl_inr": float(base.sum()),
            "exit_policy_pnl_inr": float(pp.sum()),
            "delta_inr": float((pp - base).sum()),
            "model_exits": int(g.model_exit.astype(bool).sum()),
        })
    return out


def combined_policy(
    atlas: pd.DataFrame,
    entry_pred: pd.DataFrame,
    exit_policy: pd.DataFrame,
) -> pd.DataFrame:
    emap = {r["trade_id"]: r for r in entry_pred.to_dict("records")}
    xmap = {r["trade_id"]: r for r in exit_policy.to_dict("records")}
    amap = {trade_id(r): r for r in atlas.to_dict("records")}
    rows = []
    for tid, erow in emap.items():
        base = amap[tid]
        take = bool(erow["take"])
        if take:
            x = xmap.get(tid)
            pnl = float(x["policy_exit_pnl_inr"]) if x is not None else float(base["pnl_inr"])
        else:
            pnl = 0.0
        rows.append({
            "label": erow["label"],
            "trade_id": tid,
            "window": base["window"],
            "interval": base["interval"],
            "segment_id": int(base["segment_id"]),
            "engine": base["engine"],
            "baseline_pnl_inr": float(base["pnl_inr"]),
            "take": take,
            "combined_policy_pnl_inr": pnl,
        })
    return pd.DataFrame(rows)


def combined_metrics(df: pd.DataFrame) -> List[Dict]:
    out = []
    if df.empty:
        return out
    for (label, interval), g in df.groupby(["label", "interval"], sort=True):
        base = pd.to_numeric(g.baseline_pnl_inr).to_numpy(float)
        policy = pd.to_numeric(g.combined_policy_pnl_inr).to_numpy(float)
        take = g.take.astype(bool).to_numpy()
        out.append({
            "label": label,
            "interval": interval,
            "opportunities": len(g),
            "baseline_independent_lane_pnl_inr": float(base.sum()),
            "combined_policy_pnl_inr": float(policy.sum()),
            "delta_inr": float((policy - base).sum()),
            "trade_retention": float(take.mean()) if len(take) else 0.0,
            "taken_trades": int(take.sum()),
            "baseline_win_rate": float(np.mean(base > 0)) if len(base) else 0.0,
            "combined_taken_win_rate": float(np.mean(policy[take] > 0)) if take.any() else 0.0,
            "positive_policy_fraction_all_opportunities": float(np.mean(policy > 0)) if len(policy) else 0.0,
        })
    return out


def quantile_calibration(df: pd.DataFrame, pred_col: str, actual_col: str, kind: str):
    out = []
    if df.empty:
        return out
    for (label, interval), g in df.groupby(["label", "interval"], sort=True):
        q = g[[pred_col, actual_col]].copy()
        q[pred_col] = pd.to_numeric(q[pred_col], errors="coerce")
        q[actual_col] = pd.to_numeric(q[actual_col], errors="coerce")
        q = q.dropna()
        if len(q) < 10:
            continue
        try:
            q["bin"] = pd.qcut(q[pred_col], q=min(10, len(q)), duplicates="drop")
        except ValueError:
            continue
        for rank, (_, b) in enumerate(q.groupby("bin", observed=True, sort=True)):
            out.append({
                "kind": kind,
                "label": label,
                "interval": interval,
                "prediction_bin": rank,
                "rows": len(b),
                "prediction_mean": float(b[pred_col].mean()),
                "actual_mean": float(b[actual_col].mean()),
                "actual_positive_fraction": float((b[actual_col] > 0).mean()),
            })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("canonical_csv", type=Path)
    ap.add_argument("recent_csv_or_gz", type=Path)
    ap.add_argument("--atlas", type=Path, default=DEFAULT_ATLAS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True, exist_ok=True)

    atlas = realized(pd.read_csv(a.atlas))
    atlas["segment_id"] = pd.to_numeric(atlas.segment_id).astype(int)

    print("loading raw causal sources", flush=True)
    hraw = microstate.load_raw(a.canonical_csv, nrows=canonical.RESEARCH_ROWS)
    rraw = microstate.load_raw(a.recent_csv_or_gz)

    print("enriching entry opportunities", flush=True)
    entries = enrich_entries(atlas, hraw, rraw)

    print("building sampled arrays for trajectory checkpoints", flush=True)
    sampled = build_sampled_arrays(a.canonical_csv, a.recent_csv_or_gz)
    print("building 5-second in-trade snapshot metadata", flush=True)
    snap_meta = build_exit_snapshot_metadata(atlas, sampled)
    print(f"enriching {len(snap_meta)} exit checkpoints", flush=True)
    snapshots = enrich_exit_snapshots(
        snap_meta, a.canonical_csv, a.recent_csv_or_gz, hraw, rraw
    )

    print("running entry walk-forward", flush=True)
    entry_pred = entry_walkforward(entries)
    print("running continuation walk-forward", flush=True)
    exit_pred = exit_walkforward(snapshots)

    entry_metrics = prediction_metrics(
        entry_pred,
        "actual_pnl_inr",
        "predicted_entry_ev_inr",
        "take",
        "entry",
    )
    exit_prediction_metrics = prediction_metrics(
        exit_pred,
        "continuation_value_inr",
        "predicted_continuation_ev_inr",
        "hold",
        "exit_snapshot",
    )
    entry_engine = per_engine_entry(entry_pred)
    ownership = ownership_diagnostic(entry_pred)

    exit_policy = build_exit_trade_policy(atlas, exit_pred)
    exit_metrics = exit_policy_metrics(exit_policy)
    exit_engine = per_engine_exit(exit_policy)

    combined = combined_policy(atlas, entry_pred, exit_policy)
    combined_summary = combined_metrics(combined)

    calibration = quantile_calibration(
        entry_pred, "predicted_entry_ev_inr", "actual_pnl_inr", "entry"
    )
    calibration += quantile_calibration(
        exit_pred,
        "predicted_continuation_ev_inr",
        "continuation_value_inr",
        "exit_snapshot",
    )

    write_csv(a.output / "entry_dataset.csv", entries.to_dict("records"))
    write_csv(a.output / "exit_snapshots.csv", snapshots.to_dict("records"))
    write_csv(a.output / "entry_predictions.csv", entry_pred.to_dict("records"))
    write_csv(a.output / "exit_predictions.csv", exit_pred.to_dict("records"))
    write_csv(a.output / "entry_metrics.csv", entry_metrics)
    write_csv(a.output / "entry_per_engine.csv", entry_engine)
    write_csv(a.output / "simultaneous_ownership.csv", ownership)
    write_csv(a.output / "exit_prediction_metrics.csv", exit_prediction_metrics)
    write_csv(a.output / "exit_trade_policy.csv", exit_policy.to_dict("records"))
    write_csv(a.output / "exit_policy_metrics.csv", exit_metrics)
    write_csv(a.output / "exit_per_engine.csv", exit_engine)
    write_csv(a.output / "combined_policy_trades.csv", combined.to_dict("records"))
    write_csv(a.output / "combined_policy_metrics.csv", combined_summary)
    write_csv(a.output / "prediction_calibration.csv", calibration)

    result = {
        "schema": "xau-decision-policy-v1-foundation",
        "strategy_changed": False,
        "candidate_created": False,
        "model_search_performed": False,
        "threshold_search_performed": False,
        "feature_selection_performed": False,
        "model": "HistGradientBoostingRegressor",
        "model_params": MODEL_PARAMS,
        "checkpoint_sec": CHECKPOINT_SEC,
        "entry_target": "independent-lane fixed-size pnl_inr",
        "entry_boundary": "predicted expected P&L > 0",
        "exit_target": "legacy final P&L - current mark-equity P&L",
        "exit_boundary": "predicted continuation expected value > 0",
        "entry_features": ENTRY_FEATURE_NAMES,
        "exit_features": EXIT_FEATURE_NAMES,
        "historical_folds": "expanding canonical segments 0->1, 0-1->2, 0-2->3, 0-3->4; both grids stay within the same fold",
        "recent_transfer": "fit all historical first80 opportunities/snapshots, predict recent24h",
        "exit_trade_weighting": "each training trade contributes total weight 1 across its checkpoints",
        "final20_opened": False,
        "promotion_evidence": False,
        "entry_rows": int(len(entries)),
        "exit_snapshot_rows": int(len(snapshots)),
        "entry_metrics": entry_metrics,
        "exit_prediction_metrics": exit_prediction_metrics,
        "exit_policy_metrics": exit_metrics,
        "combined_policy_metrics": combined_summary,
        "simultaneous_ownership_events": int(len(ownership)),
        "decision": (
            "Diagnostic only. Use coherent chronological OOS evidence to decide whether "
            "a separately frozen full shared-slot Candidate F is justified."
        ),
    }
    (a.output / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
