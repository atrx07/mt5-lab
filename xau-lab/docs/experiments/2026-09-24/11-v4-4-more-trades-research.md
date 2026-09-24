# 11 — V4.4 more-trades research

Date: 2026-09-24

## Goal

Increase trade frequency without sacrificing expectancy, while preserving the locked V4.3 risk discipline.

The final 20% holdout remains unopened.

## Frozen methodology

The run spec is recorded in [`docs/plans/V4_4_RUN_SPEC.md`](../../plans/V4_4_RUN_SPEC.md).

The first pass keeps the locked V4.3 primary and secondary engines and adds a short-horizon MICRO pullback/resumption candidate generator with a cost/quality gate.

## Search result

1,800 deterministic randomized parameter combinations were generated; 1,714 passed the seed trade-count filter. The strongest 90 seed candidates were evaluated across the later first-80% research segments.

A provisional candidate A emerged with:

- 151 trades vs 115 for V4.3 in the same reconstructed harness;
- +₹1,063.48 vs +₹683.22 same-harness net P&L;
- PF 1.600 vs 1.485;
- max DD ₹198.08 vs ₹184.16;
- provisional constrained-opportunity capture 14.21% vs 9.13% in the same harness.

The MICRO engine itself contributed 41 trades and +₹262.21 in the continuous research replay.

## Important parity caveat

The reconstructed harness used for this run does not reproduce the canonical locked V4.3 result exactly.

Canonical V4.3:

- +₹603.60;
- PF 1.456;
- 114 trades;
- 8.07% capture.

Current reconstructed reference:

- +₹683.22;
- PF 1.485;
- 115 trades;
- 9.13% capture.

Therefore candidate A's absolute 14.21% capture is provisional. The meaningful evidence for now is the same-harness relative improvement.

## Fold behavior

Candidate A reset to ₹500 on each chronological region:

- 0–40%: +₹674.42, PF 1.764, 93 trades;
- 40–50%: +₹67.43, PF 1.579, 22 trades;
- 50–60%: -₹19.09, PF 0.508, 7 trades;
- 60–70%: +₹10.23, PF 1.101, 12 trades;
- 70–80%: +₹94.21, PF 2.075, 16 trades.

The 50–60% regime is a real weakness and is not hidden by the aggregate result.

## Cost stress

Candidate A remained positive under:

- $0.02 / $0.05 / $0.10 adverse slippage per side;
- +10% and +25% spread stress.

It continued to outperform the same-harness V4.3 reference in each listed stress.

## Decision

**Continue research; do not lock V4.4 yet.**

Next steps:

1. reconcile V4.3 replay parity;
2. rerun candidate A in the parity-restored simulator;
3. run 1-second sampling and feature-lag tests;
4. investigate the weak 50–60% regime without directly fitting to it;
5. keep the final 20% holdout sealed.

Evidence: [`results/simulations/2026-09-24-v4_4-more-trades/`](../../../results/simulations/2026-09-24-v4_4-more-trades/)
