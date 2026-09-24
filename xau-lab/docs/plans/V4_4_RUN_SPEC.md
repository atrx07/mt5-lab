# V4.4 run spec — more trades without sacrificing expectancy

Date: 2026-09-24

Status: **research plan frozen before simulation**

## Baseline

V4.3 is locked and must not be edited in place.

Reference first-80% research result:

- net P&L: +₹603.60
- final balance: ₹1,103.60
- PF: 1.456
- trades: 114
- constrained-opportunity capture: 8.07%
- max drawdown: ₹257.52
- final 20% holdout: unopened

Any accepted change from this run becomes V4.4.

## Goal

Increase trade frequency **and** preserve or improve trade quality.

Primary research objectives:

- more completed trades than V4.3;
- constrained-opportunity capture >= 10%;
- PF preferably >= V4.3's 1.456;
- no material max-drawdown explosion;
- positive expectancy must not depend on one outlier winner.

Trade count is not optimized by itself.

## Allowed changes

V4.4 may add candidate-generation and filtering layers around the locked V4.3 architecture:

1. faster micro-trend / pullback-resumption candidate generator;
2. tick-flow and microstructure features derived only from information available at entry time;
3. candidate-specific quality / EV gate;
4. fresh-structure re-entry after a genuine reset;
5. state-based cooldown;
6. cost-to-opportunity filtering instead of blindly loosening the fixed spread gate.

The 3% planned-risk fraction and $4 stop remain fixed for this research.

## Candidate features

All features at time t must use data <= t:

- multi-horizon momentum;
- 10/30/60-second realized range and volatility;
- 30/60-second path efficiency;
- sampled up/down tick imbalance;
- raw quote-update rate;
- quote-rate acceleration;
- spread level and recent spread percentile;
- breakout overshoot;
- range compression / expansion;
- distance from recent range center and extremes;
- recent reset / pullback structure.

No hindsight benchmark feature may enter the signal path.

## Search discipline

Start from deterministic rules. Use ML only as a meta-labeler on already-generated candidates, not as a direct raw-price forecaster.

For any learned gate:

- train only on past data;
- use chronological expanding walk-forward evaluation;
- freeze scaler/model/config before each next fold;
- report both accepted and rejected candidate outcomes.

Do not optimize win rate directly. Optimize net expectancy after bid/ask costs subject to risk and drawdown constraints.

## Data split

Use only the original first 80% research pool.

Maintain the existing chronological boundaries:

- 0–40% seed/search;
- 40–50% evaluation 1;
- 50–60% evaluation 2;
- 60–70% evaluation 3;
- 70–80% evaluation 4;
- 80–100% final holdout: **do not read**.

## Stop conditions

Reject a variant if higher trade count comes mainly from:

- duplicated entries into the same unresolved move;
- materially worse PF;
- materially larger drawdown without proportional capture gain;
- one-trade dependence;
- later-fold collapse;
- cost sensitivity that erases the gain.

Do not create `paper_challenge_v4_4.py` until a V4.4 candidate is selected.
