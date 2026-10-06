"""Candidate N: Candidate-M pullback acceptance plus an independent accepted-breakout lane.

Frozen by docs/plans/V4_5_CANDIDATE_N_DUAL_ACCEPTANCE.md before P&L evaluation.
Known data may reject this candidate but cannot promote it. Final20 remains sealed.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Dict, List, Tuple

import numpy as np

import canonical_replay as canonical
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_candidate_l_normalized_resumption as lbase
import v4_5_candidate_m_pullback_acceptance as mbase

BREAKOUT_LOOKBACK_SEC = 30.0
BREAKOUT_TIMEOUT_SEC = 30.0
ACCEPT_SEC = mbase.ACCEPT_SEC

CONFIG = {
    "schema": "xau-candidate-n-dual-acceptance-v1",
    "base_pullback_path": "Candidate M unchanged",
    "external_data_used": False,
    "model_search": False,
    "threshold_search": False,
    "final20_opened": False,
    "breakout_reference": "prior 30 clock-second same-session mid extreme, current row excluded",
    "breakout_timeout_sec": BREAKOUT_TIMEOUT_SEC,
    "breakout_acceptance": "reference +/- frozen arm spread for 2.0 continuous clock seconds",
    "breakout_cancel_on_pullback": True,
    "entry_confirmation": mbase.CONFIG["entry_confirmation"],
    "max_spread_usd": mbase.CONFIG["max_spread_usd"],
    "max_spread_fraction_range60": mbase.CONFIG["max_spread_fraction_range60"],
    "risk_fraction": mbase.CONFIG["risk_fraction"],
    "stop_usd": mbase.CONFIG["stop_usd"],
    "take_profit_usd": mbase.CONFIG["take_profit_usd"],
    "max_hold_sec": mbase.CONFIG["max_hold_sec"],
    "flow_exit": mbase.CONFIG["flow_exit"],
}


def prior_30s_extrema(arr: Dict[str, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    """Causal prior-window extrema excluding the current row and respecting sessions."""
    t = np.asarray(arr["t"], float)
    mid = np.asarray(arr["mid"], float)
    ss = np.asarray(arr["ss"])
    hi = np.full(len(t), np.nan, dtype=float)
    lo = np.full(len(t), np.nan, dtype=float)
    maxq: deque[int] = deque(); minq: deque[int] = deque()
    prev_session = None
    for i in range(len(t)):
        cur_session = ss[i]
        if i == 0 or cur_session != prev_session:
            maxq.clear(); minq.clear()
        cutoff = t[i] - BREAKOUT_LOOKBACK_SEC
        while maxq and (ss[maxq[0]] != cur_session or t[maxq[0]] < cutoff):
            maxq.popleft()
        while minq and (ss[minq[0]] != cur_session or t[minq[0]] < cutoff):
            minq.popleft()
        if maxq:
            hi[i] = mid[maxq[0]]
        if minq:
            lo[i] = mid[minq[0]]
        while maxq and mid[maxq[-1]] <= mid[i]:
            maxq.pop()
        while minq and mid[minq[-1]] >= mid[i]:
            minq.pop()
        maxq.append(i); minq.append(i)
        prev_session = cur_session
    return hi, lo


def compact(m: Dict) -> Dict:
    keys = (
        "pnl_inr", "terminal_unrealized_inr", "terminal_equity_pnl_inr", "open_position_at_end",
        "profit_factor", "trades", "wins", "win_rate", "max_drawdown_inr",
        "pullback_arms", "pullback_entries", "breakout_arms", "breakout_entries",
        "breakout_expiries", "breakout_trend_cancels", "breakout_pullback_cancels",
        "acceptance_timer_resets", "flow_exits", "trend_failure_exits", "stop_exits", "tp_exits", "time_exits",
    )
    return {k: m[k] for k in keys if k in m}


def simulate_n(
    arr: Dict[str, np.ndarray], start: int, end: int, *,
    raw: Dict[str, np.ndarray], cache: Dict[Tuple[float, int], Dict[str, float]],
    breakout_ctx: Tuple[np.ndarray, np.ndarray] | None = None,
    extra_slippage_usd_per_side: float = 0.0,
    capture_trades: bool = False,
    context: str = "",
) -> Dict:
    t = np.asarray(arr["t"], float); bid = np.asarray(arr["bid"], float); ask = np.asarray(arr["ask"], float); mid = np.asarray(arr["mid"], float)
    session_starts = lbase.session_start_times(arr)
    prev_hi, prev_lo = breakout_ctx if breakout_ctx is not None else prior_30s_extrema(arr)
    slip = float(extra_slippage_usd_per_side)

    bal = canonical.START_BALANCE_INR; gp = gl = 0.0; peakbal = bal; maxdd = 0.0; ntr = wins = 0
    pos = 0; side = 0; entry = oz = ptime = peak = 0.0; next_check = math.inf; neg_conf = 0; entry_path = ""

    # Candidate-M path state.
    m_side = 0; m_time = 0.0; m_anchor = math.nan; m_spread = math.nan; m_accept_since = -1e30; m_latch_side = 0
    # Breakout path state.
    b_side = 0; b_time = 0.0; b_anchor = math.nan; b_spread = math.nan; b_accept_since = -1e30
    b_latch_side = 0; b_latch_anchor = math.nan

    pullback_arms = pullback_entries = 0
    breakout_arms = breakout_entries = breakout_expiries = breakout_trend_cancels = breakout_pullback_cancels = 0
    acceptance_timer_resets = 0
    flow_exits = trend_failure_exits = stop_exits = tp_exits = time_exits = 0
    trade_rows: List[Dict] = []

    def enter(i: int, s: int, path: str) -> bool:
        nonlocal pos, side, entry, oz, ptime, peak, next_check, neg_conf, entry_path, pullback_entries, breakout_entries
        px = float((ask[i] + slip) if s == 1 else (bid[i] - slip))
        oz_new = min(
            bal * 0.03 / (lbase.STOP_USD * canonical.INR_PER_USD),
            (bal / canonical.INR_PER_USD * 100.0) / px,
        )
        if not math.isfinite(oz_new) or oz_new <= 0:
            return False
        pos = 1; side = s; entry = px; oz = oz_new; ptime = float(t[i]); peak = 0.0
        next_check = ptime + lbase.FLOW_CHECK_SEC; neg_conf = 0; entry_path = path
        if path == "PULLBACK_ACCEPTANCE": pullback_entries += 1
        else: breakout_entries += 1
        return True

    for i in range(start, end):
        ts = float(t[i])

        if pos:
            exit_px = (bid[i] - slip) if side == 1 else (ask[i] + slip)
            move = float((exit_px - entry) if side == 1 else (entry - exit_px)); held = ts - ptime; peak = max(peak, move)
            reason = 0
            if move <= -lbase.STOP_USD:
                reason = 1; stop_exits += 1
            elif move >= lbase.TP_USD:
                reason = 2; tp_exits += 1
            if reason == 0 and ts >= next_check:
                while next_check <= ts: next_check += lbase.FLOW_CHECK_SEC
                armed = peak >= lbase.FLOW_ARM_MFE_USD and (peak - move) >= lbase.FLOW_MIN_GIVEBACK_USD
                if armed:
                    bad, _ = hbase.decay_state(raw, ts, side, cache); neg_conf = neg_conf + 1 if bad else 0
                else:
                    neg_conf = 0
                if neg_conf >= lbase.FLOW_CONFIRMATIONS:
                    reason = 8; flow_exits += 1
            if reason == 0:
                m300 = float(arr["m300"][i])
                if math.isfinite(m300) and side * m300 <= 0:
                    reason = 5; trend_failure_exits += 1
            if reason == 0 and held >= lbase.MAX_HOLD_SEC:
                reason = 7; time_exits += 1
            if reason:
                pnl = move * oz * canonical.INR_PER_USD; bal += pnl; ntr += 1
                if pnl > 0: gp += pnl; wins += 1
                elif pnl < 0: gl -= pnl
                peakbal = max(peakbal, bal); maxdd = max(maxdd, peakbal - bal)
                if capture_trades:
                    trade_rows.append({"context": context, "entry_ts": ptime, "exit_ts": ts, "side": "BUY" if side == 1 else "SELL", "entry_path": entry_path, "exit_move_usd": move, "mfe_usd": peak, "held_sec": held, "pnl_inr": pnl, "exit_reason": reason})
                pos = 0; side = 0; neg_conf = 0; next_check = math.inf; entry_path = ""
            continue

        s = lbase.structural_side(arr, i, session_starts)
        pb_now = (s != 0 and mbase.current_pullback(arr, i, s))

        # Pullback latch semantics are Candidate M's.
        if m_latch_side and (s != m_latch_side or not mbase.current_pullback(arr, i, m_latch_side)):
            m_latch_side = 0

        # Breakout latch only clears after a revisit of the frozen breakout reference or trend invalidation.
        if b_latch_side:
            if s != b_latch_side or not math.isfinite(b_latch_anchor) or b_latch_side * (float(mid[i]) - b_latch_anchor) <= 0:
                b_latch_side = 0; b_latch_anchor = math.nan

        # Candidate-M arm always has priority and remains unchanged in meaning.
        if m_side:
            if s != m_side:
                m_side = 0; m_accept_since = -1e30
                continue
            if ts - m_time > mbase.ARM_TIMEOUT_SEC:
                m_side = 0; m_accept_since = -1e30
                continue
            beyond = m_side * (float(mid[i]) - float(m_anchor)) >= float(m_spread)
            if beyond:
                if m_accept_since < -1e20: m_accept_since = ts
                if ts - m_accept_since >= ACCEPT_SEC and lbase.execution_ok(arr, i):
                    ok, _ = mbase.entry_flow_ok(arr, i, m_side, raw, cache)
                    if ok and enter(i, m_side, "PULLBACK_ACCEPTANCE"):
                        m_side = 0; m_accept_since = -1e30
            else:
                if m_accept_since > -1e20: acceptance_timer_resets += 1
                m_accept_since = -1e30
            continue

        # A developing M pullback cancels a waiting breakout and owns setup creation.
        if pb_now:
            if b_side:
                b_side = 0; b_accept_since = -1e30; breakout_pullback_cancels += 1
            if not m_latch_side:
                m10 = float(arr["m10"][i]); spread = float(arr["spread"][i])
                m_side = s; m_time = ts; m_anchor = float(mid[i] - m10); m_spread = spread; m_accept_since = -1e30; m_latch_side = s; pullback_arms += 1
            continue

        # Maintain a waiting breakout arm.
        if b_side:
            if s != b_side:
                b_side = 0; b_accept_since = -1e30; breakout_trend_cancels += 1
                continue
            if ts - b_time > BREAKOUT_TIMEOUT_SEC:
                b_side = 0; b_accept_since = -1e30; breakout_expiries += 1
                continue
            beyond = b_side * (float(mid[i]) - float(b_anchor)) >= float(b_spread)
            if beyond:
                if b_accept_since < -1e20: b_accept_since = ts
                if ts - b_accept_since >= ACCEPT_SEC and lbase.execution_ok(arr, i):
                    ok, _ = mbase.entry_flow_ok(arr, i, b_side, raw, cache)
                    if ok and enter(i, b_side, "BREAKOUT_ACCEPTANCE"):
                        b_side = 0; b_accept_since = -1e30
            else:
                if b_accept_since > -1e20: acceptance_timer_resets += 1
                b_accept_since = -1e30
            continue

        if s == 0 or b_latch_side:
            continue
        ref = float(prev_hi[i]) if s == 1 else float(prev_lo[i])
        if not math.isfinite(ref):
            continue
        crossed = float(mid[i]) > ref if s == 1 else float(mid[i]) < ref
        if not crossed:
            continue
        spread = float(arr["spread"][i])
        if not math.isfinite(spread) or spread <= 0:
            continue
        b_side = s; b_time = ts; b_anchor = ref; b_spread = spread; b_accept_since = -1e30
        b_latch_side = s; b_latch_anchor = ref; breakout_arms += 1

    pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0); terminal = 0.0
    if pos and end > start:
        j = end - 1; px = float((bid[j] - slip) if side == 1 else (ask[j] + slip)); mv = float((px - entry) if side == 1 else (entry - px)); terminal = mv * oz * canonical.INR_PER_USD
    return {
        "pnl_inr": float(bal - canonical.START_BALANCE_INR), "terminal_unrealized_inr": float(terminal),
        "terminal_equity_pnl_inr": float(bal - canonical.START_BALANCE_INR + terminal), "open_position_at_end": bool(pos),
        "profit_factor": float(pf), "trades": int(ntr), "wins": int(wins), "win_rate": float(wins / ntr) if ntr else 0.0, "max_drawdown_inr": float(maxdd),
        "pullback_arms": int(pullback_arms), "pullback_entries": int(pullback_entries), "breakout_arms": int(breakout_arms), "breakout_entries": int(breakout_entries),
        "breakout_expiries": int(breakout_expiries), "breakout_trend_cancels": int(breakout_trend_cancels), "breakout_pullback_cancels": int(breakout_pullback_cancels),
        "acceptance_timer_resets": int(acceptance_timer_resets), "flow_exits": int(flow_exits), "trend_failure_exits": int(trend_failure_exits),
        "stop_exits": int(stop_exits), "tp_exits": int(tp_exits), "time_exits": int(time_exits), "trade_rows": trade_rows if capture_trades else None,
    }


def compounded(rows: List[Dict]) -> Dict:
    factor = 1.0; trades = wins = 0; dds: List[float] = []
    counters = {k: 0 for k in ("pullback_arms", "pullback_entries", "breakout_arms", "breakout_entries", "breakout_expiries", "breakout_trend_cancels", "breakout_pullback_cancels", "flow_exits", "trend_failure_exits", "stop_exits", "tp_exits", "time_exits")}
    for m in rows:
        factor *= 1.0 + float(m["pnl_inr"]) / canonical.START_BALANCE_INR
        trades += int(m["trades"]); wins += int(m["wins"]); dds.append(float(m["max_drawdown_inr"]))
        for k in counters: counters[k] += int(m.get(k, 0))
    return {"compounded_pnl_inr": float(canonical.START_BALANCE_INR * (factor - 1.0)), "trades": trades, "wins": wins, "win_rate": wins / trades if trades else 0.0, "max_segment_drawdown_inr": max(dds) if dds else 0.0, **counters}
