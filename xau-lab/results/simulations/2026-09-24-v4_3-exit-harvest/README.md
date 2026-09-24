# V4.3 exit-harvest experiment

Date: 2026-09-24

Status: **V4.3 recorded as an experimental fractional version. V4.2 remains the direct baseline; the final 20% holdout remains unopened.**

## Objective

After the earlier >=20% attempt failed, this run narrowed the immediate engineering target to **>=10% constrained-opportunity capture** without changing the 3% planned-risk rule or forcing additional trades.

The working hypothesis was that the easiest missing capture was not another entry family, but poor harvesting of moves already detected by the V4.2 architecture.

## What changed

V4.3 leaves V4.2 entry logic unchanged.

The changes are in position management:

- PRIMARY: $30 take-profit cap, 2400 s maximum hold, 120 s momentum zero-cross reversal, $6 trail trigger with an $8 give-back, and a recovery-to-breakeven exit after a favorable $10 move;
- BREAKOUT: $21 take-profit cap, 900 s maximum hold, existing 300 s zero-cross reversal, no trailing exit, and the same $10 recovery-to-breakeven rule;
- after a profitable BREAKOUT exit, the secondary cooldown contracts from 450 s to 120 s so a legitimate continuation can be taken;
- after a non-profitable BREAKOUT exit, cooldown remains 450 s;
- 3% planned risk, $4 stop distance, $0.30 spread gate and one-position-at-a-time behavior are unchanged.

Spread-recovery arming was tested but did not improve the selected configuration, so it was not promoted.

## Search

The run evaluated roughly **7,800 targeted configurations** across exit harvesting, profitable-exit continuation cooldowns, reset-focused diagnostics and sampling/cost robustness neighborhoods.

Because this search repeatedly used the first-80% research pool, none of its internal chronological segments are described as untouched validation.

## Selected result

On the continuous first-80% research replay from ₹500:

- final synthetic balance: **₹1,436.69**;
- net: **+₹936.69**;
- constrained-opportunity capture: **12.52%**;
- PF: **2.141**;
- 120 trades;
- max drawdown: **₹170.89**;
- best trade: +₹187.42;
- worst trade: -₹39.08.

Removing the single best trade still leaves **+₹749.27**, or **10.01% capture**. This was a useful anti-outlier check because the >=10% objective still survives that deletion.

Engine contribution in the selected continuous replay:

- PRIMARY: 81 trades, +₹445.29;
- BREAKOUT: 39 trades, +₹491.40.

Exit counts:

- trend reversal: 104;
- stop: 10;
- take profit: 4;
- trail: 1;
- max hold: 1.

## Chronological reset diagnostics

All five research segments were positive when independently reset to ₹500:

| Raw fraction | Net | PF | Trades |
| --- | ---: | ---: | ---: |
| 0–40% | +₹497.26 | 2.072 | 77 |
| 40–50% | +₹52.04 | 2.535 | 18 |
| 50–60% | +₹1.50 | 1.159 | 5 |
| 60–70% | +₹34.68 | 1.498 | 10 |
| 70–80% | +₹102.52 | 2.943 | 10 |

Their reset-P&L sum is +₹687.99, equivalent to 9.19% of the common ex-post ceiling. The >=10% result therefore belongs to the continuous compounding replay, not to the reset-segment sum.

## Stress

The selected V4.3 candidate stayed profitable under every recorded stress:

- +10% spread: +₹526.09, PF 1.629;
- +25% spread: +₹122.55, PF 1.322;
- adverse slippage $0.02 / side: +₹893.16;
- adverse slippage $0.05 / side: +₹828.27;
- adverse slippage $0.10 / side: +₹745.88, PF 1.880;
- 1-second sampling: +₹225.60, PF 1.335.

The **1-second sampling drop is a major caveat**: profitability remains positive, but capture falls from 12.52% to about 3.01%. V4.3 is therefore still cadence-sensitive and is not evidence of a production-ready edge.

## Decision

Record this configuration as **V4.3 experimental**.

It crossed the requested 10% continuous capture target without raising planned risk, remained above 10% after deleting its single best trade, kept all five reset research segments positive, and remained profitable in the recorded execution-cost stresses.

This is still research evidence, not a profitability claim. The final 20% holdout remains sealed.
