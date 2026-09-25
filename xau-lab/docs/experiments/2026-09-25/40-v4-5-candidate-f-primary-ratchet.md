# 40 — V4.5 Candidate F PRIMARY profit-ratchet full replay

Date: 2026-09-25

Status: **candidate architecture frozen; full shared-slot diagnostic pending**

## Objective

Move the strongest Experiment-39 mechanism into the real Candidate-D simulator without changing entries.

Frozen plan:

`docs/plans/V4_5_CANDIDATE_F_PRIMARY_RATCHET.md`

## Candidate

Candidate F = Candidate D + PRIMARY-only profit ratchet:

- activate at +1R MFE = +$4;
- retain 50% of live MFE;
- evaluate every 5 wall-clock seconds;
- no SECONDARY/MICRO/BURST ratchet;
- all entry/risk/lifecycle rules otherwise unchanged.

## Required diagnostic

- canonical first80 500 ms / 1 s;
- exact Candidate D parity;
- recent24h whole and 60/40 split;
- real contiguous random four-hour windows;
- $0.00/$0.05/$0.10/$0.20 per-side slippage stress;
- full path-dependent shared-slot/cooldown/compounding behavior;
- final20 sealed.

Known data cannot promote Candidate F.

## Evidence

- implementation: `research/v4_5_candidate_f_primary_ratchet.py`
- results: `results/simulations/2026-09-25-v4_5-candidate-f-primary-ratchet/`
