# 25 — V4.5 cross-window engine robustness baseline

Date: 2026-09-25

Status: **completed no-tuning diagnostic; no router or candidate promoted**

## Objective

Measure how each Candidate D engine behaves when the market window changes before another router search. No trading rule, threshold, parameter or engine priority is changed.

The comparison uses the canonical seven-day first-80% engine summary from Experiment 23 and the separate Experiment 22 recent 24-hour Candidate D seed/evaluation ledgers.

## Accounting caveat

Experiment 22's inherited single-slot simulator records realized trades and may leave an open position at split boundaries. Recent P&L below is descriptive engine attribution, not terminal-equity full-window return.

## Results

| Grid | Engine | Historical trades/wins | Historical P&L | Recent split trades/wins | Recent realized P&L |
| --- | --- | ---: | ---: | ---: | ---: |
| 500 ms | PRIMARY | 74 / 35 | +₹586.30 | 24 / 4 | **-₹184.37** |
| 500 ms | SECONDARY | 30 / 13 | +₹89.67 | 5 / 1 | **-₹27.96** |
| 500 ms | MICRO | 42 / 20 | +₹197.69 | 5 / 0 | **-₹20.71** |
| 500 ms | BURST | 17 / 13 | +₹100.85 | 4 / 0 | **-₹9.36** |
| 1 s | PRIMARY | 69 / 27 | +₹156.00 | 20 / 5 | **-₹118.65** |
| 1 s | SECONDARY | 42 / 16 | -₹51.80 | 7 / 3 | +₹0.93 |
| 1 s | MICRO | 33 / 20 | +₹198.36 | 3 / 0 | **-₹12.28** |
| 1 s | BURST | 12 / 8 | +₹22.04 | 3 / 0 | **-₹8.86** |

PRIMARY's fresh failure is supported by 20–24 recent trades and occurs in both recent splits and both grids. MICRO and BURST have too few recent trades for a global conclusion. SECONDARY remains unstable across grids and windows.

## Decision

No engine receives a global allow/deny rule. The next router must condition on market state using the frozen `xau-raw-event-regime-v1` representation and evidence from independent windows.

Future router evaluation must track trade-count/opportunity retention explicitly so robustness is not achieved merely by suppressing most trades, and must allow HOLD/no-trade where no engine has demonstrated positive cross-window expectancy.

Do not use this comparison to tune another fixed threshold on the seven-day history.

## Evidence

- historical source: `results/simulations/2026-09-25-v4_5-regime-normalization/engine_robustness_4h.csv`
- recent source: `results/simulations/2026-09-24-recent-micro-long-validation/candidate_d_*_trades.csv`
- script: `research/v4_5_cross_window_engine_robustness.py`
- result bundle: `results/simulations/2026-09-25-v4_5-cross-window-engine-robustness/`
