"""Honest tick-level backtest harness for mcx-gold-lab.

NON-NEGOTIABLE RULES (violations are bugs, not features):
  1. NO LOOK-AHEAD. A signal computed from tick t executes at tick t+1, never t.
  2. BID/ASK FILLS. Buys fill at the ask, sells fill at the bid. Mid-price fills
     do not exist in this harness.
  3. COSTS ARE REAL. Every executed order pays the MCX cost schedule
     (tools/mcx_cost_model.py). Paper P&L without costs is fiction.
  4. MARGIN IS ENFORCED. Orders that exceed available margin are rejected,
     exactly as a broker RMS would reject them.
  5. CIRCUITS EXIST. MCX enforces 3%/6%/9% daily price bands. Ticks outside the
     widest band are not tradable in this harness.

The harness validates EXECUTION ACCOUNTING, not strategy profitability.
A strategy that is profitable here has passed accounting, not validation.
Validation requires: frozen plan -> dev data -> untouched holdout -> paper.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from mcx_cost_model import order_cost  # noqa: E402


@dataclass
class Tick:
    ts: int
    bid: float   # Rs per gram
    ask: float   # Rs per gram

    @property
    def mid(self) -> float:  # DERIVED — never used for fills
        return (self.bid + self.ask) / 2.0


@dataclass
class Fill:
    tick_idx: int
    side: str        # "buy" | "sell"
    price: float     # ask for buy, bid for sell
    lots: int
    cost_rs: float


@dataclass
class HarnessConfig:
    grams_per_lot: float = 1.0
    tick_rs_per_lot: float = 1.0   # Rs P&L per Rs 1 price move per lot
    margin_pct: float = 0.07
    gold_inr_per_gram: float = 12000.0
    circuit_band: float = 0.09     # widest MCX band; ticks beyond are untradable
    max_lots: int = 10             # hard inventory cap


@dataclass
class HarnessResult:
    net_pnl: float
    gross_pnl: float          # realized, before costs
    total_costs: float
    trades: int               # closing legs executed
    wins: int
    profit_factor: float       # gross profit / gross loss
    expectancy_per_trade: float
    max_drawdown: float
    win_rate: float
    cost_ratio: float          # total_costs / gross_profit
    fills: list = field(default_factory=list)
    equity_curve: list = field(default_factory=list)


class Harness:
    """Tick replay. Strategy protocol: on_tick(tick, state) -> target net lots."""

    def __init__(self, ticks: list[Tick], config: HarnessConfig,
                 account_rs: float, strategy):
        assert len(ticks) > 1, "need at least 2 ticks"
        self.ticks = ticks
        self.cfg = config
        self.account = account_rs
        self.strategy = strategy
        self.lots = 0
        self.avg_price = 0.0
        self.fills: list[Fill] = []
        self.equity = [account_rs]
        self.realized = 0.0
        self.costs = 0.0
        self.gross_profit = 0.0
        self.wins = 0
        self.closed_trades = 0
        self.ref_price = ticks[0].mid
        self._pending: int | None = None

    # -- helpers -----------------------------------------------------------

    def _notional(self, lots: int) -> float:
        return abs(lots) * self.cfg.grams_per_lot * self.cfg.gold_inr_per_gram

    def _execute(self, idx: int, target: int):
        tick = self.ticks[idx]
        delta = target - self.lots
        if delta == 0:
            return
        if abs(target) > self.cfg.max_lots:
            return                       # deterministic inventory cap
        if abs(tick.mid - self.ref_price) / self.ref_price > self.cfg.circuit_band:
            return                       # circuit: untradable
        if self._notional(target) * self.cfg.margin_pct > self.account + self.realized:
            return                       # RMS would reject

        side = "buy" if delta > 0 else "sell"
        price = tick.ask if delta > 0 else tick.bid   # RULE 2
        lots = abs(delta)
        cost = order_cost(self._notional(lots), side)["total"]

        old = self.lots
        if old == 0 or (old > 0) == (delta > 0):
            closing = 0                  # fresh open or adding
        else:
            closing = min(abs(old), lots)  # reducing / reversing

        if closing:
            if old > 0:   # long closed by sell @ bid
                pnl = (price - self.avg_price) * closing * self.cfg.tick_rs_per_lot
            else:         # short closed by buy @ ask
                pnl = (self.avg_price - price) * closing * self.cfg.tick_rs_per_lot
            self.realized += pnl
            if pnl > 0:
                self.gross_profit += pnl
                self.wins += 1
            self.closed_trades += 1

        opening = lots - closing
        if opening:
            if old != 0 and (old > 0) == (delta > 0):
                tot = abs(old) + opening  # add: weighted average
                self.avg_price = (abs(self.avg_price * old) + price * opening) / tot
            else:                          # fresh or reversal remainder
                self.avg_price = price
        self.lots = target               # net position == target by construction
        self.costs += cost
        self.fills.append(Fill(idx, side, price, lots, cost))

    def _unrealized(self, idx: int) -> float:
        if self.lots == 0:
            return 0.0
        tick = self.ticks[idx]
        ref = tick.bid if self.lots > 0 else tick.ask  # conservative mark
        return (ref - self.avg_price) * self.lots * self.cfg.tick_rs_per_lot

    # -- main loop ----------------------------------------------------------

    def run(self) -> HarnessResult:
        n = len(self.ticks)
        peak, max_dd = self.account, 0.0
        for i in range(n):
            if self._pending is not None:          # RULE 1: signal from tick
                self._execute(i, self._pending)    #   i-1 executes at tick i
                self._pending = None
            if i < n - 1:
                snap = dict(idx=i, lots=self.lots, avg_price=self.avg_price,
                            realized=self.realized, costs=self.costs)
                self._pending = int(self.strategy.on_tick(self.ticks[i], snap))
            eq = self.account + self.realized - self.costs + self._unrealized(i)
            self.equity.append(eq)
            peak = max(peak, eq)
            max_dd = max(max_dd, peak - eq)

        if self.lots != 0:
            self._execute(n - 1, 0)                # force-flat at end of data

        gross_loss = max(self.gross_profit - self.realized, 0.0)
        if gross_loss > 1e-9:
            pf = self.gross_profit / gross_loss
        else:
            pf = float("inf") if self.gross_profit > 0 else 0.0
        net = self.realized - self.costs
        return HarnessResult(
            net_pnl=net,
            gross_pnl=self.realized,
            total_costs=self.costs,
            trades=self.closed_trades,
            wins=self.wins,
            profit_factor=pf,
            expectancy_per_trade=net / self.closed_trades if self.closed_trades else 0.0,
            max_drawdown=max_dd,
            win_rate=self.wins / self.closed_trades if self.closed_trades else 0.0,
            cost_ratio=self.costs / self.gross_profit if self.gross_profit > 1e-9 else float("inf"),
            fills=self.fills,
            equity_curve=self.equity,
        )
