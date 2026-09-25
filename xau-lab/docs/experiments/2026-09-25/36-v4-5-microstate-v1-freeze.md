# 36 — V4.5 raw-event microstate-v1 foundation

Date: 2026-09-25

Status: **frozen before execution; representation-only**

## Objective

Introduce genuinely new causal market information after Experiments 33–35 showed that neither current engine routing, frozen SNAPBACK, nor the current state-v2 ridge admission test solved cross-window robustness.

This experiment does **not** create a trading candidate.

The exact schema is frozen in:

`docs/plans/V4_5_MICROSTATE_FOUNDATION.md`

before execution.

## Data discipline

The feature layer is evaluated only for:

- causal finite coverage;
- sampling-grid stability;
- distribution drift.

P&L and future outcomes are not used to define, select, rank or threshold the features.

Canonical final20 remains sealed.

## Inputs

Opportunity timestamps come from Experiment 33's independent shadow atlas so shared-slot path does not determine which market states are sampled.

Raw-event features are recomputed directly from:

- canonical seven-day first80 raw quotes;
- the separate recent 24-hour raw snapshot.

## Decision rule

A stable representation may be retained as a foundation.

It **cannot** justify a strategy change on known data. Any future signal/admission rule using microstate-v1 must be specified before outcome testing and ultimately validated unchanged on genuinely new non-overlapping raw data.

## Evidence

- `docs/plans/V4_5_MICROSTATE_FOUNDATION.md`
- `research/v4_5_microstate_v1_freeze.py`
- `results/simulations/2026-09-25-v4_5-microstate-v1-freeze/`
