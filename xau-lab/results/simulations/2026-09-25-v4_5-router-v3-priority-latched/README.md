# Experiment 32 — Router v3 priority-latched

Status: **completed; not promoted**.

Router v3 was frozen before evaluation. It preserved Candidate D engine priority, used the unchanged Router-v2 score only as a veto, and latched vetoed engines for their pre-existing Candidate-D cooldown horizon.

Known-data result:

- canonical 500 ms: +₹1,162.46 / 159 trades / 79 wins versus Candidate D +₹1,430.31 / 163 / 81;
- canonical 1 s: +₹214.06 / 155 / 70 versus Candidate D +₹385.25 / 156 / 71;
- recent 500 ms: -₹210.63 versus D -₹223.27;
- recent 1 s: -₹128.87 versus D -₹135.91.

The key structural result is **zero fallback entries** on canonical first80. Every veto was a PRIMARY-only opportunity, so the architecture behaved as sparse gating rather than useful engine substitution.

Random known real-window stress also failed to show a broad advantage: Router v3 beat D in 15% of 500 ms windows and 2.5% of 1 s windows.

Candidate D remains the leader. Next research moves away from router tuning and measures each engine as an independent shadow opportunity stream.
