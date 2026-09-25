# 39 — V4.5 Decision Policy v2: signal episodes + short-horizon exit

Date: 2026-09-25

Status: **architecture frozen; diagnostic pending; no Candidate F**

## Objective

Fix the representation/target failures found in Experiment 38 without tuning its thresholds or model hyperparameters.

The frozen specification is:

`docs/plans/V4_5_DECISION_POLICY_V2.md`

## Frozen changes versus v1

Entry:

- model complete cooldown-free legacy signal episodes;
- checkpoint every 2 seconds while eligibility persists;
- learn TAKE NOW / WAIT / SKIP timing;
- weight each episode equally.

Exit:

- add causal trajectory-change features;
- predict incremental value over the next 30 seconds rather than all the way to the legacy exit;
- require two consecutive non-positive predictions before model exit;
- weight each trade equally.

Comparator:

- once MFE reaches +1R, test a fixed 50%-of-MFE profit-retention ratchet at the same 5-second checkpoints.

The HistGradientBoostingRegressor architecture remains exactly the Experiment-38 architecture.

## Data discipline

- historical canonical first80 only;
- expanding chronological segment walk-forward;
- recent24h only as later transfer;
- final20 sealed;
- known data cannot promote a strategy.

## Decision

No Candidate F is created unless this experiment shows coherent OOS behavior sufficient to justify a separately frozen full shared-slot replay.

## Evidence

- implementation: `research/v4_5_decision_policy_v2.py`
- results: `results/simulations/2026-09-25-v4_5-decision-policy-v2/`
