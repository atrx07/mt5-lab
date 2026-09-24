# V4.4 manager / exit optimization

Date: 2026-09-24

Status: **research only; no V4.4 lock. V4.3 remains the current locked fractional version.**

## Scope

This pass starts from provisional V4.4 Candidate A (V4.3 primary/secondary plus the MICRO structural pullback/resumption engine) and tests the management ideas raised after Candidate A:

- per-engine exits;
- early stagnation exits;
- breakout-failure exits;
- candidate arbitration / priority changes;
- shadow-signal opportunity logging;
- tight MICRO exit tuning;
- MICRO partial profit-taking;
- simple hostile-regime guards;
- 1-second sampling robustness;
- spread/slippage stress.

The final 20% holdout remains unopened.

All headline comparisons below use the same reconstructed 500 ms research harness. That harness still does not exactly reproduce canonical locked V4.3, so absolute capture values remain provisional until parity is reconciled.

## Candidate A reference

Same-harness Candidate A:

- net: **+₹1,063.48**
- PF: **1.600**
- trades: **151**
- max DD: **₹198.08**
- provisional capture: **14.21%**

## What worked at 500 ms

The strongest simple management changes were early stagnation exits:

- SECONDARY: after 60 s, exit if peak favorable move never exceeded $0.50;
- MICRO: after 60 s, exit if peak favorable move never exceeded $0.50.

Applied together, these produced:

- +₹1,185.80;
- PF 1.691;
- 152 trades;
- max DD ₹176.87;
- provisional capture 15.85%.

Adding a 67% MICRO partial realization at +$6 increased the 500 ms result further to **+₹1,248.78 / PF 1.712 / 16.69% capture**.

However, this apparent leader failed the 1-second robustness test because the SECONDARY stagnation rule was highly sampling-sensitive.

## Robust management candidate J

The strongest management idea that improved both 500 ms and 1-second replays removes the fragile SECONDARY stagnation exit and keeps only:

1. Candidate A entries and engine priority;
2. MICRO early-stagnation exit:
   - after 60 s;
   - if peak favorable move < $0.50, exit;
3. MICRO partial profit:
   - once move reaches +$6;
   - realize 67% of the synthetic MICRO position;
   - let the remaining 33% continue under the existing $10 TP / +$4 trigger / $2 give-back trail / $4 stop rules.

500 ms result:

- net **+₹1,179.81**;
- PF **1.662**;
- 151 trades;
- max DD **₹197.76**;
- provisional capture **15.77%**.

Compared with Candidate A in the same harness:

- +₹116.32 additional net P&L;
- PF 1.600 -> 1.662;
- trade count unchanged at 151;
- max DD slightly lower;
- capture 14.21% -> 15.77%.

The MICRO partial does not increase planned entry risk. It only reduces exposure after a favorable +$6 move.

## 1-second sampling robustness

| Configuration | Net P&L | PF | Trades | Max DD | Capture |
| --- | ---: | ---: | ---: | ---: | ---: |
| Candidate A, 500 ms | +₹1,063.48 | 1.600 | 151 | ₹198.08 | 14.21% |
| Candidate J, 500 ms | **+₹1,179.81** | **1.662** | 151 | **₹197.76** | **15.77%** |
| Candidate A, 1 s | +₹673.25 | 1.339 | 155 | ₹233.02 | 9.00% |
| Candidate J, 1 s | **+₹734.24** | **1.362** | 155 | **₹224.26** | **9.81%** |

The absolute performance drops materially at 1-second sampling, but Candidate J still improves P&L, PF and drawdown relative to Candidate A.

By contrast, the SECONDARY 60-second stagnation exit collapsed at 1-second sampling and is rejected for now.

## Negative results

### Candidate arbitration

Changing priority from PRIMARY -> SECONDARY -> MICRO to PRIMARY -> MICRO -> SECONDARY did not improve aggregate performance.

A hand-built quality-score arbitration layer performed substantially worse than Candidate A. The current sample does not justify replacing deterministic engine priority with a score router.

### SECONDARY breakout-failure exit

Exiting a secondary trade simply because it returned inside its prior channel after 15-60 seconds was destructive. The best tested 30-second version fell to roughly +₹507 and PF 1.39.

### PRIMARY trailing

Adding generic PRIMARY trails also reduced aggregate P&L. The least damaging tested trail (+$20 trigger / $8 give-back) still underperformed Candidate A.

### Simple hostile-regime guard

Requiring MICRO to agree more strongly with 300-second momentum reduced activity and aggregate P&L and did not solve the weak research fold. No general hostile-regime veto is accepted from this pass.

## Shadow blocked-opportunity diagnostic

Raw structural signals were logged while another engine occupied the shared position slot, debounced to at most one event per engine/direction per 60 seconds, then replayed independently as a diagnostic.

The blocked SECONDARY set was negative in aggregate, while blocked PRIMARY and MICRO signals were positive in aggregate.

This supports keeping SECONDARY lower in strategic importance, but the direct priority/arbitration simulations did not improve enough to justify changing execution priority yet.

The shadow study is diagnostic only; repeated raw structural signals are not equivalent to executable independent trades.

## Cost stress — Candidate J

| Stress | Net P&L | PF | Trades | Max DD |
| --- | ---: | ---: | ---: | ---: |
| Base | +₹1,179.81 | 1.662 | 151 | ₹197.76 |
| $0.02 adverse slippage / side | +₹1,053.83 | 1.588 | 153 | ₹200.46 |
| $0.05 adverse slippage / side | +₹944.79 | 1.529 | 153 | ₹218.80 |
| $0.10 adverse slippage / side | +₹788.40 | 1.459 | 154 | ₹221.65 |
| Spread +10% | +₹962.20 | 1.525 | 143 | ₹258.59 |
| Spread +25% | +₹353.11 | 1.345 | 116 | ₹169.02 |

Candidate J remains positive in all tested stresses, but the +25% spread case is still a major degradation and actually trails Candidate A under that extreme spread shock.

## Decision

**Do not lock V4.4 yet.**

Candidate J is the strongest *robust management follow-up* from this pass, but two issues remain:

1. canonical V4.3 replay parity is still unresolved;
2. 1-second Candidate J reaches ~9.81% capture, just under the 10% research target.

The final 20% holdout remains sealed.
