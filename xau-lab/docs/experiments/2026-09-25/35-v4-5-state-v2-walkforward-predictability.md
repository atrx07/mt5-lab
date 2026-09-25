# 35 — V4.5 state-v2 walk-forward predictability

Date: 2026-09-25

Status: **frozen before execution; diagnostic pending**

## Objective

Test whether frozen `xau-state-v2` contains chronologically transferable information about independent fixed-size trade outcome.

This experiment makes **no trading-strategy change**.

The exact model protocol is frozen in:

`docs/plans/V4_5_ADAPTIVE_ADMISSION_FEASIBILITY.md`

before performance execution.

## Why now

Experiment 33 showed that the existing engine family does not supply robust cross-regime complementarity by itself. At 500 ms all four independent engines lost on the recent window. At 1 s only SECONDARY remained positive on a small sample.

Before adding another manually tuned router rule, test whether the existing state representation can predict which opportunities are worth taking using only past labels.

## Frozen method

For each grid separately:

- 20 `xau-state-v2` inputs;
- four engine one-hot indicators;
- no side feature;
- training-only median imputation;
- training-only z-score standardization;
- ridge regression, fixed `alpha=1.0`;
- target = Experiment-33 fixed-size `pnl_inr`;
- natural diagnostic admission proxy = predicted expected P&L > 0.

No hyperparameter, feature or threshold search.

Historical walk-forward:

- train segment 0 -> test 1;
- train 0–1 -> test 2;
- train 0–2 -> test 3;
- train 0–3 -> test 4.

Then train on all historical first80 opportunities and predict the later recent 24-hour opportunities.

Final20 remains sealed.

## Comparator

The frozen Router-v2 hand-written state score is evaluated on the same future opportunity labels, using its unchanged 0.0 floor.

## Interpretation

This test can reject or support the **idea** of an adaptive meta-labeler.

It cannot promote a strategy from known data.

If transfer is weak or unstable, stop tuning state-v2 admission and move to a genuinely complementary new opportunity generator.

If transfer is materially positive on chronological OOS and recent diagnostics, the next step is to freeze a causal adaptive admission candidate and test it unchanged on genuinely new non-overlapping market data.

## Evidence

- `docs/plans/V4_5_ADAPTIVE_ADMISSION_FEASIBILITY.md`
- `research/v4_5_state_v2_walkforward_predictability.py`
- `results/simulations/2026-09-25-v4_5-state-v2-walkforward-predictability/`
