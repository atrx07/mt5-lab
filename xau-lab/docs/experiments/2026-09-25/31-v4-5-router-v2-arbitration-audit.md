# 31 — V4.5 Router v2 arbitration divergence audit

Date: 2026-09-25

Status: **in progress — diagnostic harness frozen; known-data execution pending**

## Objective

Explain **where the Experiment-30 Router v2 expectancy loss comes from** before proposing any new score, threshold or routing rule.

Experiment 30 showed that the router preserved the canonical trade count while losing approximately ₹579 at 500 ms and ₹88 at 1 s versus Candidate D. Therefore the first question is not "which threshold should move?" It is "which arbitration decisions displaced high-value Candidate D opportunities, and by what mechanism?"

## Allowed work

Diagnostic instrumentation only:

- run Candidate D and frozen Router v2 side-by-side on the same sampled ticks;
- record every flat-state candidate set and divergence;
- classify direct score substitutions, Router HOLDs, cooldown-history divergences and slot-occupancy cascades;
- preserve engine, side, timestamp, Router score/components and cooldown state;
- record realized trade P&L/MFE/MAE for both strategies;
- run isolated fixed-₹500 counterfactual lifecycle replays at **direct same-time arbitration divergences** so candidate quality can be compared without account-balance contamination;
- pair nearby trades to expose same-engine timing shifts and replacement cascades.

No strategy parameter, score component, score weight, score floor, engine threshold, lifecycle rule or risk value may change.

The final20 holdout remains sealed.

## Data

- canonical seven-day first80 at 500 ms and 1 s;
- frozen recent 24-hour raw snapshot at 500 ms and 1 s.

Both are already-known data and are used only for diagnosis.

## Required parity

The instrumented simulator must reproduce the exact Experiment-30 Candidate D and Router-v2 results before any audit output is accepted.

Canonical expected:

- 500 ms Candidate D +₹1,430.311133793068; Router v2 +₹851.2651000196032; 163 trades each;
- 1 s Candidate D +₹385.2544619534224; Router v2 +₹297.6666981590078; 156 trades each.

It also compares its whole-recent results against the uninstrumented Experiment-30 engine during execution.

## Outputs

- `summary.json` — parity, aggregate divergence counts and top counterfactual damage events;
- `segment_damage.csv` — exact segment-level P&L/count differences;
- `arbitration_events.csv` — every classified decision divergence;
- `decision_category_summary.csv` — divergence class counts and normalized counterfactual deltas;
- `substitution_matrix.csv` — Candidate-D action → Router action direct substitutions;
- `trade_pairs.csv` — exact/shifted/replacement trade pairing;
- `candidate_d_trades.csv` and `router_v2_trades.csv` — instrumented realized ledgers;
- `top_damage_events.csv` — worst direct counterfactual decisions.

## Decision discipline

Experiment 31 is an autopsy, **not an optimizer**.

A result may justify a structural hypothesis for Experiment 32, but no new rule is selected merely because it would recover known historical winners. Any proposed revision must be causally interpretable, frozen before another genuinely unseen snapshot, and tested without opening final20.

## Evidence

- `research/v4_5_router_v2_arbitration_audit.py`
- `results/simulations/2026-09-25-v4_5-router-v2-arbitration-audit/`
