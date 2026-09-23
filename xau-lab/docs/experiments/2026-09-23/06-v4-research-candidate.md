# V4 research candidate — 2026-09-23

## Design direction

- maximum entry spread: USD 0.28;
- wait for a directional impulse;
- wait for a pullback instead of buying/selling the most stretched point;
- enter only after directional resumption;
- refuse a new trade in the same impulse until the market resets;
- hard stop around ₹8 on a ₹500 synthetic account;
- profit protection begins around ₹4;
- retain roughly 65% of peak paper profit once lock activates;
- ~45 s cooldown;
- ~60 s max hold;
- local deterministic exits remain authoritative.

The implementation is in [`scripts/paper_challenge_v4.py`](../../../scripts/paper_challenge_v4.py).

## What V4 is *not*

It is not declared profitable, production-ready, or suitable for real money.

The next meaningful validation step is multi-day broker tick replay with walk-forward / untouched holdout windows.

## Related algorithm

[V4 algorithm](../../algorithms/v4.md)
