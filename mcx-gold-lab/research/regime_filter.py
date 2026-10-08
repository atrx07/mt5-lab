"""Causal regime filter for mcx-gold-lab (Experiment 03).

Hypothesis (from Exp 02): Donchian breakout is a regime bet — it harvests
trends and bleeds in chop. Gate its ENTRIES on a causal trend-efficiency
reading; never gate exits (the filter must never trap a position).

Causality: efficiency at bar t uses only closes up to and including t.
Signal executes at t+1's open per harness rule. No look-ahead anywhere.

Efficiency E(t) = |close[t]/close[t-N] - 1| / sum(|daily returns| over N days)
High E = trending (price went somewhere); low E = chop (price went nowhere).
"""

from collections import deque

from baselines_daily import DonchianBreakout


class RegimeGatedDonchian:
    def __init__(self, n_donchian=20, eff_lookback=20, threshold=0.30, lots=1):
        self.don = DonchianBreakout(n_donchian, lots)
        self.eff_n = eff_lookback
        self.threshold = threshold
        self.closes = deque(maxlen=eff_lookback + 1)

    def efficiency(self) -> float:
        if len(self.closes) < self.eff_n + 1:
            return 0.0
        c = list(self.closes)
        path = sum(abs(c[i + 1] - c[i]) / c[i] for i in range(len(c) - 1))
        net = abs(c[-1] / c[0] - 1)
        return net / path if path > 1e-12 else 0.0

    def on_bar(self, bar, state):
        self.closes.append(bar.close)
        eff = self.efficiency()
        # keep Donchian's lookback warm even when gated out, so levels are
        # correct the moment the gate reopens
        sig = self.don.on_bar(bar, state)
        if state["lots"] == 0 and eff <= self.threshold:
            return 0  # choppy regime: no new entries
        return sig
