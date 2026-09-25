"""Experiment 23: raw-event regime-normalization diagnostic for V4.5.

No trading rule changes. The script verifies V4.4/B/D parity, derives causal
market-state features from raw tick events before execution-grid sampling, and
measures cross-grid regime stability plus engine robustness by four-hour window.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy

RESULT_DIR = (
    Path(__file__).resolve().parents[1]
    / "results"
    / "simulations"
    / "2026-09-25-v4_5-regime-normalization"
)
EXPECTED_D = {
    "500ms": {"pnl": 1430.311133793068, "trades": 163, "wins": 81},
    "1s": {"pnl": 385.2544619534224, "trades": 156, "wins": 71},
}


def candidate_d_rows(csv_path: Path, interval: str):
    arrays, bounds = canonical.build_features(csv_path, interval)
    v44 = canonical.run_strategy(arrays, bounds, "v4_4")
    canonical.assert_baseline(v44, interval, canonical.DEFAULT_GOLDEN)
    b = canonical.run_strategy(arrays, bounds, "v4_5_b")
    for key, expected in autopsy.REFERENCE[interval].items():
        if abs(b[key] - expected) > 1e-9:
            raise RuntimeError(f"Candidate B drift {interval} {key}")

    args = [arrays[x] for x in canonical.FEATURE_NAMES]
    cfg = canonical.burst_config("v4_5_b")
    segments, rows = [], []
    for sid, (start, end) in enumerate(autopsy.indices(arrays, bounds)):
        control = autopsy.simulate_trace(*args, start, end, cfg, 0.0)
        for j, name in enumerate(
            ("pnl_inr", "profit_factor", "trades", "wins", "max_drawdown_inr")
        ):
            if abs(control[j] - b["segments"][sid][name]) > 1e-9:
                raise RuntimeError(
                    f"Candidate B trace parity failed {interval} segment {sid} {name}"
                )

        r = autopsy.simulate_trace(*args, start, end, cfg, 1.0)
        segments.append(
            {
                "segment_id": sid,
                "pnl_inr": float(r[0]),
                "profit_factor": float(r[1]),
                "trades": int(r[2]),
                "wins": int(r[3]),
                "max_drawdown_inr": float(r[4]),
            }
        )
        for tid, x in enumerate(r[5]):
            engine, side = int(x[2]), int(x[3])
            rows.append(
                {
                    "trade_id": f"{interval}-s{sid}-t{tid}",
                    "interval": interval,
                    "segment_id": sid,
                    "engine": autopsy.ENGINES[engine],
                    "side": "BUY" if side == 1 else "SELL",
                    "entry_ts": float(x[5]),
                    "exit_ts": float(x[6]),
                    "pnl_inr": float(x[9]),
                }
            )

    factor = 1.0
    for segment in segments:
        factor *= 1.0 + segment["pnl_inr"] / 500.0
    d = {
        "compounded_pnl_inr": 500.0 * (factor - 1.0),
        "trades_sum": sum(s["trades"] for s in segments),
        "wins_sum": sum(s["wins"] for s in segments),
    }
    expected = EXPECTED_D[interval]
    if (
        abs(d["compounded_pnl_inr"] - expected["pnl"]) > 1e-9
        or d["trades_sum"] != expected["trades"]
        or d["wins_sum"] != expected["wins"]
    ):
        raise RuntimeError(f"Candidate D parity failed {interval}: {d}")
    return {"v4_4": v44, "candidate_b": b, "candidate_d": d}, rows


def raw_frame(path: Path):
    df = pd.read_csv(path, nrows=canonical.RESEARCH_ROWS, usecols=["timestamp_utc", "bid", "ask"])
    df["t"] = pd.to_datetime(df.timestamp_utc, utc=True, format="mixed")
    df = df.sort_values("t", kind="stable").reset_index(drop=True)
    df["mid"] = (df.bid + df.ask) / 2.0
    df["spread"] = df.ask - df.bid
    gap = df.t.diff().dt.total_seconds().fillna(0)
    df["session"] = (gap > 5.0).cumsum().astype("int32")
    move = df.mid.diff()
    move[df.session.diff().fillna(1) != 0] = 0
    df["up"] = (move > 0).astype(np.int32)
    df["down"] = (move < 0).astype(np.int32)
    df["absdiff"] = move.abs().fillna(0.0)
    return df


def completed_baselines(df):
    raw = df.set_index("t")
    minute = pd.DataFrame(
        {
            "spread_med": raw.spread.resample("1min").median(),
            "range1m": raw.mid.resample("1min").max() - raw.mid.resample("1min").min(),
            "last1m": raw.mid.resample("1min").last(),
        }
    )
    minute["absret1m"] = minute.last1m.diff().abs()
    minute["spread_base"] = minute.spread_med.rolling(30, min_periods=10).median().shift(1)
    minute["range_base"] = minute.range1m.rolling(30, min_periods=10).median().shift(1)
    minute["m60_base"] = minute.absret1m.rolling(30, min_periods=10).median().shift(1)

    five = raw.mid.resample("5min").last().to_frame("last5m")
    five["absret5m"] = five.last5m.diff().abs()
    five["m300_base"] = five.absret5m.rolling(24, min_periods=8).median().shift(1)

    ten = raw.mid.resample("10s").size().to_frame("count10")
    ten["activity_base"] = ten.count10.rolling(180, min_periods=60).median().shift(1)
    return minute, five, ten


def before(series, ts):
    i = series.index.searchsorted(ts, side="right") - 1
    return float(series.iloc[i]) if i >= 0 and np.isfinite(series.iloc[i]) else np.nan


def bucket(value, low, high, labels):
    if not np.isfinite(value):
        return "unknown"
    if value < low:
        return labels[0]
    if value <= high:
        return labels[1]
    return labels[2]


def overlay(path: Path, trades):
    df = raw_frame(path)
    minute, five, ten = completed_baselines(df)

    t = df.t.to_numpy(dtype="datetime64[ns]").astype(np.int64) / 1e9
    mid, spread, session = df.mid.to_numpy(), df.spread.to_numpy(), df.session.to_numpy()
    up, down, absdiff = df.up.to_numpy(), df.down.to_numpy(), df.absdiff.to_numpy()

    idx = np.arange(len(df), dtype=np.int64)
    starts = np.where(np.r_[True, session[1:] != session[:-1]], idx, 0)
    starts = np.maximum.accumulate(starts)
    cup = np.cumsum(up, dtype=np.int64)
    cdown = np.cumsum(down, dtype=np.int64)
    cpath = np.cumsum(absdiff, dtype=np.float64)

    def csum(values, a, b):
        return values[b] - (values[a - 1] if a else 0)

    def ratio(value, baseline):
        if np.isfinite(value) and np.isfinite(baseline) and abs(baseline) > 1e-12:
            return float(value / baseline)
        return np.nan

    out = []
    for trade in trades:
        ts = float(trade["entry_ts"])
        i = int(np.searchsorted(t, ts, side="right") - 1)
        s0 = int(starts[i])
        a10 = max(s0, int(np.searchsorted(t, t[i] - 10, side="left")))
        a60 = max(s0, int(np.searchsorted(t, t[i] - 60, side="left")))
        j60 = int(np.searchsorted(t, t[i] - 60, side="right") - 1)
        j300 = int(np.searchsorted(t, t[i] - 300, side="right") - 1)

        m60 = mid[i] - mid[j60] if j60 >= s0 else np.nan
        m300 = mid[i] - mid[j300] if j300 >= s0 else np.nan
        range60 = float(np.max(mid[a60 : i + 1]) - np.min(mid[a60 : i + 1]))
        path60 = csum(cpath, a60, i)
        er60 = abs(m60) / path60 if np.isfinite(m60) and path60 > 1e-12 else np.nan
        u, d = csum(cup, a10, i), csum(cdown, a10, i)
        imbalance = (u - d) / (u + d) if u + d else 0.0
        count10 = i - a10 + 1

        dt = pd.Timestamp(t[i], unit="s", tz="UTC")
        minute_key = dt.floor("min") - pd.Timedelta("1ns")
        five_key = dt.floor("5min") - pd.Timedelta("1ns")
        ten_key = dt.floor("10s") - pd.Timedelta("1ns")

        row = dict(trade)
        row.update(
            {
                "raw_spread_rel": ratio(spread[i], before(minute.spread_base, minute_key)),
                "raw_range60_rel": ratio(range60, before(minute.range_base, minute_key)),
                "raw_m60_rel": ratio(m60, before(minute.m60_base, minute_key)),
                "raw_m300_rel": ratio(m300, before(five.m300_base, five_key)),
                "raw_activity_rel": ratio(count10, before(ten.activity_base, ten_key)),
                "raw_er60": float(er60),
                "raw_imb10": float(imbalance),
            }
        )
        row["raw_vol_regime"] = bucket(row["raw_range60_rel"], 0.75, 1.50, ("low","normal","high"))
        row["raw_spread_regime"] = bucket(row["raw_spread_rel"], 0.75, 1.25, ("tight","normal","wide"))
        row["raw_efficiency_regime"] = bucket(row["raw_er60"], 0.10, 0.25, ("choppy","mixed","efficient"))
        row["raw_activity_regime"] = bucket(row["raw_activity_rel"], 0.75, 1.50, ("slow","normal","fast"))
        row["raw_regime_key"] = "|".join(
            (row["raw_vol_regime"], row["raw_spread_regime"], row["raw_efficiency_regime"], row["raw_activity_regime"])
        )
        out.append(row)
    return out


def profit_factor(values):
    gp = sum(x for x in values if x > 0)
    gl = -sum(x for x in values if x < 0)
    return gp / gl if gl else (999.0 if gp else 0.0)


def cross_grid_matches(rows):
    first = [r for r in rows if r["interval"] == "500ms"]
    second = [r for r in rows if r["interval"] == "1s"]
    used, matches = set(), []
    for a in first:
        options = [
            (abs(b["entry_ts"] - a["entry_ts"]), j, b)
            for j, b in enumerate(second)
            if j not in used
            and b["segment_id"] == a["segment_id"]
            and b["engine"] == a["engine"]
            and b["side"] == a["side"]
            and abs(b["entry_ts"] - a["entry_ts"]) <= 120
        ]
        if not options:
            continue
        _, j, b = min(options, key=lambda x: x[0])
        used.add(j)
        matches.append(
            {
                "vol_match": a["raw_vol_regime"] == b["raw_vol_regime"],
                "spread_match": a["raw_spread_regime"] == b["raw_spread_regime"],
                "efficiency_match": a["raw_efficiency_regime"] == b["raw_efficiency_regime"],
                "activity_match": a["raw_activity_regime"] == b["raw_activity_regime"],
                "regime_key_match": a["raw_regime_key"] == b["raw_regime_key"],
            }
        )
    return matches


def write_csv(path: Path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path, default=RESULT_DIR)
    args = parser.parse_args()

    digest = canonical.verify_dataset(args.csv)
    metadata, trades = {}, []
    for interval in ("500ms", "1s"):
        meta, interval_trades = candidate_d_rows(args.csv, interval)
        metadata[interval] = meta
        trades.extend(interval_trades)
        print(f"{interval}: V4.4/B/D parity PASS; {len(interval_trades)} Candidate D trades", flush=True)

    rows = overlay(args.csv, trades)
    matches = cross_grid_matches(rows)

    frame = pd.DataFrame(rows)
    frame["entry_dt"] = pd.to_datetime(frame.entry_ts, unit="s", utc=True)
    frame["window4h"] = frame.entry_dt.dt.floor("4h")
    robustness = []
    for (interval, engine), group in frame.groupby(["interval", "engine"]):
        windows = group.groupby("window4h").pnl_inr.sum()
        robustness.append(
            {
                "interval": interval,
                "engine": engine,
                "trades": len(group),
                "wins": int((group.pnl_inr > 0).sum()),
                "total_pnl_inr": float(group.pnl_inr.sum()),
                "profit_factor": float(profit_factor(group.pnl_inr.tolist())),
                "positive_4h_windows": int((windows > 0).sum()),
                "negative_4h_windows": int((windows < 0).sum()),
                "median_4h_pnl_inr": float(windows.median()),
                "worst_4h_pnl_inr": float(windows.min()),
                "best_4h_pnl_inr": float(windows.max()),
            }
        )

    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "candidate_d_raw_regime_trades.csv", rows)
    write_csv(args.output / "engine_robustness_4h.csv", robustness)

    agreement = {
        key: float(np.mean([m[key] for m in matches]))
        for key in ("vol_match","spread_match","efficiency_match","activity_match","regime_key_match")
    }
    summary = {
        "schema_version": "xau-raw-event-regime-v1",
        "dataset_sha256": digest,
        "research_rows": canonical.RESEARCH_ROWS,
        "raw_boundaries": canonical.BOUND_RAW,
        "holdout_evaluated": False,
        "strategy_changed": False,
        "parity": metadata,
        "cross_grid": {"matched_trades": len(matches), "agreement": agreement},
        "decision": "Diagnostic schema accepted; no strategy or engine gate promoted. Replay unchanged on non-overlapping snapshots before selecting a router.",
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["cross_grid"], indent=2), flush=True)


if __name__ == "__main__":
    main()
