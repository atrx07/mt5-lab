# V4.5 run spec — robustness before more complexity

Date: 2026-09-24

Status: **research plan**

## Baseline

V4.4 Candidate K is locked and must not be edited in place.

Official reference:

- 500 ms canonical capture: 16.36%;
- 1 s robustness capture: 11.54%;
- final 20% holdout unopened.

Any accepted change becomes V4.5.

## First research direction

Test whether raw-event market-state features can improve robustness without simply adding another engine.

Priority order:

1. raw-event quote-flow / sampling-invariant features;
2. lifecycle continuation / exit decisions;
3. selective SECONDARY filtering;
4. hostile-regime detection.

The first pass begins conservatively by testing raw-event activity as a MICRO admission requirement.

## Discipline

- first 80% only;
- 0–40% seed selection, later chronological segments used for evaluation;
- final 20% holdout remains unopened;
- 3% planned risk and $4 stop remain fixed;
- no real execution;
- no V4.5 lock unless the candidate improves the locked V4.4 robustness case rather than only one sampling grid.
