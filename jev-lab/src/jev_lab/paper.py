"""Deterministic, long-only candle replay for the frozen BTC/USDT baseline."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence

from .binance_spot import INTERVAL_MS, MarketDataError, _validate_kline


@dataclass(frozen=True)
class Bar:
    open_ms: int
    open: float
    high: float
    low: float
    close: float


def parse_bars(rows: Sequence[list], interval: str) -> list[Bar]:
    """Parse only the caller-provided research rows, never a sealed holdout."""
    if not rows or interval not in INTERVAL_MS:
        raise MarketDataError("missing bars or unsupported interval")
    first_open_ms = rows[0][0]
    parsed: list[Bar] = []
    for index, row in enumerate(rows):
        _validate_kline(row, first_open_ms + index * INTERVAL_MS[interval], INTERVAL_MS[interval])
        parsed.append(Bar(row[0], *(float(row[field]) for field in (1, 2, 3, 4))))
    return parsed


def run_paper(
    bars: Sequence[Bar],
    *,
    mode: str,
    starting_usdt: float,
    allocation_fraction: float,
    fee_bps: float,
    penalty_bps: float,
    breakout_bars: int,
    sma_bars: int,
    max_hold_bars: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Replay a frozen rule, buy-and-hold comparator, or no-trade comparator."""
    if mode not in {"rule", "buy_hold", "no_trade"} or not bars:
        raise ValueError("mode and nonempty bars are required")
    numbers = (starting_usdt, allocation_fraction, fee_bps, penalty_bps)
    if not all(math.isfinite(x) for x in numbers) or starting_usdt <= 0 or not 0 < allocation_fraction <= 1 or min(fee_bps, penalty_bps) < 0:
        raise ValueError("invalid paper account or cost settings")
    if min(breakout_bars, sma_bars, max_hold_bars) < 1:
        raise ValueError("lookbacks and maximum hold must be positive")
    warmup = max(breakout_bars, sma_bars)
    if len(bars) <= warmup:
        raise ValueError("segment is too short for the frozen warmup")

    fee = fee_bps / 10_000
    penalty = penalty_bps / 10_000
    cash = starting_usdt
    qty = 0.0
    entry_budget = 0.0
    entry_fee = 0.0
    entry_price = 0.0
    entry_index = -1
    pending: str | None = None
    pending_reason: str | None = None
    fees_total = 0.0
    peak_equity = starting_usdt
    max_drawdown = 0.0
    exposure_bars = 0
    trades: list[dict[str, Any]] = []

    for index, bar in enumerate(bars):
        if pending == "buy" and qty == 0:
            entry_price = bar.open * (1 + penalty)
            entry_budget = cash * allocation_fraction
            qty = entry_budget / (entry_price * (1 + fee))
            entry_fee = qty * entry_price * fee
            fees_total += entry_fee
            cash -= entry_budget
            entry_index = index
        elif pending == "sell" and qty > 0:
            exit_price = bar.open * (1 - penalty)
            proceeds = qty * exit_price
            exit_fee = proceeds * fee
            cash += proceeds - exit_fee
            fees_total += exit_fee
            trades.append({
                "entry_open_ms": bars[entry_index].open_ms,
                "exit_open_ms": bar.open_ms,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "quantity_btc": qty,
                "entry_fee_usdt": entry_fee,
                "exit_fee_usdt": exit_fee,
                "net_pnl_usdt": proceeds - exit_fee - entry_budget,
                "hold_bars": index - entry_index,
                "exit_reason": pending_reason,
            })
            qty = 0.0
        pending = None
        pending_reason = None

        if qty > 0:
            exposure_bars += 1
        marked_equity = cash + qty * bar.close
        peak_equity = max(peak_equity, marked_equity)
        max_drawdown = max(max_drawdown, peak_equity - marked_equity)

        if index == len(bars) - 1:
            break
        if mode == "no_trade" or index < warmup - 1:
            continue
        if mode == "buy_hold":
            if index == warmup - 1:
                pending = "buy"
            continue

        sma = sum(item.close for item in bars[index - sma_bars + 1 : index + 1]) / sma_bars
        if qty > 0:
            if bar.close < sma:
                pending, pending_reason = "sell", "below_sma"
            elif index - entry_index + 1 >= max_hold_bars:
                pending, pending_reason = "sell", "max_hold"
        elif bar.close > max(item.high for item in bars[index - breakout_bars : index]) and bar.close > sma:
            pending = "buy"

    if qty > 0:
        last = bars[-1]
        exit_price = last.close * (1 - penalty)
        proceeds = qty * exit_price
        exit_fee = proceeds * fee
        cash += proceeds - exit_fee
        fees_total += exit_fee
        trades.append({
            "entry_open_ms": bars[entry_index].open_ms,
            "exit_open_ms": last.open_ms,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity_btc": qty,
            "entry_fee_usdt": entry_fee,
            "exit_fee_usdt": exit_fee,
            "net_pnl_usdt": proceeds - exit_fee - entry_budget,
            "hold_bars": len(bars) - entry_index,
            "exit_reason": "terminal_liquidation_at_last_close",
        })
        peak_equity = max(peak_equity, cash)
        max_drawdown = max(max_drawdown, peak_equity - cash)

    net_pnl = cash - starting_usdt
    summary = {
        "mode": mode,
        "start_open_ms": bars[0].open_ms,
        "end_open_ms": bars[-1].open_ms,
        "bars": len(bars),
        "starting_usdt": starting_usdt,
        "ending_usdt": cash,
        "net_pnl_usdt": net_pnl,
        "return_pct": 100 * net_pnl / starting_usdt,
        "max_marked_drawdown_usdt": max_drawdown,
        "trades": len(trades),
        "wins": sum(trade["net_pnl_usdt"] > 0 for trade in trades),
        "win_rate": sum(trade["net_pnl_usdt"] > 0 for trade in trades) / len(trades) if trades else None,
        "exposure_bars": exposure_bars,
        "fees_usdt": fees_total,
        "fee_bps_per_side": fee_bps,
        "penalty_bps_per_side": penalty_bps,
        "terminal_fill": "last close if still open, with exit penalty and fee",
    }
    return summary, trades
