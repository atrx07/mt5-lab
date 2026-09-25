# V4.5 Decision Policy v2 — signal-episode timing + short-horizon exit specification

Date: 2026-09-25

Status: **frozen before Experiment 39 outcome evaluation**

## Why v2 exists

Experiment 38 rejected the first nonlinear decision policy without tuning it.

The failure was structural:

- one cooldown-selected entry row per trade does not represent **when** an engine should enter during a live signal episode;
- terminal legacy-exit continuation is too distant/noisy for a rolling exit decision;
- single snapshots omit the recent evolution of P&L, MFE, giveback and microstructure;
- the v1 exit policy collapsed toward "exit almost everything" and destroyed historical edge.

Experiment 39 changes the data and target structure. It does **not** tune v1 hyperparameters or thresholds.

## Part A — entry timing / engine decision

### Cooldown-free signal episodes

Replay each execution grid and evaluate the existing Candidate-D signal conditions with engine cooldowns disabled for diagnostic labeling only.

For each engine and side:

- start an episode when its legacy entry condition becomes eligible;
- keep the episode alive while that same engine/side remains continuously eligible;
- end it when eligibility disappears, side flips or the continuity session changes.

Record a candidate entry checkpoint at episode onset and every **2 seconds** of continued eligibility.

This exposes the missing action space:

**TAKE NOW / WAIT / SKIP**, rather than only "accept or reject the cooldown-selected trade."

### Counterfactual checkpoint label

At each checkpoint, independently enter that engine at executable bid/ask using the same fixed ₹500 sizing and the unchanged Candidate-D engine lifecycle.

No shared slot, cross-engine cooldown or compounding is included in the label.

Target:

`counterfactual_pnl_inr`

Censored segment-end trades are excluded from model fitting.

### Entry features

Use only causal state at the checkpoint:

- 20 frozen `xau-state-v2` fields;
- 23 frozen `xau-microstate-v1` fields;
- engine one-hot;
- execution-grid identity;
- episode age seconds;
- episode checkpoint count;
- number of simultaneously eligible engines;
- number of simultaneously eligible engines aligned to the same side.

### Episode policy

Prediction boundary remains natural and unsearched:

`predicted entry EV > 0`.

For each OOS episode:

- choose the **first** checkpoint with predicted EV > 0;
- if no checkpoint qualifies, SKIP the episode.

Compare the chosen counterfactual outcome with entering at episode onset.

Training weights make each signal episode contribute total weight 1 regardless of duration/checkpoint count.

## Part B — short-horizon continuation controller

Reuse Experiment-38 causal in-trade snapshots, but add trajectory-evolution features.

### New causal dynamics

For each 5-second snapshot add past-only changes:

- current-move change over approximately 5 / 15 / 30 seconds;
- P&L velocity;
- MFE growth;
- giveback growth / giveback speed;
- change in `dir_mid_move2`;
- change in `dir_event_imb2`;
- change in event-rate acceleration;
- change in spread-relative state;
- change in activity;
- change in short-flow alignment.

### New target

Instead of predicting all the way to the legacy exit, predict **30-second incremental mark-equity value**:

- if the legacy trade remains open for at least another 30 seconds, use the first causal checkpoint at/after +30 s;
- if the legacy exit occurs first, use the legacy final trade P&L.

Target:

`forward_30s_value_inr = future_30s_or_exit_equity - current_mark_equity`.

Thirty seconds is frozen because Candidate D already uses a 30-second momentum layer; it is not selected from Experiment-38 outcomes.

### Exit action / hysteresis

Evaluate every 5 seconds.

A single negative prediction creates a warning only.

Model exit occurs on the **second consecutive** checkpoint with:

`predicted forward-30s EV <= 0`.

A positive prediction resets the warning.

This two-observation confirmation is frozen before evaluation and exists to prevent the v1 one-shot exit collapse.

Hard legacy stop/TP/lifecycle limits remain the safety ceiling in any future strategy integration.

Training weights make each trade contribute total weight 1 across all snapshots.

## Part C — deterministic profit-ratchet comparator

Because the user requirement explicitly includes preventing profitable trades from draining away, also evaluate one outcome-independent risk-unit comparator:

- inactive until live MFE reaches **+1R**;
- after activation, retain at least **50% of live MFE**;
- at a 5-second checkpoint, exit if current R <= 0.5 × live MFE R.

This is a scale-free comparator, not a selected Candidate-F rule. No threshold sweep is allowed.

It answers whether simple profit retention is more reliable than prediction.

## Model

Keep the exact Experiment-38 model architecture to isolate the representation/target change:

`HistGradientBoostingRegressor`

- squared-error loss;
- learning rate 0.05;
- 160 iterations;
- max 7 leaves;
- min 20 samples/leaf;
- L2 1.0;
- seed 20260925.

No hyperparameter search or feature subset search.

## Validation

Historical expanding walk-forward:

- segment 0 → test 1;
- 0-1 → 2;
- 0-2 → 3;
- 0-3 → 4.

Recent24h transfer:

- fit all historical first80;
- predict recent24h unchanged.

Both grids remain within the same chronological fold.

Final20 remains sealed.

## Promotion discipline

Experiment 39 is diagnostic. It cannot promote a strategy on known data.

Only if entry timing and/or exit management show coherent historical OOS behavior plus sensible recent transfer may a separately frozen Candidate F be implemented in the full shared-slot simulator.

A future Candidate F still requires genuinely new non-overlapping raw data for promotion.

## Evidence contract

Experiment:
`docs/experiments/2026-09-25/39-v4-5-decision-policy-v2.md`

Implementation:
`research/v4_5_decision_policy_v2.py`

Evidence:
`results/simulations/2026-09-25-v4_5-decision-policy-v2/`
