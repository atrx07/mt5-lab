# V4.5 Candidate F — PRIMARY profit-ratchet full-replay specification

Date: 2026-09-25

Status: **frozen before Experiment 40 full-strategy outcome evaluation**

## Basis

Experiment 39 rejected both learned Decision Policy v2 models, but its fixed MFE-ratchet comparator revealed a narrower mechanism:

- the universal ratchet improved historical walk-forward at both grids;
- post-run decomposition showed PRIMARY's ratchet contribution was positive in all four historical/recent grid comparisons;
- the recent 1 s damage came from ratcheting SECONDARY.

Because the PRIMARY-only decomposition was observed after Experiment 39 results, it is **not** candidate evidence. This document freezes the mechanism before it is allowed to enter the full shared-slot Candidate-D simulator.

## Candidate F

Candidate F is Candidate D with **one exit-only change**.

Entries are completely unchanged.

### PRIMARY profit ratchet

For PRIMARY positions only:

1. inactive until live MFE reaches **+1R**;
2. Candidate D uses a $4 emergency-stop distance, therefore +1R = **+$4 favorable XAU move**;
3. once activated, the trade must retain at least **50% of its live MFE**;
4. evaluate the ratchet on a wall-clock **5-second cadence** using the first sampled quote at/after each checkpoint;
5. if current favorable move <= 0.5 × live MFE at a ratchet checkpoint, close the PRIMARY position;
6. normal emergency stop and take profit remain higher-priority exits;
7. ratchet exit then updates PRIMARY's existing cooldown exactly like any other Candidate-D exit.

No ratchet is added to SECONDARY, MICRO or BURST.

## Unchanged

- PRIMARY → SECONDARY → MICRO → BURST entry priority;
- every entry threshold;
- Candidate D BURST one-second confirmed-failure exit;
- MICRO partial/trailing logic;
- SECONDARY lifecycle;
- PRIMARY take-profit / max-hold / legacy reversal behavior;
- shared one-position slot;
- 3% planned-risk sizing and leverage cap;
- $4 emergency stop;
- spread rule and executable bid/ask accounting.

## Known-data full diagnostic

Run Candidate D and Candidate F through the same complete shared-slot simulator.

Required:

- canonical first80 five-segment replay at 500 ms and 1 s;
- Candidate D exact parity gate;
- recent24h whole replay;
- recent 60/40 split;
- 40 deterministic real contiguous four-hour windows per grid;
- adverse entry+exit slippage of $0.00 / $0.05 / $0.10 / $0.20 per side;
- ratchet-exit counts;
- trade retention, win rate and drawdown.

The final20 historical holdout stays sealed.

## Decision discipline

Known data can reject Candidate F but cannot promote it.

A coherent result should improve or preserve the Candidate-D edge without reproducing the Router-v2/v3 path-dependence disaster.

If Candidate F survives this diagnostic unchanged, the next step is **genuinely new non-overlapping raw XAU data**. No ratchet trigger/retention/cadence sweep is allowed on the known windows.

## Evidence contract

Experiment:
`docs/experiments/2026-09-25/40-v4-5-candidate-f-primary-ratchet.md`

Implementation:
`research/v4_5_candidate_f_primary_ratchet.py`

Evidence:
`results/simulations/2026-09-25-v4_5-candidate-f-primary-ratchet/`
