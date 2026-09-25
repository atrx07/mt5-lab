# 37 — V4.5 Candidate E PRIMARY microstate confirmation

Date: 2026-09-25

Status: **candidate architecture frozen; known-data full simulation pending; no promotion**

## Objective

Turn the retained Experiment-36 `xau-microstate-v1` representation into the first actual strategy candidate that uses the new raw-event information, while preserving Candidate D's proven path/priority structure.

The frozen pre-run specification is:
`docs/plans/V4_5_CANDIDATE_E_MICROSTATE_CONFIRMATION.md`

## Baseline

Control: **Candidate D**, the provisional V4.5 leader from Experiment 19.

Candidate D must reproduce its canonical first80 reference before Candidate E evidence is accepted:

- 500 ms: +₹1,430.31, 163 trades, 81 wins;
- 1 s: +₹385.25, 156 trades, 71 wins.

The V4.4 canonical regression gate must also pass on the same feature build.

## Frozen Candidate E change

Candidate E changes PRIMARY admission only.

When Candidate D's highest-priority eligible signal is PRIMARY, compute the frozen `xau-microstate-v1` raw-event state. HOLD for that sampled quote only when:

`dir_mid_move2 < 0 AND dir_event_imb2 < 0`

This means both immediate raw mid movement and immediate raw event pressure contradict the intended PRIMARY direction.

No outcome/P&L-derived threshold is used. Zero is the direction-neutral boundary already implied by the feature definitions.

A veto:

- does not mutate cooldown state;
- does not fall through to another engine on that tick;
- may be followed by a later PRIMARY entry if the legacy signal persists and the contradiction clears;
- fails open when either required microstate value is not finite.

All non-PRIMARY entries and every Candidate D exit/risk/execution rule remain unchanged.

## Data discipline

Known data are diagnostic only:

- seven-day canonical first80;
- separate Experiment-22 recent 24-hour snapshot.

The final20 holdout stays sealed.

The known-data run includes canonical segments, recent whole/split replay, deterministic real four-hour windows, and $0.00/$0.05/$0.10/$0.20 per-side execution stress. A good result cannot promote Candidate E from these already-observed windows.

## Decision rule

Experiment 37 may reject Candidate E if implementation parity fails or the frozen rule is clearly destructive.

If it remains viable, the next promotion-relevant step is a **new non-overlapping raw snapshot** with the Candidate E rule unchanged.

Do not tune the two-feature rule against Experiment-37 outputs.

## Evidence

- implementation: `research/v4_5_candidate_e_microstate_confirmation.py`
- result bundle: `results/simulations/2026-09-25-v4_5-candidate-e-microstate-confirmation/`
