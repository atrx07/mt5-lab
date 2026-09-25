# 43 — V4.5 Candidate H flow-confirmed ghost exit

Date: 2026-09-26
Status: **completed full diagnostic; not promoted; exit mechanism retained**

Candidate H keeps Candidate D's entry path and Candidate G's path-preserving ghost occupancy.

The new PRIMARY profit-retention rule does not fire on giveback alone. After +1R MFE, it waits for at least 1R giveback plus two consecutive five-second confirmations that both immediate raw price movement and raw event pressure have reversed against the trade.

Frozen plan:
`docs/plans/V4_5_CANDIDATE_H_FLOW_CONFIRMED_GHOST_EXIT.md`

Implementation:
`research/v4_5_candidate_h_flow_confirmed_ghost_exit.py`

Evidence:
`results/simulations/2026-09-26-v4_5-candidate-h-flow-confirmed-ghost-exit/`

Candidate D remains leader until the full diagnostic says otherwise. Final20 remains sealed.


## Result

Candidate H preserved Candidate D's entry path exactly on canonical first80 and recent24h.

Canonical first80:

| Grid | Candidate D | Candidate H | H - D | Win rate D → H | Max segment DD D → H |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **+₹1,430.31** | +₹1,287.09 | -₹143.22 | 49.69% → 50.92% | ₹218.94 → **₹148.66** |
| 1 s | **+₹385.25** | +₹360.79 | -₹24.46 | 45.51% → **48.08%** | ₹172.14 → ₹170.82 |

The signal-confirmed exit retained far more historical upside than Candidate G's blunt ratchet while still improving risk characteristics.

Recent24h:

- 500 ms: -₹223.27 → **-₹208.47** (+₹14.80);
- 1 s: -₹135.91 → **-₹128.63** (+₹7.28).

Random real four-hour windows:

- 500 ms mean: -₹6.26 → **-₹3.36**; median -₹23.59 → **-₹20.84**; positive-window fraction 30.0% → **35.0%**;
- 1 s mean: -₹8.25 → **-₹7.21**; positive-window fraction 27.5% → **30.0%**.

Candidate H improved mean random-window expectancy on both grids, but mean expectancy remained negative and the recent whole window remained negative.

Cost stress preserved the same qualitative pattern: H stayed below D on canonical history but above D on the hostile recent window at every tested added-slippage level.

## Interpretation

The exit controller is now behaving materially better than the learned v1/v2 controllers and the blunt Candidate-G ratchet:

- it does not exit almost every trade;
- it preserves the exact downstream entry/cooldown path;
- it uses actual signal deterioration rather than giveback alone;
- it substantially reduces the historical damage of profit protection;
- it improves recent losses and random-window means on both grids.

The remaining problem is selectivity. Eighteen 500 ms and seventeen 1 s historical PRIMARY exits still clip enough high-upside runners to keep H below Candidate D's canonical P&L.

## Decision

**Do not promote Candidate H yet. Candidate D remains the V4.5 leader.**

Retain Candidate H as the strongest path-preserving exit-management branch so far. Do not threshold-sweep the known windows.

The next exit research should distinguish **healthy pullback inside a still-live PRIMARY trend** from **terminal decay after a favorable excursion**, while preserving the same ghost-occupancy architecture.

Final20 remains sealed.
