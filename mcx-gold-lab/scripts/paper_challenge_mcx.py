#!/usr/bin/env python3
"""Paper-challenge executor for mcx-gold-lab — PAPER ONLY BY CONSTRUCTION.

Runs a FROZEN strategy module against a tick archive through research/harness.py
with full MCX cost accounting. Writes a ledger JSON to results/paper/.

HARD RULES:
  * No broker/order-placement imports are allowed in this directory. Ever.
  * The strategy module must be frozen (git hash recorded in the ledger).
  * Paper fills at bid/ask; costs on every fill; margin + circuits enforced.
  * A paper challenge that "works" is evidence of plumbing, not edge.

Usage:
  python scripts/paper_challenge_mcx.py <ticks.csv.gz> <strategy_module> [--account 25000]
"""

import argparse
import gzip
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "research"))
from harness import Harness, HarnessConfig, Tick


def load_ticks(path: str) -> list[Tick]:
    ticks = []
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as f:
        for row in csv.DictReader(f):
            ticks.append(Tick(ts=int(row["ts"]), bid=float(row["bid"]),
                              ask=float(row["ask"])))
    return ticks


def git_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticks")
    ap.add_argument("strategy_module")
    ap.add_argument("--account", type=float, default=25000.0)
    a = ap.parse_args()

    if "SYNTHETIC" in os.path.basename(a.ticks).upper():
        print("WARNING: running on SYNTHETIC data — plumbing check only.")

    ticks = load_ticks(a.ticks)
    mod = __import__(a.strategy_module)
    strategy = mod.STRATEGY  # frozen strategy modules expose STRATEGY instance

    h = Harness(ticks, HarnessConfig(), a.account, strategy)
    r = h.run()

    ledger = dict(
        timestamp=datetime.now(timezone.utc).isoformat(),
        git_hash=git_hash(),
        ticks_path=a.ticks,
        n_ticks=len(ticks),
        strategy_module=a.strategy_module,
        account_rs=a.account,
        net_pnl=round(r.net_pnl, 2),
        gross_pnl=round(r.gross_pnl, 2),
        total_costs=round(r.total_costs, 2),
        trades=r.trades,
        win_rate=round(r.win_rate, 4),
        profit_factor=r.profit_factor,
        expectancy_per_trade=round(r.expectancy_per_trade, 2),
        max_drawdown=round(r.max_drawdown, 2),
        cost_ratio=r.cost_ratio,
    )
    os.makedirs("results/paper", exist_ok=True)
    out = f"results/paper/{a.strategy_module}_{ledger['timestamp'][:10]}.json"
    with open(out, "w") as f:
        json.dump(ledger, f, indent=2)
    print(json.dumps(ledger, indent=2))
    print(f"\nledger -> {out}")
    print("Paper evidence only. Not a claim of profitability.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
