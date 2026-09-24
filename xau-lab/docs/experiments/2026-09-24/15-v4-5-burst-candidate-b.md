# 15 — V4.5 additive BURST candidate B

Date: 2026-09-24

## Lesson from V4.5-A

Tightening the existing MICRO gate reduced useful activity and capture.

Candidate B therefore leaves V4.4 intact and adds an independent BURST engine only after PRIMARY, SECONDARY and MICRO all decline the sample.

## Canonical replay verification

Candidate B was rerun through the permanent parity-gated replay harness:

`scripts/canonical_replay.py`

Before Candidate B executes, that harness automatically replays V4.4 on the same arrays and asserts the result against the frozen regression oracle.

Both the 500 ms and 1 s Candidate B runs passed that baseline assertion.

## Canonical result

500 ms:

- V4.4: +₹1,097.66, 14.6695% capture, 148 trades, median segment PF 1.284.
- Candidate B: **+₹1,299.37, 17.3652% capture, 163 trades, median segment PF 1.361.**

1 second:

- V4.4: +₹333.27, 4.4539% capture, 145 trades, median segment PF 1.367.
- Candidate B: **+₹365.25, 4.8814% capture, 156 trades, median segment PF 1.382.**

Candidate B therefore increases P&L, capture and completed trade count on both canonical grids.

## Historical V4.4 numbers

The V4.4 lock originally recorded 16.36% at 500 ms and 11.54% at 1 s using an older ad-hoc replay pipeline.

Those figures remain preserved as historical experiment evidence, but they are not the regression oracle for V4.5+ because that exact pipeline could not be reproduced consistently.

The reproducible V4.4 canonical regression reference is now frozen in:

[`results/regression/canonical_v4_4_reference.json`](../../../results/regression/canonical_v4_4_reference.json)

## Caveats

Candidate B remains provisional because:

- the 50–60% research region is still negative;
- extreme spread / adverse-slippage diagnostics can erase part of BURST's advantage;
- the final 20% holdout remains unopened.

## Decision

Keep Candidate B as the current V4.5 research leader. Do not create or lock a V4.5 paper version yet.

Next work: preserve the extra BURST trades and improve only their cost robustness / lifecycle behavior.

Evidence:

[`results/simulations/2026-09-24-v4_5-burst-candidate-b/`](../../../results/simulations/2026-09-24-v4_5-burst-candidate-b/)
