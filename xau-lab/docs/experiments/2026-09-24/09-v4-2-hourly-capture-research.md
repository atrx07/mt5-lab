# 09 — V4.2 hourly-capture research

## Goal

Test whether a successor to locked V4.1 can materially increase earning velocity toward the research target of **₹50 per active market hour** without forcing trades, increasing planned risk, or opening the final holdout.

The hourly target is an evaluation benchmark, not a live quota. Quiet hours are not treated as strategy failures merely because they contain less than ₹50 of constrained ex-post opportunity.

## Versioning rule

This experiment established a clearer version policy:

- **major versions** (V5, V6, ...) require the hard graduation/promotion bar;
- **fractional versions** (V4.2, V4.3, ...) are allowed to be real experimental versions when they make a distinct measurable improvement while preserving fixed risk discipline.

Under that rule, the strongest composite from this run is recorded as **V4.2** even though it is not yet strong enough to justify a new major generation.

## Reproducibility repair

Before successor research, V4.1 replay parity was restored exactly. A quote gap greater than 5 seconds starts a new continuity session; momentum and rolling pullback features do not bridge that gap.

That reconstruction reproduces the locked results exactly:

- development: +₹127.52245, 69 trades, PF 1.323289;
- validation: +₹38.78559, 8 trades, PF 1.810702.

## Opportunity / capture diagnostic

A constrained ex-post opportunity ceiling was added for hourly diagnosis. It uses observed bid/ask execution, spread <= $0.30, fixed 3%/$4 sizing, a 30-second executable grid, fixed 60/120/300/600/900-second exits, a $4 adverse stop and a 60-second cooldown.

Direction and horizon are chosen with hindsight, so this ceiling is deliberately optimistic and is **not** a tradable forecast.

Measured opportunity:

- development: ₹5,565.71 across 68 observed hours;
- validation: ₹1,916.89 across 22 observed hours.

Locked V4.1 captured roughly 2.29% / 2.02% of that constrained ceiling.

## Search budget

Four families were explored:

- generalized slow trend / pullback: 241 candidates;
- range breakout: 240;
- mean reversion: 240;
- V4.1 + secondary-breakout composite: 321.

Total recorded parameter candidates: **1,042**.

The search was stopped rather than extended indefinitely because further parameter fishing would increase selection bias.

## V4.2 configuration

Config hash: `f75134b98dc1`.

V4.2 preserves V4.1 exactly as the primary engine. Outside V4.1's slow directional gate it permits a secondary breakout engine using:

- 120-second prior channel;
- $0.50 breakout buffer;
- aligned 30-second momentum of at least $2.00;
- prior 120-second range of at least $3.00;
- spread <= $0.30;
- 450-second secondary cooldown;
- unchanged 3% planned risk and $4 stop;
- $12 secondary take profit;
- 300-second zero-cross reversal exit;
- 900-second maximum secondary hold;
- one position at a time across both engines.

Aggregate replay:

| Metric | Development | Validation* |
| --- | ---: | ---: |
| Net P&L | **+₹225.11** | **+₹129.27** |
| PF | 1.386 | 1.918 |
| Trades | 95 | 19 |
| Max drawdown | ₹125.25 | ₹76.47 |
| Net after removing best trade | +₹133.31 | +₹46.90 |
| Avg P&L / observed hour | ₹3.31 | ₹5.88 |
| Constrained-ceiling capture | 4.04% | 6.74% |
| Hours reaching ₹50 | 2 / 68 | 2 / 22 |

\* Multiple composite variants were compared on validation during exploration, so validation is now selection-contaminated for this architecture and is not presented as pristine out-of-sample evidence.

## Stress

V4.2 remains positive under +10% spread, 1-second sampling and adverse slippage through $0.10 per side in these research partitions.

At +25% spread:

- development: +₹25.39;
- validation: **-₹25.93**.

Cost sensitivity therefore remains unresolved.

## Decision

**Record the composite as V4.2.**

It is a genuine fractional experimental version because it increases both activity and aggregate replay P&L over V4.1 without increasing planned risk or resorting to a pickier single-signal strategy.

That does **not** mean the major-generation bar has been met:

- V4.1 remains the locked baseline;
- V4.2 becomes the current experimental paper candidate;
- the ₹50/hour objective remains diagnostic rather than compulsory;
- the final 20% holdout remains unopened;
- V5 will require a materially stronger and cleaner promotion case.

The runnable experimental script is `scripts/paper_challenge_v4_2.py`.

## Evidence

Machine-readable summaries are stored under:

[`results/simulations/2026-09-24-v4_2-hourly-capture/`](../../../results/simulations/2026-09-24-v4_2-hourly-capture/)
