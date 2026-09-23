# V4.2 hourly-capture research — no promotion

Date: 2026-09-24

Status: **research run complete; V4.1 remains the locked strategy. No V4.2 live-paper script is promoted by this run.**

## Objective

The new objective was not merely total profitability. The run asked whether a successor could move toward **₹50 per active market hour** while refusing to force trades when the market did not offer enough opportunity. It also introduced an opportunity/capture diagnostic so a quiet hour is distinguished from an hour in which the engine left substantial movement unused. Risk remained fixed at 3% planned risk per trade with the same $4 stop-distance sizing and no real order execution.

## Replay parity repaired first

Before testing successors, the V4.1 replay was reconstructed exactly. The critical historical feature rule is that a sampled quote gap greater than 5 seconds starts a new continuity session; momentum and rolling pullback features may not bridge that gap. With that restored, the replay reproduces the locked results exactly: development +₹127.52245 on 69 trades and validation +₹38.78559 on 8 trades.

## Opportunity benchmark

The hourly benchmark is a **constrained ex-post opportunity ceiling**, not an achievable forecast and not a trading signal. It uses a 30-second executable grid, minute-aligned candidate entries, observed bid/ask, spread <= $0.30, the same 3%/$4 risk sizing, fixed future holding horizons (60/120/300/600/900 seconds), a $4 adverse stop, a 60-second post-exit cooldown, and weighted non-overlap selection. Direction and fixed horizon are chosen with hindsight, so the ceiling is intentionally optimistic.

Development contained ₹5,565.71 of constrained ex-post opportunity across 68 observed clock-hours; validation contained ₹1,916.89 across 22 hours. Because the ceiling uses hindsight, **capture ratio must be read as a diagnostic, not as an attainable efficiency target.**

## Search budget

Four rule families were explored on development data: generalized trend/pullback, range breakout, mean reversion, and a composite retaining V4.1 as the primary engine while adding a secondary breakout only outside V4.1's slow directional gate. The recorded sweeps total **1,042 parameter candidates**, plus a small composite architecture comparison. Continuing to search indefinitely after this budget would increase selection/overfit risk rather than strengthen the evidence.

## Strongest research candidate

The strongest aggregate candidate found has config hash `f75134b98dc1` (sweep row `8c1a6fd2881d`). It keeps V4.1 intact as the primary engine and adds this secondary engine only when neither V4.1 slow gate is active:

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

## Why it is not V4.2 yet

The new hourly objective is still nowhere close. The candidate averages only ₹3.31 per observed development hour and ₹5.88 per observed validation hour. Its constrained-ceiling capture rises from V4.1's ~2.29% / ~2.02% to ~4.04% / ~6.74%, but that still means the engine ignores most ex-post movement. It reached ₹50 in only 2 of 68 development hours and 2 of 22 validation hours.

Cost sensitivity also remains. +10% spread stress stays profitable on both research partitions, but +25% spread produces +₹25.39 development and **-₹25.93 validation**. One-second sampling remains positive (+₹83.79 / +₹60.53), and adverse slippage tests through $0.10 per side remain positive.

Therefore this candidate is worth retaining, but under the promotion rule it is **not satisfying enough to replace V4.1**. No `paper_challenge_v4_2.py` is created and the final holdout remains unopened.

## Validation caveat

During exploration, multiple composite variants were compared on the validation partition. From that point onward validation ceased to be an untouched selection set for this architecture. This is recorded explicitly rather than silently treating the strongest composite as pristine validation evidence. The final 20% holdout has **not** been evaluated in this run.

## Next research implication

The result says the problem is no longer simply “find a profitable filter.” A secondary breakout can increase activity without immediately destroying the edge, but the remaining gap to the hourly goal is too large to justify more parameter fishing in the same rule family. A genuinely new information source or model family should be tested next, with the holdout kept closed until a successor is frozen.
