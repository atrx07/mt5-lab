# 38 — V4.5 Decision Policy v1: entry ownership + continuation controller

Date: 2026-09-25

Status: **completed diagnostic; v1 decision policy rejected; no Candidate F created**

## Objective

Build a more precise decision layer around Candidate D without another hand-written threshold search.

Experiment 38 separated:

- **entry EV / engine ownership** — whether an eligible opportunity deserves capital and which simultaneous engine should own the slot;
- **continuation EV** — whether remaining in an open trade still adds value versus exiting now.

The model/features/thresholds were frozen before the run in:

`docs/plans/V4_5_DECISION_POLICY_V1.md`

## Frozen architecture

Both tasks used a shallow `HistGradientBoostingRegressor` with no model search:

- learning rate 0.05;
- 160 iterations;
- max 7 leaves;
- min 20 samples/leaf;
- L2 1.0;
- random seed 20260925.

Entry features combined all 20 `xau-state-v2` fields, all 23 `xau-microstate-v1` fields, engine identity and sampling-grid identity.

Exit features added live position state: hold time, current move/R, MFE, MAE, giveback, MFE capture, time since MFE and MICRO partial state.

The entry boundary was predicted EV > 0. The exit boundary was predicted continuation EV > 0. Neither boundary was searched.

Historical evaluation used expanding segment walk-forward; recent24h was predicted only after fitting all historical first80. Final20 remained sealed.

## Entry result

The nonlinear model did **not** solve opportunity selection.

| Evaluation | Grid | Spearman | Sign accuracy | Baseline independent-lane P&L | Predicted-positive P&L |
| --- | --- | ---: | ---: | ---: | ---: |
| historical walk-forward | 500 ms | 0.021 | 50.56% | +₹267.42 | +₹153.70 |
| historical walk-forward | 1 s | -0.107 | 46.74% | +₹166.76 | +₹59.54 |
| recent transfer | 500 ms | 0.092 | 30.43% | -₹352.50 | -₹256.95 |
| recent transfer | 1 s | 0.167 | 36.36% | -₹191.70 | -₹148.24 |

The recent loss reduction mainly came from rejecting some trades in a broadly hostile regime; it did not demonstrate accurate per-opportunity ranking.

Historical walk-forward lost substantial valid edge by filtering profitable opportunities.

Only eight exact-timestamp multi-engine ownership events appeared in the OOS predictions, reinforcing Experiment 33's finding that same-tick engine competition is too rare to be the main bottleneck.

## Continuation / exit result

Snapshot-level continuation prediction was also weak:

| Evaluation | Grid | Spearman | Sign accuracy |
| --- | --- | ---: | ---: |
| historical walk-forward | 500 ms | 0.086 | 54.40% |
| historical walk-forward | 1 s | 0.033 | 51.39% |
| recent transfer | 500 ms | 0.094 | 57.62% |
| recent transfer | 1 s | 0.005 | 53.63% |

The reconstructed first-negative-EV exit policy became far too aggressive:

| Evaluation | Grid | Legacy P&L | v1 exit-policy P&L | Delta | Model exit fraction |
| --- | --- | ---: | ---: | ---: | ---: |
| historical walk-forward | 500 ms | +₹270.57 | **-₹68.17** | -₹338.75 | 92.94% |
| historical walk-forward | 1 s | +₹170.06 | **-₹64.09** | -₹234.15 | 91.01% |
| recent transfer | 500 ms | -₹352.50 | **-₹41.62** | +₹310.88 | 95.65% |
| recent transfer | 1 s | -₹191.70 | **-₹69.04** | +₹122.66 | 97.73% |

The recent result looks superficially dramatic, but the mechanism is not acceptable: the policy learned something close to **exit almost everything early**. That behavior protects a hostile window while destroying the profitable historical walk-forward population.

Historical false-early-exit cost exceeded avoided giveback:

- 500 ms: ₹334.99 saved versus ₹673.73 false-exit cost;
- 1 s: ₹442.58 saved versus ₹676.73 false-exit cost.

## Combined policy

Combining entry filtering and the exit controller remained negative on historical OOS:

- 500 ms: +₹267.42 baseline → **-₹35.10**;
- 1 s: +₹166.76 baseline → **-₹49.87**.

