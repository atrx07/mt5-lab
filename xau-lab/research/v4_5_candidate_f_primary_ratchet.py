"""Experiment 40: Candidate F PRIMARY-only profit ratchet.

Candidate F is Candidate D with one frozen exit-only addition:
  * PRIMARY only;
  * activate after +1R MFE (+$4 favorable XAU move);
  * retain at least 50% of live MFE;
  * evaluate on a 5-second wall-clock cadence.

No entry, sizing, spread, cooldown, other-engine lifecycle, or routing rule is
changed. Known data are diagnostic only. Final20 remains sealed.
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

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_regime_portability as portability
import v4_5_router_v2 as v2
import v4_5_router_v2_full_eval as full_eval

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = (
    ROOT / "results" / "simulations" /
    "2026-09-25-v4_5-candidate-f-primary-ratchet"
)

EXPECTED_D = {
    "500ms": {"pnl": 1430.311133793068, "trades": 163, "wins": 81},
    "1s": {"pnl": 385.2544619534224, "trades": 156, "wins": 71},
}
EXPECTED_RECENT_D = {
    "500ms": {"pnl": -223.27329174700338, "trades": 39, "wins": 5},
    "1s": {"pnl": -135.9095261798986, "trades": 34, "wins": 8},
}

RATCHET_TRIGGER_USD = 4.0
RATCHET_RETAIN_FRACTION = 0.50
RATCHET_CHECK_SEC = 5.0
RANDOM_SEED = 20260925
RANDOM_WINDOWS = 40
RANDOM_HOURS = 4.0
SLIPPAGE_STRESS_USD_PER_SIDE = (0.0, 0.05, 0.10, 0.20)

CONFIG = {
    "schema": "xau-candidate-f-primary-ratchet-v1",
    "base_strategy": "Candidate D from Experiment 19",
    "strategy_changed": True,
    "entry_changed": False,
    "exit_changed": True,
    "ratchet_engine": "PRIMARY",
    "ratchet_trigger_mfe_usd": RATCHET_TRIGGER_USD,
    "ratchet_trigger_r": 1.0,
    "ratchet_retain_fraction_of_live_mfe": RATCHET_RETAIN_FRACTION,
    "ratchet_check_sec": RATCHET_CHECK_SEC,
    "secondary_changed": False,
    "micro_changed": False,
    "burst_changed": False,
    "known_data_promotion_allowed": False,
    "final20_opened": False,
}


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


def simulate(
    arr: Dict[str, np.ndarray],
    start: int,
    end: int,
    *,
    candidate_f: bool,
    extra_slippage_usd_per_side: float = 0.0,
    ratchet_events: List[Dict] | None = None,
    context: str = "",
):
    t, bid, ask = arr["t"], arr["bid"], arr["ask"]
    m30, m300 = arr["m30"], arr["m300"]
    r300, er60 = arr["range300"], arr["er60"]
    cfg = canonical.burst_config("v4_5_b")
    slip = float(extra_slippage_usd_per_side)

    bal = 500.0
    gp = 0.0
    gl = 0.0
    ntr = 0
    wins = 0
    peakbal = 500.0
    maxdd = 0.0

    pos = 0
    side = 0
    entry = 0.0
    oz = 0.0
    ptime = 0.0
    peak = 0.0
    partial = 0.0
    partial_done = 0
    highopen = 0
    failure_since = -1e30
    next_ratchet_check = math.inf

    last = {1: -1e30, 2: -1e30, 3: -1e30, 4: -1e30}
    prev_ss = None
    cont = 0.0

    ratchet_exit_count = 0
    primary_entry_count = 0

    for i in range(start, end):
        ts = float(t[i])
        if prev_ss is None or arr["ss"][i] != prev_ss:
            cont = ts
            prev_ss = arr["ss"][i]

        if pos:
            exit_px = (bid[i] - slip) if side == 1 else (ask[i] + slip)
            move = float((exit_px - entry) if side == 1 else (entry - exit_px))
            held = ts - ptime
            if move > peak:
                peak = move

            if pos == 3 and partial_done == 0 and move >= 5.5:
                closeoz = oz * 0.75
                part = move * closeoz * canonical.INR_PER_USD
                bal += part
                partial += part
                oz -= closeoz
                partial_done = 1

            reason = 0
            rev = 1
            trig = -1.0
            gb = 0.0
            tp = 12.0
            maxhold = 900.0

            if pos == 3:
                tp = 10.0
                trig = 4.0
                gb = 2.0
            elif pos == 4:
                tp = cfg[11]
                maxhold = cfg[12]
                trig = cfg[15]
                gb = cfg[16]
                rev = 0
            elif pos == 1 and highopen == 1:
                tp = 25.0
                maxhold = 900.0
                rev = 0
            elif pos == 2 and highopen == 1:
                tp = 8.0
                maxhold = 1200.0
                rev = 0
                trig = 12.0
                gb = 3.0
            elif pos == 1:
                tp = 21.0
                maxhold = 1800.0

            if move <= -4.0:
                reason = 1
            elif move >= tp:
                reason = 2

            if reason == 0 and trig > 0 and peak >= trig and move <= peak - gb:
                reason = 3
            if reason == 0 and pos == 3 and held >= 45.0 and peak < 0.75:
                reason = 4
            if reason == 0 and pos == 4 and held >= cfg[13] and peak < cfg[14]:
                reason = 4

            if pos == 4 and not np.isfinite(m30[i]):
                failure_since = -1e30
            if reason == 0 and pos == 4 and np.isfinite(m30[i]):
                failure = (side == 1 and m30[i] <= 0) or (side == -1 and m30[i] >= 0)
                if failure:
                    if failure_since < -1e20:
                        failure_since = ts
                    if ts - failure_since >= 1.0:
                        reason = 5
                else:
                    failure_since = -1e30

            # Candidate F's only lifecycle addition. Check on wall-clock cadence,
            # not every sampled tick, so 500 ms and 1 s use the same timing rule.
            if (
                reason == 0
                and candidate_f
                and pos == 1
                and ts >= next_ratchet_check
            ):
                while next_ratchet_check <= ts:
                    next_ratchet_check += RATCHET_CHECK_SEC
                if (
                    peak >= RATCHET_TRIGGER_USD
                    and move <= RATCHET_RETAIN_FRACTION * peak
                ):
                    reason = 8

            if reason == 0 and rev == 1 and np.isfinite(m300[i]):
                if (side == 1 and m300[i] <= 0) or (side == -1 and m300[i] >= 0):
                    reason = 5
            if reason == 0 and held >= maxhold:
                reason = 7

            if reason:
                pnl = move * oz * canonical.INR_PER_USD
                total = pnl + partial
                bal += pnl
                ntr += 1
                if total > 0:
                    gp += total
                    wins += 1
                elif total < 0:
                    gl -= total

                peakbal = max(peakbal, bal)
                maxdd = max(maxdd, peakbal - bal)
                last[pos] = ts

                if reason == 8:
                    ratchet_exit_count += 1
                    if ratchet_events is not None:
                        ratchet_events.append({
                            "context": context,
                            "entry_ts": float(ptime),
                            "exit_ts": ts,
                            "side": "BUY" if side == 1 else "SELL",
                            "held_sec": float(held),
                            "peak_move_usd": float(peak),
                            "exit_move_usd": float(move),
                            "retained_fraction": float(move / peak) if peak > 0 else math.nan,
                            "trade_pnl_inr": float(total),
                        })

                pos = 0
            continue

        candidates = v2.signal_candidates(arr, i, cont, last)
        if not candidates:
            continue

        engine, sside = candidates[0]
        high = bool(
            np.isfinite(r300[i])
            and np.isfinite(er60[i])
            and r300[i] >= 5.0
            and er60[i] >= 0.03
        )

        entry = float((ask[i] + slip) if sside == 1 else (bid[i] - slip))
        oz = min(
            bal * 0.03 / (4 * canonical.INR_PER_USD),
            (bal / canonical.INR_PER_USD * 100) / entry,
        )
        pos = engine
        side = sside
        ptime = ts
        peak = 0.0
        partial = 0.0
        partial_done = 0
        highopen = 1 if high else 0
        failure_since = -1e30
        next_ratchet_check = (
            ts + RATCHET_CHECK_SEC
            if candidate_f and engine == 1
            else math.inf
        )
        if engine == 1:
            primary_entry_count += 1

    pf = gp / gl if gl > 0 else 999.0
    terminal_unrealized = 0.0
    if pos and end > start:
        j = end - 1
        exit_px = (bid[j] - slip) if side == 1 else (ask[j] + slip)
        terminal_move = float((exit_px - entry) if side == 1 else (entry - exit_px))
        terminal_unrealized = terminal_move * oz * canonical.INR_PER_USD

    return {
        "pnl_inr": bal - 500.0,
        "terminal_unrealized_inr": terminal_unrealized,
        "terminal_equity_pnl_inr": bal - 500.0 + terminal_unrealized,
        "open_position_at_end": bool(pos),
        "profit_factor": pf,
        "trades": ntr,
        "wins": wins,
        "win_rate": wins / ntr if ntr else 0.0,
        "max_drawdown_inr": maxdd,
        "primary_entries": primary_entry_count,
        "primary_ratchet_exits": ratchet_exit_count,
    }


def compact(m: Dict) -> Dict:
    return {
        k: m[k]
        for k in (
            "pnl_inr",
            "terminal_unrealized_inr",
            "terminal_equity_pnl_inr",
            "open_position_at_end",
            "profit_factor",
            "trades",
            "wins",
            "win_rate",
            "max_drawdown_inr",
            "primary_entries",
            "primary_ratchet_exits",
        )
        if k in m
    }


def summarize_segments(rows: List[Dict]) -> Dict:
    factor = 1.0
    trades = wins = primary_entries = ratchet_exits = 0
    dds = []
    for m in rows:
        factor *= 1.0 + m["pnl_inr"] / canonical.START_BALANCE_INR
        trades += int(m["trades"])
        wins += int(m["wins"])
        primary_entries += int(m.get("primary_entries", 0))
        ratchet_exits += int(m.get("primary_ratchet_exits", 0))
        dds.append(float(m["max_drawdown_inr"]))
    return {
        "compounded_pnl_inr": canonical.START_BALANCE_INR * (factor - 1.0),
        "trades": trades,
        "wins": wins,
        "win_rate": wins / trades if trades else 0.0,
        "max_segment_drawdown_inr": max(dds) if dds else 0.0,
        "primary_entries": primary_entries,
        "primary_ratchet_exits": ratchet_exits,
    }


def assert_candidate_d(summary: Dict, interval: str):
    exp = EXPECTED_D[interval]
    if abs(summary["compounded_pnl_inr"] - exp["pnl"]) > 1e-6:
        raise RuntimeError(f"Candidate D P&L parity drift {interval}: {summary}")
    if summary["trades"] != exp["trades"] or summary["wins"] != exp["wins"]:
        raise RuntimeError(f"Candidate D count parity drift {interval}: {summary}")


def assert_recent_d(summary: Dict, interval: str):
    exp = EXPECTED_RECENT_D[interval]
    if abs(summary["terminal_equity_pnl_inr"] - exp["pnl"]) > 1e-6:
        raise RuntimeError(f"Recent Candidate D P&L parity drift {interval}: {summary}")
    if summary["trades"] != exp["trades"] or summary["wins"] != exp["wins"]:
        raise RuntimeError(f"Recent Candidate D count parity drift {interval}: {summary}")


def random_summary(rows: List[Dict], prefix: str) -> Dict:
    pnl = np.asarray([r[f"{prefix}_pnl"] for r in rows], dtype=float)
    tr = np.asarray([r[f"{prefix}_trades"] for r in rows], dtype=float)
    wi = np.asarray([r[f"{prefix}_wins"] for r in rows], dtype=float)
    return {
        "windows": len(rows),
        "median_terminal_equity_pnl_inr": float(np.median(pnl)) if len(pnl) else 0.0,
        "mean_terminal_equity_pnl_inr": float(np.mean(pnl)) if len(pnl) else 0.0,
        "p05_terminal_equity_pnl_inr": float(np.quantile(pnl, 0.05)) if len(pnl) else 0.0,
        "p95_terminal_equity_pnl_inr": float(np.quantile(pnl, 0.95)) if len(pnl) else 0.0,
        "positive_window_fraction": float(np.mean(pnl > 0)) if len(pnl) else 0.0,
        "total_trades": int(tr.sum()),
        "total_wins": int(wi.sum()),
        "aggregate_win_rate": float(wi.sum() / tr.sum()) if tr.sum() else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("canonical_csv", type=Path)
    ap.add_argument("recent_csv_or_gz", type=Path)
    ap.add_argument("--random-windows", type=int, default=RANDOM_WINDOWS)
    ap.add_argument("--random-hours", type=float, default=RANDOM_HOURS)
    ap.add_argument("--seed", type=int, default=RANDOM_SEED)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "candidate_f_config.json").write_text(
        json.dumps(CONFIG, indent=2) + "\n", encoding="utf-8"
    )

    result = {
        "schema": "xau-candidate-f-primary-ratchet-eval-v1",
        "candidate_config": CONFIG,
        "known_data_promotion_allowed": False,
        "final20_opened": False,
        "random_window_method": (
            "deterministic real contiguous four-hour windows from known canonical "
            "first80/recent24h; stress only, never promotion evidence"
        ),
        "slippage_stress_usd_per_side": list(SLIPPAGE_STRESS_USD_PER_SIDE),
        "intervals": {},
    }
    segment_rows = []
    split_rows = []
    random_rows_all = []
    stress_rows = []
    ratchet_events = []

    for interval in ("500ms", "1s"):
        print(f"{interval}: canonical", flush=True)
        h_arr, h_bounds = canonical.build_features(a.canonical_csv, interval)
        canonical.assert_baseline(
            canonical.run_strategy(h_arr, h_bounds, "v4_4"),
            interval,
            canonical.DEFAULT_GOLDEN,
        )
        h_inds = autopsy.indices(h_arr, h_bounds)

        dseg = []
        fseg = []
        for sid, (s, e) in enumerate(h_inds):
            d = simulate(h_arr, s, e, candidate_f=False)
            legacy = v2.simulate(h_arr, s, e, legacy=True)
            for key in ("pnl_inr", "profit_factor", "trades", "wins", "max_drawdown_inr"):
                if abs(float(d[key]) - float(legacy[key])) > 1e-9:
                    raise RuntimeError(
                        f"Candidate D implementation parity failure {interval} segment {sid} {key}"
                    )
            f = simulate(
                h_arr,
                s,
                e,
                candidate_f=True,
                ratchet_events=ratchet_events,
                context=f"historical7d:{interval}:segment{sid}",
            )
            dseg.append(d)
            fseg.append(f)
            segment_rows.append({
                "interval": interval,
                "segment_id": sid,
                "candidate_d_pnl_inr": d["pnl_inr"],
                "candidate_f_pnl_inr": f["pnl_inr"],
                "delta_f_vs_d_inr": f["pnl_inr"] - d["pnl_inr"],
                "candidate_d_trades": d["trades"],
                "candidate_f_trades": f["trades"],
                "candidate_d_wins": d["wins"],
                "candidate_f_wins": f["wins"],
                "candidate_d_max_drawdown_inr": d["max_drawdown_inr"],
                "candidate_f_max_drawdown_inr": f["max_drawdown_inr"],
                "candidate_f_primary_ratchet_exits": f["primary_ratchet_exits"],
            })

        ds = summarize_segments(dseg)
        fs = summarize_segments(fseg)
        assert_candidate_d(ds, interval)

        print(f"{interval}: recent", flush=True)
        r_arr, _ = canonical.build_features(a.recent_csv_or_gz, interval)
        rd = simulate(r_arr, 0, len(r_arr["t"]), candidate_f=False)
        assert_recent_d(rd, interval)
        rf = simulate(
            r_arr,
            0,
            len(r_arr["t"]),
            candidate_f=True,
            ratchet_events=ratchet_events,
            context=f"recent24h:{interval}:whole",
        )

        times = pd.read_csv(a.recent_csv_or_gz, usecols=["timestamp_utc"])["timestamp_utc"]
        cut_ts = pd.to_datetime(times.iloc[int(len(times) * 0.6)], utc=True).timestamp()
        cut = int(np.searchsorted(r_arr["t"], cut_ts, "left"))
        recent_split = []
        for name, s, e in (("seed", 0, cut), ("evaluation", cut, len(r_arr["t"]))):
            d = simulate(r_arr, s, e, candidate_f=False)
            f = simulate(r_arr, s, e, candidate_f=True)
            row = {
                "split": name,
                "candidate_d": compact(d),
                "candidate_f": compact(f),
                "delta_f_vs_d_inr": f["terminal_equity_pnl_inr"] - d["terminal_equity_pnl_inr"],
            }
            recent_split.append(row)
            split_rows.append({
                "interval": interval,
                "split": name,
                "candidate_d_terminal_equity_pnl_inr": d["terminal_equity_pnl_inr"],
                "candidate_f_terminal_equity_pnl_inr": f["terminal_equity_pnl_inr"],
                "delta_f_vs_d_inr": f["terminal_equity_pnl_inr"] - d["terminal_equity_pnl_inr"],
                "candidate_d_trades": d["trades"],
                "candidate_f_trades": f["trades"],
                "candidate_d_wins": d["wins"],
                "candidate_f_wins": f["wins"],
                "candidate_f_primary_ratchet_exits": f["primary_ratchet_exits"],
            })

        rng = np.random.default_rng(a.seed + (0 if interval == "500ms" else 1))
        hist_ranges = full_eval.continuous_ranges(h_arr, h_inds)
        recent_ranges = full_eval.continuous_ranges(r_arr, [(0, len(r_arr["t"]))])
        random_rows = []
        for wid in range(a.random_windows):
            source = "historical7d" if wid % 2 == 0 else "recent24h"
            if source == "historical7d":
                arr = h_arr
                ranges = hist_ranges
            else:
                arr = r_arr
                ranges = recent_ranges
            s, e, range_id = full_eval.random_window_from_ranges(
                arr, ranges, rng, a.random_hours
            )
            d = simulate(arr, s, e, candidate_f=False)
            f = simulate(arr, s, e, candidate_f=True)
            row = {
                "interval": interval,
                "window_id": wid,
                "source": source,
                "source_range_id": range_id,
                "start_ts": float(arr["t"][s]),
                "end_ts": float(arr["t"][e - 1]),
                "candidate_d_pnl": float(d["terminal_equity_pnl_inr"]),
                "candidate_f_pnl": float(f["terminal_equity_pnl_inr"]),
                "candidate_d_trades": int(d["trades"]),
                "candidate_f_trades": int(f["trades"]),
                "candidate_d_wins": int(d["wins"]),
                "candidate_f_wins": int(f["wins"]),
                "candidate_f_primary_ratchet_exits": int(f["primary_ratchet_exits"]),
            }
            random_rows.append(row)
            random_rows_all.append(row)

        dr = random_summary(random_rows, "candidate_d")
        fr = random_summary(random_rows, "candidate_f")

        cost_stress = []
        for slip in SLIPPAGE_STRESS_USD_PER_SIDE:
            d_stress_seg = [
                simulate(
                    h_arr, s, e,
                    candidate_f=False,
                    extra_slippage_usd_per_side=slip,
                )
                for s, e in h_inds
            ]
            f_stress_seg = [
                simulate(
                    h_arr, s, e,
                    candidate_f=True,
                    extra_slippage_usd_per_side=slip,
                )
                for s, e in h_inds
            ]
            hd = summarize_segments(d_stress_seg)
            hf = summarize_segments(f_stress_seg)
            rds = simulate(
                r_arr, 0, len(r_arr["t"]),
                candidate_f=False,
                extra_slippage_usd_per_side=slip,
            )
            rfs = simulate(
                r_arr, 0, len(r_arr["t"]),
                candidate_f=True,
                extra_slippage_usd_per_side=slip,
            )
            stress = {
                "extra_slippage_usd_per_side": slip,
                "historical_candidate_d_compounded_pnl_inr": hd["compounded_pnl_inr"],
                "historical_candidate_f_compounded_pnl_inr": hf["compounded_pnl_inr"],
                "historical_delta_f_vs_d_inr": hf["compounded_pnl_inr"] - hd["compounded_pnl_inr"],
                "recent_candidate_d_terminal_equity_pnl_inr": rds["terminal_equity_pnl_inr"],
                "recent_candidate_f_terminal_equity_pnl_inr": rfs["terminal_equity_pnl_inr"],
                "recent_delta_f_vs_d_inr": rfs["terminal_equity_pnl_inr"] - rds["terminal_equity_pnl_inr"],
                "historical_candidate_f_ratchet_exits": hf["primary_ratchet_exits"],
                "recent_candidate_f_ratchet_exits": rfs["primary_ratchet_exits"],
            }
            cost_stress.append(stress)
            stress_rows.append({"interval": interval, **stress})

        result["intervals"][interval] = {
            "canonical_first80": {
                "candidate_d": ds,
                "candidate_f": fs,
                "delta_f_vs_d_inr": fs["compounded_pnl_inr"] - ds["compounded_pnl_inr"],
                "trade_retention": fs["trades"] / ds["trades"] if ds["trades"] else 0.0,
                "win_rate_delta": fs["win_rate"] - ds["win_rate"],
                "candidate_d_segments": [compact(x) for x in dseg],
                "candidate_f_segments": [compact(x) for x in fseg],
            },
            "recent24h_whole": {
                "candidate_d": compact(rd),
                "candidate_f": compact(rf),
                "delta_f_vs_d_inr": rf["terminal_equity_pnl_inr"] - rd["terminal_equity_pnl_inr"],
                "trade_retention": rf["trades"] / rd["trades"] if rd["trades"] else 0.0,
                "win_rate_delta": rf["win_rate"] - rd["win_rate"],
            },
            "recent24h_split": recent_split,
            "random_real_windows": {
                "candidate_d": dr,
                "candidate_f": fr,
                "candidate_f_better_than_d_fraction": float(
                    np.mean([x["candidate_f_pnl"] > x["candidate_d_pnl"] for x in random_rows])
                ) if random_rows else 0.0,
                "candidate_f_equal_to_d_fraction": float(
                    np.mean([
                        abs(x["candidate_f_pnl"] - x["candidate_d_pnl"]) <= 1e-9
                        for x in random_rows
                    ])
                ) if random_rows else 0.0,
                "trade_retention": fr["total_trades"] / dr["total_trades"] if dr["total_trades"] else 0.0,
            },
            "cost_stress": cost_stress,
        }

        del h_arr, r_arr

    write_csv(a.output / "canonical_segment_comparison.csv", segment_rows)
    write_csv(a.output / "recent_split_comparison.csv", split_rows)
    write_csv(a.output / "random_real_windows.csv", random_rows_all)
    write_csv(a.output / "cost_stress.csv", stress_rows)
    write_csv(a.output / "primary_ratchet_events.csv", ratchet_events)
    (a.output / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
