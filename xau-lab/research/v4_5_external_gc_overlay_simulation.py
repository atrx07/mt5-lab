"""Experiment 46: same-timeline external GC overlay simulation.

Every external observation is fetched for the archived MT5 dates and consumed
causally using the fixed Experiment-45 clock correction. No current GC data is
mixed into historical replays.

Variants:
  D         Candidate D
  H         Candidate H
  GC-entry  Candidate D + GC admission guard + path-preserving entry ghosts
  GC-exit   Candidate H exit requiring GC confirmation
  I         GC-entry + GC-exit combined
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
import v4_5_candidate_g_ghost_ratchet as gbase
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_external_gc_correlation as gcbridge
import v4_5_microstate_v1_freeze as microstate
import v4_5_regime_portability as portability
import v4_5_router_v2 as router
import v4_5_router_v2_full_eval as full_eval

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-09-26-v4_5-external-gc-overlay-simulation"

CLOCK_CORRECTION_SEC = -10797.910989
BAR_SEC = 300.0
RANDOM_SEED = hbase.RANDOM_SEED
RANDOM_WINDOWS = hbase.RANDOM_WINDOWS
RANDOM_HOURS = hbase.RANDOM_HOURS
SLIPPAGE_STRESS_USD_PER_SIDE = hbase.SLIPPAGE_STRESS_USD_PER_SIDE
VARIANTS = ("D", "H", "GC-entry", "GC-exit", "I")

CONFIG = {
    "schema": "xau-external-gc-overlay-v1",
    "external_symbol": "GC=F",
    "external_interval": "5m",
    "external_timeline_policy": "same archived MT5 dates only; never current data",
    "mt5_true_utc_correction_sec": CLOCK_CORRECTION_SEC,
    "external_causality": "last fully completed 5-minute GC bar only",
    "entry_guard_engines": ["PRIMARY", "SECONDARY"],
    "entry_guard": "dir_gc_ret5 < 0 AND dir_gc_ret15 < 0",
    "entry_skip_policy": "capital-free legacy ghost preserves slot/cooldown path",
    "micro_burst_entry_changed": False,
    "candidate_h_base": "Experiment 43",
    "external_exit_confirmation": "dir_gc_ret5 < 0 AND dir_gc_ret15 < 0",
    "known_data_promotion_allowed": False,
    "threshold_search": False,
    "lag_search": False,
    "final20_opened": False,
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


def prepare_gc(raw: pd.DataFrame) -> pd.DataFrame:
    q = raw.copy().sort_values("timestamp_utc").drop_duplicates("timestamp_utc")
    q["close"] = pd.to_numeric(q["close"], errors="coerce")
    q["volume"] = pd.to_numeric(q["volume"], errors="coerce").fillna(0.0)
    q = q.dropna(subset=["close"]).reset_index(drop=True)
    logp = np.log(q["close"].to_numpy(float))
    q["gc_ret5"] = np.r_[np.nan, np.diff(logp)]
    q["gc_ret15"] = np.log(q["close"] / q["close"].shift(3))
    q["gc_ret30"] = np.log(q["close"] / q["close"].shift(6))
    q["volume_median_1h"] = q["volume"].rolling(12, min_periods=4).median()
    q["volume_rel_1h"] = q["volume"] / q["volume_median_1h"].replace(0, np.nan)
    q["volume_rel_1h"] = q["volume_rel_1h"].replace([np.inf, -np.inf], np.nan)
    return q


class GCSensor:
    def __init__(self, bars: pd.DataFrame):
        self.df = bars.copy()
        self.ts = self.df["timestamp_utc"].astype("int64").to_numpy() / 1e9

    def state(self, mt5_reported_ts: float, side: int, mt5_mid: float) -> Dict[str, float]:
        true_ts = float(mt5_reported_ts) + CLOCK_CORRECTION_SEC
        # Yahoo timestamps are bar starts. Only use a bar whose full 5-minute
        # interval ended before the MT5 decision time.
        eligible_start = true_ts - BAR_SEC
        j = int(np.searchsorted(self.ts, eligible_start, side="right") - 1)
        if j < 0:
            return {
                "available": False,
                "gc_bar_start_utc": math.nan,
                "gc_close": math.nan,
                "gc_ret5": math.nan,
                "gc_ret15": math.nan,
                "gc_ret30": math.nan,
                "gc_volume": math.nan,
                "gc_volume_rel_1h": math.nan,
                "dir_gc_ret5": math.nan,
                "dir_gc_ret15": math.nan,
                "dir_gc_ret30": math.nan,
                "basis_gc_minus_mt5": math.nan,
            }
        r = self.df.iloc[j]
        vals = {
            "gc_ret5": float(r["gc_ret5"]),
            "gc_ret15": float(r["gc_ret15"]),
            "gc_ret30": float(r["gc_ret30"]),
            "gc_volume": float(r["volume"]),
            "gc_volume_rel_1h": float(r["volume_rel_1h"]) if pd.notna(r["volume_rel_1h"]) else math.nan,
        }
        available = all(math.isfinite(vals[k]) for k in ("gc_ret5", "gc_ret15"))
        return {
            "available": bool(available),
            "gc_bar_start_utc": float(self.ts[j]),
            "gc_close": float(r["close"]),
            **vals,
            "dir_gc_ret5": float(side) * vals["gc_ret5"],
            "dir_gc_ret15": float(side) * vals["gc_ret15"],
            "dir_gc_ret30": float(side) * vals["gc_ret30"] if math.isfinite(vals["gc_ret30"]) else math.nan,
            "basis_gc_minus_mt5": float(r["close"]) - float(mt5_mid),
        }


def gc_conflict(state: Dict[str, float]) -> bool:
    return bool(
        state.get("available")
        and float(state["dir_gc_ret5"]) < 0.0
        and float(state["dir_gc_ret15"]) < 0.0
    )


def generic_legacy_reason(
    engine: int,
    move: float,
    held: float,
    highopen: int,
    side: int,
    m30_value: float,
    m300_value: float,
    peak: float,
    failure_since: float,
    cfg,
) -> Tuple[int, float]:
    reason = 0
    rev = 1
    trig = -1.0
    gb = 0.0
    tp = 12.0
    maxhold = 900.0
    if engine == 3:
        tp = 10.0
        trig = 4.0
        gb = 2.0
    elif engine == 4:
        tp = cfg[11]
        maxhold = cfg[12]
        trig = cfg[15]
        gb = cfg[16]
        rev = 0
    elif engine == 1 and highopen == 1:
        tp = 25.0
        maxhold = 900.0
        rev = 0
    elif engine == 2 and highopen == 1:
        tp = 8.0
        maxhold = 1200.0
        rev = 0
        trig = 12.0
        gb = 3.0
    elif engine == 1:
        tp = 21.0
        maxhold = 1800.0

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

    if engine == 4:
        if not np.isfinite(m30_value):
            failure_since = -1e30
        if reason == 0 and np.isfinite(m30_value):
            failure = (side == 1 and m30_value <= 0) or (side == -1 and m30_value >= 0)
            if failure:
                if failure_since < -1e20:
                    failure_since = held
                if held - failure_since >= 1.0:
                    reason = 5
            else:
                failure_since = -1e30

    if reason == 0 and rev == 1 and np.isfinite(m300_value):
        if (side == 1 and m300_value <= 0) or (side == -1 and m300_value >= 0):
            reason = 5
    if reason == 0 and held >= maxhold:
        reason = 7
    return reason, failure_since


def simulate(
    arr: Dict[str, np.ndarray],
    start: int,
    end: int,
    *,
    variant: str,
    gc: GCSensor,
    raw: Dict[str, np.ndarray] | None = None,
    feature_cache: Dict[Tuple[float, int], Dict[str, float]] | None = None,
    extra_slippage_usd_per_side: float = 0.0,
    entry_events: List[Dict] | None = None,
    exit_events: List[Dict] | None = None,
    ghost_events: List[Dict] | None = None,
    context: str = "",
    capture_trace: bool = False,
):
    if variant not in VARIANTS:
        raise ValueError(variant)
    entry_guard = variant in ("GC-entry", "I")
    h_exit = variant in ("H", "GC-exit", "I")
    exit_requires_gc = variant in ("GC-exit", "I")

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
    next_check = math.inf
    decay_confirm = 0

    ghost_active = False
    ghost_engine = 0
    ghost_side = 0
    ghost_entry = ghost_ptime = ghost_peak = 0.0
    ghost_highopen = 0
    ghost_failure_since = -1e30
    ghost_origin_ts = 0.0
    ghost_kind = ""

    last = {1: -1e30, 2: -1e30, 3: -1e30, 4: -1e30}
    prev_ss = None
    cont = 0.0
    real_primary_entries = 0
    h_exits = 0
    entry_skips = 0
    ghost_releases = 0
    trace: List[Tuple[float, int, int]] = []

    if h_exit and (raw is None or feature_cache is None):
        raise RuntimeError("H-derived exit requires raw microstate source")

    for i in range(start, end):
        ts = float(t[i])
        mid_now = float((bid[i] + ask[i]) / 2.0)
        if prev_ss is None or arr["ss"][i] != prev_ss:
            cont = ts
            prev_ss = arr["ss"][i]

        if ghost_active:
            px = (bid[i] - slip) if ghost_side == 1 else (ask[i] + slip)
            move = float((px - ghost_entry) if ghost_side == 1 else (ghost_entry - px))
            ghost_peak = max(ghost_peak, move)
            held = ts - ghost_ptime
            reason, ghost_failure_since = generic_legacy_reason(
                ghost_engine, move, held, ghost_highopen, ghost_side,
                float(m30[i]), float(m300[i]), ghost_peak,
                ghost_failure_since, cfg,
            )
            if reason:
                last[ghost_engine] = ts
                ghost_active = False
                ghost_releases += 1
                if ghost_events is not None:
                    ghost_events.append({
                        "context": context,
                        "variant": variant,
                        "ghost_kind": ghost_kind,
                        "ghost_engine": ghost_engine,
                        "ghost_side": "BUY" if ghost_side == 1 else "SELL",
                        "origin_ts": ghost_origin_ts,
                        "legacy_release_ts": ts,
                        "ghost_duration_sec": ts - ghost_origin_ts,
                        "legacy_exit_reason": reason,
                        "legacy_exit_move_usd": move,
                    })
            continue

        if pos:
            exit_px = (bid[i] - slip) if side == 1 else (ask[i] + slip)
            move = float((exit_px - entry) if side == 1 else (entry - exit_px))
            held = ts - ptime
            peak = max(peak, move)

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
                tp = 10.0; trig = 4.0; gb = 2.0
            elif pos == 4:
                tp = cfg[11]; maxhold = cfg[12]; trig = cfg[15]; gb = cfg[16]; rev = 0
            elif pos == 1 and highopen == 1:
                tp = 25.0; maxhold = 900.0; rev = 0
            elif pos == 2 and highopen == 1:
                tp = 8.0; maxhold = 1200.0; rev = 0; trig = 12.0; gb = 3.0
            elif pos == 1:
                tp = 21.0; maxhold = 1800.0

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

            h_fired = False
            decay_feat = None
            gc_state = None
            if reason == 0 and h_exit and pos == 1 and ts >= next_check:
                while next_check <= ts:
                    next_check += hbase.CHECK_SEC
                armed = peak >= hbase.TRIGGER_MFE_USD and (peak - move) >= hbase.MIN_GIVEBACK_USD
                if armed:
                    bad, decay_feat = hbase.decay_state(raw, ts, side, feature_cache)
                    decay_confirm = decay_confirm + 1 if bad else 0
                else:
                    decay_confirm = 0
                if decay_confirm >= hbase.NEGATIVE_CONFIRMATIONS:
                    gc_state = gc.state(ts, side, mid_now)
                    external_ok = gc_conflict(gc_state)
                    if (not exit_requires_gc) or external_ok:
                        reason = 8
                        h_fired = True

            legacy_same_tick = 0
            if h_fired:
                legacy_same_tick = gbase.primary_legacy_reason(
                    move=move, held=held, highopen=highopen,
                    side=side, m300_value=float(m300[i]),
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
                closing_highopen = highopen
                closing_peak = peak

                pnl = move * oz * canonical.INR_PER_USD
                total = pnl + partial
                bal += pnl
                ntr += 1
                if total > 0:
                    gp += total; wins += 1
                elif total < 0:
                    gl -= total
                peakbal = max(peakbal, bal)
                maxdd = max(maxdd, peakbal - bal)

                if reason == 8:
                    h_exits += 1
                    if exit_events is not None:
                        feat = decay_feat or {}
                        gs = gc_state or gc.state(ts, side, mid_now)
                        exit_events.append({
                            "context": context,
                            "variant": variant,
                            "entry_ts": closing_ptime,
                            "exit_ts": ts,
                            "side": "BUY" if closing_side == 1 else "SELL",
                            "held_sec": held,
                            "mfe_usd": closing_peak,
                            "exit_move_usd": move,
                            "giveback_usd": closing_peak - move,
                            "retained_fraction": move / closing_peak if closing_peak > 0 else math.nan,
                            "dir_mid_move2": feat.get("dir_mid_move2", math.nan),
                            "dir_event_imb2": feat.get("dir_event_imb2", math.nan),
                            **{k: gs.get(k, math.nan) for k in (
                                "gc_bar_start_utc","gc_close","gc_ret5","gc_ret15","gc_ret30",
                                "gc_volume","gc_volume_rel_1h","dir_gc_ret5","dir_gc_ret15",
                                "dir_gc_ret30","basis_gc_minus_mt5"
                            )},
                            "trade_pnl_inr": total,
                        })
                    if legacy_same_tick:
                        last[1] = ts
                    else:
                        ghost_active = True
                        ghost_engine = 1
                        ghost_side = closing_side
                        ghost_entry = closing_entry
                        ghost_ptime = closing_ptime
                        ghost_peak = closing_peak
                        ghost_highopen = closing_highopen
                        ghost_failure_since = -1e30
                        ghost_origin_ts = ts
                        ghost_kind = "post_real_exit"
                else:
                    last[closing_pos] = ts
                pos = 0
                decay_confirm = 0
            continue

        candidates = router.signal_candidates(arr, i, cont, last)
        if not candidates:
            continue
        engine, sside = candidates[0]
        high = bool(
            np.isfinite(r300[i]) and np.isfinite(er60[i])
            and r300[i] >= 5.0 and er60[i] >= 0.03
        )
        proposed_entry = float((ask[i] + slip) if sside == 1 else (bid[i] - slip))

        if entry_guard and engine in (1, 2):
            gs = gc.state(ts, sside, mid_now)
            if gc_conflict(gs):
                entry_skips += 1
                ghost_active = True
                ghost_engine = int(engine)
                ghost_side = int(sside)
                ghost_entry = proposed_entry
                ghost_ptime = ts
                ghost_peak = 0.0
                ghost_highopen = 1 if high else 0
                ghost_failure_since = -1e30
                ghost_origin_ts = ts
                ghost_kind = "admission_skip"
                if capture_trace:
                    trace.append((ts, int(engine), int(sside)))
                if entry_events is not None:
                    entry_events.append({
                        "context": context,
                        "variant": variant,
                        "entry_ts": ts,
                        "engine": {1:"PRIMARY",2:"SECONDARY",3:"MICRO",4:"BURST"}[engine],
                        "side": "BUY" if sside == 1 else "SELL",
                        **{k: gs.get(k, math.nan) for k in (
                            "gc_bar_start_utc","gc_close","gc_ret5","gc_ret15","gc_ret30",
                            "gc_volume","gc_volume_rel_1h","dir_gc_ret5","dir_gc_ret15",
                            "dir_gc_ret30","basis_gc_minus_mt5"
                        )},
                    })
                continue

        entry = proposed_entry
        oz = min(
            bal * 0.03 / (4 * canonical.INR_PER_USD),
            (bal / canonical.INR_PER_USD * 100) / entry,
        )
        pos = int(engine)
        side = int(sside)
        ptime = ts
        peak = 0.0
        partial = 0.0
        partial_done = 0
        highopen = 1 if high else 0
        failure_since = -1e30
        decay_confirm = 0
        next_check = ts + hbase.CHECK_SEC if h_exit and engine == 1 else math.inf
        if engine == 1:
            real_primary_entries += 1
        if capture_trace:
            trace.append((ts, int(engine), int(sside)))

    pf = gp / gl if gl > 0 else 999.0
    terminal_unrealized = 0.0
    if pos and end > start:
        j = end - 1
        px = (bid[j] - slip) if side == 1 else (ask[j] + slip)
        mv = float((px - entry) if side == 1 else (entry - px))
        terminal_unrealized = mv * oz * canonical.INR_PER_USD

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
        "real_primary_entries": real_primary_entries,
        "primary_flow_exits": h_exits,
        "external_entry_skips": entry_skips,
        "ghost_releases": ghost_releases,
        "entry_trace": trace if capture_trace else None,
    }


def compact(m: Dict) -> Dict:
    return {k: m[k] for k in (
        "pnl_inr","terminal_unrealized_inr","terminal_equity_pnl_inr",
        "open_position_at_end","ghost_active_at_end","profit_factor",
        "trades","wins","win_rate","max_drawdown_inr",
        "real_primary_entries","primary_flow_exits","external_entry_skips","ghost_releases"
    )}


def summarize(rows: List[Dict]) -> Dict:
    factor = 1.0
    trades = wins = skips = exits = ghosts = 0
    dds = []
    for m in rows:
        factor *= 1.0 + m["pnl_inr"] / canonical.START_BALANCE_INR
        trades += int(m["trades"]); wins += int(m["wins"])
        skips += int(m["external_entry_skips"]); exits += int(m["primary_flow_exits"])
        ghosts += int(m["ghost_releases"]); dds.append(float(m["max_drawdown_inr"]))
    return {
        "compounded_pnl_inr": canonical.START_BALANCE_INR * (factor - 1.0),
        "trades": trades, "wins": wins,
        "win_rate": wins / trades if trades else 0.0,
        "max_segment_drawdown_inr": max(dds) if dds else 0.0,
        "external_entry_skips": skips,
        "primary_flow_exits": exits,
        "ghost_releases": ghosts,
    }


def random_summary(rows: List[Dict], prefix: str) -> Dict:
    pnl = np.asarray([r[f"{prefix}_pnl"] for r in rows], float)
    tr = np.asarray([r[f"{prefix}_trades"] for r in rows], float)
    wi = np.asarray([r[f"{prefix}_wins"] for r in rows], float)
    return {
        "windows": len(rows),
        "median_terminal_equity_pnl_inr": float(np.median(pnl)),
        "mean_terminal_equity_pnl_inr": float(np.mean(pnl)),
        "p05_terminal_equity_pnl_inr": float(np.quantile(pnl, 0.05)),
        "p95_terminal_equity_pnl_inr": float(np.quantile(pnl, 0.95)),
        "positive_window_fraction": float(np.mean(pnl > 0)),
        "total_trades": int(tr.sum()), "total_wins": int(wi.sum()),
        "aggregate_win_rate": float(wi.sum() / tr.sum()) if tr.sum() else 0.0,
    }


def fetch_same_timeline_gc(canonical_csv: Path, recent_csv: Path, out: Path) -> Tuple[GCSensor, Dict]:
    hist_ts = pd.read_csv(canonical_csv, nrows=canonical.RESEARCH_ROWS, usecols=["timestamp_utc"])
    recent_ts = pd.read_csv(recent_csv, usecols=["timestamp_utc"])
    hs = pd.to_datetime(hist_ts.timestamp_utc.iloc[0], utc=True)
    he = pd.to_datetime(hist_ts.timestamp_utc.iloc[-1], utc=True)
    rs = pd.to_datetime(recent_ts.timestamp_utc.iloc[0], utc=True)
    re = pd.to_datetime(recent_ts.timestamp_utc.iloc[-1], utc=True)
    request_start = min(hs, rs) + pd.to_timedelta(CLOCK_CORRECTION_SEC, unit="s") - pd.Timedelta(hours=2)
    request_end = max(he, re) + pd.to_timedelta(CLOCK_CORRECTION_SEC, unit="s") + pd.Timedelta(hours=2)
    raw, meta = gcbridge.fetch_yahoo(request_start, request_end)
    bars = prepare_gc(raw)
    used = bars[[
        "timestamp_utc","close","volume","gc_ret5","gc_ret15","gc_ret30",
        "volume_median_1h","volume_rel_1h"
    ]].copy()
    used.to_csv(out / "gc_features_5m_used.csv", index=False)
    manifest = {
        "schema": "xau-external-gc-overlay-source-v1",
        **meta,
        "mt5_clock_correction_sec": CLOCK_CORRECTION_SEC,
        "timeline_policy": "request derived from archived MT5 timestamps; no current data",
        "causal_policy": "use only fully completed 5-minute GC bars",
        "derived_feature_rows_committed": int(len(used)),
        "final20_opened": False,
    }
    (out / "external_source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return GCSensor(bars), manifest


def assert_d(summary: Dict, interval: str):
    exp = gbase.fbase.EXPECTED_D[interval]
    if abs(summary["compounded_pnl_inr"] - exp["pnl"]) > 1e-6:
        raise RuntimeError(f"D P&L parity drift {interval}: {summary}")
    if summary["trades"] != exp["trades"] or summary["wins"] != exp["wins"]:
        raise RuntimeError(f"D count parity drift {interval}: {summary}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("canonical_csv", type=Path)
    ap.add_argument("recent_csv_or_gz", type=Path)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "candidate_i_config.json").write_text(json.dumps(CONFIG, indent=2) + "\n", encoding="utf-8")

    print("fetching same-timeline GC data", flush=True)
    gc, source_manifest = fetch_same_timeline_gc(a.canonical_csv, a.recent_csv_or_gz, a.output)

    hraw = microstate.load_raw(a.canonical_csv, nrows=canonical.RESEARCH_ROWS)
    rraw = microstate.load_raw(a.recent_csv_or_gz)
    hcache: Dict[Tuple[float,int],Dict[str,float]] = {}
    rcache: Dict[Tuple[float,int],Dict[str,float]] = {}

    result = {
        "schema": "xau-external-gc-overlay-eval-v1",
        "config": CONFIG,
        "source_manifest": source_manifest,
        "variants": list(VARIANTS),
        "known_data_promotion_allowed": False,
        "final20_opened": False,
        "intervals": {},
    }
    segment_rows=[]; split_rows=[]; random_rows_all=[]; stress_rows=[]
    entry_events=[]; exit_events=[]; ghost_events=[]; parity_rows=[]

    for interval in ("500ms","1s"):
        print(f"{interval}: canonical", flush=True)
        h_arr,h_bounds=canonical.build_features(a.canonical_csv,interval)
        canonical.assert_baseline(canonical.run_strategy(h_arr,h_bounds,"v4_4"),interval,canonical.DEFAULT_GOLDEN)
        h_inds=autopsy.indices(h_arr,h_bounds)

        seg_by_variant={v:[] for v in VARIANTS}
        for sid,(s,e) in enumerate(h_inds):
            traces={}
            for v in VARIANTS:
                m=simulate(
                    h_arr,s,e,variant=v,gc=gc,raw=hraw,feature_cache=hcache,
                    entry_events=entry_events if v in ("GC-entry","I") else None,
                    exit_events=exit_events if v in ("H","GC-exit","I") else None,
                    ghost_events=ghost_events if v!="D" else None,
                    context=f"historical7d:{interval}:segment{sid}",
                    capture_trace=True,
                )
                seg_by_variant[v].append(m)
                traces[v]=m["entry_trace"]
            for v in VARIANTS[1:]:
                parity = traces[v] == traces["D"]
                parity_rows.append({"window":"historical7d","interval":interval,"segment_id":sid,"variant":v,"match":parity})
                if not parity:
                    raise RuntimeError(f"Entry-path parity failed {interval} seg{sid} {v}")
            segment_rows.append({
                "interval":interval,"segment_id":sid,
                **{f"{v}_pnl_inr":seg_by_variant[v][-1]["pnl_inr"] for v in VARIANTS},
                **{f"{v}_trades":seg_by_variant[v][-1]["trades"] for v in VARIANTS},
                **{f"{v}_wins":seg_by_variant[v][-1]["wins"] for v in VARIANTS},
                **{f"{v}_entry_skips":seg_by_variant[v][-1]["external_entry_skips"] for v in VARIANTS},
                **{f"{v}_flow_exits":seg_by_variant[v][-1]["primary_flow_exits"] for v in VARIANTS},
            })
        sums={v:summarize(seg_by_variant[v]) for v in VARIANTS}
        assert_d(sums["D"],interval)

        print(f"{interval}: recent", flush=True)
        r_arr,_=canonical.build_features(a.recent_csv_or_gz,interval)
        recent={}
        traces={}
        for v in VARIANTS:
            m=simulate(
                r_arr,0,len(r_arr["t"]),variant=v,gc=gc,raw=rraw,feature_cache=rcache,
                entry_events=entry_events if v in ("GC-entry","I") else None,
                exit_events=exit_events if v in ("H","GC-exit","I") else None,
                ghost_events=ghost_events if v!="D" else None,
                context=f"recent24h:{interval}:whole",
                capture_trace=True,
            )
            recent[v]=m; traces[v]=m["entry_trace"]
        exp_recent=gbase.fbase.EXPECTED_RECENT_D[interval]
        if abs(recent["D"]["terminal_equity_pnl_inr"]-exp_recent["pnl"])>1e-6:
            raise RuntimeError(f"Recent D parity drift {interval}")
        for v in VARIANTS[1:]:
            parity=traces[v]==traces["D"]
            parity_rows.append({"window":"recent24h","interval":interval,"segment_id":-1,"variant":v,"match":parity})
            if not parity:
                raise RuntimeError(f"Recent entry-path parity failed {interval} {v}")

        times=pd.read_csv(a.recent_csv_or_gz,usecols=["timestamp_utc"])["timestamp_utc"]
        cut_ts=pd.to_datetime(times.iloc[int(len(times)*0.6)],utc=True).timestamp()
        cut=int(np.searchsorted(r_arr["t"],cut_ts,"left"))
        splits=[]
        for name,s,e in (("seed",0,cut),("evaluation",cut,len(r_arr["t"]))):
            row={"interval":interval,"split":name}
            item={"split":name}
            for v in VARIANTS:
                m=simulate(r_arr,s,e,variant=v,gc=gc,raw=rraw,feature_cache=rcache)
                item[v]=compact(m)
                row[f"{v}_terminal_equity_pnl_inr"]=m["terminal_equity_pnl_inr"]
                row[f"{v}_trades"]=m["trades"]
                row[f"{v}_entry_skips"]=m["external_entry_skips"]
                row[f"{v}_flow_exits"]=m["primary_flow_exits"]
            splits.append(item); split_rows.append(row)

        rng=np.random.default_rng(RANDOM_SEED+(0 if interval=="500ms" else 1))
        hist_ranges=full_eval.continuous_ranges(h_arr,h_inds)
        recent_ranges=full_eval.continuous_ranges(r_arr,[(0,len(r_arr["t"]))])
        rr=[]
        for wid in range(RANDOM_WINDOWS):
            source="historical7d" if wid%2==0 else "recent24h"
            arr,ranges,raw,cache=(h_arr,hist_ranges,hraw,hcache) if source=="historical7d" else (r_arr,recent_ranges,rraw,rcache)
            s,e,rid=full_eval.random_window_from_ranges(arr,ranges,rng,RANDOM_HOURS)
            dm=simulate(arr,s,e,variant="D",gc=gc,raw=raw,feature_cache=cache)
            hm=simulate(arr,s,e,variant="H",gc=gc,raw=raw,feature_cache=cache)
            im=simulate(arr,s,e,variant="I",gc=gc,raw=raw,feature_cache=cache)
            row={
                "interval":interval,"window_id":wid,"source":source,"source_range_id":rid,
                "start_ts":float(arr["t"][s]),"end_ts":float(arr["t"][e-1]),
                "D_pnl":dm["terminal_equity_pnl_inr"],"H_pnl":hm["terminal_equity_pnl_inr"],"I_pnl":im["terminal_equity_pnl_inr"],
                "D_trades":dm["trades"],"H_trades":hm["trades"],"I_trades":im["trades"],
                "D_wins":dm["wins"],"H_wins":hm["wins"],"I_wins":im["wins"],
                "I_entry_skips":im["external_entry_skips"],"I_flow_exits":im["primary_flow_exits"],
            }
            rr.append(row); random_rows_all.append(row)
        random_summary={v:random_summary(rr,v) for v in ("D","H","I")}

        costs=[]
        for slip in SLIPPAGE_STRESS_USD_PER_SIDE:
            row={"interval":interval,"extra_slippage_usd_per_side":slip}
            for v in ("D","H","I"):
                hs=[simulate(h_arr,s,e,variant=v,gc=gc,raw=hraw,feature_cache=hcache,extra_slippage_usd_per_side=slip) for s,e in h_inds]
                sm=summarize(hs)
                rm=simulate(r_arr,0,len(r_arr["t"]),variant=v,gc=gc,raw=rraw,feature_cache=rcache,extra_slippage_usd_per_side=slip)
                row[f"{v}_historical_compounded_pnl_inr"]=sm["compounded_pnl_inr"]
                row[f"{v}_recent_terminal_equity_pnl_inr"]=rm["terminal_equity_pnl_inr"]
            costs.append(row); stress_rows.append(row)

        result["intervals"][interval]={
            "canonical_first80":{v:sums[v] for v in VARIANTS},
            "recent24h_whole":{v:compact(recent[v]) for v in VARIANTS},
            "recent24h_split":splits,
            "random_real_windows":random_summary,
            "cost_stress":costs,
        }

    write_csv(a.output/"entry_path_parity.csv",parity_rows)
    write_csv(a.output/"canonical_segment_comparison.csv",segment_rows)
    write_csv(a.output/"recent_split_comparison.csv",split_rows)
    write_csv(a.output/"random_real_windows.csv",random_rows_all)
    write_csv(a.output/"cost_stress.csv",stress_rows)
    write_csv(a.output/"external_entry_skip_events.csv",entry_events)
    write_csv(a.output/"external_confirmed_exit_events.csv",exit_events)
    write_csv(a.output/"ghost_release_events.csv",ghost_events)

    (a.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
