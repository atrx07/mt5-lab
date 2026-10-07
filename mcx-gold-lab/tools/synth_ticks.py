#!/usr/bin/env python3
"""Synthetic tick generator — HARNESS VALIDATION ONLY.

These ticks carry NO information about any real market. They exist so the
harness's accounting (fills, costs, no-look-ahead, margin, circuits) can be
unit-tested deterministically. NEVER report a strategy's P&L on synthetic
data as evidence of anything except "the harness runs".

Model: geometric Brownian motion on mid-price + fixed bid/ask spread.
Calibrated loosely to gold: ~1.2% daily realized vol, Rs 2/g spread.
"""

import math
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "research"))
from harness import Tick


def gen_ticks(n: int, start_price: float = 12000.0, spread: float = 2.0,
              daily_vol: float = 0.012, ticks_per_day: int = 55800,
              seed: int = 7, drift: float = 0.0) -> list[Tick]:
    """Generate n synthetic ticks, 1 tick/sec across a ~15.5h MCX session."""
    rng = random.Random(seed)
    per_tick_vol = daily_vol / math.sqrt(ticks_per_day)
    price = start_price
    out = []
    for i in range(n):
        shock = rng.gauss(drift / ticks_per_day, per_tick_vol)
        price *= math.exp(shock)
        half = spread / 2.0
        out.append(Tick(ts=i, bid=round(price - half, 2), ask=round(price + half, 2)))
    return out


def main() -> int:
    import pickle
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    ticks = gen_ticks(n)
    os.makedirs("data/raw", exist_ok=True)
    with open("data/raw/SYNTHETIC_ticks_100k.pkl", "wb") as f:
        pickle.dump(ticks, f)
    print(f"wrote {len(ticks)} SYNTHETIC ticks -> data/raw/SYNTHETIC_ticks_100k.pkl")
    print("WARNING: synthetic. Harness validation only. Not market evidence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
