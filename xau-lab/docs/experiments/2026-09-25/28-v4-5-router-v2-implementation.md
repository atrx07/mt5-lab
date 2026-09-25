# 28 — V4.5 stronghold-aware Router v2 implementation

Date: 2026-09-25

Status: **implementation frozen; unseen performance validation pending; no candidate promoted**

## Objective

Implement the stronghold-aware routing mechanics requested after Experiment 27 without performing another P&L threshold search on the already known seven-day and 24-hour windows.

The implementation is allowed to use the semantics of the frozen `xau-state-v2` features and the documented engine roles. It is not allowed to fit component weights, score thresholds or feature subsets from known trade outcomes.

## Router mechanics

Candidate D's underlying engine signal rules, entry fills, lifecycle exits, risk sizing, spread payment and shared one-position slot remain unchanged.

When the slot is flat:

1. evaluate all four engine signal conditions independently;
2. retain every engine that is currently eligible after its existing cooldown/session rules;
3. obtain that side's `xau-state-v2` state from raw events;
4. compute the engine's stronghold score;
5. sort candidates by score, using the legacy PRIMARY → SECONDARY → MICRO → BURST priority only as a tie-break;
6. accept the first candidate with score >= 0;
7. fall through to lower-scoring candidates if a higher candidate does not clear neutral;
8. HOLD when no candidate clears neutral.

This directly addresses trade-retention risk from Experiment 24: rejecting PRIMARY does not automatically delete an otherwise valid MICRO/BURST/SECONDARY opportunity at the same moment.

## Frozen structural score

All engine components are equal-weight.

Common transforms:

- direction-normalized momentum: positive part passed through `tanh(x / 3)`;
- flow alignment: already bounded to [-1, 1];
- relative range/activity: `tanh(ratio - 1)`, so the causal rolling baseline equals neutral;
- heat penalty: `-tanh(max(0, ratio - 1))`;
- pullback-to-favorable-edge: `1 - 2 * pullback60`, clipped to the observed 0–1 range;
- long/short balance stability: negative absolute squashed imbalance.

Engine components:

- **PRIMARY:** 300 s momentum, 60 s momentum, 60 s flow, favorable-edge proximity, short/long stability, market-heat penalty, execution-heat penalty;
- **SECONDARY:** 30 s momentum, 60 s momentum, 10 s flow, 10-vs-60 acceleration, favorable-edge proximity, range expansion, execution-heat penalty;
- **MICRO:** 10 s momentum, 60 s momentum, 10 s flow, 60 s flow, 10-vs-60 acceleration, favorable-edge proximity, execution-heat penalty;
- **BURST:** 10 s momentum, 30 s momentum, 10 s flow, 10-vs-60 acceleration, activity expansion, range expansion, execution-heat penalty.

Frozen constants:

- score floor: **0.0**;
- momentum squash scale: **3.0**;
- component weights: **equal**;
- tie-break priority: Candidate D legacy order.

These choices are structural, not the result of a score/grid search.

## Implementation parity

`research/v4_5_router_v2.py` contains a legacy-priority mode using the same lifecycle as Candidate D. Before any Router v2 result can be considered, the implementation must reproduce Candidate D segment metrics against the existing instrumented Candidate D trace.

Known historical/recent data may be used only for this parity/diagnostic purpose. If the Router v2 known-data output looks attractive or ugly, do not alter the frozen score because of it.

## First valid evaluation

The first promotion-relevant Router v2 comparison requires a genuinely new non-overlapping raw XAU snapshot.

Pre-registered requirements:

- Router v2 net P&L > Candidate D on both 500 ms and 1 s;
- Router v2 win rate > Candidate D on both grids;
- system-level trade count >= 95% of Candidate D, unless same-time fall-through replacement keeps effective opportunity count within 5%;
- no material max-drawdown deterioration;
- no hidden change to Candidate D risk/lifecycle semantics;
- cost/slippage stress before promotion.

Failure on the new snapshot is preserved; the score is not retroactively tuned against that same validation window.

## Evidence

- implementation: `research/v4_5_router_v2.py`
- frozen config: `results/simulations/2026-09-25-v4_5-router-v2-implementation/router_v2_config.json`
- result note: `results/simulations/2026-09-25-v4_5-router-v2-implementation/README.md`