Recent losses were reduced but remained negative:

- 500 ms: -₹352.50 → -₹54.82;
- 1 s: -₹191.70 → -₹77.70.

## Interpretation

Experiment 38 answers an important question: simply adding a nonlinear learner to the current single-snapshot state does **not** provide the precision required for entry or exit.

The failure points to two representation/label problems rather than a need to tune model parameters:

1. **entry timing is underrepresented** — Experiment-33 rows contain one cooldown-selected entry per lane, not the full signal episode and its changing entry opportunity;
2. **terminal continuation is too distant/noisy a target** — asking one snapshot to predict the value all the way to the legacy exit makes the controller collapse toward regime-level behavior;
3. **single-state snapshots miss local evolution** — exit decisions need causal derivatives such as recent P&L velocity, MFE growth, giveback speed and state/microstate change;
4. exact simultaneous engine ownership is rare, so the bigger problem is **TAKE / WAIT / SKIP within an engine's signal episode**, not global engine ranking.

## Decision

**Reject Decision Policy v1. Do not create Candidate F from this model.**

Do not tune the zero thresholds or gradient-boosting hyperparameters against these outputs.

The next diagnostic should change the data/target structure instead:

- model full signal episodes so entry can choose **when** to take an engine;
- use episode-level weighting to avoid pseudo-replication;
- model short-horizon continuation instead of terminal legacy-exit value;
- add causal trajectory deltas and confirmation/hysteresis to exit decisions.

Candidate D remains the V4.5 leader. Final20 remains sealed.

## Evidence

`results/simulations/2026-09-25-v4_5-decision-policy-v1/`

Key files:

- `summary.json`
- `entry_metrics.csv`
- `entry_per_engine.csv`
- `simultaneous_ownership.csv`
- `exit_prediction_metrics.csv`
- `exit_policy_metrics.csv`
- `exit_per_engine.csv`
- `combined_policy_metrics.csv`
- `prediction_calibration.csv`


## Result

The worker completed after one implementation-only retry caused by a pandas column/method name collision in final aggregation. The research calculation itself then completed and the evidence bundle was committed.

Entry EV remained weak:

- historical walk-forward 500 ms: Spearman 0.021; taking predicted-positive opportunities reduced fixed-size P&L from +₹267.42 to +₹153.70;
- historical walk-forward 1 s: Spearman -0.107; P&L fell from +₹166.76 to +₹59.54;
- recent transfer remained negative on both grids despite skipping some losses.

The global entry regressor therefore did not demonstrate reliable trade ranking.

The continuation controller showed the opposite failure mode: it was useful in the hostile recent regime but far too aggressive historically.

- historical 500 ms: legacy +₹270.57 → exit policy -₹68.17;
- historical 1 s: legacy +₹170.06 → exit policy -₹64.09;
- recent 500 ms: legacy -₹352.50 → exit policy -₹41.62;
- recent 1 s: legacy -₹191.70 → exit policy -₹69.04.

It model-exited roughly 91-98% of represented trades. This confirms that a single global terminal-continuation model does not respect engine-specific lifecycle and phase structure.

## Diagnosis

Two conceptual problems were identified for the next iteration.

1. **Entry target contamination:** training entry quality on final realized P&L mixes entry quality with exit quality. An entry can create large favorable excursion and still receive a poor label because the legacy exit gave it back.
2. **Exit target/lifecycle mismatch:** `legacy_final_pnl - current_mark_pnl` asks whether holding all the way to the legacy terminal exit beats exiting now. It is too terminal and path-dependent for a local continuation controller, and a first-negative-decision policy amplifies prediction noise.

The model was given engine one-hot identity, but not a full signal fingerprint containing the rule margins and regime/mode that caused that engine to fire. The action policy was also global rather than engine-specific.

## Decision

**Reject Decision Policy v1 as a candidate foundation. Do not create Candidate F from it.**

The next iteration must separate entry quality from exit quality, expose engine-specific signal provenance/strength, use local-horizon continuation targets, and apply engine-aware hysteresis rather than a universal immediate-exit rule.

Candidate D remains the V4.5 leader. Final20 remains sealed.
