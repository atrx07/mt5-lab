"""Experiment 47: MT5-native quote-flow phase controller.

Uses only the same MT5/broker feed available to live execution. Candidate-D
opportunity timing is reproduced by an independent capital-free baseline shadow,
so modified real entries/exits cannot manufacture new downstream opportunities.

Variants:
  Quote-entry  phase-aware PRIMARY/SECONDARY TAKE/WAIT/SKIP, legacy exits
  Quote-exit   Candidate-D entries, phase-tamed Candidate-H PRIMARY exit
  Candidate J both controllers

No external market data, ML fitting, threshold search, or final20 access.
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
import v4_5_candidate_g_ghost_ratchet as gbase
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_microstate_v1_freeze as microstate
import v4_5_regime_portability as portability
import v4_5_router_v2 as router
import v4_5_router_v2_full_eval as full_eval
import v4_5_tick_tape_field_audit as tape

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-09-26-v4_5-quote-flow-phase-controller"

ENTRY_WAIT_SEC = 2.0
CHECK_SEC = hbase.CHECK_SEC
TRIGGER_MFE_USD = hbase.TRIGGER_MFE_USD
MIN_GIVEBACK_USD = hbase.MIN_GIVEBACK_USD
NEGATIVE_CONFIRMATIONS = hbase.NEGATIVE_CONFIRMATIONS
RANDOM_SEED = hbase.RANDOM_SEED
RANDOM_WINDOWS = hbase.RANDOM_WINDOWS
RANDOM_HOURS = hbase.RANDOM_HOURS
SLIPPAGE_STRESS_USD_PER_SIDE = hbase.SLIPPAGE_STRESS_USD_PER_SIDE

VARIANTS = ("Quote-entry", "Quote-exit", "Candidate-J")
ENGINE_NAMES = {1: "PRIMARY", 2: "SECONDARY", 3: "MICRO", 4: "BURST"}
PHASES = ("IGNITION", "HEALTHY_TREND", "HEALTHY_PULLBACK", "DECAY", "REVERSAL", "UNCERTAIN")
ENTRY_ACCEPT = {"IGNITION", "HEALTHY_TREND"}
ENTRY_BAD = {"DECAY", "REVERSAL"}
EXIT_BAD = {"DECAY", "REVERSAL"}

CONFIG = {
    "schema": "xau-quote-flow-phase-controller-v1",
    "runtime_data_scope": "MT5/broker-native only",
    "external_data_used": False,
    "entry_wait_sec": ENTRY_WAIT_SEC,
    "phase_windows_sec": [2, 10],
    "entry_changed_engines": ["PRIMARY", "SECONDARY"],
    "micro_burst_entry_changed": False,
    "exit_changed_engine": "PRIMARY only",
    "exit_base": "Candidate H from Experiment 43",
    "trigger_mfe_usd": TRIGGER_MFE_USD,
    "min_giveback_usd": MIN_GIVEBACK_USD,
    "exit_check_sec": CHECK_SEC,
    "negative_confirmations": NEGATIVE_CONFIRMATIONS,
    "path_policy": "capital-free Candidate-D baseline shadow owns opportunity/cooldown path",
    "model_search": False,
    "threshold_search": False,
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


def safe_ratio(a: float, b: float) -> float:
    return float(a / b) if math.isfinite(a) and math.isfinite(b) and abs(b) > 1e-12 else 0.0


def quote_window_features(raw: Dict[str, np.ndarray], j: int, side: int, seconds: int) -> Dict[str, float]:
    t = raw["t"]
    ss = int(raw["session_start"][j])
    a = max(ss, int(np.searchsorted(t, float(t[j]) - float(seconds), side="left")))
    b = j + 1
    if b - a < 2:
        return {
            f"dir_mid_move{seconds}": 0.0,
            f"aligned_mag{seconds}": 0.0,
            f"adverse_mag{seconds}": 0.0,
            f"aligned_count{seconds}": 0,
            f"adverse_count{seconds}": 0,
            f"path_efficiency{seconds}": 0.0,
            f"adverse_tail_run{seconds}": 0,
            f"last_nonzero_sign{seconds}": 0,
            f"seconds_since_aligned{seconds}": math.inf,
            f"seconds_since_adverse{seconds}": math.inf,
            f"bid_update_frac{seconds}": 0.0,
            f"ask_update_frac{seconds}": 0.0,
            f"both_update_frac{seconds}": 0.0,
            f"bid_ask_update_imb{seconds}": 0.0,
            f"spread_change{seconds}": 0.0,
        }

    bid = raw["bid"][a:b]
    ask = raw["ask"][a:b]
    tt = raw["t"][a:b]
    flags = raw["flags"][a:b]
    mid = (bid + ask) / 2.0
    spread = ask - bid

    # A movement is considered only on an MT5 event explicitly marked as a
    # bid and/or ask update. This makes the path use the exact broker flags.
    quote_event = ((flags & tape.FLAG_BID) != 0) | ((flags & tape.FLAG_ASK) != 0)
    dmid = np.diff(mid)
    current_event_is_quote = quote_event[1:]
    signed = float(side) * dmid
    signed = np.where(current_event_is_quote, signed, 0.0)

    eps = 1e-12
    aligned_mask = signed > eps
    adverse_mask = signed < -eps
    aligned_mag = float(signed[aligned_mask].sum()) if np.any(aligned_mask) else 0.0
    adverse_mag = float((-signed[adverse_mask]).sum()) if np.any(adverse_mask) else 0.0
    aligned_count = int(aligned_mask.sum())
    adverse_count = int(adverse_mask.sum())
    gross = float(np.abs(signed).sum())
    net = float(side) * float(mid[-1] - mid[0])
    efficiency = abs(net) / gross if gross > eps else 0.0

    nz_idx = np.flatnonzero(np.abs(signed) > eps)
    tail_run = 0
    last_sign = 0
    if len(nz_idx):
        last_sign = 1 if signed[nz_idx[-1]] > 0 else -1
        for k in nz_idx[::-1]:
            if signed[k] < 0:
                tail_run += 1
            else:
                break

    move_times = tt[1:]
    ai = np.flatnonzero(aligned_mask)
    di = np.flatnonzero(adverse_mask)
    since_aligned = float(t[j] - move_times[ai[-1]]) if len(ai) else math.inf
    since_adverse = float(t[j] - move_times[di[-1]]) if len(di) else math.inf

    bid_flag = (flags & tape.FLAG_BID) != 0
    ask_flag = (flags & tape.FLAG_ASK) != 0
    both = bid_flag & ask_flag
    n = len(flags)
    bid_n = int(bid_flag.sum())
    ask_n = int(ask_flag.sum())

    return {
        f"dir_mid_move{seconds}": net,
        f"aligned_mag{seconds}": aligned_mag,
        f"adverse_mag{seconds}": adverse_mag,
        f"aligned_count{seconds}": aligned_count,
        f"adverse_count{seconds}": adverse_count,
        f"path_efficiency{seconds}": efficiency,
        f"adverse_tail_run{seconds}": tail_run,
        f"last_nonzero_sign{seconds}": last_sign,
        f"seconds_since_aligned{seconds}": since_aligned,
        f"seconds_since_adverse{seconds}": since_adverse,
        f"bid_update_frac{seconds}": bid_n / n if n else 0.0,
        f"ask_update_frac{seconds}": ask_n / n if n else 0.0,
        f"both_update_frac{seconds}": int(both.sum()) / n if n else 0.0,
        f"bid_ask_update_imb{seconds}": safe_ratio(bid_n - ask_n, bid_n + ask_n),
        f"spread_change{seconds}": float(spread[-1] - spread[0]),
    }


def quote_state(
    raw: Dict[str, np.ndarray],
    ts: float,
    side: int,
    cache: Dict[Tuple[float, int], Dict[str, float]],
) -> Dict[str, float]:
    key = (float(ts), int(side))
    cached = cache.get(key)
    if cached is not None:
        return cached

    t = raw["t"]
    j = int(np.searchsorted(t, float(ts), side="right") - 1)
    if j < 0:
        out: Dict[str, float] = {"phase": "UNCERTAIN"}
        cache[key] = out
        return out

    out = {}
    out.update(quote_window_features(raw, j, side, 2))
    out.update(quote_window_features(raw, j, side, 10))

    d2 = float(out["dir_mid_move2"])
    d10 = float(out["dir_mid_move10"])
    a2 = float(out["aligned_mag2"])
    x2 = float(out["adverse_mag2"])
    a10 = float(out["aligned_mag10"])
    x10 = float(out["adverse_mag10"])
    tail2 = int(out["adverse_tail_run2"])
    last2 = int(out["last_nonzero_sign2"])

    if d2 < 0 and d10 < 0 and x2 > a2 and x10 > a10:
        phase = "REVERSAL"
    elif d2 < 0 and x2 > a2 and tail2 >= 2 and last2 < 0:
        phase = "DECAY"
    elif d10 > 0 and a10 >= x10 and d2 < 0:
        phase = "HEALTHY_PULLBACK"
    elif d10 > 0 and a10 >= x10 and d2 >= 0:
        phase = "HEALTHY_TREND"
    elif d2 > 0 and a2 > x2:
        phase = "IGNITION"
    else:
        phase = "UNCERTAIN"

    out["phase"] = phase
    cache[key] = out
    return out


def phase_fields(state: Dict[str, float]) -> Dict[str, float]:
    keys = [
        "phase",
        "dir_mid_move2", "dir_mid_move10",
        "aligned_mag2", "adverse_mag2", "aligned_mag10", "adverse_mag10",
        "aligned_count2", "adverse_count2", "aligned_count10", "adverse_count10",
        "path_efficiency2", "path_efficiency10",
        "adverse_tail_run2", "last_nonzero_sign2",
        "seconds_since_aligned2", "seconds_since_adverse2",
        "bid_update_frac2", "ask_update_frac2", "both_update_frac2", "bid_ask_update_imb2",
        "bid_update_frac10", "ask_update_frac10", "both_update_frac10", "bid_ask_update_imb10",
        "spread_change2", "spread_change10",
    ]
    return {k: state.get(k, math.nan) for k in keys}


def legacy_reason(
    engine: int,
    move: float,
    held: float,
    peak: float,
    highopen: int,
    side: int,
    m30_value: float,
    m300_value: float,
    failure_since: float,
    ts: float,
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

    if engine == 4 and not np.isfinite(m30_value):
        failure_since = -1e30
    if reason == 0 and engine == 4 and np.isfinite(m30_value):
        failure = (side == 1 and m30_value <= 0) or (side == -1 and m30_value >= 0)
        if failure:
            if failure_since < -1e20:
                failure_since = ts
            if ts - failure_since >= 1.0:
                reason = 5
        else:
            failure_since = -1e30

    if reason == 0 and rev == 1 and np.isfinite(m300_value):
        if (side == 1 and m300_value <= 0) or (side == -1 and m300_value >= 0):
            reason = 5
    if reason == 0 and held >= maxhold:
        reason = 7
    return reason, failure_since


def simulate_overlay(
    arr: Dict[str, np.ndarray],
    start: int,
    end: int,
    *,
    variant: str,
    tape_raw: Dict[str, np.ndarray],
    micro_raw: Dict[str, np.ndarray],
    quote_cache: Dict[Tuple[float, int], Dict[str, float]],
    micro_cache: Dict[Tuple[float, int], Dict[str, float]],
    extra_slippage_usd_per_side: float = 0.0,
    entry_events: Optional[List[Dict]] = None,
    exit_events: Optional[List[Dict]] = None,
    context: str = "",
    capture_shadow_trace: bool = False,
):
    if variant not in VARIANTS:
        raise ValueError(variant)
    use_entry = variant in ("Quote-entry", "Candidate-J")
    use_exit = variant in ("Quote-exit", "Candidate-J")

    t, bid, ask = arr["t"], arr["bid"], arr["ask"]
    m30, m300 = arr["m30"], arr["m300"]
    r300, er60 = arr["range300"], arr["er60"]
    cfg = canonical.burst_config("v4_5_b")
    slip = float(extra_slippage_usd_per_side)

    # Candidate-D baseline shadow. It alone defines opportunity/cooldown timing.
    sh_pos = 0
    sh_side = 0
    sh_entry = sh_ptime = sh_peak = 0.0
    sh_highopen = 0
    sh_failure_since = -1e30
    last = {1: -1e30, 2: -1e30, 3: -1e30, 4: -1e30}
    prev_ss = None
    cont = 0.0
    shadow_trace: List[Tuple[float, int, int]] = []

    # Real capital position.
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

    pending = None
    immediate_entries = delayed_entries = skipped_entries = busy_skips = 0
    phase_exits = 0
    protected_pullbacks = 0
    shadow_opportunities = 0

    def open_real(engine: int, sside: int, i: int):
        nonlocal pos, side, entry, oz, ptime, peak, partial, partial_done
        nonlocal highopen, failure_since, next_check, decay_confirm
        nonlocal immediate_entries
        ts = float(t[i])
        high = bool(
            np.isfinite(r300[i]) and np.isfinite(er60[i])
            and r300[i] >= 5.0 and er60[i] >= 0.03
        )
        px = float((ask[i] + slip) if sside == 1 else (bid[i] - slip))
        size = min(
            bal * 0.03 / (4 * canonical.INR_PER_USD),
            (bal / canonical.INR_PER_USD * 100) / px,
        )
        pos = int(engine)
        side = int(sside)
        entry = px
        oz = size
        ptime = ts
        peak = 0.0
        partial = 0.0
        partial_done = 0
        highopen = 1 if high else 0
        failure_since = -1e30
        next_check = ts + CHECK_SEC if use_exit and engine == 1 else math.inf
        decay_confirm = 0
        immediate_entries += 1

    for i in range(start, end):
        ts = float(t[i])
        if prev_ss is None or arr["ss"][i] != prev_ss:
            cont = ts
            prev_ss = arr["ss"][i]

        shadow_exited = False

        # 1) Advance Candidate-D baseline shadow.
        if sh_pos:
            px = (bid[i] - slip) if sh_side == 1 else (ask[i] + slip)
            move = float((px - sh_entry) if sh_side == 1 else (sh_entry - px))
            held = ts - sh_ptime
            sh_peak = max(sh_peak, move)
            reason, sh_failure_since = legacy_reason(
                sh_pos, move, held, sh_peak, sh_highopen, sh_side,
                float(m30[i]), float(m300[i]), sh_failure_since, ts, cfg,
            )
            if reason:
                last[sh_pos] = ts
                sh_pos = 0
                shadow_exited = True
                if pending is not None:
                    if entry_events is not None:
                        entry_events.append({
                            "context": context,
                            "variant": variant,
                            "action": "SKIP_SHADOW_ENDED",
                            **pending,
                        })
                    skipped_entries += 1
                    pending = None

        # 2) Advance real capital position.
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
            # Hard/native exits before the extra quote-phase exit.
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

            qstate = None
            mstate = None
            if reason == 0 and use_exit and pos == 1 and ts >= next_check:
                while next_check <= ts:
                    next_check += CHECK_SEC
                armed = peak >= TRIGGER_MFE_USD and (peak - move) >= MIN_GIVEBACK_USD
                if armed:
                    _, mstate = hbase.decay_state(micro_raw, ts, side, micro_cache)
                    micro_bad = (
                        math.isfinite(float(mstate.get("dir_mid_move2", math.nan)))
                        and math.isfinite(float(mstate.get("dir_event_imb2", math.nan)))
                        and float(mstate["dir_mid_move2"]) < 0.0
                        and float(mstate["dir_event_imb2"]) < 0.0
                    )
                    qstate = quote_state(tape_raw, ts, side, quote_cache)
                    phase = str(qstate["phase"])
                    phase_bad = phase in EXIT_BAD
                    if phase == "HEALTHY_PULLBACK":
                        protected_pullbacks += 1
                    decay_confirm = decay_confirm + 1 if (micro_bad and phase_bad) else 0
                else:
                    decay_confirm = 0

                if decay_confirm >= NEGATIVE_CONFIRMATIONS:
                    reason = 8
                    phase_exits += 1

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

                if reason == 8 and exit_events is not None:
                    if qstate is None:
                        qstate = quote_state(tape_raw, ts, side, quote_cache)
                    if mstate is None:
                        _, mstate = hbase.decay_state(micro_raw, ts, side, micro_cache)
                    exit_events.append({
                        "context": context,
                        "variant": variant,
                        "entry_ts": ptime,
                        "exit_ts": ts,
                        "side": "BUY" if side == 1 else "SELL",
                        "held_sec": held,
                        "mfe_usd": peak,
                        "exit_move_usd": move,
                        "giveback_usd": peak - move,
                        "retained_fraction": move / peak if peak > 0 else math.nan,
                        "micro_dir_mid_move2": mstate.get("dir_mid_move2", math.nan),
                        "micro_dir_event_imb2": mstate.get("dir_event_imb2", math.nan),
                        **phase_fields(qstate),
                    })
                pos = 0
                decay_confirm = 0

        # 3) Pending entry may ignite while baseline shadow is still occupying.
        if pending is not None and pos == 0 and sh_pos:
            engine = int(pending["engine_id"])
            sside = int(pending["side_sign"])
            qstate = quote_state(tape_raw, ts, sside, quote_cache)
            phase = str(qstate["phase"])
            same_signal = (engine, sside) in router.signal_candidates(arr, i, cont, last)

            if phase in ENTRY_BAD:
                if entry_events is not None:
                    entry_events.append({
                        "context": context, "variant": variant,
                        "action": "SKIP_DECAY_DURING_WAIT",
                        **pending, "decision_ts": ts, **phase_fields(qstate),
                    })
                skipped_entries += 1
                pending = None
            elif same_signal and phase in ENTRY_ACCEPT and ts <= float(pending["deadline_ts"]):
                open_real(engine, sside, i)
                immediate_entries -= 1
                delayed_entries += 1
                if entry_events is not None:
                    entry_events.append({
                        "context": context, "variant": variant,
                        "action": "TAKE_DELAYED",
                        **pending, "decision_ts": ts,
                        "wait_sec": ts - float(pending["baseline_entry_ts"]),
                        **phase_fields(qstate),
                    })
                pending = None
            elif ts >= float(pending["deadline_ts"]):
                if entry_events is not None:
                    entry_events.append({
                        "context": context, "variant": variant,
                        "action": "SKIP_WAIT_EXPIRED",
                        **pending, "decision_ts": ts, **phase_fields(qstate),
                    })
                skipped_entries += 1
                pending = None

        # Candidate-D simulator never opens a new trade on an exit tick.
        if shadow_exited or sh_pos:
            continue

        # 4) Start next Candidate-D baseline opportunity.
        candidates = router.signal_candidates(arr, i, cont, last)
        if not candidates:
            continue
        engine, sside = candidates[0]
        high = bool(
            np.isfinite(r300[i]) and np.isfinite(er60[i])
            and r300[i] >= 5.0 and er60[i] >= 0.03
        )
        sh_pos = int(engine)
        sh_side = int(sside)
        sh_entry = float((ask[i] + slip) if sside == 1 else (bid[i] - slip))
        sh_ptime = ts
        sh_peak = 0.0
        sh_highopen = 1 if high else 0
        sh_failure_since = -1e30
        shadow_opportunities += 1
        if capture_shadow_trace:
            shadow_trace.append((ts, int(engine), int(sside)))

        if pos:
            busy_skips += 1
            if entry_events is not None:
                entry_events.append({
                    "context": context, "variant": variant,
                    "action": "SKIP_REAL_SLOT_BUSY",
                    "baseline_entry_ts": ts,
                    "engine": ENGINE_NAMES[engine],
                    "engine_id": int(engine),
                    "side": "BUY" if sside == 1 else "SELL",
                    "side_sign": int(sside),
                })
            continue

        if not use_entry or engine not in (1, 2):
            open_real(engine, sside, i)
            if entry_events is not None:
                entry_events.append({
                    "context": context, "variant": variant,
                    "action": "TAKE_UNCHANGED",
                    "baseline_entry_ts": ts,
                    "decision_ts": ts,
                    "engine": ENGINE_NAMES[engine],
                    "engine_id": int(engine),
                    "side": "BUY" if sside == 1 else "SELL",
                    "side_sign": int(sside),
                })
            continue

        qstate = quote_state(tape_raw, ts, sside, quote_cache)
        phase = str(qstate["phase"])
        base = {
            "baseline_entry_ts": ts,
            "engine": ENGINE_NAMES[engine],
            "engine_id": int(engine),
            "side": "BUY" if sside == 1 else "SELL",
            "side_sign": int(sside),
        }

        if phase in ENTRY_ACCEPT:
            open_real(engine, sside, i)
            if entry_events is not None:
                entry_events.append({
                    "context": context, "variant": variant,
                    "action": "TAKE_IMMEDIATE",
                    **base, "decision_ts": ts, **phase_fields(qstate),
                })
        elif phase in ENTRY_BAD:
            skipped_entries += 1
            if entry_events is not None:
                entry_events.append({
                    "context": context, "variant": variant,
                    "action": "SKIP_BAD_PHASE",
                    **base, "decision_ts": ts, **phase_fields(qstate),
                })
        else:
            pending = {
                **base,
                "deadline_ts": ts + ENTRY_WAIT_SEC,
                "initial_phase": phase,
            }
            if entry_events is not None:
                entry_events.append({
                    "context": context, "variant": variant,
                    "action": "WAIT",
                    **base, "decision_ts": ts,
                    "deadline_ts": ts + ENTRY_WAIT_SEC,
                    **phase_fields(qstate),
                })

    pf = gp / gl if gl > 0 else 999.0
    terminal_unrealized = 0.0
    if pos and end > start:
        j = end - 1
        px = (bid[j] - slip) if side == 1 else (ask[j] + slip)
        move = float((px - entry) if side == 1 else (entry - px))
        terminal_unrealized = move * oz * canonical.INR_PER_USD

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
        "shadow_opportunities": shadow_opportunities,
        "immediate_entries": immediate_entries,
        "delayed_entries": delayed_entries,
        "skipped_entries": skipped_entries,
        "busy_skips": busy_skips,
        "phase_exits": phase_exits,
        "protected_pullbacks": protected_pullbacks,
        "shadow_trace": shadow_trace if capture_shadow_trace else None,
    }


def compact(m: Dict) -> Dict:
    keys = (
        "pnl_inr", "terminal_unrealized_inr", "terminal_equity_pnl_inr",
        "open_position_at_end", "profit_factor", "trades", "wins", "win_rate",
        "max_drawdown_inr", "shadow_opportunities", "immediate_entries",
        "delayed_entries", "skipped_entries", "busy_skips",
        "phase_exits", "protected_pullbacks",
    )
    return {k: m[k] for k in keys if k in m}


def summarize(rows: List[Dict]) -> Dict:
    factor = 1.0
    trades = wins = 0
    dds = []
    counters = {
        "shadow_opportunities": 0, "immediate_entries": 0, "delayed_entries": 0,
        "skipped_entries": 0, "busy_skips": 0, "phase_exits": 0,
        "protected_pullbacks": 0,
    }
    for m in rows:
        factor *= 1.0 + m["pnl_inr"] / canonical.START_BALANCE_INR
        trades += int(m["trades"])
        wins += int(m["wins"])
        dds.append(float(m["max_drawdown_inr"]))
        for k in counters:
            counters[k] += int(m.get(k, 0))
    return {
        "compounded_pnl_inr": canonical.START_BALANCE_INR * (factor - 1.0),
        "trades": trades,
        "wins": wins,
        "win_rate": wins / trades if trades else 0.0,
        "max_segment_drawdown_inr": max(dds) if dds else 0.0,
        **counters,
    }


def summarize_h(rows: List[Dict]) -> Dict:
    factor = 1.0
    trades = wins = 0
    dds = []
    exits = ghosts = 0
    for m in rows:
        factor *= 1.0 + m["pnl_inr"] / canonical.START_BALANCE_INR
        trades += int(m["trades"]); wins += int(m["wins"])
        dds.append(float(m["max_drawdown_inr"]))
        exits += int(m.get("primary_flow_exits", 0))
        ghosts += int(m.get("ghost_releases", 0))
    return {
        "compounded_pnl_inr": canonical.START_BALANCE_INR * (factor - 1.0),
        "trades": trades, "wins": wins,
        "win_rate": wins / trades if trades else 0.0,
        "max_segment_drawdown_inr": max(dds) if dds else 0.0,
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
        "total_trades": int(tr.sum()),
        "total_wins": int(wi.sum()),
        "aggregate_win_rate": float(wi.sum() / tr.sum()) if tr.sum() else 0.0,
    }


def assert_d(summary: Dict, interval: str):
    exp = gbase.fbase.EXPECTED_D[interval]
    if abs(summary["compounded_pnl_inr"] - exp["pnl"]) > 1e-6:
        raise RuntimeError(f"Candidate D parity drift {interval}: {summary}")
    if summary["trades"] != exp["trades"] or summary["wins"] != exp["wins"]:
        raise RuntimeError(f"Candidate D count drift {interval}: {summary}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("canonical_csv", type=Path)
    ap.add_argument("recent_csv_or_gz", type=Path)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "candidate_j_config.json").write_text(json.dumps(CONFIG, indent=2) + "\n", encoding="utf-8")

    print("loading MT5-native raw quote/event sources", flush=True)
    htape = tape.load_raw(a.canonical_csv, nrows=canonical.RESEARCH_ROWS)
    rtape = tape.load_raw(a.recent_csv_or_gz)
    hmicro = microstate.load_raw(a.canonical_csv, nrows=canonical.RESEARCH_ROWS)
    rmicro = microstate.load_raw(a.recent_csv_or_gz)

    hqcache: Dict[Tuple[float, int], Dict[str, float]] = {}
    rqcache: Dict[Tuple[float, int], Dict[str, float]] = {}
    hmcache: Dict[Tuple[float, int], Dict[str, float]] = {}
    rmcache: Dict[Tuple[float, int], Dict[str, float]] = {}

    result = {
        "schema": "xau-quote-flow-phase-controller-eval-v1",
        "config": CONFIG,
        "known_data_promotion_allowed": False,
        "final20_opened": False,
        "intervals": {},
    }

    entry_events: List[Dict] = []
    exit_events: List[Dict] = []
    parity_rows: List[Dict] = []
    segment_rows: List[Dict] = []
    split_rows: List[Dict] = []
    random_rows_all: List[Dict] = []
    stress_rows: List[Dict] = []

    for interval in ("500ms", "1s"):
        print(f"{interval}: canonical", flush=True)
        h_arr, h_bounds = canonical.build_features(a.canonical_csv, interval)
        canonical.assert_baseline(
            canonical.run_strategy(h_arr, h_bounds, "v4_4"),
            interval, canonical.DEFAULT_GOLDEN,
        )
        h_inds = autopsy.indices(h_arr, h_bounds)

        dseg = []
        hseg = []
        qseg = {v: [] for v in VARIANTS}
        for sid, (s, e) in enumerate(h_inds):
            d = hbase.simulate(h_arr, s, e, candidate_h=False, capture_trace=True)
            h = hbase.simulate(
                h_arr, s, e, candidate_h=True,
                raw=hmicro, feature_cache=hmcache, capture_trace=True,
            )
            dseg.append(d); hseg.append(h)

            row = {"interval": interval, "segment_id": sid}
            for v in VARIANTS:
                q = simulate_overlay(
                    h_arr, s, e, variant=v,
                    tape_raw=htape, micro_raw=hmicro,
                    quote_cache=hqcache, micro_cache=hmcache,
                    entry_events=entry_events,
                    exit_events=exit_events,
                    context=f"historical7d:{interval}:segment{sid}",
                    capture_shadow_trace=True,
                )
                qseg[v].append(q)
                parity = q["shadow_trace"] == d["entry_trace"]
                parity_rows.append({
                    "window": "historical7d", "interval": interval,
                    "segment_id": sid, "variant": v, "match": parity,
                    "d_entries": len(d["entry_trace"]), "shadow_entries": len(q["shadow_trace"]),
                })
                if not parity:
                    raise RuntimeError(f"baseline shadow parity failure {interval} seg {sid} {v}")
                row[f"{v}_pnl_inr"] = q["pnl_inr"]
                row[f"{v}_trades"] = q["trades"]
                row[f"{v}_wins"] = q["wins"]
                row[f"{v}_delayed_entries"] = q["delayed_entries"]
                row[f"{v}_skipped_entries"] = q["skipped_entries"]
                row[f"{v}_phase_exits"] = q["phase_exits"]
            row["D_pnl_inr"] = d["pnl_inr"]
            row["H_pnl_inr"] = h["pnl_inr"]
            segment_rows.append(row)

        ds = summarize_h(dseg)
        hs = summarize_h(hseg)
        assert_d(ds, interval)
        qsums = {v: summarize(qseg[v]) for v in VARIANTS}

        print(f"{interval}: recent", flush=True)
        r_arr, _ = canonical.build_features(a.recent_csv_or_gz, interval)
        rd = hbase.simulate(r_arr, 0, len(r_arr["t"]), candidate_h=False, capture_trace=True)
        rh = hbase.simulate(
            r_arr, 0, len(r_arr["t"]), candidate_h=True,
            raw=rmicro, feature_cache=rmcache, capture_trace=True,
        )
        exp_recent = gbase.fbase.EXPECTED_RECENT_D[interval]
        if abs(rd["terminal_equity_pnl_inr"] - exp_recent["pnl"]) > 1e-6:
            raise RuntimeError(f"Recent D parity drift {interval}")

        rq = {}
        for v in VARIANTS:
            q = simulate_overlay(
                r_arr, 0, len(r_arr["t"]), variant=v,
                tape_raw=rtape, micro_raw=rmicro,
                quote_cache=rqcache, micro_cache=rmcache,
                entry_events=entry_events,
                exit_events=exit_events,
                context=f"recent24h:{interval}:whole",
                capture_shadow_trace=True,
            )
            rq[v] = q
            parity = q["shadow_trace"] == rd["entry_trace"]
            parity_rows.append({
                "window": "recent24h", "interval": interval,
                "segment_id": -1, "variant": v, "match": parity,
                "d_entries": len(rd["entry_trace"]), "shadow_entries": len(q["shadow_trace"]),
            })
            if not parity:
                raise RuntimeError(f"recent shadow parity failure {interval} {v}")

        times = pd.read_csv(a.recent_csv_or_gz, usecols=["timestamp_utc"])["timestamp_utc"]
        cut_ts = pd.to_datetime(times.iloc[int(len(times) * 0.6)], utc=True).timestamp()
        cut = int(np.searchsorted(r_arr["t"], cut_ts, "left"))
        splits = []
        for name, s, e in (("seed", 0, cut), ("evaluation", cut, len(r_arr["t"]))):
            row = {"interval": interval, "split": name}
            item = {"split": name}
            d = hbase.simulate(r_arr, s, e, candidate_h=False)
            h = hbase.simulate(
                r_arr, s, e, candidate_h=True,
                raw=rmicro, feature_cache=rmcache,
            )
            item["D"] = compact(d); item["H"] = compact(h)
            row["D_terminal_equity_pnl_inr"] = d["terminal_equity_pnl_inr"]
            row["H_terminal_equity_pnl_inr"] = h["terminal_equity_pnl_inr"]
            for v in VARIANTS:
                q = simulate_overlay(
                    r_arr, s, e, variant=v,
                    tape_raw=rtape, micro_raw=rmicro,
                    quote_cache=rqcache, micro_cache=rmcache,
                )
                item[v] = compact(q)
                row[f"{v}_terminal_equity_pnl_inr"] = q["terminal_equity_pnl_inr"]
                row[f"{v}_trades"] = q["trades"]
                row[f"{v}_delayed_entries"] = q["delayed_entries"]
                row[f"{v}_skipped_entries"] = q["skipped_entries"]
                row[f"{v}_phase_exits"] = q["phase_exits"]
            splits.append(item)
            split_rows.append(row)

        rng = np.random.default_rng(RANDOM_SEED + (0 if interval == "500ms" else 1))
        hist_ranges = full_eval.continuous_ranges(h_arr, h_inds)
        recent_ranges = full_eval.continuous_ranges(r_arr, [(0, len(r_arr["t"]))])
        rr = []
        for wid in range(RANDOM_WINDOWS):
            source = "historical7d" if wid % 2 == 0 else "recent24h"
            if source == "historical7d":
                arr, ranges, traw, mraw, qcache, mcache = h_arr, hist_ranges, htape, hmicro, hqcache, hmcache
            else:
                arr, ranges, traw, mraw, qcache, mcache = r_arr, recent_ranges, rtape, rmicro, rqcache, rmcache
            s, e, rid = full_eval.random_window_from_ranges(arr, ranges, rng, RANDOM_HOURS)
            d = hbase.simulate(arr, s, e, candidate_h=False)
            h = hbase.simulate(arr, s, e, candidate_h=True, raw=mraw, feature_cache=mcache)
            j = simulate_overlay(
                arr, s, e, variant="Candidate-J",
                tape_raw=traw, micro_raw=mraw,
                quote_cache=qcache, micro_cache=mcache,
            )
            row = {
                "interval": interval, "window_id": wid, "source": source,
                "source_range_id": rid,
                "start_ts": float(arr["t"][s]), "end_ts": float(arr["t"][e - 1]),
                "D_pnl": d["terminal_equity_pnl_inr"],
                "H_pnl": h["terminal_equity_pnl_inr"],
                "J_pnl": j["terminal_equity_pnl_inr"],
                "D_trades": d["trades"], "H_trades": h["trades"], "J_trades": j["trades"],
                "D_wins": d["wins"], "H_wins": h["wins"], "J_wins": j["wins"],
                "J_delayed_entries": j["delayed_entries"],
                "J_skipped_entries": j["skipped_entries"],
                "J_phase_exits": j["phase_exits"],
            }
            rr.append(row)
            random_rows_all.append(row)

        random_stats = {
            "D": random_summary(rr, "D"),
            "H": random_summary(rr, "H"),
            "J": random_summary(rr, "J"),
        }

        costs = []
        for slip in SLIPPAGE_STRESS_USD_PER_SIDE:
            row = {"interval": interval, "extra_slippage_usd_per_side": slip}
            for label in ("D", "H", "J"):
                if label == "D":
                    hs2 = [hbase.simulate(h_arr, s, e, candidate_h=False, extra_slippage_usd_per_side=slip) for s, e in h_inds]
                    rs2 = hbase.simulate(r_arr, 0, len(r_arr["t"]), candidate_h=False, extra_slippage_usd_per_side=slip)
                    sm = summarize_h(hs2)
                elif label == "H":
                    hs2 = [hbase.simulate(h_arr, s, e, candidate_h=True, raw=hmicro, feature_cache=hmcache, extra_slippage_usd_per_side=slip) for s, e in h_inds]
                    rs2 = hbase.simulate(r_arr, 0, len(r_arr["t"]), candidate_h=True, raw=rmicro, feature_cache=rmcache, extra_slippage_usd_per_side=slip)
                    sm = summarize_h(hs2)
                else:
                    hs2 = [
                        simulate_overlay(
                            h_arr, s, e, variant="Candidate-J",
                            tape_raw=htape, micro_raw=hmicro,
                            quote_cache=hqcache, micro_cache=hmcache,
                            extra_slippage_usd_per_side=slip,
                        )
                        for s, e in h_inds
                    ]
                    rs2 = simulate_overlay(
                        r_arr, 0, len(r_arr["t"]), variant="Candidate-J",
                        tape_raw=rtape, micro_raw=rmicro,
                        quote_cache=rqcache, micro_cache=rmcache,
                        extra_slippage_usd_per_side=slip,
                    )
                    sm = summarize(hs2)
                row[f"{label}_historical_compounded_pnl_inr"] = sm["compounded_pnl_inr"]
                row[f"{label}_recent_terminal_equity_pnl_inr"] = rs2["terminal_equity_pnl_inr"]
            costs.append(row)
            stress_rows.append(row)

        result["intervals"][interval] = {
            "canonical_first80": {
                "D": ds,
                "H": hs,
                **qsums,
            },
            "recent24h_whole": {
                "D": compact(rd),
                "H": compact(rh),
                **{v: compact(rq[v]) for v in VARIANTS},
            },
            "recent24h_split": splits,
            "random_real_windows": random_stats,
            "cost_stress": costs,
        }

    write_csv(a.output / "baseline_shadow_parity.csv", parity_rows)
    write_csv(a.output / "canonical_segment_comparison.csv", segment_rows)
    write_csv(a.output / "recent_split_comparison.csv", split_rows)
    write_csv(a.output / "random_real_windows.csv", random_rows_all)
    write_csv(a.output / "cost_stress.csv", stress_rows)
    write_csv(a.output / "entry_phase_actions.csv", entry_events)
    write_csv(a.output / "quote_phase_exit_events.csv", exit_events)

    phase_counts = {}
    for row in entry_events:
        phase = str(row.get("phase", "NA"))
        action = str(row.get("action", "NA"))
        key = f"{action}|{phase}"
        phase_counts[key] = phase_counts.get(key, 0) + 1
    result["entry_action_phase_counts"] = phase_counts
    result["exit_events"] = len(exit_events)
    result["decision"] = (
        "Known-data diagnostic only. Candidate J may be rejected here but cannot be "
        "promoted without a fresh non-overlapping MT5-only snapshot."
    )

    (a.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
