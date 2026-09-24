# 15 — V4.5 additive BURST candidate B

Date: 2026-09-24

## Lesson from V4.5-A

Tightening the existing MICRO gate reduced useful activity and capture.

The next experiment therefore left all V4.4 engines untouched and added an independent BURST engine that only gets the shared slot after PRIMARY, SECONDARY and MICRO all decline the current sample.

## Result

In the same reconstructed harness, Candidate B beats reconstructed V4.4 on **P&L, capture and trade count at both 500 ms and 1 s**.

500 ms:

- V4.4: +₹1,097.66, 14.67% capture, 148 trades, median segment PF 1.284.
- Candidate B: **+₹1,299.37, 17.37% capture, 163 trades, median segment PF 1.361.**

1 second:

- V4.4: +₹333.27, 4.45% capture, 145 trades, median segment PF 1.367.
- Candidate B: **+₹365.25, 4.88% capture, 156 trades, median segment PF 1.382.**

This is the first V4.5 research candidate in this sequence that moves the desired three metrics in the same direction on both grids.

## Caveats

The fresh V4.5 harness still fails to reproduce the official locked V4.4 1-second headline, so Candidate B's absolute capture is not promotion evidence.

Extreme spread and adverse-slippage diagnostics also show that the extra BURST trades are not yet cost-robust enough.

## Decision

Keep Candidate B as the current V4.5 research leader. Do not create or lock a V4.5 paper version yet.

Next work: preserve the BURST engine and improve its cost-aware admission / lifecycle handling without reducing the V4.4 engines' existing opportunity set.

Evidence:

[`results/simulations/2026-09-24-v4_5-burst-candidate-b/`](../../../results/simulations/2026-09-24-v4_5-burst-candidate-b/)
