# 26 — V4.5 frozen regime portability on recent raw data

Date: 2026-09-25

Status: **completed no-tuning portability diagnostic; no router or candidate promoted**

## Objective

Apply the exact frozen `xau-raw-event-regime-v1` representation from Experiment 23 to Experiment 22's separate recent 24-hour raw MT5 snapshot without changing a threshold, engine rule, strategy parameter or accounting rule.

The test asks two separate questions:

1. does the raw-event representation describe the recent market consistently across 500 ms and 1 s sampling; and
2. do historical engine+regime profitability labels transfer to the recent window strongly enough to justify a router?

## Dataset verification

Recent archive:

- gzip bytes: 5,603,455
- gzip SHA-256: `2d3c963f678aa0341224efe5f6859651018e11a43c8c5797bb5685f8dce19aeb`
- decompressed bytes: 44,977,021
- decompressed SHA-256: `9243ac73c3d180417ff634fe9371a28939713a531c9ccfa63f919c94eb9a28b1`
- rows: 476,535

Both hashes match the committed Experiment 22 manifest.

The MT5 timestamp caveat from Experiment 22 remains: the reported tick clock was roughly three hours ahead of host UTC. No clock correction was introduced here.

## Frozen state replay

The Experiment 23 formulas and bins were reused unchanged:

- relative 60 s raw range;
- relative spread;
- raw 60 s path efficiency;
- relative 10 s raw activity;
- continuous normalized 60 s / 300 s momentum and raw imbalance diagnostics;
- category boundaries 0.75 / 1.50 for range and activity, 0.75 / 1.25 for spread, and 0.10 / 0.25 for ER60.

Candidate D recent traces were regenerated from the raw snapshot using the existing Experiment 22 60/40 seed/evaluation cut. Regenerated trade counts and per-engine P&L matched the preserved Experiment 22 ledgers.

## Recent cross-grid state agreement

27 trades matched one-to-one by split, engine, side and entry time within 120 seconds.

| State component | Exact agreement |
| --- | ---: |
| volatility | **92.59%** |
| spread | **92.59%** |
| efficiency | **96.30%** |
| activity | **100.00%** |
| complete four-part key | **85.19%** |

This is at least as encouraging as Experiment 23's historical cross-grid stability. The representation itself is not the problem.

## Historical stronghold portability

For each recent trade, the exact historical Candidate D `grid + engine + four-part regime key` was looked up from the canonical Experiment 23 history. No threshold was selected from the recent data.

| Grid | Historical key class | Recent trades | Wins | Recent realized P&L | Win rate |
| --- | --- | ---: | ---: | ---: | ---: |
| 500 ms | historically positive | 23 | 4 | **-₹90.74** | 17.39% |
| 500 ms | historically non-positive | 14 | 1 | **-₹145.21** | 7.14% |
| 500 ms | unseen | 1 | 0 | -₹6.45 | 0% |
| 1 s | historically positive | 21 | 4 | **-₹123.88** | 19.05% |
| 1 s | historically non-positive | 10 | 4 | +₹4.74 | 40.00% |
| 1 s | unseen | 2 | 0 | -₹19.71 | 0% |

Therefore the four-part regime key is **not** a portable profitability permission table. A state can have the same coarse label across windows while the conditional expectancy changes materially.

## PRIMARY failure anatomy

PRIMARY remains the largest recent loss source, but its successful outcome class did not disappear.

| Window | Grid | Exit | Trades | Wins | P&L |
| --- | --- | --- | ---: | ---: | ---: |
| recent 24h | 500 ms | emergency stop | 13 | 0 | **-₹172.84** |
| recent 24h | 500 ms | momentum zero-cross | 7 | 0 | **-₹51.34** |
| recent 24h | 500 ms | max hold | 4 | 4 | **+₹39.82** |
| recent 24h | 1 s | emergency stop | 9 | 0 | **-₹129.78** |
| recent 24h | 1 s | momentum zero-cross | 6 | 0 | **-₹39.24** |
| recent 24h | 1 s | max hold | 5 | 5 | **+₹50.37** |

Historically, PRIMARY max-hold and take-profit outcomes were also the profitable outcome classes. The recent degradation is therefore primarily an admission/exhaustion problem: many more admitted trades terminate as stop or zero-cross failures before the trend opportunity can mature.

A descriptive continuous-state check found recent PRIMARY max-hold entries had substantially lower median `range60_rel × activity_rel` than recent stop/zero-cross entries on both grids:

- 500 ms: max-hold 1.159 vs stop 1.698 vs zero-cross 1.772;
- 1 s: max-hold 1.168 vs stop 1.807 vs zero-cross 1.893.

This is a **feature-design clue only**, not a threshold. The current recent window has already been observed and must not be used to tune a gate that is then called out-of-sample.

## Decision

Keep `xau-raw-event-regime-v1` as a stable descriptive layer, but reject the idea that the four categorical dimensions alone define engine strongholds.

No engine is globally disabled and no router is promoted.

Next:

1. define a richer causal state representation using continuous direction-normalized momentum/exhaustion and market-heat diagnostics;
2. freeze formulas before seeing the next snapshot;
3. preserve HOLD/no-trade as a valid router output;
4. require opportunity/trade retention as an objective so robustness cannot come only from suppressing trades;
5. validate the frozen representation on a new non-overlapping window before selecting another router family.

## Evidence

- script: `research/v4_5_regime_portability.py`
- result bundle: `results/simulations/2026-09-25-v4_5-regime-portability/`
