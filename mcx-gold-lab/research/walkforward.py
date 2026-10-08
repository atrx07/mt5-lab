"""Walk-forward validation for mcx-gold-lab.

The anti-overfitting gate. Splits a bar series into rolling train/test windows:
optimize (or freeze) on train, evaluate ONCE on the following test window, roll
forward. Reports aggregate out-of-sample metrics and IS->OOS degradation.

Rules:
  * Test windows are NEVER used for any decision (parameter choice, candidate
    selection, early stopping). One evaluation per window, recorded.
  * Degradation = 1 - (OOS metric / IS metric). Sharpe degradation > 30% or
    profit-factor collapse across windows = overfit warning. Do not promote.
  * A strategy factory takes (train_bars) and returns a frozen strategy for
    the test window. For fixed-parameter baselines the factory ignores train.

Usage:
  from walkforward import walk_forward
  res = walk_forward(bars, make_strategy, train=250, test=60, step=60)
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daily_harness import DailyHarness, DailyConfig


def _sharpe(equity: list[float]) -> float:
    rets = []
    for a, b in zip(equity, equity[1:]):
        if a > 0:
            rets.append((b - a) / a)
    if len(rets) < 2:
        return 0.0
    mu = sum(rets) / len(rets)
    var = sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)
    return (mu / math.sqrt(var) * math.sqrt(252)) if var > 0 else 0.0


def walk_forward(bars, make_strategy, train: int, test: int, step: int,
                 config: DailyConfig | None = None,
                 account_rs: float = 25000.0) -> dict:
    """Rolling train/test evaluation. Returns per-window + aggregate metrics."""
    config = config or DailyConfig()
    windows = []
    start = 0
    while start + train + test <= len(bars):
        train_bars = bars[start:start + train]
        test_bars = bars[start + train:start + train + test]
        strategy = make_strategy(train_bars)   # frozen for this window
        r = DailyHarness(test_bars, config, account_rs, strategy).run()
        # in-sample reference: same frozen strategy on train (diagnostic only)
        r_is = DailyHarness(train_bars, config, account_rs,
                            make_strategy(train_bars)).run()
        windows.append(dict(
            test_from=test_bars[0].date, test_to=test_bars[-1].date,
            is_net=r_is.net_pnl, is_pf=r_is.profit_factor,
            is_sharpe=_sharpe(r_is.equity_curve),
            oos_net=r.net_pnl, oos_pf=r.profit_factor,
            oos_sharpe=_sharpe(r.equity_curve),
            oos_trades=r.trades, oos_maxdd=r.max_drawdown,
            oos_cost_ratio=r.cost_ratio,
        ))
        start += step

    agg = {}
    if windows:
        oos_nets = [w["oos_net"] for w in windows]
        agg = dict(
            n_windows=len(windows),
            total_oos_net=round(sum(oos_nets), 2),
            mean_oos_net=round(sum(oos_nets) / len(oos_nets), 2),
            positive_windows=sum(1 for x in oos_nets if x > 0),
            mean_oos_pf=round(sum(w["oos_pf"] for w in windows
                                  if w["oos_pf"] != float("inf")) / len(windows), 3),
            mean_oos_sharpe=round(sum(w["oos_sharpe"] for w in windows) / len(windows), 3),
        )
        # degradation: 1 - mean(OOS Sharpe)/mean(IS Sharpe), guarded
        is_s = sum(w["is_sharpe"] for w in windows) / len(windows)
        oos_s = agg["mean_oos_sharpe"]
        agg["sharpe_degradation"] = round(1 - oos_s / is_s, 3) if is_s > 0.05 else None
        agg["overfit_warning"] = bool(
            agg["sharpe_degradation"] is not None and agg["sharpe_degradation"] > 0.30)
    return dict(windows=windows, aggregate=agg)


def render(res: dict) -> str:
    L = ["WALK-FORWARD RESULT", "-" * 60]
    for w in res["windows"]:
        L.append(f"  {w['test_from']}..{w['test_to']}: OOS net Rs {w['oos_net']:>9.2f} "
                 f"PF {w['oos_pf']:>6.2f} Sharpe {w['oos_sharpe']:>6.2f} "
                 f"trades {w['oos_trades']:>3} (IS Sharpe {w['is_sharpe']:>6.2f})")
    a = res["aggregate"]
    L.append("-" * 60)
    L.append(f"  windows={a.get('n_windows')} total_OOS=Rs {a.get('total_oos_net')} "
             f"positive={a.get('positive_windows')}/{a.get('n_windows')}")
    L.append(f"  mean OOS Sharpe={a.get('mean_oos_sharpe')} "
             f"degradation={a.get('sharpe_degradation')}")
    if a.get("overfit_warning"):
        L.append("  *** OVERFIT WARNING: IS->OOS Sharpe degradation > 30%. DO NOT PROMOTE. ***")
    return "\n".join(L)
