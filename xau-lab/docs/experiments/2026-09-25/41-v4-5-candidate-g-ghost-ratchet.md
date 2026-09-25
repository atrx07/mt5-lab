# 41 — V4.5 Candidate G path-preserving ghost ratchet

Date: 2026-09-25

Status: **candidate architecture frozen; diagnostic pending**

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
