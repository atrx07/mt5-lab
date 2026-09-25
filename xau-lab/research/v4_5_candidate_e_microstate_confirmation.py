"""Experiment 37: Candidate E microstate confirmation.

Candidate E keeps Candidate D's priority, entries, exits, sizing, cooldowns, and
confirmed BURST failure exit. The only strategy change is a fail-open PRIMARY
admission veto driven by the frozen xau-microstate-v1 representation:

    veto PRIMARY for the current sampled quote iff
      dir_mid_move2 < 0 AND dir_event_imb2 < 0

Both tests use natural zero boundaries and are direction-normalized. A veto does
not start or extend any engine cooldown and does not fall through to a lower
priority engine on that tick. If the legacy PRIMARY setup remains valid on a
later quote and the contradiction clears, Candidate E may enter then.

Known historical/recent runs are diagnostic only. They may reject a broken
candidate but cannot promote it; promotion requires genuinely new non-overlapping
raw XAU data. The final 20% historical holdout remains sealed.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_microstate_v1_freeze as microstate
import v4_5_regime_portability as portability
import v4_5_router_v2 as v2
import v4_5_router_v2_full_eval as full_eval

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-09-25-v4_5-candidate-e-microstate-confirmation"

EXPECTED_D = {
    "500ms": {"pnl": 1430.311133793068, "trades": 163, "wins": 81},
    "1s": {"pnl": 385.2544619534224, "trades": 156, "wins": 71},
}
EXPECTED_RECENT_D = {
    "500ms": {"pnl": -223.27329174700338, "trades": 39, "wins": 5},
    "1s": {"pnl": -135.9095261798986, "trades": 34, "wins": 8},
}
RANDOM_SEED = 20260925
RANDOM_WINDOWS = 40
RANDOM_HOURS = 4.0
SLIPPAGE_STRESS_USD_PER_SIDE = (0.0, 0.05, 0.10, 0.20)

CANDIDATE_CONFIG = {
    "schema": "xau-candidate-e-primary-micro-confirmation-v1",
    "base_strategy": "Candidate D from Experiment 19",
    "strategy_changed": True,
    "changed_engine": "PRIMARY only",
    "microstate_schema": "xau-microstate-v1",
    "primary_veto": {
        "all_of": ["dir_mid_move2 < 0", "dir_event_imb2 < 0"],
        "meaning": "immediate raw price movement and raw event pressure both contradict intended PRIMARY direction",
        "threshold_source": "natural direction-neutral zero; no outcome/P&L search",
    },
    "missing_feature_policy": "fail open (allow legacy Candidate D entry)",
    "veto_cooldown": "none; do not mutate Candidate D cooldown state",
    "same_tick_fall_through": False,
    "retry_policy": "legacy PRIMARY signal may be reconsidered on later sampled quotes if still valid",
    "unchanged": [
        "Candidate D engine priority PRIMARY > SECONDARY > MICRO > BURST",
        "all engine signal thresholds",
        "all exit/lifecycle rules including BURST 1-second confirmed failure",
        "3% planned-risk sizing and leverage cap",
        "$4 emergency stop",
        "spread rules",
        "shared single-position slot",
    ],
    "known_data_promotion_allowed": False,
    "final20_opened": False,
    "prospective_validation_required": True,
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
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def micro_features(
    raw: Dict[str, np.ndarray],
    ts: float,
    side: int,
    cache: Dict[Tuple[float, int], Dict[str, float]],
) -> Dict[str, float]:
    key = (float(ts), int(side))
    row = cache.get(key)
    if row is None:
        row = microstate.features_at(raw, float(ts), int(side))
        cache[key] = row
    return row


def primary_is_contradicted(features: Dict[str, float]) -> bool:
    move = float(features.get("dir_mid_move2", math.nan))
    pressure = float(features.get("dir_event_imb2", math.nan))
    if not (math.isfinite(move) and math.isfinite(pressure)):
        return False
    return move < 0.0 and pressure < 0.0


def simulate(
    arr: Dict[str, np.ndarray],
    start: int,
    end: int,
    *,
    candidate_e: bool,
    micro_raw: Optional[Dict[str, np.ndarray]] = None,
    micro_cache: Optional[Dict[Tuple[float, int], Dict[str, float]]] = None,
    extra_slippage_usd_per_side: float = 0.0,
    veto_rows: Optional[List[Dict]] = None,
    context: str = "",
):
    t, bid, ask = arr["t"], arr["bid"], arr["ask"]
    m30, m300 = arr["m30"], arr["m300"]
    r300, er60 = arr["range300"], arr["er60"]
    cfg = canonical.burst_config("v4_5_b")
    slip = float(extra_slippage_usd_per_side)

    bal = 500.0
    gp = gl = 0.0
    ntr = wins = 0
    peakbal = 500.0
    maxdd = 0.0
    pos = 0
    side = 0
    entry = oz = ptime = peak = 0.0
    partial = 0.0
    partial_done = 0
    highopen = 0
    failure_since = -1e30
    last = {1: -1e30, 2: -1e30, 3: -1e30, 4: -1e30}
    prev_ss = None
    cont = 0.0

    primary_signals = 0
    primary_vetoes = 0
    delayed_primary_entries = 0
    previous_tick_vetoed_primary = False

    for i in range(start, end):
        ts = float(t[i])
        if prev_ss is None or arr["ss"][i] != prev_ss:
            cont = ts
            prev_ss = arr["ss"][i]

        if pos:
            exit_px = (bid[i] - slip) if side == 1 else (ask[i] + slip)
            move = (exit_px - entry) if side == 1 else (entry - exit_px)
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
                pos = 0
            continue

        candidates = v2.signal_candidates(arr, i, cont, last)
        if not candidates:
            previous_tick_vetoed_primary = False
            continue

        engine, sside = candidates[0]

        if candidate_e and engine == 1:
            primary_signals += 1
            if micro_raw is None or micro_cache is None:
                raise RuntimeError("Candidate E requires raw microstate data and cache")
            feat = micro_features(micro_raw, ts, sside, micro_cache)
            if primary_is_contradicted(feat):
                primary_vetoes += 1
                previous_tick_vetoed_primary = True
                if veto_rows is not None:
                    row = {
                        "context": context,
                        "sample_index": i,
                        "entry_ts": ts,
                        "side": "BUY" if sside == 1 else "SELL",
                    }
                    row.update({name: feat.get(name, math.nan) for name in microstate.FEATURES})
                    veto_rows.append(row)
                continue
            if previous_tick_vetoed_primary:
                delayed_primary_entries += 1
            previous_tick_vetoed_primary = False
        else:
            previous_tick_vetoed_primary = False

        high = bool(np.isfinite(r300[i]) and np.isfinite(er60[i]) and r300[i] >= 5.0 and er60[i] >= 0.03)
        entry = (ask[i] + slip) if sside == 1 else (bid[i] - slip)
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

    pf = gp / gl if gl > 0 else 999.0
    terminal_unrealized = 0.0
    if pos and end > start:
        j = end - 1
        exit_px = (bid[j] - slip) if side == 1 else (ask[j] + slip)
        terminal_move = (exit_px - entry) if side == 1 else (entry - exit_px)
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
        "primary_signal_ticks": primary_signals,
        "primary_veto_ticks": primary_vetoes,
        "delayed_primary_entries": delayed_primary_entries,
    }


def compact(m: Dict) -> Dict:
    return {
        key: m[key]
        for key in (
            "pnl_inr",
            "terminal_unrealized_inr",
            "terminal_equity_pnl_inr",
            "open_position_at_end",
            "profit_factor",
            "trades",
            "wins",
            "win_rate",
            "max_drawdown_inr",
            "primary_signal_ticks",
            "primary_veto_ticks",
            "delayed_primary_entries",
        )
        if key in m
    }


def summarize_segments(rows: List[Dict]) -> Dict:
    factor = 1.0
    trades = wins = 0
    dds: List[float] = []
    vetoes = signal_ticks = delayed = 0
    for m in rows:
        factor *= 1.0 + m["pnl_inr"] / canonical.START_BALANCE_INR
        trades += int(m["trades"])
        wins += int(m["wins"])
        dds.append(float(m["max_drawdown_inr"]))
        vetoes += int(m.get("primary_veto_ticks", 0))
        signal_ticks += int(m.get("primary_signal_ticks", 0))
        delayed += int(m.get("delayed_primary_entries", 0))
    return {
        "compounded_pnl_inr": canonical.START_BALANCE_INR * (factor - 1.0),
        "trades": trades,
        "wins": wins,
        "win_rate": wins / trades if trades else 0.0,
        "max_segment_drawdown_inr": max(dds) if dds else 0.0,
        "primary_signal_ticks": signal_ticks,
        "primary_veto_ticks": vetoes,
        "delayed_primary_entries": delayed,
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
    (a.output / "candidate_e_config.json").write_text(
        json.dumps(CANDIDATE_CONFIG, indent=2) + "\n", encoding="utf-8"
    )

    print("loading raw microstate sources", flush=True)
    historical_micro_raw = microstate.load_raw(a.canonical_csv, nrows=canonical.RESEARCH_ROWS)
    recent_micro_raw = microstate.load_raw(a.recent_csv_or_gz)
    historical_micro_cache: Dict[Tuple[float, int], Dict[str, float]] = {}
    recent_micro_cache: Dict[Tuple[float, int], Dict[str, float]] = {}

    result = {
        "schema": "xau-candidate-e-primary-micro-confirmation-eval-v1",
        "candidate_config": CANDIDATE_CONFIG,
        "known_data_promotion_allowed": False,
        "final20_opened": False,
        "random_window_method": (
            "deterministic real contiguous four-hour windows from known canonical first80/recent24h; "
            "stress only, never promotion evidence"
        ),
        "slippage_stress_usd_per_side": list(SLIPPAGE_STRESS_USD_PER_SIDE),
        "intervals": {},
        "decision": "Known-data diagnostic only; no promotion from these already-observed windows.",
    }
    all_random: List[Dict] = []
    segment_rows: List[Dict] = []
    split_rows: List[Dict] = []
    stress_rows: List[Dict] = []
    veto_rows: List[Dict] = []

    for interval in ("500ms", "1s"):
        print(f"{interval}: canonical features", flush=True)
        h_arr, h_bounds = canonical.build_features(a.canonical_csv, interval)
        canonical.assert_baseline(
            canonical.run_strategy(h_arr, h_bounds, "v4_4"),
            interval,
            canonical.DEFAULT_GOLDEN,
        )
        h_inds = autopsy.indices(h_arr, h_bounds)

        dseg: List[Dict] = []
        eseg: List[Dict] = []
        for sid, (s, e) in enumerate(h_inds):
            d = simulate(h_arr, s, e, candidate_e=False)
            legacy = v2.simulate(h_arr, s, e, legacy=True)
            for key in ("pnl_inr", "profit_factor", "trades", "wins", "max_drawdown_inr"):
                if abs(float(d[key]) - float(legacy[key])) > 1e-9:
                    raise RuntimeError(f"Candidate D implementation parity failure {interval} segment {sid} {key}")
            cand = simulate(
                h_arr,
                s,
                e,
                candidate_e=True,
                micro_raw=historical_micro_raw,
                micro_cache=historical_micro_cache,
                veto_rows=veto_rows,
                context=f"historical7d:{interval}:segment{sid}",
            )
            dseg.append(d)
            eseg.append(cand)
            segment_rows.append(
                {
                    "interval": interval,
                    "segment_id": sid,
                    "candidate_d_pnl_inr": d["pnl_inr"],
                    "candidate_e_pnl_inr": cand["pnl_inr"],
                    "delta_e_vs_d_inr": cand["pnl_inr"] - d["pnl_inr"],
                    "candidate_d_trades": d["trades"],
                    "candidate_e_trades": cand["trades"],
                    "candidate_d_wins": d["wins"],
                    "candidate_e_wins": cand["wins"],
                    "candidate_d_max_drawdown_inr": d["max_drawdown_inr"],
                    "candidate_e_max_drawdown_inr": cand["max_drawdown_inr"],
                    "candidate_e_primary_veto_ticks": cand["primary_veto_ticks"],
                    "candidate_e_delayed_primary_entries": cand["delayed_primary_entries"],
                }
            )

        ds = summarize_segments(dseg)
        es = summarize_segments(eseg)
        assert_candidate_d(ds, interval)

        print(f"{interval}: recent features", flush=True)
        r_arr, _ = canonical.build_features(a.recent_csv_or_gz, interval)
        rd = simulate(r_arr, 0, len(r_arr["t"]), candidate_e=False)
        assert_recent_d(rd, interval)
        re = simulate(
            r_arr,
            0,
            len(r_arr["t"]),
            candidate_e=True,
            micro_raw=recent_micro_raw,
            micro_cache=recent_micro_cache,
            veto_rows=veto_rows,
            context=f"recent24h:{interval}:whole",
        )

        times = pd.read_csv(a.recent_csv_or_gz, usecols=["timestamp_utc"])["timestamp_utc"]
        cut_ts = pd.to_datetime(times.iloc[int(len(times) * 0.6)], utc=True).timestamp()
        cut = int(np.searchsorted(r_arr["t"], cut_ts, "left"))
        recent_split = []
        for name, s, e in (("seed", 0, cut), ("evaluation", cut, len(r_arr["t"]))):
            d = simulate(r_arr, s, e, candidate_e=False)
            cand = simulate(
                r_arr,
                s,
                e,
                candidate_e=True,
                micro_raw=recent_micro_raw,
                micro_cache=recent_micro_cache,
            )
            row = {
                "split": name,
                "candidate_d": compact(d),
                "candidate_e": compact(cand),
                "delta_e_vs_d_inr": cand["terminal_equity_pnl_inr"] - d["terminal_equity_pnl_inr"],
            }
            recent_split.append(row)
            split_rows.append(
                {
                    "interval": interval,
                    "split": name,
                    "candidate_d_terminal_equity_pnl_inr": d["terminal_equity_pnl_inr"],
                    "candidate_e_terminal_equity_pnl_inr": cand["terminal_equity_pnl_inr"],
                    "delta_e_vs_d_inr": cand["terminal_equity_pnl_inr"] - d["terminal_equity_pnl_inr"],
                    "candidate_d_trades": d["trades"],
                    "candidate_e_trades": cand["trades"],
                    "candidate_d_wins": d["wins"],
                    "candidate_e_wins": cand["wins"],
                    "candidate_e_primary_veto_ticks": cand["primary_veto_ticks"],
                }
            )

        rng = np.random.default_rng(a.seed + (0 if interval == "500ms" else 1))
        hist_ranges = full_eval.continuous_ranges(h_arr, h_inds)
        recent_ranges = full_eval.continuous_ranges(r_arr, [(0, len(r_arr["t"]))])
        random_rows: List[Dict] = []
        for wid in range(a.random_windows):
            source = "historical7d" if wid % 2 == 0 else "recent24h"
            if source == "historical7d":
                arr = h_arr
                raw = historical_micro_raw
                cache = historical_micro_cache
                ranges = hist_ranges
            else:
                arr = r_arr
                raw = recent_micro_raw
                cache = recent_micro_cache
                ranges = recent_ranges
            s, e, range_id = full_eval.random_window_from_ranges(arr, ranges, rng, a.random_hours)
            d = simulate(arr, s, e, candidate_e=False)
            cand = simulate(
                arr,
                s,
                e,
                candidate_e=True,
                micro_raw=raw,
                micro_cache=cache,
            )
            row = {
                "interval": interval,
                "window_id": wid,
                "source": source,
                "source_range_id": range_id,
                "start_ts": float(arr["t"][s]),
                "end_ts": float(arr["t"][e - 1]),
                "candidate_d_pnl": float(d["terminal_equity_pnl_inr"]),
                "candidate_e_pnl": float(cand["terminal_equity_pnl_inr"]),
                "candidate_d_trades": int(d["trades"]),
                "candidate_e_trades": int(cand["trades"]),
                "candidate_d_wins": int(d["wins"]),
                "candidate_e_wins": int(cand["wins"]),
                "candidate_e_primary_veto_ticks": int(cand["primary_veto_ticks"]),
            }
            random_rows.append(row)
            all_random.append(row)

        dr = random_summary(random_rows, "candidate_d")
        er = random_summary(random_rows, "candidate_e")

        cost_stress = []
        for slip in SLIPPAGE_STRESS_USD_PER_SIDE:
            d_stress_seg = [
                simulate(h_arr, s, e, candidate_e=False, extra_slippage_usd_per_side=slip)
                for s, e in h_inds
            ]
            e_stress_seg = [
                simulate(
                    h_arr,
                    s,
                    e,
                    candidate_e=True,
                    micro_raw=historical_micro_raw,
                    micro_cache=historical_micro_cache,
                    extra_slippage_usd_per_side=slip,
                )
                for s, e in h_inds
            ]
            hd = summarize_segments(d_stress_seg)
            he = summarize_segments(e_stress_seg)
            rds = simulate(
                r_arr, 0, len(r_arr["t"]), candidate_e=False, extra_slippage_usd_per_side=slip
            )
            res = simulate(
                r_arr,
                0,
                len(r_arr["t"]),
                candidate_e=True,
                micro_raw=recent_micro_raw,
                micro_cache=recent_micro_cache,
                extra_slippage_usd_per_side=slip,
            )
            stress = {
                "extra_slippage_usd_per_side": slip,
                "historical_candidate_d_compounded_pnl_inr": hd["compounded_pnl_inr"],
                "historical_candidate_e_compounded_pnl_inr": he["compounded_pnl_inr"],
                "historical_delta_e_vs_d_inr": he["compounded_pnl_inr"] - hd["compounded_pnl_inr"],
                "recent_candidate_d_terminal_equity_pnl_inr": rds["terminal_equity_pnl_inr"],
                "recent_candidate_e_terminal_equity_pnl_inr": res["terminal_equity_pnl_inr"],
                "recent_delta_e_vs_d_inr": res["terminal_equity_pnl_inr"] - rds["terminal_equity_pnl_inr"],
            }
            cost_stress.append(stress)
            stress_rows.append({"interval": interval, **stress})

        result["intervals"][interval] = {
            "canonical_first80": {
                "candidate_d": ds,
                "candidate_e": es,
                "delta_e_vs_d_inr": es["compounded_pnl_inr"] - ds["compounded_pnl_inr"],
                "trade_retention": es["trades"] / ds["trades"] if ds["trades"] else 0.0,
                "win_rate_delta": es["win_rate"] - ds["win_rate"],
                "candidate_d_segments": [compact(x) for x in dseg],
                "candidate_e_segments": [compact(x) for x in eseg],
            },
            "recent24h_whole": {
                "candidate_d": compact(rd),
                "candidate_e": compact(re),
                "delta_e_vs_d_inr": re["terminal_equity_pnl_inr"] - rd["terminal_equity_pnl_inr"],
                "trade_retention": re["trades"] / rd["trades"] if rd["trades"] else 0.0,
                "win_rate_delta": re["win_rate"] - rd["win_rate"],
            },
            "recent24h_split": recent_split,
            "random_real_windows": {
                "candidate_d": dr,
                "candidate_e": er,
                "candidate_e_better_than_d_fraction": float(
                    np.mean([x["candidate_e_pnl"] > x["candidate_d_pnl"] for x in random_rows])
                )
                if random_rows
                else 0.0,
                "candidate_e_equal_to_d_fraction": float(
                    np.mean(
                        [
                            abs(x["candidate_e_pnl"] - x["candidate_d_pnl"]) <= 1e-9
                            for x in random_rows
                        ]
                    )
                )
                if random_rows
                else 0.0,
                "trade_retention": er["total_trades"] / dr["total_trades"] if dr["total_trades"] else 0.0,
            },
            "cost_stress": cost_stress,
        }

        del h_arr, r_arr

    write_csv(a.output / "canonical_segment_comparison.csv", segment_rows)
    write_csv(a.output / "recent_split_comparison.csv", split_rows)
    write_csv(a.output / "random_real_windows.csv", all_random)
    write_csv(a.output / "cost_stress.csv", stress_rows)
    write_csv(a.output / "primary_veto_events.csv", veto_rows)
    (a.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
