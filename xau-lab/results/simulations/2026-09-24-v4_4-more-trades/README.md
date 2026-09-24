# V4.4 more-trades research — provisional candidate A

Date: 2026-09-24

Status: **research in progress; no V4.4 lock and no paper_challenge_v4_4.py yet.**

## Goal

Increase trade frequency without simply loosening V4.3 into lower-quality overtrading.

The frozen run spec requires:

- more trades than V4.3;
- constrained-opportunity capture >=10%;
- PF preferably at or above V4.3 territory;
- no material drawdown explosion;
- no increase to the 3% planned-risk fraction or $4 stop.

The final 20% holdout remains unopened.

## Architecture tested

The first pass keeps the V4.3 primary and secondary engines and adds a third **MICRO** candidate engine.

A MICRO candidate must form a genuine short-horizon reset / resumption structure rather than a timer-only re-entry.

Provisional candidate A requires, at entry time:

- 120-second momentum >= +$6 for BUY / <= -$6 for SELL;
- 60-second momentum >= +$2 / <= -$2;
- a real opposite 10-second pullback of at least $0.50 within the previous 30 seconds;
- current 10-second resumption >= $0.20 in the trend direction;
- 60-second path efficiency >= 0.12;
- 60-second range >= $2;
- current spread <= 25% of the 60-second range and <= the existing $0.30 hard cap;
- 10-second raw-tick imbalance may be neutral or better in the trade direction;
- 10s / 30s quote-rate ratio >= 0.65;
- 60-second MICRO cooldown.

MICRO exit rules in candidate A:

- $4 stop;
- $10 take profit;
- 900-second max hold;
- 300-second momentum reversal exit;
- trail activates after +$4 and exits after a $2 give-back.

One position is shared across PRIMARY / SECONDARY / MICRO, so there is no pyramiding.

## Search

A deterministic randomized search generated 1,800 parameter combinations from the frozen candidate family. 1,714 passed the basic trade-count filter on the 0–40% seed block.

The strongest 90 seed candidates were carried into the later first-80% research segments. Candidate A was selected from that internally evaluated set.

Because the later research folds participated in candidate ranking, these folds are **selection-contaminated** for candidate A. They are useful research evidence, not pristine OOS evidence.

## Same-harness comparison

The V4.3 reconstruction used for this pass does not exactly reproduce the archived canonical V4.3 +₹603.60 / 8.07% result. In this harness V4.3 produces +₹683.22 and 9.13% capture.

Therefore the absolute candidate capture below is **provisional**. The relative same-harness comparison is the meaningful result until replay parity is reconciled.

| Metric | V4.3 same harness | Candidate A |
| --- | ---: | ---: |
| Net P&L | +₹683.22 | **+₹1,063.48** |
| PF | 1.485 | **1.600** |
| Trades | 115 | **151** |
| Wins | 52 | **69** |
| Max DD | **₹184.16** | ₹198.08 |
| Capture vs ₹7,482.60 ceiling | 9.13% | **14.21%** |
| Trades / 90 observed hours | 1.28 | **1.68** |

Same-harness changes:

- net P&L: +55.7%;
- completed trades: +31.3%;
- PF: +7.7%;
- max DD: +7.6%.

This is the type of change the run was looking for: activity increased substantially without the PF collapsing.

## Chronological research segments

Candidate A with each segment reset to ₹500:

| Segment | Net P&L | PF | Trades | Max DD |
| --- | ---: | ---: | ---: | ---: |
| 0–40% seed | +₹674.42 | 1.764 | 93 | ₹190.94 |
| 40–50% | +₹67.43 | 1.579 | 22 | ₹46.12 |
| 50–60% | -₹19.09 | 0.508 | 7 | ₹31.96 |
| 60–70% | +₹10.23 | 1.101 | 12 | ₹55.92 |
| 70–80% | +₹94.21 | 2.075 | 16 | ₹21.90 |

The 50–60% segment remains the obvious weak regime and must not be hidden by the aggregate result.

## Engine attribution

On the continuous first-80% run:

| Engine | Trades | Wins | Win rate | Net P&L | Avg trade |
| --- | ---: | ---: | ---: | ---: | ---: |
| PRIMARY | 75 | 36 | 48.0% | +₹729.16 | +₹9.72 |
| SECONDARY | 35 | 15 | 42.9% | +₹72.11 | +₹2.06 |
| MICRO | 41 | 18 | 43.9% | **+₹262.21** | **+₹6.40** |

The MICRO engine is not merely generating extra tickets: in this harness its own aggregate contribution is positive.

## Cost stress

| Stress | Candidate A net | PF | Trades | V4.3 same-harness net | V4.3 PF |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base | +₹1,063.48 | 1.600 | 151 | +₹683.22 | 1.485 |
| Slippage $0.02 each side | +₹945.36 | 1.531 | 153 | +₹525.96 | 1.372 |
| Slippage $0.05 each side | +₹857.16 | 1.480 | 153 | +₹490.80 | 1.347 |
| Slippage $0.10 each side | +₹733.70 | 1.428 | 154 | +₹441.13 | 1.317 |
| Spread +10% | +₹899.72 | 1.497 | 143 | +₹706.05 | 1.421 |
| Spread +25% | +₹389.80 | 1.378 | 115 | +₹159.18 | 1.190 |

Cost sensitivity still exists, but candidate A remains positive in every stress shown here.

## Current decision

**Do not lock V4.4 yet.**

Candidate A is promising enough to continue:

- materially more trades;
- higher PF in the same harness;
- >10% provisional capture;
- positive MICRO-engine aggregate contribution;
- acceptable same-harness DD increase;
- positive tested cost stresses.

Before a V4.4 lock:

1. reconcile the remaining V4.3 replay-parity discrepancy;
2. retest the candidate in the parity-restored simulator;
3. investigate the weak 50–60% regime without fitting directly to it;
4. run 1-second sampling / feature-lag robustness;
5. keep the final 20% holdout sealed.
