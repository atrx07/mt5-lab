"""Baseline strategies for mcx-gold-lab — CALIBRATION ONLY.

These exist to prove the harness works and to set the "known-negative" floor
every future candidate must beat. They are NOT candidates. No baseline here
is expected to be profitable; the MA crossover is included precisely because
honest public research shows it loses (the shape every real candidate must
demonstrably differ from).

All strategies speak the harness protocol: on_tick(tick, state) -> target lots.
"""

from collections import deque


class HoldAndClose:
    """Test double: opens 1 lot at first tick, closes at tick `exit_at`.

    Used by the accounting smoke test, not as a strategy.
    """

    def __init__(self, exit_at: int):
        self.exit_at = exit_at
        self.opened = False

    def on_tick(self, tick, state):
        if not self.opened:
            self.opened = True
            return 1
        if state["idx"] >= self.exit_at:
            return 0
        return state["lots"]


class NeverTrade:
    """Test double: always flat. Net P&L must be exactly 0."""

    def on_tick(self, tick, state):
        return 0


class MACrossover:
    """Classic fast/slow moving-average crossover on 60 s sampled mid-price.

    KNOWN-NEGATIVE calibration baseline. Long on fast>slow, short on fast<slow,
    flat never (always in the market). Expectation: loses to costs + whipsaw.
    """

    def __init__(self, fast_n: int = 10, slow_n: int = 30, sample_secs: int = 60,
                 lots: int = 1):
        self.fast_n, self.slow_n = fast_n, slow_n
        self.sample_secs, self.lots = sample_secs, lots
        self.mids = deque(maxlen=slow_n)
        self._last_sample = None

    def on_tick(self, tick, state):
        if self._last_sample is None or tick.ts - self._last_sample >= self.sample_secs:
            self._last_sample = tick.ts
            self.mids.append(tick.mid)
        if len(self.mids) < self.slow_n:
            return 0
        fast = sum(list(self.mids)[-self.fast_n:]) / self.fast_n
        slow = sum(self.mids) / self.slow_n
        return self.lots if fast > slow else -self.lots


class SimpleGrid:
    """Symmetric grid around a rolling anchor — PROTOTYPE, not a candidate.

    Places `levels` buy levels below and sell levels above the anchor, spaced
    `spacing_rs` apart. Net position is bounded by `max_lots` (harness cap).
    Mean-reversion prototype: buys weakness, sells strength, always flat-able.

    Expectation on drifting synthetic data: loses. Its value is structural —
    it exercises partial fills, inventory flipping, and cost drag in the harness.
    """

    def __init__(self, levels: int = 5, spacing_rs: float = 5.0, lots: int = 1):
        self.levels, self.spacing = levels, spacing_rs
        self.lot = lots
        self.anchor = None

    def on_tick(self, tick, state):
        if self.anchor is None:
            self.anchor = tick.mid
        # re-anchor slowly toward price so the grid doesn't strand (prototype only)
        self.anchor += 0.001 * (tick.mid - self.anchor)
        dist = (tick.mid - self.anchor) / self.spacing
        # target: negative distance => long bias, positive => short bias, clipped
        target = int(max(-self.levels, min(self.levels, -round(dist)))) * self.lot
        return target
