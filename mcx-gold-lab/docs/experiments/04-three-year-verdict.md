# Experiment 04 — Three Years of Data: The Daily-Bar Verdict

**Date:** 2026-10-08 · **Status:** COMPLETE ·
**Verdict: NO DAILY-BAR ALPHA. Track closed as an alpha search.**

## 1. What changed

Extended the dataset to 3 years (2023-10-09 → 2026-10-06, 772 bars,
25–27 rolls) via the free bhavcopy pull. Re-ran everything with 12
walk-forward windows (train 150d / test 50d) instead of 2.

## 2. Results (GOLDPETAL, 1 lot, real MCX bhavcopy)

| Strategy | WF total OOS | Positive | Mean OOS Sharpe | Degradation |
|---|---|---|---|---|
| Ungated Donchian(20) | +Rs 6,903 | 8/12 | 1.97 | none (−0.13) |
| Gated Donchian (Exp 03) | +Rs 4,228 | 7/12 | 1.49 | 0.17 |
| TrendMA(10,30) | +Rs 3,204 | 9/12 | 1.82 | 0.08 |
| Buy-and-hold | +Rs 9,383 | — | — | — |

Full-sample risk comparison (3y):

| | Net | MaxDD | DD / Return |
|---|---|---|---|
| Buy-and-hold | +Rs 9,383 | Rs 5,272 | 0.56 |
| Donchian(20), 37 trades | +Rs 7,661 | Rs 4,410 | 0.58 |

## 3. Reading — why this closes the track

Donchian captured **82% of buy-and-hold's return with 84% of its drawdown**.
Risk-adjusted, it is a slightly *worse* buy-and-hold. That is not alpha;
that is beta-harvesting with extra steps and extra trades.

The 3-year window is a +162% historic bull run — the single most favorable
possible regime for trend-following, and it still couldn't beat passive.
There is no bear-market data in the sample, which is exactly when
trend systems earn their keep, but nothing here suggests they'd do better
than holding through it.

The Exp 03 falsification held over 3 years too (gated still worse):
the regime-filter idea is dead, not under-tested.

## 4. What the daily track proved (its actual value)

- The full pipeline works on real multi-year data: fetch → curate →
  continuous → harness → walk-forward, all reproducible (Exp 04's continuous
  series regenerates byte-identical from the curated CSV).
- Costs are negligible at daily holding periods (the fee schedule was never
  the binding constraint — confirmed empirically, not just modeled).
- **Where not to look:** daily-bar trend/breakout variants. Running 20 more
  parameter variants until one backtests well would be the exact sin this
  lab was built to prevent. Track closed.

## 5. Where the alpha search goes now

The remaining questions are intraday and invisible at daily resolution:
does any edge exist *inside* the day, net of the Rs 2–3 spread on Rs 1
ticks? That needs tick capture — blocked on the broker API decision.
Nothing further can be honestly learned about edge from daily bars.
