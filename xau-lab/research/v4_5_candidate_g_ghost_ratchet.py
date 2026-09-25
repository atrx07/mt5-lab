"""Experiment 41: Candidate G path-preserving PRIMARY ratchet.

Candidate G banks the frozen Candidate-F PRIMARY ratchet exit, but keeps a
capital-free virtual copy of the original PRIMARY occupying the shared slot
until Candidate D's untouched PRIMARY lifecycle would have exited. PRIMARY
cooldown starts at that virtual legacy-exit timestamp.

The architecture is designed to separate profit retention from the downstream
path mutation that rejected Candidate F. Canonical zero-cost entry-path parity
with Candidate D is a mandatory invariant.
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

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_candidate_f_primary_ratchet as fbase
import v4_5_regime_portability as portability
import v4_5_router_v2 as v2
import v4_5_router_v2_full_eval as full_eval

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = (
    ROOT / "results" / "simulations" /
    "2026-09-25-v4_5-candidate-g-ghost-ratchet"
)

RATCHET_TRIGGER_USD = fbase.RATCHET_TRIGGER_USD
RATCHET_RETAIN_FRACTION = fbase.RATCHET_RETAIN_FRACTION
RATCHET_CHECK_SEC = fbase.RATCHET_CHECK_SEC
RANDOM_SEED = fbase.RANDOM_SEED
RANDOM_WINDOWS = fbase.RANDOM_WINDOWS
RANDOM_HOURS = fbase.RANDOM_HOURS
SLIPPAGE_STRESS_USD_PER_SIDE = fbase.SLIPPAGE_STRESS_USD_PER_SIDE

CONFIG = {
    "schema": "xau-candidate-g-path-preserving-ghost-ratchet-v1",
    "base_strategy": "Candidate D from Experiment 19",
    "strategy_changed": True,
    "entry_changed": False,
    "real_exit_change": "PRIMARY-only frozen Candidate-F ratchet",
    "ratchet_trigger_mfe_usd": RATCHET_TRIGGER_USD,
    "ratchet_trigger_r": 1.0,
    "ratchet_retain_fraction_of_live_mfe": RATCHET_RETAIN_FRACTION,
    "ratchet_check_sec": RATCHET_CHECK_SEC,
    "post_ratchet_slot_policy": "capital-free ghost PRIMARY preserves Candidate-D occupancy until legacy exit",
    "primary_cooldown_anchor": "ghost legacy-exit timestamp",
    "canonical_entry_path_parity_required": True,
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


def primary_legacy_reason(
    *,
    move: float,
    held: float,
    highopen: int,
    side: int,
    m300_value: float,
) -> int:
    tp = 25.0 if highopen == 1 else 21.0
    maxhold = 900.0 if highopen == 1 else 1800.0
    if move <= -4.0:
        return 1
    if move >= tp:
        return 2
    if highopen == 0 and np.isfinite(m300_value):
        if (side == 1 and m300_value <= 0) or (side == -1 and m300_value >= 0):
            return 5
    if held >= maxhold:
        return 7
    return 0


def simulate(
    arr: Dict[str, np.ndarray],
    start: int,
    end: int,
    *,
    candidate_g: bool,
    extra_slippage_usd_per_side: float = 0.0,
    ratchet_events: List[Dict] | None = None,
    ghost_events: List[Dict] | None = None,
    context: str = "",
    capture_trace: bool = False,
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

    ghost_active = False
    ghost_side = 0
    ghost_entry = 0.0
    ghost_ptime = 0.0
    ghost_highopen = 0
    ghost_origin_ratchet_ts = 0.0

    last = {1: -1e30, 2: -1e30, 3: -1e30, 4: -1e30}
    prev_ss = None
    cont = 0.0

    primary_entries = 0
    ratchet_exits = 0
    ghost_releases = 0
    trace: List[Tuple[float, int, int]] = []

    for i in range(start, end):
        ts = float(t[i])
        if prev_ss is None or arr["ss"][i] != prev_ss:
            cont = ts
            prev_ss = arr["ss"][i]

        # A real ratchet exit does not free the strategy slot. The ghost carries
        # no P&L/risk; it exists only to reproduce Candidate D's occupancy and
        # PRIMARY cooldown anchor.
        if ghost_active:
            ghost_exit_px = (bid[i] - slip) if ghost_side == 1 else (ask[i] + slip)
            ghost_move = float(
                (ghost_exit_px - ghost_entry)
                if ghost_side == 1
                else (ghost_entry - ghost_exit_px)
            )
            ghost_held = ts - ghost_ptime
            reason = primary_legacy_reason(
                move=ghost_move,
                held=ghost_held,
                highopen=ghost_highopen,
                side=ghost_side,
                m300_value=float(m300[i]),
            )
            if reason:
                ghost_active = False
                ghost_releases += 1
                last[1] = ts
                if ghost_events is not None:
                    ghost_events.append({
                        "context": context,
                        "ratchet_exit_ts": float(ghost_origin_ratchet_ts),
                        "legacy_release_ts": ts,
                        "ghost_duration_sec": float(ts - ghost_origin_ratchet_ts),
                        "side": "BUY" if ghost_side == 1 else "SELL",
                        "legacy_exit_reason": int(reason),
                        "legacy_exit_move_usd": ghost_move,
                    })
            # Candidate D exits and then continues to the next sampled quote
            # before considering another entry. Preserve that exact loop path.
            continue

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

            ratchet_fired = False
            if (
                reason == 0
                and candidate_g
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
                    ratchet_fired = True

            # If the untouched PRIMARY lifecycle would also exit on this exact
            # quote, no ghost interval is needed; Candidate D frees the slot now.
            legacy_same_tick = 0
            if ratchet_fired:
                legacy_same_tick = primary_legacy_reason(
                    move=move,
                    held=held,
                    highopen=highopen,
                    side=side,
                    m300_value=float(m300[i]),
                )
            elif reason == 0 and rev == 1 and np.isfinite(m300[i]):
                if (side == 1 and m300[i] <= 0) or (side == -1 and m300[i] >= 0):
                    reason = 5
            if reason == 0 and held >= maxhold:
                reason = 7

            if reason:
                closing_pos = pos
                closing_side = side
                closing_entry = entry
                closing_ptime = ptime
                closing_peak = peak
                closing_highopen = highopen

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

                if reason == 8:
                    ratchet_exits += 1
                    if ratchet_events is not None:
                        ratchet_events.append({
                            "context": context,
                            "entry_ts": float(closing_ptime),
                            "ratchet_exit_ts": ts,
                            "side": "BUY" if closing_side == 1 else "SELL",
                            "held_sec": float(held),
                            "peak_move_usd": float(closing_peak),
                            "exit_move_usd": float(move),
                            "retained_fraction": (
                                float(move / closing_peak)
                                if closing_peak > 0
                                else math.nan
                            ),
                            "trade_pnl_inr": float(total),
                            "legacy_same_tick_exit": bool(legacy_same_tick),
                        })

                    if legacy_same_tick:
                        last[1] = ts
                    else:
                        ghost_active = True
                        ghost_side = closing_side
                        ghost_entry = closing_entry
                        ghost_ptime = closing_ptime
                        ghost_highopen = closing_highopen
                        ghost_origin_ratchet_ts = ts
                else:
                    last[closing_pos] = ts

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
            if candidate_g and engine == 1
            else math.inf
        )
        if engine == 1:
            primary_entries += 1
        if capture_trace:
            trace.append((ts, int(engine), int(sside)))

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
        "ghost_active_at_end": bool(ghost_active),
        "profit_factor": pf,
        "trades": ntr,
        "wins": wins,
        "win_rate": wins / ntr if ntr else 0.0,
        "max_drawdown_inr": maxdd,
        "primary_entries": primary_entries,
        "primary_ratchet_exits": ratchet_exits,
        "ghost_releases": ghost_releases,
        "entry_trace": trace if capture_trace else None,
    }


def compact(m: Dict) -> Dict:
    return {
        k: m[k]
        for k in (
            "pnl_inr",
            "terminal_unrealized_inr",
            "terminal_equity_pnl_inr",
            "open_position_at_end",
            "ghost_active_at_end",
            "profit_factor",
            "trades",
            "wins",
            "win_rate",
            "max_drawdown_inr",
            "primary_entries",
            "primary_ratchet_exits",
            "ghost_releases",
        )
        if k in m
    }


def summarize_segments(rows: List[Dict]) -> Dict:
    factor = 1.0
    trades = wins = primary_entries = ratchet_exits = ghost_releases = 0
    dds = []
    for m in rows:
        factor *= 1.0 + m["pnl_inr"] / canonical.START_BALANCE_INR
        trades += int(m["trades"])
        wins += int(m["wins"])
        primary_entries += int(m.get("primary_entries", 0))
        ratchet_exits += int(m.get("primary_ratchet_exits", 0))
        ghost_releases += int(m.get("ghost_releases", 0))
        dds.append(float(m["max_drawdown_inr"]))
    return {
        "compounded_pnl_inr": canonical.START_BALANCE_INR * (factor - 1.0),
        "trades": trades,
        "wins": wins,
        "win_rate": wins / trades if trades else 0.0,
        "max_segment_drawdown_inr": max(dds) if dds else 0.0,
        "primary_entries": primary_entries,
        "primary_ratchet_exits": ratchet_exits,
        "ghost_releases": ghost_releases,
    }


def assert_candidate_d(summary: Dict, interval: str):
    exp = fbase.EXPECTED_D[interval]
    if abs(summary["compounded_pnl_inr"] - exp["pnl"]) > 1e-6:
        raise RuntimeError(f"Candidate D P&L parity drift {interval}: {summary}")
    if summary["trades"] != exp["trades"] or summary["wins"] != exp["wins"]:
        raise RuntimeError(f"Candidate D count parity drift {interval}: {summary}")


def assert_recent_d(summary: Dict, interval: str):
    exp = fbase.EXPECTED_RECENT_D[interval]
    if abs(summary["terminal_equity_pnl_inr"] - exp["pnl"]) > 1e-6:
        raise RuntimeError(f"Recent Candidate D P&L parity drift {interval}: {summary}")
    if summary["trades"] != exp["trades"] or summary["wins"] != exp["wins"]:
        raise RuntimeError(f"Recent Candidate D count parity drift {interval}: {summary}")


def compare_trace(d: Dict, g: Dict) -> Dict:
    dt = d.get("entry_trace") or []
    gt = g.get("entry_trace") or []
    first = None
    for idx, (a, b) in enumerate(zip(dt, gt)):
        if a != b:
            first = {
                "index": idx,
                "candidate_d": list(a),
                "candidate_g": list(b),
            }
            break
    if first is None and len(dt) != len(gt):
        first = {
            "index": min(len(dt), len(gt)),
            "candidate_d": list(dt[len(gt)]) if len(dt) > len(gt) else None,
            "candidate_g": list(gt[len(dt)]) if len(gt) > len(dt) else None,
        }
    return {
        "match": first is None and len(dt) == len(gt),
        "candidate_d_entries": len(dt),
        "candidate_g_entries": len(gt),
        "first_mismatch": first,
    }


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
    (a.output / "candidate_g_config.json").write_text(
        json.dumps(CONFIG, indent=2) + "\n", encoding="utf-8"
    )

    result = {
        "schema": "xau-candidate-g-ghost-ratchet-eval-v1",
        "candidate_config": CONFIG,
        "known_data_promotion_allowed": False,
        "final20_opened": False,
        "canonical_entry_path_parity_required": True,
        "random_window_method": (
            "deterministic real contiguous four-hour windows from known canonical "
            "first80/recent24h; stress only, never promotion evidence"
        ),
        "slippage_stress_usd_per_side": list(SLIPPAGE_STRESS_USD_PER_SIDE),
        "intervals": {},
    }

    segment_rows: List[Dict] = []
    split_rows: List[Dict] = []
    random_rows_all: List[Dict] = []
    stress_rows: List[Dict] = []
    ratchet_events: List[Dict] = []
    ghost_events: List[Dict] = []
    path_rows: List[Dict] = []

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
        gseg = []
        path_ok = True
        for sid, (s, e) in enumerate(h_inds):
            d = simulate(h_arr, s, e, candidate_g=False, capture_trace=True)
            legacy = v2.simulate(h_arr, s, e, legacy=True)
            for key in ("pnl_inr", "profit_factor", "trades", "wins", "max_drawdown_inr"):
                if abs(float(d[key]) - float(legacy[key])) > 1e-9:
                    raise RuntimeError(
                        f"Candidate D implementation parity failure {interval} segment {sid} {key}"
                    )

            g = simulate(
                h_arr,
                s,
                e,
                candidate_g=True,
                ratchet_events=ratchet_events,
                ghost_events=ghost_events,
                context=f"historical7d:{interval}:segment{sid}",
                capture_trace=True,
            )
            parity = compare_trace(d, g)
            path_ok = path_ok and bool(parity["match"])
            path_rows.append({
                "interval": interval,
                "segment_id": sid,
                "match": parity["match"],
                "candidate_d_entries": parity["candidate_d_entries"],
                "candidate_g_entries": parity["candidate_g_entries"],
                "first_mismatch_json": json.dumps(parity["first_mismatch"]),
            })

            dseg.append(d)
            gseg.append(g)
            segment_rows.append({
                "interval": interval,
                "segment_id": sid,
                "candidate_d_pnl_inr": d["pnl_inr"],
                "candidate_g_pnl_inr": g["pnl_inr"],
                "delta_g_vs_d_inr": g["pnl_inr"] - d["pnl_inr"],
                "candidate_d_trades": d["trades"],
                "candidate_g_trades": g["trades"],
                "candidate_d_wins": d["wins"],
                "candidate_g_wins": g["wins"],
                "candidate_d_max_drawdown_inr": d["max_drawdown_inr"],
                "candidate_g_max_drawdown_inr": g["max_drawdown_inr"],
                "candidate_g_primary_ratchet_exits": g["primary_ratchet_exits"],
                "candidate_g_ghost_releases": g["ghost_releases"],
                "entry_path_match": parity["match"],
            })

        ds = summarize_segments(dseg)
        gs = summarize_segments(gseg)
        assert_candidate_d(ds, interval)
        if not path_ok:
            raise RuntimeError(
                f"Candidate G canonical entry-path parity failure on {interval}; "
                "see entry_path_parity.csv after diagnostic repair"
            )

        print(f"{interval}: recent", flush=True)
        r_arr, _ = canonical.build_features(a.recent_csv_or_gz, interval)
        rd = simulate(r_arr, 0, len(r_arr["t"]), candidate_g=False, capture_trace=True)
        assert_recent_d(rd, interval)
        rg = simulate(
            r_arr,
            0,
            len(r_arr["t"]),
            candidate_g=True,
            ratchet_events=ratchet_events,
            ghost_events=ghost_events,
            context=f"recent24h:{interval}:whole",
            capture_trace=True,
        )
        recent_path = compare_trace(rd, rg)

        times = pd.read_csv(a.recent_csv_or_gz, usecols=["timestamp_utc"])["timestamp_utc"]
        cut_ts = pd.to_datetime(times.iloc[int(len(times) * 0.6)], utc=True).timestamp()
        cut = int(np.searchsorted(r_arr["t"], cut_ts, "left"))
        recent_split = []
        for name, s, e in (("seed", 0, cut), ("evaluation", cut, len(r_arr["t"]))):
            d = simulate(r_arr, s, e, candidate_g=False)
            g = simulate(r_arr, s, e, candidate_g=True)
            row = {
                "split": name,
                "candidate_d": compact(d),
                "candidate_g": compact(g),
                "delta_g_vs_d_inr": g["terminal_equity_pnl_inr"] - d["terminal_equity_pnl_inr"],
            }
            recent_split.append(row)
            split_rows.append({
                "interval": interval,
                "split": name,
                "candidate_d_terminal_equity_pnl_inr": d["terminal_equity_pnl_inr"],
                "candidate_g_terminal_equity_pnl_inr": g["terminal_equity_pnl_inr"],
                "delta_g_vs_d_inr": g["terminal_equity_pnl_inr"] - d["terminal_equity_pnl_inr"],
                "candidate_d_trades": d["trades"],
                "candidate_g_trades": g["trades"],
                "candidate_d_wins": d["wins"],
                "candidate_g_wins": g["wins"],
                "candidate_g_primary_ratchet_exits": g["primary_ratchet_exits"],
                "candidate_g_ghost_releases": g["ghost_releases"],
            })

        rng = np.random.default_rng(a.seed + (0 if interval == "500ms" else 1))
        hist_ranges = full_eval.continuous_ranges(h_arr, h_inds)
        recent_ranges = full_eval.continuous_ranges(r_arr, [(0, len(r_arr["t"]))])
        random_rows = []
        for wid in range(a.random_windows):
            source = "historical7d" if wid % 2 == 0 else "recent24h"
            if source == "historical7d":
                arr, ranges = h_arr, hist_ranges
            else:
                arr, ranges = r_arr, recent_ranges
            s, e, range_id = full_eval.random_window_from_ranges(
                arr, ranges, rng, a.random_hours
            )
            d = simulate(arr, s, e, candidate_g=False)
            g = simulate(arr, s, e, candidate_g=True)
            row = {
                "interval": interval,
                "window_id": wid,
                "source": source,
                "source_range_id": range_id,
                "start_ts": float(arr["t"][s]),
                "end_ts": float(arr["t"][e - 1]),
                "candidate_d_pnl": float(d["terminal_equity_pnl_inr"]),
                "candidate_g_pnl": float(g["terminal_equity_pnl_inr"]),
                "candidate_d_trades": int(d["trades"]),
                "candidate_g_trades": int(g["trades"]),
                "candidate_d_wins": int(d["wins"]),
                "candidate_g_wins": int(g["wins"]),
                "candidate_g_ratchet_exits": int(g["primary_ratchet_exits"]),
                "candidate_g_ghost_releases": int(g["ghost_releases"]),
            }
            random_rows.append(row)
            random_rows_all.append(row)

        dr = random_summary(random_rows, "candidate_d")
        gr = random_summary(random_rows, "candidate_g")

        cost_stress = []
        for slip in SLIPPAGE_STRESS_USD_PER_SIDE:
            d_stress_seg = [
                simulate(
                    h_arr, s, e,
                    candidate_g=False,
                    extra_slippage_usd_per_side=slip,
                )
                for s, e in h_inds
            ]
            g_stress_seg = [
                simulate(
                    h_arr, s, e,
                    candidate_g=True,
                    extra_slippage_usd_per_side=slip,
                )
                for s, e in h_inds
            ]
            hd = summarize_segments(d_stress_seg)
            hg = summarize_segments(g_stress_seg)
            rds = simulate(
                r_arr, 0, len(r_arr["t"]),
                candidate_g=False,
                extra_slippage_usd_per_side=slip,
            )
            rgs = simulate(
                r_arr, 0, len(r_arr["t"]),
                candidate_g=True,
                extra_slippage_usd_per_side=slip,
            )
            stress = {
                "extra_slippage_usd_per_side": slip,
                "historical_candidate_d_compounded_pnl_inr": hd["compounded_pnl_inr"],
                "historical_candidate_g_compounded_pnl_inr": hg["compounded_pnl_inr"],
                "historical_delta_g_vs_d_inr": hg["compounded_pnl_inr"] - hd["compounded_pnl_inr"],
                "recent_candidate_d_terminal_equity_pnl_inr": rds["terminal_equity_pnl_inr"],
                "recent_candidate_g_terminal_equity_pnl_inr": rgs["terminal_equity_pnl_inr"],
                "recent_delta_g_vs_d_inr": rgs["terminal_equity_pnl_inr"] - rds["terminal_equity_pnl_inr"],
                "historical_candidate_g_ratchet_exits": hg["primary_ratchet_exits"],
                "historical_candidate_g_ghost_releases": hg["ghost_releases"],
                "recent_candidate_g_ratchet_exits": rgs["primary_ratchet_exits"],
                "recent_candidate_g_ghost_releases": rgs["ghost_releases"],
            }
            cost_stress.append(stress)
            stress_rows.append({"interval": interval, **stress})

        result["intervals"][interval] = {
            "canonical_first80": {
                "entry_path_parity": True,
                "candidate_d": ds,
                "candidate_g": gs,
                "delta_g_vs_d_inr": gs["compounded_pnl_inr"] - ds["compounded_pnl_inr"],
                "trade_retention": gs["trades"] / ds["trades"] if ds["trades"] else 0.0,
                "win_rate_delta": gs["win_rate"] - ds["win_rate"],
                "candidate_d_segments": [compact(x) for x in dseg],
                "candidate_g_segments": [compact(x) for x in gseg],
            },
            "recent24h_whole": {
                "entry_path_parity": recent_path,
                "candidate_d": compact(rd),
                "candidate_g": compact(rg),
                "delta_g_vs_d_inr": rg["terminal_equity_pnl_inr"] - rd["terminal_equity_pnl_inr"],
                "trade_retention": rg["trades"] / rd["trades"] if rd["trades"] else 0.0,
                "win_rate_delta": rg["win_rate"] - rd["win_rate"],
            },
            "recent24h_split": recent_split,
            "random_real_windows": {
                "candidate_d": dr,
                "candidate_g": gr,
                "candidate_g_better_than_d_fraction": float(
                    np.mean([x["candidate_g_pnl"] > x["candidate_d_pnl"] for x in random_rows])
                ) if random_rows else 0.0,
                "candidate_g_equal_to_d_fraction": float(
                    np.mean([
                        abs(x["candidate_g_pnl"] - x["candidate_d_pnl"]) <= 1e-9
                        for x in random_rows
                    ])
                ) if random_rows else 0.0,
                "trade_retention": gr["total_trades"] / dr["total_trades"] if dr["total_trades"] else 0.0,
            },
            "cost_stress": cost_stress,
        }

        del h_arr, r_arr

    write_csv(a.output / "entry_path_parity.csv", path_rows)
    write_csv(a.output / "canonical_segment_comparison.csv", segment_rows)
    write_csv(a.output / "recent_split_comparison.csv", split_rows)
    write_csv(a.output / "random_real_windows.csv", random_rows_all)
    write_csv(a.output / "cost_stress.csv", stress_rows)
    write_csv(a.output / "primary_ratchet_events.csv", ratchet_events)
    write_csv(a.output / "ghost_release_events.csv", ghost_events)
    (a.output / "summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
