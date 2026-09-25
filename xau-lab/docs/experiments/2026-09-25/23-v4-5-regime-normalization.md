# 23 — V4.5 raw-event regime-normalization foundation

Date: 2026-09-25

Status: **completed diagnostic foundation; schema accepted; no strategy or engine gate promoted**

## Objective

Stop iterating V4.5 by repeatedly repairing quirks observed in the same seven-day XAUUSD development episode. Establish a market-state representation that is causal, calculated from raw tick events before the 500 ms / 1 s execution grids, and mostly expressed in relative terms so future engine admission can adapt to changing volatility, spread and activity.

This experiment changes no trading rule. It does not optimize a router, disable an engine, promote Candidate D, change canonical replay semantics, or inspect the final 20% holdout.

## Data and parity discipline

Source: canonical seven-day XAUUSD raw dataset.

- raw SHA-256: `007e7ab10cc16519b544003dbe81521f46cf868bf267780932638d1e8cec86e5`
- rows read: first 1,869,979 only
- raw boundaries: `[0, 934989, 1168737, 1402484, 1636231, 1869979]`
- final 20%: **not read**
- execution grids: 500 ms and 1 s

Before accepting the diagnostic:

1. locked V4.4 reproduced the golden oracle on both grids;
2. Candidate B reproduced canonical comparator values and trace parity;
3. provisional Candidate D reproduced Experiment 19 first-80% results.

| Candidate D parity | 500 ms | 1 s |
| --- | ---: | ---: |
| Compounded P&L | +₹1,430.31 | +₹385.25 |
| Trades | 163 | 156 |
| Wins | 81 | 71 |

## Frozen raw-event state

At each Candidate D entry, regime state is recovered from the underlying raw ticks at or before that timestamp. The diagnostic includes:

- relative 60 s raw range;
- relative raw spread;
- relative signed 60 s and 300 s momentum;
- relative 10 s raw-event activity;
- raw 60 s path efficiency;
- raw 10 s directional tick imbalance.

References are built only from completed, lagged buckets:

- spread/range/60 s move: rolling median of the prior 30 one-minute buckets, minimum 10;
- 300 s move: rolling median of the prior 24 five-minute absolute moves, minimum 8;
- activity: rolling median of the prior 180 ten-second event counts, minimum 60.

Fixed structural bins:

| State | First | Middle | Third |
| --- | ---: | ---: | ---: |
| relative 60 s range | low <0.75 | normal 0.75–1.50 | high >1.50 |
| relative spread | tight <0.75 | normal 0.75–1.25 | wide >1.25 |
| raw ER60 | choppy <0.10 | mixed 0.10–0.25 | efficient >0.25 |
| relative activity | slow <0.75 | normal 0.75–1.50 | fast >1.50 |

The bin edges were not selected using trade P&L.

## Cross-grid stability

Trades were matched one-to-one when they shared segment, engine and side and their entries were within 120 seconds. There were 119 matched pairs.

| Component | Exact category agreement |
| --- | ---: |
| volatility | **92.44%** (110/119) |
| spread | **89.92%** (107/119) |
| efficiency | **92.44%** (110/119) |
| activity | **95.80%** (114/119) |
| complete four-part key | **76.47%** (91/119) |

The common raw-event state is substantially less tied to execution-grid sampling than independently deriving regime state after sampling. This does not prove profitability out of sample.

## Four-hour engine robustness

| Grid | Engine | Trades | Total P&L | PF | Positive / negative 4h windows | Median 4h P&L |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | BURST | 17 | +₹100.85 | 8.210 | 9 / 2 | +₹3.00 |
| 500 ms | MICRO | 42 | +₹197.69 | 2.006 | 10 / 6 | +₹12.94 |
| 500 ms | PRIMARY | 74 | +₹586.30 | 1.838 | 10 / 10 | -₹3.06 |
| 500 ms | SECONDARY | 30 | +₹89.67 | 1.265 | 6 / 8 | -₹8.33 |
| 1 s | BURST | 12 | +₹22.04 | 2.447 | 6 / 4 | +₹1.83 |
| 1 s | MICRO | 33 | +₹198.36 | 2.672 | 10 / 5 | +₹11.14 |
| 1 s | PRIMARY | 69 | +₹156.00 | 1.251 | 9 / 9 | -₹0.76 |
| 1 s | SECONDARY | 42 | **-₹51.80** | 0.892 | 7 / 9 | -₹11.66 |

PRIMARY's positive historical aggregate is concentrated enough that its median four-hour result is negative on both grids. SECONDARY is even less stable and loses in aggregate at 1 s. BURST and MICRO are more consistently positive in this historical episode.

These observations **must not** be converted directly into an on/off permission matrix using the same dataset. That would repeat the adaptive-overfitting problem this experiment is intended to address.

## Decision

Accept `xau-raw-event-regime-v1` as a diagnostic representation only.

Next:

1. replay the exact frozen schema unchanged on the already non-overlapping Experiment 22 snapshot;
2. add additional non-overlapping snapshots as they become available;
3. compare engine expectancy and failure modes across windows/regimes;
4. only then design and freeze a deterministic regime router for chronological evaluation.

JEV/ML may later be tested as a meta-labeler, but it is not part of Experiment 23 and no work belongs in the separate `jev-lab` project for this XAU research line.

## Evidence

- `scripts/v4_5_regime_normalization.py`
- `results/simulations/2026-09-25-v4_5-regime-normalization/README.md`
- `results/simulations/2026-09-25-v4_5-regime-normalization/run_config.json`
- `results/simulations/2026-09-25-v4_5-regime-normalization/summary.json`
- `results/simulations/2026-09-25-v4_5-regime-normalization/engine_robustness_4h.csv`
- `results/simulations/2026-09-25-v4_5-regime-normalization/regime_dimension_summary.csv`

The local diagnostic also generated detailed per-trade overlays and one-to-one match ledgers. The compact committed bundle records the canonical aggregate result; the script reproduces detailed ledgers from the hash-verified raw dataset.
