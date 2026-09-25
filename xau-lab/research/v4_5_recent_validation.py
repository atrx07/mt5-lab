"""Parity-gated diagnostic replay of a frozen recent MT5 quote snapshot.

This script has no broker connection and never submits an order. It evaluates
an existing snapshot with the unchanged canonical feature builder.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_multi_ticket_horizon as multi


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECENT = ROOT / "xau_ticks_recent_24h_2026-09-24.csv"
DEFAULT_OUTPUT = ROOT / "results" / "simulations" / "2026-09-24-recent-micro-long-validation"
RECENT_SHA = "9243ac73c3d180417ff634fe9371a28939713a531c9ccfa63f919c94eb9a28b1"
MULTI_FEATURES = [
    "t", "bid", "ask", "mid", "spread", "ss", "imb10", "qacc", "m10", "m30",
    "m60", "m120", "m300", "m1800", "range60", "range300", "er60",
    "min_m10_30", "max_m10_30",
]


def summarize(row, ledger=None):
    out = {
        "realized_pnl_inr": float(row[0]),
        "profit_factor": float(row[1]),
        "trades": int(row[2]),
        "wins": int(row[3]),
        "drawdown_inr": float(row[4]),
    }
    if ledger is not None:
        out["median_hold_sec"] = float(ledger.hold_sec.median()) if len(ledger) else None
        out["mean_hold_sec"] = float(ledger.hold_sec.mean()) if len(ledger) else None
        out["ticket_exposure_hours"] = float(row[5] / 3600)
        out["peak_open_tickets"] = int(row[6])
        out["horizons"] = {
            name: {
                "trades": int(len(part)),
                "pnl_inr": float(part.pnl_inr.sum()),
                "median_hold_sec": float(part.hold_sec.median()),
            }
            for name, part in ledger.groupby("horizon", sort=True)
        }
        out["sides"] = {
            str(int(side)): {"trades": int(len(part)), "pnl_inr": float(part.pnl_inr.sum())}
            for side, part in ledger.groupby("side", sort=True)
        }
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recent", type=Path, default=DEFAULT_RECENT)
    parser.add_argument("--canonical", type=Path, default=ROOT / "xau_ticks_7d.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    actual_sha = canonical.sha256_file(args.recent)
    if actual_sha != RECENT_SHA:
        raise RuntimeError(f"recent snapshot SHA mismatch: {actual_sha}")
    canonical.verify_dataset(args.canonical)
    raw_times = pd.read_csv(args.recent, usecols=["timestamp_utc"])["timestamp_utc"]
    raw_cut_row = int(len(raw_times) * 0.6)
    raw_cut = pd.to_datetime(raw_times.iloc[raw_cut_row], utc=True).timestamp()
    result = {
        "schema_version": "recent-micro-long-diagnostic-v1",
        "dataset_sha256": actual_sha,
        "canonical_dataset_sha256": canonical.DATASET_SHA256,
        "holdout_evaluated": False,
        "raw_rows": int(len(raw_times)),
        "raw_seed_cut_row": raw_cut_row,
        "raw_seed_cut_epoch_sec": raw_cut,
        "selection_note": "Existing modes 0/1 plus one seed-derived mode 3 ablation; no evaluation-segment tuning",
        "accounting_note": "Multi-ticket segments force close; inherited single-slot segments report realized trades only",
        "multi_ticket_common_config": multi.COMMON_CONFIG,
        "multi_ticket_prototypes": {str(mode): multi.PROTOTYPES[mode] for mode in (0, 1, 3)},
        "intervals": {},
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for interval in ("500ms", "1s"):
        historical, historical_bounds = canonical.build_features(args.canonical, interval)
        canonical.assert_baseline(
            canonical.run_strategy(historical, historical_bounds, "v4_4"),
            interval, canonical.DEFAULT_GOLDEN,
        )
        print(interval, "historical V4.4 golden PASS", flush=True)
        arrays, _ = canonical.build_features(args.recent, interval)
        cut = int(np.searchsorted(arrays["t"], raw_cut, "left"))
        intervals = {"sampled_rows": len(arrays["t"]), "sampled_cut_index": cut, "segments": {}}
        common = [arrays[key] for key in canonical.FEATURE_NAMES]
        multi_args = [arrays[key] for key in MULTI_FEATURES]
        for name, start, end in (("seed", 0, cut), ("evaluation", cut, len(arrays["t"]))):
            seg = {}
            for strategy in ("v4_4", "v4_5_b"):
                seg[strategy] = summarize(canonical.simulate(*common, start, end, canonical.burst_config(strategy)))
            d = autopsy.simulate_trace(*common, start, end, canonical.burst_config("v4_5_b"), 1.0)
            seg["candidate_d"] = summarize(d)
            trace = pd.DataFrame(d[5], columns=[
                "entry_index", "exit_index", "engine", "side", "exit_reason", "entry_epoch_sec",
                "exit_epoch_sec", "entry_usd", "entry_oz", "pnl_inr", "peak_usd", "trough_usd",
                "mfe_time_sec", "exit_move_usd",
            ])
            trace["engine_name"] = trace.engine.map(autopsy.ENGINES)
            trace.to_csv(args.output / f"candidate_d_{name}_{interval}_trades.csv", index=False)
            seg["candidate_d"]["engines"] = {
                engine: {"trades": int(len(part)), "pnl_inr": float(part.pnl_inr.sum())}
                for engine, part in trace.groupby("engine_name", sort=True)
            }
            for mode in (0, 1, 3):
                row = multi.simulate_multi(*multi_args, start, end, 0.0, mode)
                stressed = multi.simulate_multi(*multi_args, start, end, 0.20, mode)
                ledger = pd.DataFrame(row[7], columns=multi.LEDGER_COLUMNS)
                ledger["horizon"] = ledger.horizon.map({1.0: "trend", 2.0: "impulse"})
                ledger["exit_reason"] = ledger.exit_reason.map(multi.REASONS)
                if not np.isclose(ledger.pnl_inr.sum(), row[0], atol=1e-8):
                    raise RuntimeError("multi ledger does not match segment P&L")
                ledger.to_csv(args.output / f"multi_mode_{mode}_{name}_{interval}_trades.csv", index=False)
                seg[f"multi_mode_{mode}"] = summarize(row, ledger)
                seg[f"multi_mode_{mode}"]["adverse_fill_20c_each_side_pnl_inr"] = float(stressed[0])
                seg[f"multi_mode_{mode}"]["adverse_fill_20c_each_side_trades"] = int(stressed[2])
            intervals["segments"][name] = seg
            print(interval, name, {k: round(v["realized_pnl_inr"], 2) for k, v in seg.items()}, flush=True)
        full = {}
        for mode in (0, 1, 3):
            row = multi.simulate_multi(*multi_args, 0, len(arrays["t"]), 0.0, mode)
            stressed = multi.simulate_multi(*multi_args, 0, len(arrays["t"]), 0.20, mode)
            ledger = pd.DataFrame(row[7], columns=multi.LEDGER_COLUMNS)
            ledger["horizon"] = ledger.horizon.map({1.0: "trend", 2.0: "impulse"})
            ledger["exit_reason"] = ledger.exit_reason.map(multi.REASONS)
            if not np.isclose(ledger.pnl_inr.sum(), row[0], atol=1e-8):
                raise RuntimeError("full multi ledger does not match P&L")
            ledger.to_csv(args.output / f"multi_mode_{mode}_full_{interval}_trades.csv", index=False)
            full[f"multi_mode_{mode}"] = summarize(row, ledger)
            full[f"multi_mode_{mode}"]["adverse_fill_20c_each_side_pnl_inr"] = float(stressed[0])
            full[f"multi_mode_{mode}"]["adverse_fill_20c_each_side_trades"] = int(stressed[2])
            full[f"multi_mode_{mode}"]["reported_utc_exit_days"] = {
                day: {"trades": int(len(part)), "pnl_inr": float(part.pnl_inr.sum())}
                for day, part in ledger.groupby(
                    pd.to_datetime(ledger.exit_epoch_sec, unit="s", utc=True).dt.strftime("%Y-%m-%d"),
                    sort=True,
                )
            }
        intervals["full_24h_diagnostic"] = full
        print(interval, "full", {k: round(v["realized_pnl_inr"], 2) for k, v in full.items()}, flush=True)
        result["intervals"][interval] = intervals
    (args.output / "diagnostic_metadata.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
