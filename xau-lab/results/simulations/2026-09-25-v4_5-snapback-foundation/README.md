# Experiment 34 — SNAPBACK complementary engine

Status: **completed; rejected unchanged; no tuning performed**.

SNAPBACK was frozen before P&L evaluation using only inherited Candidate-D/MICRO gates and short BURST lifecycle constants.

Historical first80 fixed-size result:

- 500 ms: 17 trades / 3 wins / **-₹153.04**, PF 0.236;
- 1 s: 7 / 2 / **-₹44.78**, PF 0.374.

+$0.20 adverse slippage per side worsened those to -₹178.54 / -₹55.28.

The signal produced **no realized recent-24h opportunities** on either grid, so it did not supply the missing hostile-regime complement.

Do not tune the frozen constants from these known outcomes.

Harness: `research/v4_5_snapback_foundation.py`.
