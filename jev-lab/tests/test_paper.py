"""Consequential replay checks: data continuity, next-open fills, and costs."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jev_lab.binance_spot import MarketDataError  # noqa: E402
from jev_lab.paper import Bar, parse_bars, run_paper  # noqa: E402


def replay(bars, *, mode="rule", fee_bps=0, penalty_bps=0):
    return run_paper(
        bars,
        mode=mode,
        starting_usdt=1000,
        allocation_fraction=0.2,
        fee_bps=fee_bps,
        penalty_bps=penalty_bps,
        breakout_bars=2,
        sma_bars=3,
        max_hold_bars=10,
    )


class PaperTests(unittest.TestCase):
    def test_signal_uses_closed_bar_and_fills_next_open(self):
        bars = [
            Bar(0, 100, 101, 99, 100),
            Bar(1, 100, 101, 99, 100),
            Bar(2, 100, 105, 100, 105),  # Breakout known only at this close.
            Bar(3, 110, 112, 109, 111),
            Bar(4, 111, 115, 110, 115),
        ]
        result, trades = replay(bars)
        self.assertEqual(result["trades"], 1)
        self.assertEqual(trades[0]["entry_open_ms"], 3)
        self.assertEqual(trades[0]["entry_price"], 110)
        self.assertEqual(trades[0]["exit_reason"], "terminal_liquidation_at_last_close")

    def test_fee_and_penalty_reduce_net_pnl(self):
        bars = [
            Bar(0, 100, 101, 99, 100),
            Bar(1, 100, 101, 99, 100),
            Bar(2, 100, 105, 100, 105),
            Bar(3, 110, 112, 109, 111),
            Bar(4, 111, 115, 110, 115),
        ]
        free, _ = replay(bars)
        costed, trades = replay(bars, fee_bps=10, penalty_bps=5)
        self.assertLess(costed["net_pnl_usdt"], free["net_pnl_usdt"])
        self.assertGreater(costed["fees_usdt"], 0)
        self.assertAlmostEqual(costed["net_pnl_usdt"], trades[0]["net_pnl_usdt"])

    def test_no_trade_stays_flat(self):
        bars = [Bar(index, 100, 101, 99, 100) for index in range(5)]
        result, trades = replay(bars, mode="no_trade", fee_bps=10, penalty_bps=5)
        self.assertEqual(trades, [])
        self.assertEqual(result["net_pnl_usdt"], 0)

    def test_gap_in_candles_is_rejected(self):
        interval = 30 * 60 * 1000
        first = [0, "100", "101", "99", "100", "1", interval - 1, "100", 1, "1", "100", "0"]
        skipped = [2 * interval, "100", "101", "99", "100", "1", 3 * interval - 1, "100", 1, "1", "100", "0"]
        with self.assertRaises(MarketDataError):
            parse_bars([first, skipped], "30m")


if __name__ == "__main__":
    unittest.main()
