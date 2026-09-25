"""Experiment 42: signal-fingerprint entry-quality diagnostic.

Uses Experiment-39 cooldown-free signal episodes, but trains entry quality on
exit-independent excursion structure instead of final P&L. One fixed shallow
expert is fit per engine. No search is performed.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

import canonical_replay as canonical
import v4_5_decision_policy_v2 as v2
import v4_5_microstate_v1_freeze as microstate
import v4_5_regime_portability as portability
import v4_5_router_v2 as router
import v4_5_state_v2_freeze as state_v2

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-09-26-v4_5-signal-fingerprint-entry-quality"

ENGINE_IDS = {"PRIMARY": 1, "SECONDARY": 2, "MICRO": 3, "BURST": 4}
ENGINE_NAMES = {v: k for k, v in ENGINE_IDS.items()}
BASE_FEATURES = list(state_v2.FEATURES) + list(microstate.FEATURES) + [
    "interval_1s",
    "episode_age_sec",
    "episode_checkpoint_index",
    "simultaneous_engine_count",
    "same_side_engine_count",
]
FINGERPRINT_FEATURES = {
    "PRIMARY": [
        "high_regime",
        "m1800_margin",
        "m300_margin",
        "m60_reaccel_margin",
        "pullback_depth_margin",
    ],
    "SECONDARY": [
        "high_regime",
        "m30_margin",
        "channel_range_margin",
        "breakout_excess",
        "slow_dir_m1800",
        "slow_dir_m300",
    ],
    "MICRO": [
        "m120_margin",
        "m60_margin",
        "m10_reaccel_margin",
        "pullback_depth_margin",
        "qacc_margin",
        "er60_margin",
        "range60_margin",
        "spread_ratio_headroom",
        "imbalance_alignment",
    ],
    "BURST": [
        "m10_margin",
        "m30_margin",
        "m60_margin",
        "m120_direction_strength",
        "qacc_margin",
        "er60_margin",
        "range60_margin",
        "spread_ratio_headroom",
        "spread_abs_headroom",
        "imbalance_margin",
    ],
}
MODEL_PARAMS = {
    "loss": "squared_error",
    "learning_rate": 0.05,
    "max_iter": 140,
    "max_leaf_nodes": 5,
    "min_samples_leaf": 12,
    "l2_regularization": 1.0,
    "random_state": 20260926,
}


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


def finite(x):
    try:
        y = float(x)
    except Exception:
        return math.nan
    return y if math.isfinite(y) else math.nan


def fingerprint(arr: Dict[str, np.ndarray], i: int, engine: int, side: int) -> Dict[str, float]:
    s = float(side)
    m10 = finite(arr["m10"][i]); m30 = finite(arr["m30"][i])
    m60 = finite(arr["m60"][i]); m120 = finite(arr["m120"][i])
    m300 = finite(arr["m300"][i]); m1800 = finite(arr["m1800"][i])
    r60 = finite(arr["range60"][i]); r300 = finite(arr["range300"][i])
    er60 = finite(arr["er60"][i]); spread = finite(arr["spread"][i])
    mid = finite(arr["mid"][i]); qacc = finite(arr["qacc"][i]); imb = finite(arr["imb10"][i])
    min10 = finite(arr["min_m10_30"][i]); max10 = finite(arr["max_m10_30"][i])
    min60 = finite(arr["min_m60_300"][i]); max60 = finite(arr["max_m60_300"][i])
    chh = finite(arr["ch_high120"][i]); chl = finite(arr["ch_low120"][i])
    high = bool(math.isfinite(r300) and math.isfinite(er60) and r300 >= 5.0 and er60 >= 0.03)

    out: Dict[str, float] = {}
    if engine == 1:
        pull = (-min60) if side == 1 else max60
        out = {
            "high_regime": float(high),
            "m1800_margin": s * m1800 - 8.0 if math.isfinite(m1800) else math.nan,
            "m300_margin": s * m300 - 3.0 if math.isfinite(m300) else math.nan,
            "m60_reaccel_margin": s * m60 - 0.5 if math.isfinite(m60) else math.nan,
            "pullback_depth_margin": pull - 0.8 if math.isfinite(pull) else math.nan,
        }
    elif engine == 2:
        rng = chh - chl if math.isfinite(chh) and math.isfinite(chl) else math.nan
        buf = max(0.5, 0.02 * rng) if math.isfinite(rng) else math.nan
        breakout = (
            mid - (chh + buf) if side == 1
            else (chl - buf) - mid
        ) if all(math.isfinite(x) for x in (mid, chh, chl, buf)) else math.nan
        out = {
            "high_regime": float(high),
            "m30_margin": s * m30 - 1.5 if math.isfinite(m30) else math.nan,
            "channel_range_margin": rng - 4.0 if math.isfinite(rng) else math.nan,
            "breakout_excess": breakout,
            "slow_dir_m1800": s * m1800 if math.isfinite(m1800) else math.nan,
            "slow_dir_m300": s * m300 if math.isfinite(m300) else math.nan,
        }
    elif engine == 3:
        pull = (-min10) if side == 1 else max10
        out = {
            "m120_margin": s * m120 - 6.0 if math.isfinite(m120) else math.nan,
            "m60_margin": s * m60 - 2.0 if math.isfinite(m60) else math.nan,
            "m10_reaccel_margin": s * m10 - 0.2 if math.isfinite(m10) else math.nan,
            "pullback_depth_margin": pull - 0.5 if math.isfinite(pull) else math.nan,
            "qacc_margin": qacc - 0.65 if math.isfinite(qacc) else math.nan,
            "er60_margin": er60 - 0.12 if math.isfinite(er60) else math.nan,
            "range60_margin": r60 - 2.0 if math.isfinite(r60) else math.nan,
            "spread_ratio_headroom": 0.25 * r60 - spread if math.isfinite(r60) and math.isfinite(spread) else math.nan,
            "imbalance_alignment": s * imb if math.isfinite(imb) else math.nan,
        }
    elif engine == 4:
        cfg = canonical.burst_config("v4_5_b")
        out = {
            "m10_margin": s * m10 - float(cfg[2]) if math.isfinite(m10) else math.nan,
            "m30_margin": s * m30 - float(cfg[3]) if math.isfinite(m30) else math.nan,
            "m60_margin": s * m60 - float(cfg[4]) if math.isfinite(m60) else math.nan,
            "m120_direction_strength": s * m120 if math.isfinite(m120) else math.nan,
            "qacc_margin": qacc - float(cfg[6]) if math.isfinite(qacc) else math.nan,
            "er60_margin": er60 - float(cfg[5]) if math.isfinite(er60) else math.nan,
            "range60_margin": r60 - float(cfg[8]) if math.isfinite(r60) else math.nan,
            "spread_ratio_headroom": float(cfg[9]) * r60 - spread if math.isfinite(r60) and math.isfinite(spread) else math.nan,
            "spread_abs_headroom": float(cfg[10]) - spread if math.isfinite(spread) else math.nan,
            "imbalance_margin": s * imb - float(cfg[7]) if math.isfinite(imb) else math.nan,
        }
    return out


def attach_fingerprints(df: pd.DataFrame, canonical_csv: Path, recent_csv: Path) -> pd.DataFrame:
    arrays = {}
    for interval in ("500ms", "1s"):
        arrays[("historical7d", interval)] = canonical.build_features(canonical_csv, interval)[0]
        arrays[("recent24h", interval)] = canonical.build_features(recent_csv, interval)[0]
    rows = []
    for r in df.to_dict("records"):
        arr = arrays[(r["window"], r["interval"])]
        z = dict(r)
        z["interval_1s"] = 1.0 if r["interval"] == "1s" else 0.0
        z.update(fingerprint(arr, int(r["entry_index"]), int(r["engine_id"]), int(r["side_sign"])))
        mfe = float(r["counterfactual_mfe_usd"])
        mae = float(r["counterfactual_mae_usd"])
        z["excursion_edge_r"] = (mfe - abs(mae)) / 4.0
        rows.append(z)
    return pd.DataFrame(rows)


def engine_features(engine: str) -> List[str]:
    return BASE_FEATURES + FINGERPRINT_FEATURES[engine]


def matrix(df: pd.DataFrame, engine: str) -> np.ndarray:
    cols = engine_features(engine)
    return np.column_stack([
        pd.to_numeric(df[c], errors="coerce").to_numpy(float) for c in cols
    ])


def episode_weights(df: pd.DataFrame) -> np.ndarray:
    counts = df.groupby("episode_id")["episode_id"].transform("count").to_numpy(float)
    return np.divide(1.0, counts, out=np.ones_like(counts), where=counts > 0)


def fit_engine(train: pd.DataFrame, engine: str):
    q = train[train.engine == engine]
    if len(q) < 20:
        return None
    model = HistGradientBoostingRegressor(**MODEL_PARAMS)
    model.fit(
        matrix(q, engine),
        pd.to_numeric(q.excursion_edge_r).to_numpy(float),
        sample_weight=episode_weights(q),
    )
    return model


def predict_fold(train: pd.DataFrame, test: pd.DataFrame, label: str, fold: str) -> List[Dict]:
    out = []
    models = {e: fit_engine(train, e) for e in ENGINE_IDS}
    for engine, g in test.groupby("engine", sort=False):
        model = models.get(str(engine))
        if model is None:
            continue
        pp = model.predict(matrix(g, str(engine)))
        for row, pred in zip(g.to_dict("records"), pp):
            out.append({
                "label": label,
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
                "simultaneous_engine_count": int(row["simultaneous_engine_count"]),
                "same_side_engine_count": int(row["same_side_engine_count"]),
                "actual_excursion_edge_r": float(row["excursion_edge_r"]),
                "counterfactual_pnl_inr": float(row["counterfactual_pnl_inr"]),
                "mfe_usd": float(row["counterfactual_mfe_usd"]),
                "mae_usd": float(row["counterfactual_mae_usd"]),
                "predicted_excursion_edge_r": float(pred),
            })
    return out


def walkforward(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict] = []
    for fold, train_segments, test_segments in v2.v1.fold_specs():
        train = df[(df.window == "historical7d") & df.segment_id.isin(train_segments)]
        test = df[(df.window == "historical7d") & df.segment_id.isin(test_segments)]
        rows += predict_fold(train, test, "historical_walkforward", fold)
    rows += predict_fold(
        df[df.window == "historical7d"],
        df[df.window == "recent24h"],
        "recent_after_first80",
        "whole_recent",
    )
    return pd.DataFrame(rows)


def corr(a, b):
    x = pd.DataFrame({"a": a, "b": b}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(x) < 3:
        return math.nan
    return float(x.a.corr(x.b))


def spearman(a, b):
    x = pd.DataFrame({"a": a, "b": b}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(x) < 3:
        return math.nan
    return float(x.a.rank().corr(x.b.rank()))


def checkpoint_metrics(pred: pd.DataFrame) -> List[Dict]:
    out = []
    for keys, g in pred.groupby(["label", "interval", "engine"], sort=True):
        y = pd.to_numeric(g.actual_excursion_edge_r).to_numpy(float)
        p = pd.to_numeric(g.predicted_excursion_edge_r).to_numpy(float)
        out.append({
            "label": keys[0], "interval": keys[1], "engine": keys[2],
            "checkpoints": len(g),
            "pearson": corr(p, y),
            "spearman": spearman(p, y),
            "sign_accuracy": float(np.mean((p > 0) == (y > 0))),
            "actual_mean_excursion_edge_r": float(np.mean(y)),
            "predicted_positive_fraction": float(np.mean(p > 0)),
        })
    return out


def episode_policy(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (label, episode_id), g in pred.groupby(["label", "episode_id"], sort=True):
        g = g.sort_values(["episode_age_sec", "entry_ts"])
        onset = g.iloc[0]
        q = g[g.predicted_excursion_edge_r > 0]
        chosen = q.iloc[0] if len(q) else None
        rows.append({
            "label": label,
            "episode_id": episode_id,
            "window": onset.window,
            "interval": onset.interval,
            "segment_id": int(onset.segment_id),
            "engine": onset.engine,
            "side": onset.side,
            "onset_entry_ts": float(onset.entry_ts),
            "onset_excursion_edge_r": float(onset.actual_excursion_edge_r),
            "onset_pnl_inr": float(onset.counterfactual_pnl_inr),
            "policy_action": "TAKE" if chosen is not None else "SKIP",
            "policy_entry_ts": float(chosen.entry_ts) if chosen is not None else math.nan,
            "policy_wait_sec": float(chosen.episode_age_sec) if chosen is not None else math.nan,
            "policy_predicted_excursion_edge_r": float(chosen.predicted_excursion_edge_r) if chosen is not None else 0.0,
            "policy_actual_excursion_edge_r": float(chosen.actual_excursion_edge_r) if chosen is not None else 0.0,
            "policy_pnl_inr": float(chosen.counterfactual_pnl_inr) if chosen is not None else 0.0,
            "episode_checkpoints": len(g),
        })
    return pd.DataFrame(rows)


def policy_metrics(policy: pd.DataFrame) -> List[Dict]:
    out = []
    for keys, g in policy.groupby(["label", "interval", "engine"], sort=True):
        take = g.policy_action.eq("TAKE").to_numpy()
        onset_edge = pd.to_numeric(g.onset_excursion_edge_r).to_numpy(float)
        chosen_edge = pd.to_numeric(g.policy_actual_excursion_edge_r).to_numpy(float)
        onset_pnl = pd.to_numeric(g.onset_pnl_inr).to_numpy(float)
        policy_pnl = pd.to_numeric(g.policy_pnl_inr).to_numpy(float)
        waits = pd.to_numeric(g.policy_wait_sec, errors="coerce").to_numpy(float)
        out.append({
            "label": keys[0], "interval": keys[1], "engine": keys[2],
            "episodes": len(g),
            "retention": float(take.mean()),
            "onset_mean_excursion_edge_r": float(onset_edge.mean()),
            "selected_mean_excursion_edge_r": float(chosen_edge[take].mean()) if take.any() else 0.0,
            "onset_counterfactual_pnl_inr": float(onset_pnl.sum()),
            "policy_counterfactual_pnl_inr": float(policy_pnl.sum()),
            "pnl_delta_audit_inr": float((policy_pnl - onset_pnl).sum()),
            "selected_positive_excursion_fraction": float(np.mean(chosen_edge[take] > 0)) if take.any() else 0.0,
            "median_wait_sec_taken": float(np.nanmedian(waits[take])) if take.any() else math.nan,
        })
    return out


def aggregate_policy_metrics(policy: pd.DataFrame) -> List[Dict]:
    out = []
    for keys, g in policy.groupby(["label", "interval"], sort=True):
        take = g.policy_action.eq("TAKE").to_numpy()
        onset_edge = pd.to_numeric(g.onset_excursion_edge_r).to_numpy(float)
        chosen_edge = pd.to_numeric(g.policy_actual_excursion_edge_r).to_numpy(float)
        onset_pnl = pd.to_numeric(g.onset_pnl_inr).to_numpy(float)
        policy_pnl = pd.to_numeric(g.policy_pnl_inr).to_numpy(float)
        out.append({
            "label": keys[0], "interval": keys[1],
            "episodes": len(g),
            "retention": float(take.mean()),
            "onset_mean_excursion_edge_r": float(onset_edge.mean()),
            "selected_mean_excursion_edge_r": float(chosen_edge[take].mean()) if take.any() else 0.0,
            "onset_counterfactual_pnl_inr": float(onset_pnl.sum()),
            "policy_counterfactual_pnl_inr": float(policy_pnl.sum()),
            "pnl_delta_audit_inr": float((policy_pnl - onset_pnl).sum()),
        })
    return out


def ownership(pred: pd.DataFrame) -> List[Dict]:
    rows = []
    for (label, interval, ts), g in pred.groupby(["label", "interval", "entry_ts"], sort=True):
        if len(g.engine.unique()) < 2:
            continue
        positive = g[g.predicted_excursion_edge_r > 0]
        chosen = positive.sort_values("predicted_excursion_edge_r", ascending=False).iloc[0] if len(positive) else None
        legacy = g.sort_values("engine", key=lambda s: s.map({"PRIMARY":0,"SECONDARY":1,"MICRO":2,"BURST":3})).iloc[0]
        rows.append({
            "label": label, "interval": interval, "entry_ts": float(ts),
            "engines": "|".join(g.engine.astype(str)),
            "legacy_engine": legacy.engine,
            "legacy_excursion_edge_r": float(legacy.actual_excursion_edge_r),
            "legacy_pnl_inr": float(legacy.counterfactual_pnl_inr),
            "policy_engine": chosen.engine if chosen is not None else "HOLD",
            "policy_predicted_excursion_edge_r": float(chosen.predicted_excursion_edge_r) if chosen is not None else 0.0,
            "policy_actual_excursion_edge_r": float(chosen.actual_excursion_edge_r) if chosen is not None else 0.0,
            "policy_pnl_inr": float(chosen.counterfactual_pnl_inr) if chosen is not None else 0.0,
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("canonical_csv", type=Path)
    ap.add_argument("recent_csv_or_gz", type=Path)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True, exist_ok=True)

    hraw = microstate.load_raw(a.canonical_csv, nrows=canonical.RESEARCH_ROWS)
    rraw = microstate.load_raw(a.recent_csv_or_gz)

    print("building cooldown-free signal episodes", flush=True)
    base = v2.build_entry_episode_dataset(a.canonical_csv, a.recent_csv_or_gz, hraw, rraw)
    print(f"attaching rule fingerprints to {len(base)} checkpoints", flush=True)
    data = attach_fingerprints(base, a.canonical_csv, a.recent_csv_or_gz)

    print("running per-engine chronological walk-forward", flush=True)
    pred = walkforward(data)
    policy = episode_policy(pred)

    cp_metrics = checkpoint_metrics(pred)
    p_metrics = policy_metrics(policy)
    agg = aggregate_policy_metrics(policy)
    own = ownership(pred)

    write_csv(a.output / "entry_fingerprint_dataset.csv", data.to_dict("records"))
    write_csv(a.output / "checkpoint_predictions.csv", pred.to_dict("records"))
    write_csv(a.output / "checkpoint_metrics.csv", cp_metrics)
    write_csv(a.output / "episode_policy.csv", policy.to_dict("records"))
    write_csv(a.output / "episode_policy_per_engine.csv", p_metrics)
    write_csv(a.output / "episode_policy_metrics.csv", agg)
    write_csv(a.output / "simultaneous_ownership.csv", own)

    result = {
        "schema": "xau-signal-fingerprint-entry-quality-v1",
        "strategy_changed": False,
        "candidate_created": False,
        "training_target": "excursion_edge_r=(MFE_USD-abs(MAE_USD))/4",
        "final_pnl_used_for_training": False,
        "engine_experts": list(ENGINE_IDS),
        "base_features": BASE_FEATURES,
        "fingerprint_features": FINGERPRINT_FEATURES,
        "model": "HistGradientBoostingRegressor",
        "model_params": MODEL_PARAMS,
        "boundary": "predicted excursion_edge_r > 0",
        "feature_search_performed": False,
        "threshold_search_performed": False,
        "model_search_performed": False,
        "final20_opened": False,
        "promotion_evidence": False,
        "rows": int(len(data)),
        "episodes": int(data.episode_id.nunique()),
        "checkpoint_metrics": cp_metrics,
        "episode_policy_metrics": agg,
        "decision": "Diagnostic only. Use known-data OOS evidence to decide whether a later full shared-slot entry controller is justified.",
    }
    (a.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
