# 48 — V4.5 Candidate J fresh MT5-only prospective validation

Date: 2026-09-26

Status: **active staged prospective validation; first 4-hour block ready to capture**

Candidate J is frozen unchanged after Experiment 47.

Experiment 48 will not run on any already-known dataset. It requires a new 48-hour MT5 XAUUSD snapshot captured after at least 48 live market hours following the weekend reopen.

Frozen plan:
`docs/plans/V4_5_CANDIDATE_J_FRESH_VALIDATION.md`

Validator:
`research/v4_5_candidate_j_fresh_validation.py`

Candidate D remains formal leader until prospective evidence says otherwise.

Final20 remains sealed.


## Staged-capture amendment

Before the first scored prospective block, the continuous 48-hour requirement was replaced by a practical staged design:

- Stage 1 = six independent fresh 4-hour scored blocks;
- each block gets 90 minutes of causal MT5 prehistory as context only;
- the score window starts at launch and lasts exactly four wall-clock hours;
- blocks must span at least three market days where practical;
- Candidate J remains frozen unchanged;
- no block is selected or discarded based on Candidate-J outcome.

Capture tool:
`scripts/capture_candidate_j_4h_block.py`

Windows launcher:
`scripts/start_candidate_j_4h_block.ps1`

The capture tool backfills its own 90-minute MT5 context, so it does not depend on the earlier live-shadow process remaining open.

The Stage-1 pass gate is frozen in the plan before the first scored block.

Final20 remains sealed.


## Block-duration amendment

After Stage-1 Block #3 crossed a broker no-tick maintenance interval, and before any staged-block Candidate D/H/J outcomes were evaluated, the score-duration rule was amended outcome-blind:

- preserve the originally frozen block start;
- accumulate four **market-active** hours;
- pause the scored clock across MT5 no-tick gaps >=60 seconds;
- determine the end mechanically from timestamps only;
- use the same MT5/broker history for reconstruction;
- do not inspect candidate P&L when determining or repairing the endpoint.

Blocks without such a gap are unchanged. This amendment prevents scheduled broker downtime from shortening effective market exposure while keeping the laptop runtime practical.
