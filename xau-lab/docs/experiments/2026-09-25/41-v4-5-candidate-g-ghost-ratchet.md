# 41 — V4.5 Candidate G path-preserving ghost ratchet

Date: 2026-09-25

Status: **completed full diagnostic; Candidate G not promoted; Candidate D remains leader**

## Objective

Test whether PRIMARY profit retention can be separated from the path-dependence damage that rejected Candidate F.

Frozen plan:

`docs/plans/V4_5_CANDIDATE_G_GHOST_RATCHET.md`

## Candidate G

Candidate G uses Candidate F's unchanged PRIMARY +1R / 50%-MFE / five-second ratchet.

After a real ratchet exit, however, a capital-free virtual PRIMARY continues under Candidate D's untouched legacy lifecycle and keeps the shared slot occupied. PRIMARY cooldown begins only when that ghost would have exited under Candidate D.

The required invariant is **exact Candidate-D entry-path parity** on canonical first80 at zero added slippage.

## Data discipline

- known historical first80 + recent24h diagnostic only;
- random real four-hour windows;
- execution-cost stress;
- final20 sealed;
- no ratchet/cooldown/ghost parameter search.

## Evidence

- implementation: `research/v4_5_candidate_g_ghost_ratchet.py`
- bundle: `results/simulations/2026-09-25-v4_5-candidate-g-ghost-ratchet/`


## Result

Candidate G achieved exact zero-cost entry-path parity with Candidate D on canonical first80 and recent24h.

Canonical first80:
- 500 ms: D +₹1,430.31 vs G +₹1,005.57; max segment drawdown ₹218.94 → ₹119.76.
- 1 s: D +₹385.25 vs G +₹325.53; max segment drawdown ₹172.14 → ₹145.65.

Recent24h remained negative but improved modestly:
- 500 ms: -₹223.27 → -₹207.40.
- 1 s: -₹135.91 → -₹132.07.

Random four-hour windows:
- 500 ms mean: -₹6.26 → -₹1.24; positive-window fraction 30.0% → 40.0%; G beat D in 82.5% of windows.
- 1 s mean: -₹8.25 → -₹8.79; positive-window fraction 27.5% → 35.0%; G beat D in 72.5% of windows.

The ghost occupancy fixed Candidate F's extra-entry path mutation, but the frozen PRIMARY ratchet still sacrificed too much canonical upside and did not create positive expectancy across both grids.

## Decision

**Do not promote Candidate G. Candidate D remains the V4.5 leader.**

Retain ghost occupancy as a valid path-preserving mechanism for future exit experiments. Do not tune the ratchet parameters on the same known data. Final20 remains sealed.
