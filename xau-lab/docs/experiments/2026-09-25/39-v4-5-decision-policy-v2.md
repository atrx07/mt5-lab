# 39 — V4.5 Decision Policy v2: signal episodes + short-horizon exit

Date: 2026-09-25

Status: **completed diagnostic; learned v2 policy rejected; PRIMARY-only profit-ratchet mechanism retained for a separately frozen candidate test**

## Objective

Fix the representation/target failures found in Experiment 38 without tuning its thresholds or model hyperparameters.

The frozen specification was committed before outcome evaluation:

`docs/plans/V4_5_DECISION_POLICY_V2.md`

## Frozen changes versus v1

Entry:

- complete cooldown-free legacy signal episodes;
- checkpoint every 2 seconds while eligibility persists;
- TAKE / WAIT / SKIP episode policy;
- episode-level weighting.

Exit:

- causal trajectory-change features;
- 30-second incremental mark-equity target;
- two consecutive non-positive predictions required before model exit;
- trade-level weighting.

Comparator:

- fixed +1R activation and 50%-of-live-MFE profit ratchet at 5-second checkpoints.

The HistGradientBoostingRegressor architecture remained exactly Experiment 38's architecture.

## Entry timing result

The episode representation expanded the entry dataset to **7,988 usable checkpoints across 6,501 signal episodes**, but the learned policy still did not provide useful timing precision.

Historical OOS:

| Grid | Enter-at-onset P&L | Learned episode policy | Delta | Episode retention | Median wait when taken |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | +₹274.29 | **-₹1,101.86** | -₹1,376.16 | 30.65% | 0 s |
| 1 s | -₹75.80 | **-₹657.10** | -₹581.31 | 32.33% | 0 s |

Recent transfer:

| Grid | Enter-at-onset P&L | Learned episode policy | Delta |
| --- | ---: | ---: | ---: |
| 500 ms | -₹4,188.37 | -₹2,802.37 | +₹1,386.00 |
| 1 s | -₹1,928.48 | -₹1,400.96 | +₹527.51 |

The recent reduction again reflects broad hostile-regime filtering rather than accurate timing. The median selected wait remained **0 seconds**, so the learner did not discover a reliable TAKE-NOW versus WAIT structure.

**Reject the learned entry policy.**

## Short-horizon continuation result

Changing from terminal continuation to a 30-second target and adding causal trajectory deltas did not fix the learned exit controller.

Snapshot prediction remained approximately uncorrelated with future value on historical OOS:

- 500 ms Spearman: **0.0002**, sign accuracy 50.46%;
- 1 s Spearman: **-0.0259**, sign accuracy 49.99%.

The two-negative confirmation still exited almost every represented historical trade:

| Grid | Legacy P&L | Confirmed model-exit P&L | Delta | Exit fraction |
| --- | ---: | ---: | ---: | ---: |
| 500 ms | +₹270.57 | **-₹61.31** | -₹331.88 | 98.82% |
| 1 s | +₹170.06 | **-₹61.84** | -₹231.90 | 98.88% |

Recent losses were reduced, but again via an almost-always-exit behavior rather than transferable precision.

**Reject the learned continuation controller.**

## Fixed profit-ratchet comparator

The simple risk-unit comparator behaved very differently.

Rule:

- inactive before +1R MFE;
- after activation, retain at least 50% of live MFE;
- evaluate at the same 5-second checkpoints.

Historical OOS:

| Grid | Legacy P&L | Ratchet P&L | Delta | Exit fraction |
| --- | ---: | ---: | ---: | ---: |
| 500 ms | +₹270.57 | **+₹343.36** | **+₹72.79** | 11.76% |
| 1 s | +₹170.06 | **+₹246.98** | **+₹76.91** | 14.61% |

The ratchet improved historical win rate on both grids and saved materially more giveback than it sacrificed through early exits.

Recent transfer was mixed:

- 500 ms: -₹352.50 → **-₹325.46** (+₹27.04);
- 1 s: -₹191.70 → **-₹226.61** (-₹34.91).

## Post-run mechanism decomposition

The universal ratchet affected only PRIMARY and SECONDARY in this dataset. MICRO and BURST already had their own partial/trailing lifecycle and never triggered the comparator.

A post-run engine decomposition showed:

**PRIMARY ratchet contribution improved all four evaluated window/grid combinations:**

- historical 500 ms: **+₹24.90**;
- historical 1 s: **+₹20.21**;
- recent 500 ms: **+₹27.04**;
- recent 1 s: **+₹4.54**.

The recent 1 s degradation came from applying the same ratchet to SECONDARY, where the existing lifecycle was already profitable.

This PRIMARY-only decomposition was discovered **after** Experiment 39 outcomes were visible. It is therefore mechanism evidence, not a pre-registered candidate result.

Machine record:

`results/simulations/2026-09-25-v4_5-decision-policy-v2/postrun_mechanism.json`

## Interpretation

Two increasingly sophisticated learned decision policies failed on the same core issue: the currently available state is much better at identifying broad regime hostility than at predicting individual trade outcomes or near-term continuation.

The deterministic MFE state, however, contains a much cleaner management signal.

The next strategy-changing test should therefore avoid another ML threshold/model iteration and freeze a narrow candidate around the mechanism with the strongest cross-window evidence:

> **Candidate D + PRIMARY-only +1R / 50%-MFE ratchet, with all entry logic unchanged.**

That candidate must be tested in the actual shared-slot, cooldown, compounding and path-dependent simulator because the independent-lane decomposition cannot predict downstream entry timing effects.

## Decision

- learned entry policy v2: **rejected**;
- learned exit policy v2: **rejected**;
- universal PRIMARY+SECONDARY ratchet: **not promoted**;
- PRIMARY-only ratchet mechanism: **eligible for a separately frozen full Candidate-F diagnostic**.

Candidate D remains the leader until such a full candidate beats it under the complete simulator.

Final20 remains sealed.

## Evidence

`results/simulations/2026-09-25-v4_5-decision-policy-v2/`

Key files:

- `summary.json`
- `entry_episode_dataset.csv`
- `entry_episode_policy_metrics.csv`
- `exit_v2_prediction_metrics.csv`
- `exit_v2_policy_metrics.csv`
- `profit_ratchet_policy.csv`
- `profit_ratchet_metrics.csv`
- `postrun_mechanism.json`
