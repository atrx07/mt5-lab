# 14 — V4.5 first event-flow simulation

Date: 2026-09-24

## Goal

Begin V4.5 by testing sampling-invariant/raw-event activity information while preserving the locked V4.4 architecture and risk discipline.

## Candidate

V4.5-A keeps V4.4 Candidate K intact except for a stricter MICRO admission gate:

- ER60 minimum 0.12 -> 0.16;
- raw 10s/30s quote-rate ratio minimum 0.65 -> 0.85.

The candidate was selected on the 0–40% seed region before later chronological evaluation.

## Same-harness comparison

500 ms reconstructed harness:

- V4.4: +₹1,097.66, 14.67% capture, 148 trades;
- V4.5-A: +₹1,081.69, 14.46% capture, 143 trades.

1-second reconstructed harness:

- V4.4: +₹333.27, 4.45% capture, 145 trades;
- V4.5-A: +₹283.07, 3.78% capture, 145 trades.

The stricter MICRO gate therefore reduced capture at both sampling rates.

## Important limitation

This fresh reconstruction does not reproduce the official locked V4.4 reference, especially at 1 second:

- locked V4.4: 11.54% 1-second capture;
- reconstructed V4.4: 4.45%.

Therefore neither the reconstructed V4.4 nor V4.5-A absolute result is eligible to replace the locked record.

The first-pass conclusion is only the same-harness relative result: **V4.5-A is worse than its V4.4 reference.**

## Additional probe

A light SECONDARY raw-flow veto improved some reconstructed 1-second cases but materially reduced the 500 ms result. That trade-off is not sufficient for promotion.

## Decision

**Reject V4.5-A and do not create a V4.5 paper script.**

Before the next V4.5 simulation, restore the 1-second V4.4 research harness to the locked reference and then move raw-event information into lifecycle/continuation management rather than blunt admission tightening.

Evidence:

[`results/simulations/2026-09-24-v4_5-first-event-flow/`](../../../results/simulations/2026-09-24-v4_5-first-event-flow/)
