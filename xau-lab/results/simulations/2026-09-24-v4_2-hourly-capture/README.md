# V4.2 hourly-capture experiment

Date: 2026-09-24

Status: **recorded as V4.2, an experimental fractional version in the V4 family. V4.1 remains the locked baseline; V4.2 is the current experimental paper candidate.**

## Objective

The new objective was not merely total profitability. The run asked whether a successor could move toward **₹50 per active market hour** while refusing to force trades when the market did not offer enough opportunity. It also introduced an opportunity/capture diagnostic so a quiet hour is distinguished from an hour in which the engine left substantial movement unused. Risk remained fixed at 3% planned risk per trade with the same $4 stop-distance sizing and no real order execution.

The versioning policy is now explicit: strict promotion applies to new **major** generations such as V5. Fractional versions such as V4.2 may be recorded as experimental iterations when they make a distinct, measurable improvement even if they do not satisfy the next major-generation bar.

## Replay parity repaired first

Before testing successors, the V4.1 replay was reconstructed exactly. The critical historical feature rule is that a sampled quote gap greater than 5 seconds starts a new continuity session; momentum and rolling pullback features may not bridge that gap. With that restored, the replay reproduces the locked results exactly: development +₹127.52245 on 69 trades and validation +₹38.78559 on 8 trades.

## Opportunity benchmark

The hourly benchmark is a **constrained ex-post opportunity ceiling**, not an achievable forecast and not a trading signal. It uses a 30-second executable grid, minute-aligned candidate entries, observed bid/ask, spread <= $0.30, the same 3%/$4 risk sizing, fixed future holding horizons (60/120/300/600/900 seconds), a $4 adverse stop, a 60-second post-exit cooldown, and weighted non-overlap selection. Direction and fixed horizon are chosen with hindsight, so the ceiling is intentionally optimistic.

Development contained ₹5,565.71 of constrained ex-post opportunity across 68 observed clock-hours; validation contained ₹1,916.89 across 22 hours. Because the ceiling uses hindsight, **capture ratio must be read as a diagnostic, not as an attainable efficiency target.**

## Search budget

Four rule families were explored on development data: generalized trend/pullback, range breakout, mean reversion, and a composite retaining V4.1 as the primary engine while adding a secondary breakout only outside V4.1's slow directional gate. The recorded sweeps total **1,042 parameter candidates**, plus a small composite architecture comparison. Continuing to search indefinitely after this budget would increase selection/overfit risk rather than strengthen the evidence.

## V4.2 configuration

Config hash: `f75134b98dc1` (sweep row `8c1a6fd2881d`).

V4.2 keeps V4.1 intact as the primary engine and adds this secondary engine only when neither V4.1 slow gate is active:

- prior 120-second channel, excluding the current observation;
- breakout buffer: $0.50;
- 30-second momentum must agree by at least $2.00;
- prior 120-second range >= $3.00;
- observed spread <= $0.30;
- secondary cooldown 450 seconds;
- same 3% risk sizing and $4 stop;
- secondary take-profit $12;
- exit when 300-second momentum crosses zero against the position;
- maximum secondary hold 900 seconds;
- one position at a time across both engines.

It materially improves aggregate replay performance versus V4.1: development +₹225.11 / PF 1.386 / 95 trades / ₹125.25 max drawdown; validation +₹129.27 / PF 1.918 / 19 trades / ₹76.47 max drawdown. Removing the single best trade still leaves +₹133.31 development and +₹46.90 validation. All four development UTC-day reset runs remained positive.

## Why V4.2 is still experimental

The new hourly objective is still nowhere close. V4.2 averages only ₹3.31 per observed development hour and ₹5.88 per observed validation hour. Its constrained-ceiling capture rises from V4.1's ~2.29% / ~2.02% to ~4.04% / ~6.74%, but that still means the engine ignores most ex-post movement. It reached ₹50 in only 2 of 68 development hours and 2 of 22 validation hours.

Cost sensitivity also remains. +10% spread stress stays profitable on both research partitions, but +25% spread produces +₹25.39 development and **-₹25.93 validation**. One-second sampling remains positive (+₹83.79 / +₹60.53), and adverse slippage tests through $0.10 per side remain positive.

This is sufficient to record a real fractional version because it increases activity and aggregate replay P&L without raising planned risk. It is **not** sufficient evidence for a V5-style major-generation graduation.

## Validation caveat

During exploration, multiple composite variants were compared on the validation partition. From that point onward validation ceased to be an untouched selection set for this architecture. This is recorded explicitly rather than silently treating the V4.2 result as pristine validation evidence. The final 20% holdout has **not** been evaluated in this run.

## Current implementation

The live-paper implementation is now:

`scripts/paper_challenge_v4_2.py`

It logs both trades and hourly realized-P&L reviews. The ₹50/hour target is diagnostic only and never forces entries, loosens rules, or raises risk.

## Next research implication

V4.2 shows that a secondary breakout can increase activity without immediately destroying the V4.1 edge. The remaining gap to the hourly goal is still large, so future fractional experiments should test genuinely new information/model families rather than simply parameter-fishing the same rule set.
