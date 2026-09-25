# 34 — V4.5 SNAPBACK complementary-engine foundation

Date: 2026-09-25

Status: **engine rules frozen before P&L evaluation; execution pending**

## Why a new engine instead of another router

Experiment 33 showed that on the recent 500 ms window every existing engine is independently negative. Exact simultaneous multi-engine opportunities occur only about 2–4% of the time.

A router cannot select a positive edge that does not exist in the opportunity family.

Experiment 34 therefore adds a **structurally different** candidate opportunity generator rather than modifying the Router-v2/v3 score.

## SNAPBACK concept

The existing MICRO lane is continuation-oriented: it wants an established 60/120 s trend, a short pullback, then renewed short-horizon momentum and flow in the trend direction while 60 s path efficiency is at least 0.12.

SNAPBACK uses the natural opposite case:

- keep the same established 60/120 s background move;
- require **low** 60 s path efficiency (`ER60 < 0.12`);
- require short-horizon momentum to reverse against the background move;
- require 10 s quote-flow imbalance to agree with the reversal;
- reuse MICRO/global range, activity and spread-quality gates.

No outcome-derived threshold is introduced.

For example, after an upward background move SNAPBACK sells only when current 10 s momentum and flow have flipped negative. The buy case is symmetric.

## Frozen signal constants

All are inherited directly from existing Candidate-D gates:

- cooldown 60 s;
- range60 ≥ $2;
- ER60 < 0.12, using the complement of MICRO's existing ≥0.12 split;
- qacc ≥ 0.65;
- spread ≤ 25% of range60 and ≤ $0.30;
- |m120| ≥ $6;
- |m60| ≥ $2;
- reversal |m10| ≥ $0.20;
- prior 30 s m10 extreme ≥ $0.50 in the background direction.

## Frozen lifecycle

The countertrend lane reuses BURST's short lifecycle constants:

- $4 emergency stop;
- $12 take profit;
- 120 s max hold;
- stagnation after 60 s when peak < $0.80;
- trail after +$5.50 with $2 giveback.

BURST's m30 momentum-zero-cross failure is intentionally **not** reused because SNAPBACK is countertrend by definition and would otherwise fail immediately.

## Evaluation discipline

First evaluate SNAPBACK as a fixed-₹500 independent shadow lane on:

- canonical seven-day first80;
- recent 24 h;
- both 500 ms and 1 s grids;
- chronological four-hour blocks;
- +$0.20 adverse slippage per side stress;
- cross-grid matched entries.

No parameter search is permitted after seeing the result.

Known data can reject SNAPBACK. It cannot promote it.

If the unchanged engine is promising across both known windows/grids, the next step is to freeze an additive integration design and validate on genuinely new raw data. If it fails, do not tune these constants to the recent day; move to a pre-registered walk-forward adaptive learner or a different structurally motivated engine.

Final20 remains sealed.
