# Experiment 30 — full raw-tick Router v2 replay

Status: **completed known-data diagnostic; Router v2 score not promoted**.

This bundle contains the first end-to-end raw-tick replay of the Experiment-28 fall-through router. Candidate D parity passed exactly before comparison.

Headline canonical result:

- 500 ms: Candidate D **+₹1,430.31 / 163 / 81** versus Router v2 **+₹851.27 / 163 / 78**;
- 1 s: Candidate D **+₹385.25 / 156 / 71** versus Router v2 **+₹297.67 / 156 / 70**.

Whole recent 24-hour result:

- 500 ms: Candidate D **-₹223.27** versus Router v2 **-₹210.63**;
- 1 s: Candidate D **-₹135.91** versus Router v2 **-₹144.22**.

Corrected four-hour real-window stress also failed to show a general expectancy advantage: mean P&L was -₹6.26 versus -₹8.89 at 500 ms and -₹8.25 versus -₹15.23 at 1 s for Candidate D versus Router v2.

The random windows are contiguous within sampled continuity sessions. Many recent windows overlap because the 24-hour source has limited long continuous coverage, so the window set is a stress diagnostic rather than independent-day validation.

Decision: **Candidate D remains the V4.5 research leader. Do not tune the frozen Router-v2 score from this known-data result.**

Machine-readable evidence:

- `full_replay_summary.json`
- `random_real_windows.csv`
