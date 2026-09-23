# 07 — Seven-day development baseline comparison

Dataset: `xau_ticks_7d.csv`  
SHA-256: `007e7ab10cc16519b544003dbe81521f46cf868bf267780932638d1e8cec86e5`

## Scope

This stage compares **current V3.1** against **current V4** before applying any V4.1 changes.

The 2,337,474-row broker export was split chronologically by raw tick count:

- development 60%: 1,402,484 rows, 2026-09-16 14:56:19.104 UTC → 2026-09-21 15:07:52.366 UTC;
- validation 20%: 467,495 rows — not evaluated;
- holdout 20%: 467,495 rows — not evaluated.

Development was replayed at the live bot's 500 ms cadence by taking the last usable quote in each bucket, producing 382,530 observations. BUY fills use ask and exits use bid; SELL fills use bid and exits use ask. No extra slippage or commission was injected beyond the observed broker spread.

> Holdout caveat: the final partition overlaps the already-observed Sep 23 live-paper session, so that known-live interval must be excluded or explicitly marked contaminated before claiming a blind final holdout.

## Continuous ₹500 development replay

| Metric | V3.1 | V4 |
| --- | ---: | ---: |
| Final balance | **₹0.0023** | **₹9.78** |
| Net P&L | -₹500.00 | -₹490.22 |
| Return | -100.00% | -98.04% |
| Trades | 1,661 | 594 |
| Win rate | 25.59% | 26.60% |
| Profit factor | 0.372 | 0.359 |
| Max drawdown | ₹500.00 | ₹494.02 |
| Max losing streak | 20 | 19 |
| Median entry spread | $0.27 | $0.25 |
| Median hold | 14.0 s | 9.0 s |
| Maximum equity reached | ₹500.00 | ₹503.80 |

Neither baseline reached the ₹550 challenge target.

V4 survives longer because it takes far fewer trades, but this run does **not** show a positive edge for V4.

## Independent UTC-day reset diagnostic

Each development trading date was also replayed from a fresh ₹500 balance to stop the first bad day from shrinking later position sizes into irrelevance.

| Date | V3.1 final | V3.1 trades | V4 final | V4 trades |
| --- | ---: | ---: | ---: | ---: |
| 2026-09-16 | ₹34.27 | 322 | ₹208.41 | 111 |
| 2026-09-17 | ₹10.24 | 604 | ₹125.76 | 246 |
| 2026-09-18 | ₹12.74 | 534 | ₹125.30 | 184 |
| 2026-09-21 | ₹94.76 | 204 | ₹360.63 | 54 |

Both strategies were negative on every development trading date.

Across these daily-reset runs:

| Metric | V3.1 | V4 |
| --- | ---: | ---: |
| Trades | 1,664 | 595 |
| Win rate | 25.72% | 28.24% |
| Profit factor | **0.440** | **0.349** |
| Avg win | ₹3.39 | ₹3.77 |
| Avg loss | -₹2.68 | **-₹4.27** |
| Avg trade | -₹1.11 | **-₹1.98** |
| Median MFE | ₹0.18 | ₹0.52 |
| Median MAE | -₹1.64 | **-₹3.46** |

This is the important comparison: V4's lower trade frequency slows the account bleed, but its per-trade development statistics are not better than V3.1.

## Exit behavior

### V3.1

- confirmed reversal: 1,618 trades, -₹1,991.01 aggregate, -₹1.23 average;
- profit lock: 40 trades, +₹160.47 aggregate, +₹4.01 average;
- hard stop: 1 trade, -₹25.60;
- max hold / end-of-data were rare.

### V4

- confirmed reversal: 414 trades, **-₹959.80 aggregate**, -₹2.32 average, only 12.8% positive;
- profit lock: 111 trades, **+₹347.69 aggregate**, +₹3.13 average, 99.1% positive;
- hard stop: 63 trades, **-₹580.85 aggregate**, -₹9.22 average;
- max hold: 7 trades, +₹13.06 aggregate.

The nominal ₹8 V4 hard stop realizes roughly ₹9.22 average when triggered because the 500 ms sampled market can jump through the threshold before the next observation.

## Main finding

**V4 is not yet a successful successor to V3.1.**

Its account curve is less catastrophic mainly because it trades about 64% less often. The pullback/resumption entry is producing somewhat larger favorable excursions, but it is also producing much deeper adverse excursions and a lower profit factor.

This baseline supports the planned V4.1 work, especially:

- regime and chop filtering;
- cost relative to expected movement instead of spread alone;
- pullback normalized by impulse size;
- MFE/MAE-driven exit work;
- risk-based sizing.

These must now be tested individually on development data rather than bundled together.

## Replay anomaly discovered

One V3.1 position crossed the Friday-to-Monday closure and was not processed until the market produced another executable tick, giving a hold time around 180,001.5 seconds. Its P&L impact in this compounded run was negligible because the synthetic account was already nearly depleted, but **session-boundary handling must become explicit** in the replay/live-paper rules.

## Evidence

Machine-readable outputs are under:

[`results/simulations/2026-09-23-development-baseline/`](../../../results/simulations/2026-09-23-development-baseline/)

The raw seven-day tick file is intentionally not committed because of its size; the dataset hash and split boundaries are preserved in `split_manifest.json`.
