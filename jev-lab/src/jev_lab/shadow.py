"""Causal Jev Choice state for an unchanged BTC/USDT entry candidate."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Sequence

from .binance_spot import INTERVAL_MS
from .paper import Bar


def _utc(milliseconds: int) -> str:
    return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def candidate_state(
    history: Sequence[Bar],
    *,
    symbol: str,
    source: str,
    interval: str,
    breakout_bars: int,
    sma_bars: int,
    fee_bps: float,
    penalty_bps: float,
) -> dict[str, Any]:
    """Use only a candidate's closed signal bar and its earlier bars."""
    if interval not in INTERVAL_MS or len(history) < max(breakout_bars + 1, sma_bars, 21, 13):
        raise ValueError("candidate history is too short or interval is unsupported")
    if not symbol or not source or min(breakout_bars, sma_bars) < 1:
        raise ValueError("invalid candidate metadata or lookbacks")
    if any(not math.isfinite(value) or value < 0 for value in (fee_bps, penalty_bps)):
        raise ValueError("invalid friction")
    current = history[-1]
    prior_20_volume = sum(bar.volume for bar in history[-21:-1]) / 20
    if current.low <= 0 or history[-4].close <= 0 or history[-13].close <= 0 or prior_20_volume <= 0:
        raise ValueError("invalid price or volume for candidate")
    return {
        "schema": "btc-spot-breakout-state-v1",
        "symbol": symbol,
        "source": source,
        "interval": interval,
        "signal_open_utc": _utc(current.open_ms),
        "decision_available_utc": _utc(current.open_ms + INTERVAL_MS[interval]),
        "close_usdt": current.close,
        "prior_high_usdt": max(bar.high for bar in history[-breakout_bars - 1:-1]),
        "sma_usdt": sum(bar.close for bar in history[-sma_bars:]) / sma_bars,
        "return_3_bars_pct": 100 * (current.close / history[-4].close - 1),
        "return_12_bars_pct": 100 * (current.close / history[-13].close - 1),
        "range_pct_of_low": 100 * (current.high / current.low - 1),
        "volume_btc": current.volume,
        "volume_vs_prior_20_mean": current.volume / prior_20_volume,
        "estimated_round_trip_friction_bps": 2 * (fee_bps + penalty_bps),
    }
