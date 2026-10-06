# V4.5 Candidate P — persistent price + flow acceptance

Date frozen: 2026-10-06

Status: **frozen before Candidate-P P&L evaluation**

## Motivation

Candidate M materially improved hostile-regime behavior by requiring a pullback to be reclaimed before entry. Candidate N proved that adding a generic breakout lane destroys that selectivity. Candidate O proved that treating a later revisit of the reclaim anchor as a hard exit is also too aggressive.

Candidate P therefore changes neither opportunity family nor exit management. It asks whether M commits capital **too early at the first instant of accepted reclaim**.

The new hypothesis is:

> a real continuation should survive one additional acceptance clock and reproduce favorable raw quote flow after the first M-qualified confirmation, while price remains accepted beyond the same frozen reclaim level.

This is not a numeric threshold search. It reuses M's existing two-second clock and the exact same entry-flow test twice.

Known data may reject P, never promote it. Final20 remains sealed.

## Runtime information

MT5/broker-native only. No external feeds, fitted models, outcome scores, timestamp/news tables or event exclusions.

## Base setup — Candidate M unchanged through first qualification

Candidate P uses Candidate M's exact setup construction:

- >=1800 s uninterrupted sampled-session history;
- BUY `m60,m300,m1800 > 0`, SELL symmetric;
- `abs(m60)/range60 >= 0.50`, `abs(m300)/range300 >= 0.50`;
- arm when direction-normalized current `m10` is adverse by >= one current spread;
- freeze `arm_anchor = mid - m10`, arm spread, side and time;
- arm expires after 60 s or cancels if structural trend disappears/flips;
- accepted-price level is `arm_anchor +/- arm_spread`;
- price must remain beyond that level continuously for 2.0 clock seconds;
- execution gate: spread <= `$0.40` and <= `0.20*range60`;
- confirmation: `qacc >= 1`, direction-normalized raw `dir_mid_move2 > 0` and `dir_event_imb2 > 0`.

The first instant satisfying all of the above is **confirmation A**. Candidate M would enter there. Candidate P does not.

## New commitment rule — confirmation B

At confirmation A, freeze only its timestamp. Do not move the reclaim/acceptance level and do not inspect future values.

Candidate P waits one additional **2.0 clock seconds**, reusing the already-frozen Candidate-M acceptance horizon.

During the wait:

- price must remain continuously beyond the original accepted-price level;
- if price falls back inside the level, both price acceptance and confirmation-A state reset;
- the original 60-second arm timeout and structural-trend cancellation continue to apply.

At the first sampled row >=2.0 clock seconds after confirmation A:

- execution gate must still pass;
- the exact same `qacc` + raw-flow confirmation must pass again.

If it passes, this is **confirmation B** and Candidate P enters at executable bid/ask.

If B fails, confirmation A is discarded. The setup may establish a new confirmation A later while the original arm is still causally alive; no thresholds are relaxed.

Thus P requires two independent causal snapshots of favorable raw flow separated by a full M acceptance clock while price never loses acceptance.

## Position lifecycle

Exactly Candidate M:

- 3% planned account risk;
- `$4` emergency stop;
- `$12` take profit;
- 1800 s max hold;
- `m300` direction-failure exit;
- Candidate-H flow-confirmed profit protection: arm after +1R MFE with >=1R giveback, checks every 5 s, two adverse raw-flow confirmations.

Candidate O's anchor-invalidation exit is **not** included.

## Random / discontinuity behavior

- canonical >5 s session breaks clear time-dependent setup history;
- setup creation again requires 1800 s continuity;
- no synthetic empty buckets;
- no session-time or news exception table;
- both confirmations are observed-tick causal and use executable quotes.

## Development evaluation

Run P unchanged against:

1. historical canonical first80 only, 500 ms and 1 s;
2. frozen recent24h archive;
3. current seven-day archive;
4. all six Experiment-48 Stage-1 blocks individually and pooled;
5. three newly predeclared random seeds **57011, 57012, 57013**, 80 real contiguous four-hour windows/seed/grid alternating historical/current source;
6. +`$0.10` adverse slippage per side on all three full archives.

Comparators: frozen M/H/D. Final20 stays sealed. Current7d and overlapping Stage-1 blocks are not summed as independent evidence.

## Predeclared development-survival screen

P earns brand-new prospective validation only if all hold on both grids:

- historical first80 compounded P&L > 0;
- recent24h terminal-equity P&L >= 0;
- current7d terminal-equity P&L >= 0;
- >=20 completed trades on historical first80 and current7d;
- pooled six-block P&L >= 0;
- >=3/6 Stage-1 blocks positive;
- every predeclared random seed has mean four-hour P&L > 0;
- pooled random median >=0;
- pooled random positive-window fraction >=50%;
- historical, recent24h and current7d each remain >=0 under +`$0.10` adverse slippage/side;
- D/H/M comparator parity passes.

If P fails, do not tune the extra two-second clock, number of confirmations, M thresholds, stop/TP or exit rules against these outcomes. At that point the same known evidence has rejected both additive-entry and simple post-entry fixes; further rapid candidate search on these datasets should stop rather than meta-overfit.

Passing known data still does not authorize live money or V4.5 lock; it only permits new prospective evidence.
