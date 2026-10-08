#!/usr/bin/env python3
"""Smoke-test the harness on SYNTHETIC data + run calibration baselines.

READ THIS BEFORE QUOTING ANY NUMBER BELOW:
  * The tick data is synthetic GBM. It contains zero market information.
  * The smoke tests assert ACCOUNTING correctness (fills, costs, no-look-ahead).
  * Baseline P&L on synthetic data is MEANINGLESS as strategy evidence.
    It is reported only to show the harness runs end-to-end.

Usage:
  python research/run_baselines.py [--ticks 100000] [--account 25000]
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "research"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from harness import Harness, HarnessConfig, Tick
from baselines import HoldAndClose, NeverTrade, MACrossover, SimpleGrid
from synth_ticks import gen_ticks
from mcx_cost_model import order_cost


def smoke_accounting(ticks, cfg, account):
    """Buy 1 lot at tick 0, close at tick K on FLAT prices with a Rs 2 spread.

    Flat prices => the round trip must lose EXACTLY the spread (buy@ask,
    sell@bid) plus the two order costs. This asserts spread accounting too.
    """
    flat = [Tick(ts=t.ts, bid=15125.0, ask=15127.0) for t in ticks[:2000]]
    h = Harness(flat, cfg, account, HoldAndClose(exit_at=1000))
    r = h.run()
    spread_loss = 2.0  # ask - bid, 1 lot
    expected_cost = (order_cost(cfg.grams_per_lot * cfg.gold_inr_per_gram, "buy")["total"]
                     + order_cost(cfg.grams_per_lot * cfg.gold_inr_per_gram, "sell")["total"])
    assert abs(r.gross_pnl + spread_loss) < 1e-9, \
        f"gross {r.gross_pnl} != -spread {spread_loss}"
    assert abs(r.total_costs - expected_cost) < 1e-9, \
        f"costs {r.total_costs} != expected {expected_cost}"
    assert abs(r.net_pnl + spread_loss + expected_cost) < 1e-9
    print(f"[PASS] accounting: flat-price round trip gross Rs {r.gross_pnl:.2f} "
          f"(= -spread), costs Rs {r.total_costs:.2f}, net Rs {r.net_pnl:.2f}")


def smoke_no_lookahead(ticks, cfg, account):
    """Every buy must fill at the ASK of tick t+1, every sell at the BID of t+1."""
    h = Harness(ticks[:5000], cfg, account, HoldAndClose(exit_at=2500))
    r = h.run()
    assert len(r.fills) == 2, f"expected 2 fills, got {len(r.fills)}"
    buy, sell = r.fills
    assert buy.side == "buy" and abs(buy.price - ticks[buy.tick_idx].ask) < 1e-9
    assert sell.side == "sell" and abs(sell.price - ticks[sell.tick_idx].bid) < 1e-9
    # signal computed at tick 0 must execute at tick 1 (not tick 0):
    assert buy.tick_idx == 1, f"buy executed at {buy.tick_idx}, want 1 (t+1 rule)"
    print(f"[PASS] no-look-ahead: buy@{buy.price:.2f} (ask@t+1), "
          f"sell@{sell.price:.2f} (bid@t+1)")


def smoke_never_trade(ticks, cfg, account):
    h = Harness(ticks[:5000], cfg, account, NeverTrade())
    r = h.run()
    assert r.net_pnl == 0.0 and r.total_costs == 0.0 and r.trades == 0
    print("[PASS] never-trade: net 0.00, costs 0.00, 0 trades")


def run_baseline(name, ticks, cfg, account, strategy):
    h = Harness(ticks, cfg, account, strategy)
    r = h.run()
    print(f"  {name:<14} net Rs {r.net_pnl:>9.2f} | gross Rs {r.gross_pnl:>9.2f} | "
          f"costs Rs {r.total_costs:>8.2f} | trades {r.trades:>4} | "
          f"win% {r.win_rate*100:>5.1f} | PF {r.profit_factor:>6.2f} | "
          f"exp/trade Rs {r.expectancy_per_trade:>7.2f} | maxDD Rs {r.max_drawdown:>8.2f} | "
          f"cost ratio {r.cost_ratio:>5.2f}")
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticks", type=int, default=100_000)
    ap.add_argument("--account", type=float, default=25_000.0)
    a = ap.parse_args()

    print("=" * 78)
    print("MCX-GOLD-LAB  HARNESS SMOKE TEST  —  *** SYNTHETIC DATA ***")
    print("Numbers below validate accounting ONLY. They are not strategy evidence.")
    print("=" * 78)

    ticks = gen_ticks(a.ticks, seed=7)
    cfg = HarnessConfig()  # GOLDPETAL 1 g defaults

    smoke_accounting(ticks, cfg, a.account)
    smoke_no_lookahead(ticks, cfg, a.account)
    smoke_never_trade(ticks, cfg, a.account)

    print("\nCalibration baselines on synthetic GBM (meaningless as edge evidence):")
    run_baseline("ma_cross", ticks, cfg, a.account, MACrossover())
    run_baseline("grid_proto", ticks, cfg, a.account, SimpleGrid())
    print("\nDone. Next: real MCX tick capture (tools/capture_ticks.py) before any")
    print("strategy conclusion may be drawn.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
