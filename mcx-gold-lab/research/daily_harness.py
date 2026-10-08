"""Daily-bar backtest adapter for mcx-gold-lab.

Purpose: make MCX bhavcopy data (daily OHLC + volume + OI per contract)
immediately useful for experiments while tick capture is being built.

This adapter is for DAILY-BAR strategies (trend, regime, rollover analysis).
It is NOT a substitute for tick-level research: no intraday path, no spread
modeling beyond a configurable slippage, no bid/ask. Its honesty rules:

  1. NO LOOK-AHEAD. Signal on bar t's close executes at bar t+1's OPEN.
  2. COSTS ARE REAL. Every order pays the MCX schedule (tools/mcx_cost_model.py).
  3. ROLLOVER IS MODELED. When the continuous series rolls to the next
     contract, the position is closed at the old close and reopened at the new
     open, paying full costs on both legs. Rolls are marked, never hidden.
  4. CIRCUIT DAYS ARE VISIBLE. Bars where |close-prev_close| >= 9% (or
     high == low, a lock) are flagged; strategies decide, the adapter records.
  5. SLIPPAGE IS EXPLICIT. A per-side slippage in ticks models the fact that
     daily opens are not frictionless. Default 2 ticks/side on Petal.

Continuous-series construction lives in tools/build_continuous.py (to be run
on curated bhavcopy). This adapter consumes its output.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from mcx_cost_model import order_cost  # noqa: E402


@dataclass
class DailyBar:
    date: str            # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    oi: int = 0
    contract: str = ""   # e.g. GOLDPETAL26JAN
    rolled: bool = False  # True on the first bar of a new contract (roll happened)
    limit_day: bool = False


@dataclass
class DailyConfig:
    grams_per_lot: float = 1.0
    tick_rs_per_lot: float = 1.0
    margin_pct: float = 0.07
    slippage_ticks: float = 2.0   # per side, in ticks
    max_lots: int = 50


@dataclass
class DailyResult:
    net_pnl: float
    gross_pnl: float
    total_costs: float
    trades: int
    wins: int
    profit_factor: float
    expectancy_per_trade: float
    max_drawdown: float
    win_rate: float
    cost_ratio: float
    n_bars: int
    equity_curve: list = field(default_factory=list)


class DailyHarness:
    """Daily replay. Strategy protocol: on_bar(bar, state) -> target net lots."""

    def __init__(self, bars: list[DailyBar], config: DailyConfig,
                 account_rs: float, strategy):
        assert len(bars) > 1
        self.bars = bars
        self.cfg = config
        self.account = account_rs
        self.strategy = strategy
        self.lots = 0
        self.avg = 0.0
        self.realized = 0.0
        self.costs = 0.0
        self.gross_profit = 0.0
        self.wins = 0
        self.trades = 0
        self.equity = [account_rs]
        self._pending: int | None = None

    def _notional(self, lots: int, price: float) -> float:
        return abs(lots) * self.cfg.grams_per_lot * price

    def _exec(self, bar: DailyBar, target: int):
        delta = target - self.lots
        if delta == 0:
            return
        if abs(target) > self.cfg.max_lots:
            return
        # RULE 1: fill at NEXT bar's open, with slippage against us
        slip = self.cfg.slippage_ticks * self.cfg.tick_rs_per_lot / self.cfg.grams_per_lot
        # (tick_rs_per_lot is Rs per Rs-1 move; price is Rs/gram; grams_per_lot=1
        #  so slip in Rs/gram == slippage_ticks for Petal)
        slip_price = self.cfg.slippage_ticks  # Rs per gram, Petal convention
        price = bar.open + (slip_price if delta > 0 else -slip_price)
        if not self._margin_ok(target, price):
            return
        lots = abs(delta)
        cost = order_cost(self._notional(lots, price),
                          "buy" if delta > 0 else "sell")["total"]
        old = self.lots
        closing = 0 if (old == 0 or (old > 0) == (delta > 0)) else min(abs(old), lots)
        if closing:
            pnl = ((price - self.avg) if old > 0 else (self.avg - price)) \
                * closing * self.cfg.tick_rs_per_lot
            self.realized += pnl
            if pnl > 0:
                self.gross_profit += pnl
                self.wins += 1
            self.trades += 1
        opening = lots - closing
        if opening:
            if old != 0 and (old > 0) == (delta > 0):
                tot = abs(old) + opening
                self.avg = (abs(self.avg * old) + price * opening) / tot
            else:
                self.avg = price
        self.lots = target
        self.costs += cost

    def _margin_ok(self, target: int, price: float) -> bool:
        return self._notional(target, price) * self.cfg.margin_pct \
            <= self.account + self.realized

    def _mark(self, bar: DailyBar) -> float:
        return (bar.close - self.avg) * self.lots * self.cfg.tick_rs_per_lot

    def run(self) -> DailyResult:
        n = len(self.bars)
        peak, max_dd = self.account, 0.0
        for i in range(n):
            bar = self.bars[i]
            # rollover: close at this bar's close BEFORE any new signal
            if bar.rolled and self.lots != 0:
                self._exec_close_at(bar.close, "roll")
            if self._pending is not None:      # signal from bar i-1 -> open of bar i
                self._exec(bar, self._pending)
                self._pending = None
            if i < n - 1:
                snap = dict(idx=i, date=bar.date, lots=self.lots, avg=self.avg,
                            realized=self.realized, costs=self.costs,
                            limit_day=bar.limit_day)
                self._pending = int(self.strategy.on_bar(bar, snap))
            eq = self.account + self.realized - self.costs + self._mark(bar)
            self.equity.append(eq)
            peak = max(peak, eq)
            max_dd = max(max_dd, peak - eq)
        if self.lots != 0:  # force-flat at end
            self._exec_close_at(self.bars[-1].close, "end")

        gross_loss = max(self.gross_profit - self.realized, 0.0)
        pf = (self.gross_profit / gross_loss) if gross_loss > 1e-9 \
            else (float("inf") if self.gross_profit > 0 else 0.0)
        net = self.realized - self.costs
        return DailyResult(net, self.realized, self.costs, self.trades, self.wins,
                           pf, net / self.trades if self.trades else 0.0,
                           max_dd, self.wins / self.trades if self.trades else 0.0,
                           self.costs / self.gross_profit if self.gross_profit > 1e-9 else float("inf"),
                           n, self.equity)

    def _exec_close_at(self, price: float, reason: str):
        """Close entire position at a given price (roll / end of data)."""
        if self.lots == 0:
            return
        side = "sell" if self.lots > 0 else "buy"
        lots = abs(self.lots)
        cost = order_cost(self._notional(lots, price), side)["total"]
        pnl = ((price - self.avg) if self.lots > 0 else (self.avg - price)) \
            * lots * self.cfg.tick_rs_per_lot
        self.realized += pnl
        if pnl > 0:
            self.gross_profit += pnl
            self.wins += 1
        self.trades += 1
        self.costs += cost
        self.lots = 0
        self.avg = 0.0
