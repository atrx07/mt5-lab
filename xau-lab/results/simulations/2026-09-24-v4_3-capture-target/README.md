# V4.3 — locked regime-adaptive composite

Date: 2026-09-24

Status: **V4.3 locked as a fractional research version.**

V4.3 is the strongest fixed regime-adaptive candidate from the capture-target study. The original aspirational >=20% capture target was not reached; the version is locked because it is a meaningful fractional improvement over V4.2 and was explicitly selected for preservation as V4.3.

Any changes after this point become **V4.4**.

## Scope discipline

Only the original first 80% of the seven-day broker dataset was used for the V4.3 research and selection process. The final 20% holdout remains unopened.

Research pool boundaries:

- seed/search segment: 0–40% of the full dataset;
- evaluation segment 1: 40–50%;
- evaluation segment 2: 50–60%;
- evaluation segment 3: 60–70%;
- evaluation segment 4: 70–80%;
- final holdout: 80–100%, unopened.

The constrained ex-post opportunity ceiling over the first 80% is **₹7,482.60**.

## V4.2 baseline

Before V4.3 research, V4.2 replay parity was restored exactly.

Continuous V4.2 performance over the same first-80% research pool:

- +₹412.58;
- PF 1.524;
- 114 trades;
- capture ~5.51%.

## Locked V4.3 configuration

High activity:

- 300-second range >= $5;
- 60-second efficiency ratio >= 0.03.

In high activity:

- primary cooldown: 450 s;
- secondary cooldown: 90 s;
- secondary breakout may operate inside the V4.1 slow directional gate;
- secondary channel: 120 s;
- secondary buffer: max($0.50, 0.02 × channel range);
- secondary channel range >= $4;
- |30 s momentum| >= $1.50;
- primary: $25 TP, 900 s max hold, no momentum-reversal exit;
- secondary: $8 TP, 1200 s max hold, no momentum-reversal exit;
- recorded secondary trail parameters: +$12 trigger / $3 give-back.

Outside high activity, the V4.2 entry/exit rules remain in force.

Risk remains unchanged at 3% planned risk per trade with a $4 stop and 100x synthetic leverage cap.

## Locked research result

Run continuously from ₹500 over the complete first-80% research pool:

- net: **+₹603.60**;
- final synthetic balance: **₹1,103.60**;
- PF: **1.456**;
- trades: **114**;
- max drawdown: **₹257.52**;
- best trade: **+₹173.16**;
- worst trade: **-₹34.57**;
- opportunity capture: **8.07%**.

This is a research replay result, not a profitability guarantee.

## 20% target

The original 20% target would have required approximately ₹1,496.52 against the ₹7,482.60 constrained opportunity ceiling.

V4.3 did not meet that target.

A non-causal hindsight profile oracle across the tested families reached only 17.27%, which was one reason the broad search was stopped instead of continuing to parameter-fish the same feature set.

## Focused exit-harvest follow-up

A later exploratory tweak widened the high-regime profit targets to $30 primary / $15 secondary. It looked much stronger on the aggregate reconstructed research harness but failed the internal 60–80% comparison:

| Metric | Locked V4.3 adaptive | $30/$15 exit-harvest |
| --- | ---: | ---: |
| Net P&L | **+₹56.71** | +₹29.79 |
| PF | **1.335** | 1.186 |
| Trades | 18 | 17 |
| Max DD | **₹89.59** | ₹133.43 |
| Capture vs ₹1,916.8875 internal ceiling | **2.96%** | 1.55% |

The locked V4.3 candidate also beat that tweak in both 60–70% and 70–80% subfolds. The $30/$15 variant is therefore rejected.

## Decision

**Lock the 8.07% adaptive candidate as V4.3.**

- V4.3 becomes the current experimental paper version.
- V4.2 remains available as the previous version.
- V4.1 remains the locked slow-strategy baseline.
- The final 20% holdout remains unopened.
- Any further tuning or structural change becomes V4.4.

## Implementation

`scripts/paper_challenge_v4_3.py`
