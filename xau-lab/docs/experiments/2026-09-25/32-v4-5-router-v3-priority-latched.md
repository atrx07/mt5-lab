# 32 — V4.5 path-aware priority-preserving Router v3

Date: 2026-09-25

Status: **architecture frozen before performance evaluation; execution pending**

## Why this experiment exists

Experiment 31 showed that the main Router-v2 defect is not simply the instantaneous stronghold score. A changed decision modifies engine cooldown history, shared-slot occupancy, later entry timing and then balance-based sizing.

Therefore Experiment 32 is intentionally **not** a score search.

The new candidate changes routing mechanics only, using causal structure already present in Candidate D and the frozen Router-v2 representation.

## Frozen Router v3 rules

1. Preserve Candidate D's engine priority: **PRIMARY → SECONDARY → MICRO → BURST**.
2. Keep the Experiment-28 stronghold score unchanged.
3. Keep the score floor unchanged at **0.0**.
4. Use the score only as a **veto**. It can reject a priority candidate, but it cannot allow a lower-priority engine to outrank a qualifying higher-priority one.
5. When an engine is vetoed, latch that rejection for the engine's **already-existing Candidate-D cooldown duration**. This prevents the same rejected setup from being reconsidered seconds later as though it were a new independent opportunity.
6. After a veto, evaluate the next lower-priority candidate on the same tick.
7. HOLD only when no priority-ordered candidate clears the frozen score.
8. Entry/exit logic, risk, spread handling, leverage assumptions and lifecycle rules remain unchanged.

No new numeric threshold is introduced. No cooldown duration is searched. No score component or weight is changed.

## Evaluation discipline

The canonical seven-day first80 and existing recent 24-hour window are already known. They may be used only to answer:

- does the implementation preserve Candidate D parity?
- does this structural change behave as intended?
- does it avoid the known Router-v2 path pathology or create a new one?
- is it obviously dominated and therefore not worth carrying forward?

A good known-data result **cannot promote Router v3**.

Promotion still requires a genuinely new non-overlapping raw snapshot collected after this architecture was frozen.

The final20 holdout remains sealed.

## Diagnostic matrix

Run, unchanged, on both 500 ms and 1 s:

- canonical first80;
- whole recent 24 h;
- the existing 60/40 recent split for continuity with prior experiments;
- deterministic contiguous four-hour real windows sampled from the known historical/recent datasets.

The random windows are stress diagnostics only; they are not independent validation.

## Promotion gate for a future unseen snapshot

A future unseen evaluation should prefer Router v3 over Candidate D only if it simultaneously shows:

- higher net P&L on both grids;
- improved or at least non-degraded win quality;
- at least 95% system-level trade retention unless omitted trades are replaced by demonstrably better opportunities;
- no material drawdown deterioration;
- no execution-cost fragility;
- no evidence that rejection latching merely suppresses activity to manufacture robustness.

## Evidence

- `research/v4_5_router_v3_priority_latched.py`
- `results/simulations/2026-09-25-v4_5-router-v3-priority-latched/`
