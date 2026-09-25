# 37 — V4.5 Candidate E PRIMARY microstate confirmation

Date: 2026-09-25

Status: **completed known-data diagnostic; Candidate E rejected unchanged; no promotion**

## Objective

Turn the retained Experiment-36 `xau-microstate-v1` representation into the first actual strategy candidate that uses the new raw-event information, while preserving Candidate D's proven path/priority structure.

The frozen pre-run specification was committed before outcome evaluation:

`docs/plans/V4_5_CANDIDATE_E_MICROSTATE_CONFIRMATION.md`

## Baseline and parity

Control: **Candidate D**, the provisional V4.5 leader from Experiment 19.

Before Candidate E interpretation, the same implementation reproduced Candidate D exactly on canonical first80:

| Grid | Candidate D P&L | Trades | Wins |
| --- | ---: | ---: | ---: |
| 500 ms | +₹1,430.31 | 163 | 81 |
| 1 s | +₹385.25 | 156 | 71 |

The locked V4.4 canonical regression gate also passed on both grids. The final20 holdout was not opened.

## Frozen Candidate E change

Candidate E changes PRIMARY admission only.

When Candidate D's highest-priority eligible signal is PRIMARY, compute the frozen `xau-microstate-v1` raw-event state. HOLD for that sampled quote only when:

`dir_mid_move2 < 0 AND dir_event_imb2 < 0`

This means both immediate raw mid movement and immediate raw event pressure contradict the intended PRIMARY direction.

No outcome/P&L-derived threshold was used. Zero is the direction-neutral boundary implied by the frozen feature definitions.

A veto:

- does not mutate cooldown state;
- does not fall through to another engine on that tick;
- may be followed by a later PRIMARY entry if the legacy signal persists and the contradiction clears;
- fails open when either required microstate value is not finite.

All non-PRIMARY entries and every Candidate D exit/risk/execution rule remained unchanged.

## Canonical first80 result

| Grid | Candidate D | Candidate E | E - D | Trade retention | D win rate | E win rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **+₹1,430.31** | +₹1,163.47 | **-₹266.84** | 100.00% | 49.69% | 48.47% |
| 1 s | **+₹385.25** | +₹374.58 | **-₹10.67** | 99.36% | 45.51% | 45.81% |

Candidate E reduced maximum segment drawdown at 500 ms from ₹218.94 to ₹186.15 and at 1 s from ₹172.14 to ₹167.80, but the 500 ms historical profit loss was large.

The historical damage was concentrated almost entirely in the first two chronological segments:

- 500 ms segment 0: ₹696.84 → ₹532.38;
- 500 ms segment 1: ₹44.10 → ₹43.58;
- later three 500 ms segments were unchanged;
- 1 s segment 0: ₹169.92 → ₹162.25;
- 1 s segment 1: ₹41.93 → ₹41.60;
- later three 1 s segments were unchanged.

The gate recorded 17 PRIMARY veto ticks at 500 ms and 11 at 1 s on canonical first80.

## Recent 24-hour result

Whole-window terminal-equity P&L:

| Grid | Candidate D | Candidate E | E - D | Trade retention |
| --- | ---: | ---: | ---: | ---: |
| 500 ms | -₹223.27 | **-₹216.77** | +₹6.50 | 97.44% |
| 1 s | -₹135.91 | **-₹94.08** | +₹41.83 | 94.12% |

Candidate E improved the hostile recent window, especially at 1 s, but **did not make either grid profitable**.

Recent split behavior was mixed:

| Grid / split | Candidate D | Candidate E | E - D |
| --- | ---: | ---: | ---: |
| 500 ms seed | **-₹92.48** | -₹102.02 | -₹9.54 |
| 500 ms evaluation | -₹149.92 | **-₹133.11** | +₹16.82 |
| 1 s seed | -₹86.54 | **-₹86.26** | +₹0.29 |
| 1 s evaluation | -₹52.31 | **-₹2.29** | +₹50.02 |

The 1 s evaluation result is a useful mechanism clue, not promotion evidence: the snapshot was already known before Candidate E was designed.

## Real contiguous random-window stress

Forty deterministic four-hour windows per grid alternated between known historical-first80 and recent24h continuity ranges.

500 ms:

- Candidate D mean: -₹6.26; Candidate E mean: **-₹6.48**;
- median: -₹23.59 vs **-₹24.08**;
- positive-window fraction: 30.0% for both;
- Candidate E beat D in 10.0% of windows, tied 55.0%, and was worse in 35.0%.

1 s:

- Candidate D mean: -₹8.25; Candidate E mean: **-₹8.96**;
- median: -₹27.86 vs **-₹27.54**;
- positive-window fraction: 27.5% for both;
- Candidate E beat D in 50.0% of windows, tied 17.5%, and was worse in 32.5%;
- the 95th-percentile window fell from +₹83.90 for D to +₹69.73 for E.

The candidate therefore did **not** restore positive variable-window expectancy.

## Execution-cost stress

The full simulator added adverse entry and exit slippage so costs could alter stop/exit paths and later balance sizing.

At every tested slippage level, Candidate E remained below Candidate D on historical first80. At +$0.20 per side:

- historical 500 ms: D +₹335.09 vs E +₹88.10;
- historical 1 s: D +₹35.88 vs E +₹2.60.

Candidate E's recent relative advantage persisted under stress, but both recent grids remained negative.

## Interpretation

This was deliberately not another router. It preserved legacy priority and used the new raw-event representation only as a narrow PRIMARY timing veto.

The result is informative:

1. raw microstructure can materially change the hostile recent 1 s path;
2. the simple two-feature contradiction rule is **not cross-grid robust**;
3. preserving trade count does not preserve profit because small admission delays still change path, timing and later sizing;
4. the 500 ms canonical edge remains especially sensitive to PRIMARY timing;
5. random real-window expectancy did not improve.

This reinforces Experiment 31's path-dependence finding while showing that `xau-microstate-v1` itself is not disproven by this one rejected use of it.

## Decision

**Reject Candidate E unchanged. Candidate D remains the provisional V4.5 research leader.**

Do not tune the two-feature rule, add a fitted threshold, or select a feature subset against these same known outcomes.

`xau-microstate-v1` remains a retained causal feature foundation. A future microstructure hypothesis must be structurally different or use a different causal mechanism, be frozen before its outcome test, and still require genuinely new non-overlapping raw data for promotion.

The final20 holdout remains sealed.

## Evidence

- frozen plan: `docs/plans/V4_5_CANDIDATE_E_MICROSTATE_CONFIRMATION.md`
- implementation: `research/v4_5_candidate_e_microstate_confirmation.py`
- result bundle: `results/simulations/2026-09-25-v4_5-candidate-e-microstate-confirmation/`
- machine summary: `results/simulations/2026-09-25-v4_5-candidate-e-microstate-confirmation/summary.json`
- segment comparison: `.../canonical_segment_comparison.csv`
- recent split comparison: `.../recent_split_comparison.csv`
- random real windows: `.../random_real_windows.csv`
- execution stress: `.../cost_stress.csv`
- veto-state evidence: `.../primary_veto_events.csv`
