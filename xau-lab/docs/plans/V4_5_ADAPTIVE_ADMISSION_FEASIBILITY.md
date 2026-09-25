# V4.5 adaptive admission feasibility — frozen walk-forward specification

Status: **frozen before Experiment 35 execution**

Date: 2026-09-25

## Goal

Test whether the existing frozen `xau-state-v2` representation contains **chronologically transferable information about fixed-size trade outcome**.

This is deliberately not a new trading strategy yet.

Experiment 33 showed that the current four engines broadly lose together in the hostile recent regime. Before adding another hand-built rule, test whether a simple model trained only on past opportunities can distinguish later positive from negative opportunities.

## Fixed model

One model is trained separately for each execution grid.

Inputs:

- the exact 20 frozen `xau-state-v2` features;
- four fixed engine one-hot indicators: PRIMARY, SECONDARY, MICRO, BURST.

Side is not added because the state features are already direction-normalized where direction matters.

Target:

- fixed-size opportunity `pnl_inr` from Experiment 33;
- no compounding and no shared-slot path contamination.

Preprocessing, fit on training data only:

- median imputation per continuous feature;
- z-score standardization;
- fixed ridge regression with `alpha = 1.0`;
- unpenalized intercept.

No feature selection, alpha search, threshold search or hyperparameter search is allowed.

## Chronological tests

For each grid independently:

- train segment 0 -> test segment 1;
- train segments 0–1 -> test segment 2;
- train segments 0–2 -> test segment 3;
- train segments 0–3 -> test segment 4.

Then train on all historical first80 shadow opportunities and predict the later recent 24-hour window.

The final20 canonical holdout remains sealed.

## Diagnostics

Report:

- Spearman and Pearson correlation between predicted and realized fixed-size P&L;
- MAE/RMSE against a training-mean baseline;
- sign accuracy around zero;
- natural predicted-positive proxy: retain opportunities only when predicted expected P&L > 0;
- retained trade count, actual P&L and win rate;
- the same metrics for the frozen Router-v2 hand-written score as a comparator;
- per-engine predicted-positive vs predicted-nonpositive outcome summaries.

The zero threshold is not tuned. It follows directly from the expected-P&L target.

## Interpretation discipline

This experiment may answer whether an adaptive meta-labeler is worth building.

It does **not** promote a strategy from known data.

A favorable result only justifies freezing an adaptive admission candidate and testing that unchanged candidate on a genuinely new non-overlapping market snapshot.

If the predictive relationship collapses chronologically or on recent data, stop trying to rescue the current engine family with state-v2 gating and move to a genuinely complementary new engine.
