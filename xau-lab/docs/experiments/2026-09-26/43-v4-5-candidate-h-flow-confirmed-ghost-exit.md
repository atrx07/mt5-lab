# 43 — V4.5 Candidate H flow-confirmed ghost exit

Date: 2026-09-26
Status: **frozen; full diagnostic pending**

Candidate H keeps Candidate D's entry path and Candidate G's path-preserving ghost occupancy.

The new PRIMARY profit-retention rule does not fire on giveback alone. After +1R MFE, it waits for at least 1R giveback plus two consecutive five-second confirmations that both immediate raw price movement and raw event pressure have reversed against the trade.

Frozen plan:
`docs/plans/V4_5_CANDIDATE_H_FLOW_CONFIRMED_GHOST_EXIT.md`

Implementation:
`research/v4_5_candidate_h_flow_confirmed_ghost_exit.py`

Evidence:
`results/simulations/2026-09-26-v4_5-candidate-h-flow-confirmed-ghost-exit/`

Candidate D remains leader until the full diagnostic says otherwise. Final20 remains sealed.
