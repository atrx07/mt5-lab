# V4.5 Decision Policy v1 — frozen Experiment 38 specification

Date: 2026-09-25

Status: **frozen before outcome evaluation**

## Goal

Experiments 31-37 show two separate problems that should no longer be conflated:

1. **admission / ownership** — decide whether an eligible engine deserves capital and, when several are eligible, which engine should own the shared slot;
2. **continuation / exit** — once a trade is open, decide whether remaining in the trade still has positive expected value instead of letting favorable excursion drain away.

Experiment 38 is a **prediction and policy-foundation diagnostic**, not a promoted strategy. It may justify a later frozen Candidate F, but it cannot itself replace Candidate D.

## Inputs fixed before the run

Entry state uses only causal information available at the opportunity timestamp:

- all 20 frozen `xau-state-v2` features;
- all 23 frozen `xau-microstate-v1` features;
- engine one-hot: PRIMARY / SECONDARY / MICRO / BURST;
- interval one-hot: 500 ms / 1 s.

The features are direction-normalized where already defined. No outcome-selected feature subset is permitted.

Exit state uses the same causal state at each in-trade checkpoint plus frozen position-state features:

- hold seconds;
- current directional move in USD and R;
- MFE and MAE in USD and R;
- giveback from MFE in USD and R;
- current-MFE capture ratio;
- time since MFE;
- partial-take state for MICRO;
- engine one-hot;
- interval one-hot.

Hard risk rules remain outside the learned controller.

## Labels

### Entry value

Target: Experiment-33 independent-lane fixed-size realized `pnl_inr`.

This deliberately removes shared-slot competition, cross-engine cooldown cascades and balance compounding from the label. It asks whether the opportunity itself had positive expected value under the current engine lifecycle.

Natural admission boundary for later simulation: **predicted expected P&L > 0**. This boundary is not searched.

### Continuation value

Generate in-trade checkpoints every **5 seconds**, beginning 5 seconds after entry and ending before the legacy exit.

At each checkpoint:

`continuation_value_inr = legacy_final_trade_pnl_inr - current_mark_equity_pnl_inr`

This asks a direct causal decision question: relative to exiting now, did continuing under the existing lifecycle add or destroy value?

Natural continuation boundary for later simulation: **predicted continuation value > 0 = HOLD; <= 0 = EXIT**. This boundary is not searched.

## Model class

Use one fixed nonlinear tabular architecture for both tasks:

`HistGradientBoostingRegressor`

Frozen parameters:

- loss: squared error;
- learning rate: 0.05;
- max iterations: 160;
- max leaf nodes: 7;
- min samples per leaf: 20;
- L2 regularization: 1.0;
- random seed: 20260925.

No hyperparameter search, feature search, threshold sweep, ensemble search or post-hoc fold selection is allowed.

Why nonlinear: Experiment 35's fixed linear ridge transfer was non-predictive, while the hypothesized interactions are conditional (flow × spread × activity × position state).

## Leakage control

Historical evaluation is expanding chronological walk-forward by canonical segment:

- train segment 0 → test segment 1;
- train 0-1 → test 2;
- train 0-2 → test 3;
- train 0-3 → test 4.

Both sampling grids from a segment stay on the same side of a fold.

Recent24h is predicted only after fitting on **all historical first80**.

Exit snapshots from a trade never cross train/test boundaries because the whole trade inherits its segment/window.

The historical final20 holdout remains sealed.

## Diagnostic policy reconstruction

For each OOS trade:

1. entry model says TAKE only when predicted entry EV > 0;
2. if taken, exit policy closes at the first 5-second checkpoint where predicted continuation EV <= 0;
3. otherwise the legacy exit is retained.

Report both:

- exit-only policy versus legacy lifecycle;
- combined admission + exit policy versus taking every independent opportunity.

For simultaneous exact-timestamp engine opportunities, report which engine has the highest predicted entry EV versus Candidate D legacy priority. This is diagnostic ownership evidence only.

## Required metrics

Entry:

- Pearson / Spearman to realized P&L;
- sign accuracy;
- retained-opportunity fraction;
- actual P&L and win rate of predicted-positive opportunities;
- per-engine attribution;
- exact-simultaneous ownership comparison.

Exit:

- continuation-value correlation and sign accuracy;
- first model-exit policy P&L versus legacy;
- avoided giveback;
- false early-exit cost;
- MFE capture;
- per-engine results;
- number of model exits.

Combined:

- fixed-size OOS P&L;
- win rate;
- trade retention;
- per-engine contribution;
- historical walk-forward and recent transfer separately for 500 ms and 1 s.

These are diagnostics on known data. Positive known-data results do not constitute promotion evidence.

## Promotion discipline

A future Candidate F may be frozen only if Experiment 38 shows coherent walk-forward behavior rather than a single-window win.

Candidate F must then be replayed in the full shared-slot Candidate-D simulator with path-dependent cooldown, sizing and cost stress unchanged.

Promotion still requires a genuinely new non-overlapping raw XAU snapshot.

## Evidence contract

Experiment:
`docs/experiments/2026-09-25/38-v4-5-decision-policy-v1.md`

Implementation:
`research/v4_5_decision_policy_v1.py`

Evidence:
`results/simulations/2026-09-25-v4_5-decision-policy-v1/`
