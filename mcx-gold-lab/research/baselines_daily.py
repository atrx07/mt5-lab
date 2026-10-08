"""Daily-bar baselines for mcx-gold-lab — CALIBRATION ONLY.

Same contract as research/baselines.py: these exist to set the known-negative
floor and to validate the daily adapter. Not candidates.

  DailyTrendMA   — long/flat on fast/slow SMA of closes. The daily analogue of
                   the tick MA crossover: expected to lose to whipsaw + costs.
  DonchianBreakout — circuit-AWARE prototype: enter on N-day high/low break,
                   exit on opposite break or ATR stop. Skips entries the day
                   AFTER a limit day (circuit gaps invalidate breakout logic).
                   Prototype, not a candidate.
"""

from collections import deque


class DailyTrendMA:
    """Long when fast SMA > slow SMA, else flat. Always evaluated at close,
    executed at next open (harness rule)."""

    def __init__(self, fast_n=10, slow_n=30, lots=1):
        self.fast_n, self.slow_n, self.lots = fast_n, slow_n, lots
        self.closes = deque(maxlen=slow_n)

    def on_bar(self, bar, state):
        self.closes.append(bar.close)
        if len(self.closes) < self.slow_n:
            return 0
        closes = list(self.closes)
        fast = sum(closes[-self.fast_n:]) / self.fast_n
        slow = sum(closes) / self.slow_n
        return self.lots if fast > slow else 0


class DonchianBreakout:
    """Circuit-aware Donchian prototype.

    Long on close > highest high of N days; short on close < lowest low of N
    days; exit to flat on opposite signal. Additionally:
      - no NEW entries on limit days or the bar after a limit day
        (gap-through-circuit breaks breakout assumptions);
      - hard cap via harness max_lots.
    """

    def __init__(self, n=20, lots=1):
        self.n, self.lots = n, lots
        self.highs = deque(maxlen=n)
        self.lows = deque(maxlen=n)
        self.skip_next = False

    def on_bar(self, bar, state):
        if bar.limit_day:
            self.skip_next = True
            self.highs.append(bar.high)
            self.lows.append(bar.low)
            return 0
        # breakout levels from PRIOR bars only (current bar never in its own
        # lookback — otherwise close > high is impossible by construction)
        signal = 0
        if len(self.highs) >= self.n and not self.skip_next:
            hh, ll = max(self.highs), min(self.lows)
            if bar.close > hh:
                signal = self.lots
            elif bar.close < ll:
                signal = -self.lots
            else:
                signal = state["lots"]  # hold
        self.highs.append(bar.high)
        self.lows.append(bar.low)
        self.skip_next = False
        return signal
