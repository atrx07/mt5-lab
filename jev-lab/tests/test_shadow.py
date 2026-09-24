"""Check shadow requests see only the closed signal and prior candles."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jev_lab.paper import Bar, run_paper  # noqa: E402
from jev_lab.shadow import candidate_state  # noqa: E402


class ShadowTests(unittest.TestCase):
    def test_state_excludes_next_open_and_uses_prior_volume(self):
        interval_ms = 30 * 60 * 1000
        history = [Bar(i * interval_ms, 100, 101, 99, 100, 2) for i in range(48)]
        history[-1] = Bar(47 * interval_ms, 100, 106, 99, 105, 4)
        state = candidate_state(
            history,
            symbol="BTCUSDT",
            source="test",
            interval="30m",
            breakout_bars=20,
            sma_bars=48,
            fee_bps=10,
            penalty_bps=5,
        )
        self.assertEqual(state["prior_high_usdt"], 101)
        self.assertEqual(state["volume_vs_prior_20_mean"], 2)
        self.assertEqual(state["estimated_round_trip_friction_bps"], 30)
        self.assertEqual(state["decision_available_utc"], "1970-01-02T00:00:00Z")
        self.assertNotIn("next_open_usdt", state)

    def test_candidate_callback_sees_only_signal_history(self):
        bars = [
            Bar(0, 100, 101, 99, 100, 2),
            Bar(1, 100, 101, 99, 100, 2),
            Bar(2, 100, 105, 100, 105, 4),
            Bar(3, 999, 1000, 998, 999, 3),
            Bar(4, 1000, 1001, 999, 1000, 3),
        ]
        seen = []
        summary, _ = run_paper(
            bars,
            mode="rule",
            starting_usdt=1000,
            allocation_fraction=0.2,
            fee_bps=0,
            penalty_bps=0,
            breakout_bars=2,
            sma_bars=3,
            max_hold_bars=10,
            on_candidate=lambda index, history: seen.append((index, len(history), history[-1].close)),
        )
        self.assertEqual(seen, [(2, 3, 105)])
        self.assertEqual(summary["trades"], 1)


if __name__ == "__main__":
    unittest.main()
