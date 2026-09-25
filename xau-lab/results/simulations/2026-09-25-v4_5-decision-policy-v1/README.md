# Experiment 38 — Decision Policy v1

Status: **completed diagnostic; rejected; no Candidate F**

The frozen v1 policy combined `xau-state-v2` + `xau-microstate-v1` in shallow nonlinear models for entry EV and in-trade continuation EV.

It did not demonstrate transferable per-decision precision.

## Entry

Historical walk-forward predicted-positive filtering reduced independent-lane P&L:

- 500 ms: +₹267.42 → +₹153.70;
- 1 s: +₹166.76 → +₹59.54.

Recent transfer rejected some hostile opportunities but retained negative P&L:

- 500 ms: -₹352.50 → -₹256.95;
- 1 s: -₹191.70 → -₹148.24.

## Exit

The first-negative-continuation policy exited more than 90% of historical OOS trades and destroyed historical edge:

- 500 ms: +₹270.57 → -₹68.17;
- 1 s: +₹170.06 → -₹64.09.

It reduced recent losses sharply, but by behaving close to an indiscriminate early-exit regime:

- 500 ms: -₹352.50 → -₹41.62;
- 1 s: -₹191.70 → -₹69.04.

Historical false-early-exit cost materially exceeded avoided giveback.

## Conclusion

Reject v1 unchanged. Do not tune its thresholds or model parameters on the same windows.

The next line must improve the **decision representation**:

- full signal episodes for TAKE / WAIT / SKIP timing;
- causal trajectory-change features;
- short-horizon continuation targets;
- confirmation before model-driven exit.

Candidate D remains leader and final20 is sealed.
