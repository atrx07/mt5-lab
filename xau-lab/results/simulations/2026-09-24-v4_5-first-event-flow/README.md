# V4.5 first simulation — event-flow MICRO admission

Date: 2026-09-24

Status: **rejected first V4.5 candidate; no V4.5 version lock.**

## Purpose

The first V4.5 simulation tested the first robustness idea after V4.4: make the MICRO engine more selective using raw-event quote activity instead of adding another trading engine.

The candidate was selected on the 0–40% seed region only, then evaluated over the later first-80% research segments. The final 20% holdout remained unopened.

## Candidate A

The only entry change relative to V4.4 Candidate K was:

- MICRO minimum sampled 60-second path efficiency: 0.12 -> 0.16;
- MICRO minimum 10s/30s raw quote-rate ratio: 0.65 -> 0.85.

All PRIMARY, SECONDARY, risk, stop, MICRO exit, stagnation and partial-realization rules stayed unchanged.

The intent was to require a cleaner, more active MICRO move and improve sampling robustness.

## Important harness warning

This new research harness does **not** reproduce the official locked V4.4 headline exactly.

Official locked V4.4 record:

- 500 ms canonical capture: **16.36%**;
- 1 s robustness capture: **11.54%**.

Current reconstruction of the same V4.4 rules:

- 500 ms reset/compound capture: **14.67%**;
- 1 s reset/compound capture: **4.45%**.

Because the 1-second mismatch is large, absolute V4.5 results from this harness are **not eligible for promotion**. The valid comparison for this first pass is only V4.5-A versus the V4.4 reconstruction in the same harness.

## Same-harness results

| Metric | Reconstructed V4.4 | V4.5-A |
| --- | ---: | ---: |
| 500 ms compounded P&L | **+₹1,097.66** | +₹1,081.69 |
| 500 ms capture | **14.67%** | 14.46% |
| 500 ms median segment PF | 1.284 | **1.362** |
| 500 ms trades | **148** | 143 |
| 500 ms worst segment DD | **₹229.31** | ₹246.98 |
| 1 s compounded P&L | **+₹333.27** | +₹283.07 |
| 1 s capture | **4.45%** | 3.78% |
| 1 s median segment PF | 1.367 | 1.367 |
| 1 s trades | 145 | 145 |
| 1 s worst segment DD | ₹171.34 | **₹159.77** |

The candidate increased median PF at 500 ms and reduced the 1-second drawdown, but it reduced capture at both sampling rates and cut useful 500 ms trades.

## Segment P&L

500 ms reconstructed V4.4:

- +₹638.57
- +₹33.11
- -₹16.12
- +₹24.52
- +₹148.17

500 ms V4.5-A:

- +₹737.87
- -₹11.19
- -₹16.12
- +₹32.33
- +₹134.27

1 s reconstructed V4.4:

- +₹163.48
- +₹40.55
- -₹45.95
- +₹74.27
- +₹56.90

1 s V4.5-A:

- +₹111.64
- +₹40.55
- -₹45.95
- +₹85.42
- +₹56.90

The stricter MICRO gate helped the seed region at 500 ms but hurt the next chronological region and did not improve the slower-sampling replay.

## Additional event-flow probes

A light SECONDARY raw-flow veto was also probed. Some settings improved the reconstructed 1-second result, but they materially damaged the 500 ms result. This exposes a possible robustness trade-off, not a promotable configuration.

The first pass therefore does **not** support simply tightening raw-flow admission thresholds.

## Decision

**Reject V4.5-A.**

Do not create `paper_challenge_v4_5.py` from this candidate.

Next V4.5 work should:

1. first restore the V4.4 1-second research harness to the locked 11.54% reference;
2. keep raw-event features, but use them for lifecycle/continuation decisions rather than blunt entry rejection;
3. continue to keep the final 20% holdout sealed.
