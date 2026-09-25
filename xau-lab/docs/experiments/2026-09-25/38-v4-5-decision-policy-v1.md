# 38 — V4.5 Decision Policy v1: entry ownership + continuation controller

Date: 2026-09-25

Status: **architecture frozen; walk-forward diagnostic pending; no strategy promotion**

## Objective

Build a much more precise decision layer around Candidate D without doing another same-data hand-written threshold search.

Experiment 38 separates:

- **entry EV / engine ownership**: which eligible opportunity deserves the shared slot;
- **continuation EV**: whether an open trade still deserves to remain open.

The complete pre-run contract is frozen in:

`docs/plans/V4_5_DECISION_POLICY_V1.md`

## Why now

Experiment 37 showed that a simple two-feature PRIMARY veto can materially improve one hostile regime while destroying valuable historical timing. Experiment 33 also shows substantial favorable excursion can later be surrendered, especially by PRIMARY.

The next step is therefore not another boolean gate. It is a fixed nonlinear, causally-featured, chronological walk-forward decision-policy diagnostic.

## Frozen constraints

- 20 `xau-state-v2` features;
- 23 `xau-microstate-v1` features;
- fixed shallow HistGradientBoostingRegressor architecture;
- no feature selection;
- no threshold search;
- entry decision boundary: predicted EV > 0;
- exit decision boundary: predicted continuation EV > 0;
- 5-second in-trade decision checkpoints;
- expanding chronological historical folds;
- recent24h predicted only from historical training;
- final20 sealed.

## Candidate status

This experiment does **not** create Candidate F by itself.

If the fixed policy demonstrates coherent OOS value, the next numbered experiment may freeze a Candidate-F full shared-slot implementation before replay.

## Evidence

- implementation: `research/v4_5_decision_policy_v1.py`
- bundle: `results/simulations/2026-09-25-v4_5-decision-policy-v1/`
