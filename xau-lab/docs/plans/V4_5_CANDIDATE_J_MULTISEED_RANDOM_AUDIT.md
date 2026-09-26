# Experiment 47R — Candidate J multi-seed random-window robustness audit

Date: 2026-09-26
Status: **frozen before rerun**

## Objective

Test whether Experiment 47's positive 500 ms random-window mean is robust to random-window selection or was an artifact of the original deterministic seed.

Candidate J is frozen unchanged. This is a robustness audit only; no strategy rule may change.

## Window design

Run **three additional independent deterministic random batches**.

Each batch contains:
- 40 real contiguous four-hour windows on 500 ms;
- 40 real contiguous four-hour windows on 1 s;
- exactly 20 historical-first80 windows and 20 recent24h windows, alternating source as in Experiment 47;
- fresh pseudo-random start times from the frozen seeds below.

Seeds:
- batch A: 20261001 (500 ms), 20261002 (1 s);
- batch B: 20261013 (500 ms), 20261014 (1 s);
- batch C: 20261027 (500 ms), 20261028 (1 s).

The original Experiment-47 seed is not reused.

## Candidate set

Compare unchanged:
1. Candidate D.
2. Candidate H.
3. Candidate J from Experiment 47.

No tuning, threshold change, phase-rule change, or engine-scope change is permitted.

## Required evidence

For every batch/grid/candidate report:
- mean four-hour terminal-equity P&L;
- median;
- p05 / p95;
- positive-window fraction;
- total trades / wins / aggregate win rate.

For Candidate J additionally report:
- fraction of windows beating D;
- fraction beating H;
- exact baseline-shadow opportunity parity for every sampled window.

Also report pooled results across all three new batches (120 windows per grid).

## Interpretation

This audit can strengthen or weaken confidence in Candidate J on known data, but it is not independent prospective validation because all windows still come from the already-known historical-first80/recent24h datasets.

Experiment 48 remains the decisive fresh-data gate.

Final20 remains sealed.

## Evidence contract

Record:
`docs/experiments/2026-09-26/47R-v4-5-candidate-j-multiseed-random-audit.md`

Implementation:
`research/v4_5_candidate_j_multiseed_random_audit.py`

Evidence:
`results/simulations/2026-09-26-v4_5-candidate-j-multiseed-random-audit/`
