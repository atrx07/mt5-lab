# 35 — V4.5 state-v2 walk-forward predictability

Date: 2026-09-25

Status: **completed diagnostic; transferable predictability not demonstrated**

## Objective

Test whether frozen `xau-state-v2` contains chronologically transferable information about independent fixed-size trade outcome.

This experiment makes **no trading-strategy change**.

The entire protocol was frozen before execution in:

`docs/plans/V4_5_ADAPTIVE_ADMISSION_FEASIBILITY.md`

## Frozen method

For each grid separately:

- exact 20 `xau-state-v2` inputs;
- four engine one-hot indicators;
- no side feature;
- training-only median imputation;
- training-only z-score standardization;
- ridge regression with fixed `alpha=1.0`;
- target = Experiment-33 fixed-size `pnl_inr`;
- natural diagnostic admission proxy = predicted expected P&L > 0.

No feature, threshold, alpha or model search was performed.

Historical evaluation was expanding chronological walk-forward: 0->1, 0-1->2, 0-2->3, 0-3->4. Then all historical first80 opportunities trained the final diagnostic model for the later recent 24-hour snapshot.

Final20 remained sealed.

## Historical walk-forward

At 500 ms, 89 future opportunities had aggregate actual P&L +₹267.42, but prediction correlation was weak/negative:

- Pearson **-0.073**;
- Spearman **-0.136**;
- sign accuracy 46.1%.

The predicted-positive subset retained 47 trades and made +₹127.36, while the predicted-nonpositive subset still made +₹140.06. The model therefore did not isolate the profitable half reliably.

At 1 s the failure was stronger:

- 92 future opportunities;
- aggregate actual +₹166.76;
- Pearson **-0.226**;
- Spearman **-0.301**;
- sign accuracy 42.4%;
- predicted-positive trades lost **₹62.52** while predicted-nonpositive trades made **+₹229.28**.

Fold behavior was inconsistent rather than merely weak. Several profitable future folds received negative/anti-correlated predictions.

## Historical -> recent transfer

The recent window is the decisive transfer check.

500 ms:

- 46 opportunities, actual **-₹352.50**;
- Pearson 0.130, Spearman **0.018**;
- predicted-positive 31 trades, actual **-₹212.85**;
- predicted-nonpositive 15 trades, actual **-₹139.65**.

1 s:

- 44 opportunities, actual **-₹191.70**;
- Pearson 0.029, Spearman **-0.008**;
- predicted-positive 24 trades, actual **-₹127.16**;
- predicted-nonpositive 20 trades, actual **-₹64.54**.

The model predicted a positive mean expected P&L on the recent window while the realized opportunity family was deeply negative. That is a direct failure of transfer.

## Frozen Router-v2 score comparator

The hand-written Router-v2 score was also nearly non-selective:

- it retained ~98–99% of opportunities;
- historical score/outcome Spearman was approximately -0.065 / +0.013 at 500 ms / 1 s;
- recent score/outcome Spearman rose only to about +0.215 / +0.165 and retained almost the entire losing opportunity set.

So neither the fixed ridge diagnostic nor the current structural score demonstrates a portable admission signal from state-v2.

## Decision

**Do not build or tune an adaptive admission candidate from this state-v2/ridge result.**

This is not a case where changing alpha, selecting a subset of features, moving the zero threshold or swapping in a more flexible model should be tried against the same two windows until something looks good. That would convert a clean rejection into model-selection overfit.

Together Experiments 33–35 say:

1. the existing four engines broadly fail together in the hostile recent regime;
2. the first structural countertrend complement (SNAPBACK) fails unchanged and does not even fire there;
3. the frozen state representation does not show reliable chronological outcome predictability with the pre-registered simple learner.

The next research step must introduce **new information or a structurally new causal opportunity hypothesis**, freeze it before outcome testing, and then require genuinely new non-overlapping raw data for promotion. Known data may continue to reject broken ideas, but it must not be used as a scoreboard for repeated tuning.

## Evidence

- `docs/plans/V4_5_ADAPTIVE_ADMISSION_FEASIBILITY.md`
- `research/v4_5_state_v2_walkforward_predictability.py`
- `results/simulations/2026-09-25-v4_5-state-v2-walkforward-predictability/summary.json`
- `.../fold_metrics.csv`
- `.../aggregate_metrics.csv`
- `.../predictions.csv`
- `.../per_engine_prediction_summary.csv`
- `.../coefficients.json`
