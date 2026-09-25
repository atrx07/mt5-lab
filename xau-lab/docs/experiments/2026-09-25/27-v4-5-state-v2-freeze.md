# 27 — V4.5 `xau-state-v2` continuous feature freeze

Date: 2026-09-25

Status: **completed feature freeze; no strategy/router change**

## Objective

Build the richer causal state representation requested by Experiments 26 and 27's research direction **without** turning already observed outcomes into another fitted threshold.

The purpose is to give a future router enough continuous information to distinguish an engine's stronghold from late/exhausted or execution-hostile entries while keeping the market-state calculation independent of the 500 ms / 1 s execution grids.

## Data discipline

Known descriptive inputs:

- canonical seven-day first-80% Candidate D research trades: 319 across both grids;
- separate Experiment 22 recent 24-hour Candidate D trades: 71 across both grids;
- canonical final 20%: **not opened**.

Both windows are now treated as known benchmark/development evidence. No threshold, feature subset, engine veto or candidate is selected from their outcome P&L in this experiment.

## Frozen schema

Schema: `xau-state-v2`

Twenty continuous features are frozen:

1. `range60_rel` — raw 60 s range / lagged 30-minute range baseline;
2. `spread_rel` — current spread / lagged 30-minute spread baseline;
3. `activity_rel` — raw 10 s quote count / lagged 30-minute activity baseline;
4. `er60` — absolute 60 s displacement / raw tick path length;
5. `spread_to_range` — current spread / raw 60 s range;
6. `dir_m10_rel`;
7. `dir_m30_rel`;
8. `dir_m60_rel`;
9. `dir_m300_rel` — direction-normalized momentum divided by lagged absolute-move baselines;
10. `dir_eff60` — direction-normalized 60 s displacement / path length;
11. `flow_align10`;
12. `flow_align60` — direction-normalized raw up/down tick imbalance;
13. `accel_10_60` — `dir_m10_rel - dir_m60_rel`;
14. `accel_30_300` — `dir_m30_rel - dir_m300_rel`;
15. `short_long_balance` — mean short normalized momentum minus mean long normalized momentum;
16. `pullback60` — distance from the side-favorable 60 s extreme / 60 s range;
17. `pullback300` — same concept over 300 s;
18. `market_heat` — `range60_rel * activity_rel`;
19. `execution_heat` — `spread_rel * activity_rel`;
20. `session_age_sec` — seconds since the latest >5 s raw-data session gap.

BUY uses side +1 and SELL side -1 for every direction-normalized field.

### Causal baselines

- 10 s momentum: median absolute completed 10-second return over the previous 30 minutes, shifted one bucket;
- 30 s momentum: median absolute completed 30-second return over the previous 30 minutes, shifted one bucket;
- 60 s momentum/range/spread: completed one-minute rolling baselines over the previous 30 minutes, shifted one bucket;
- 300 s momentum: completed five-minute absolute returns over the previous two hours, shifted one bucket;
- activity: completed 10-second quote counts over the previous 30 minutes, shifted one bucket.

The current bucket never contributes to its own normalizer.

## Coverage

All short-horizon features were finite for 100% of the 319 historical and 71 recent trade entries.

The 300 s-derived fields (`dir_m300_rel`, `accel_30_300`, `short_long_balance`) covered:

- historical: 309 / 319 = **96.87%**;
- recent: 68 / 71 = **95.77%**.

The missing values are causal warm-up after session gaps, not imputed hindsight.

## Cross-grid stability

Matched entries use the same segment/split, engine and side, within 120 seconds.

| Window | Matched pairs | Median feature Spearman | Features >=0.80 | Features >=0.90 |
| --- | ---: | ---: | ---: | ---: |
| canonical historical | 119 | **0.916** | 17 / 20 | 11 / 20 |
| recent 24 h | 27 | **0.940** | 18 / 20 | 14 / 20 |

The weakest continuous fields were `pullback60` (0.699 historical, 0.692 recent) and `spread_rel` (0.800 historical, 0.741 recent). They remain contextual inputs rather than standalone gates.

Several core fields were especially stable on the recent window:

- `dir_m10_rel`: 0.957;
- `dir_m60_rel`: 0.956;
- `accel_10_60`: 0.965;
- `short_long_balance`: 0.990;
- `market_heat`: 0.974;
- `session_age_sec`: 1.000.

## Descriptive outcome clue — not a rule

PRIMARY's recent max-hold winners still differ from its stop/zero-cross failures in the frozen continuous state. For example, median market heat was approximately:

- 500 ms: max-hold 1.159, emergency stop 1.698, zero-cross 1.772;
- 1 s: max-hold 1.168, emergency stop 1.807, zero-cross 1.893.

Momentum acceleration, pullback depth and flow alignment also differ by outcome.

These are **descriptive profiles only**. No value above is converted into a threshold because both windows are already known.

## Router v2 pre-registration

The next strategy-changing experiment must wait for a genuinely new non-overlapping snapshot.

Router v2 should:

- evaluate each engine's candidate in `xau-state-v2`;
- reject/allow at the engine level rather than declaring an engine globally good or bad;
- fall through to lower-priority eligible engines when a higher-priority candidate is rejected;
- retain HOLD/no-trade if no engine has demonstrated a stronghold;
- target >=95% of Candidate D's total system trade count, unless replacement opportunities keep the count within 5%;
- improve both net P&L and win rate versus Candidate D on the unseen window at 500 ms and 1 s;
- avoid material drawdown deterioration and pass execution-cost stress before promotion.

The 95% retention requirement is a research constraint chosen to prevent the trivial solution of deleting most trades. It is not a profitability claim.

## Decision

Freeze `xau-state-v2` exactly as documented.

Do not change its formulas after seeing the next snapshot. The next unseen dataset is for validating this representation and the first Router v2 candidate, not for redesigning the feature layer after the fact.

## Evidence

- `scripts/v4_5_state_v2_freeze.py`
- `results/simulations/2026-09-25-v4_5-state-v2-freeze/state_v2_catalog.json`
- `results/simulations/2026-09-25-v4_5-state-v2-freeze/feature_distribution.csv`
- `results/simulations/2026-09-25-v4_5-state-v2-freeze/cross_grid_feature_stability.csv`
- `results/simulations/2026-09-25-v4_5-state-v2-freeze/primary_outcome_profiles.csv`
- `results/simulations/2026-09-25-v4_5-state-v2-freeze/summary.json`
