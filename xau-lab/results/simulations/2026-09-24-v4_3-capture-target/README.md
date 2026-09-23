# V4.3 capture-target research — target not reached

Date: 2026-09-24

Status: **research run complete; no V4.3 version was recorded because the user-set >=20% constrained-opportunity capture target was not reached. V4.2 remains the current experimental paper version.**

## Scope discipline

Only the original first 80% of the seven-day broker dataset was loaded for this run. The final 20% holdout was not read or evaluated.

Research pool boundaries were preserved by original raw-row index:

- seed/search segment: 0–40% of the full dataset;
- evaluation segment 1: 40–50%;
- evaluation segment 2: 50–60%;
- evaluation segment 3: 60–70%;
- evaluation segment 4: 70–80%;
- final holdout: 80–100%, unopened.

The existing constrained ex-post opportunity ceiling over the first 80% is **₹7,482.60** across 90 observed clock-hours. The V4.3 target therefore required at least **₹1,496.52** of captured net research P&L on a comparable basis.

## Replay parity

Before this search, the V4.2 offline replay was reconstructed and matched its recorded results exactly:

- development: +₹225.11043, 95 trades, PF 1.38564;
- validation: +₹129.26802, 19 trades, PF 1.917995.

Running V4.2 continuously across the full first-80% research pool from ₹500 produced **+₹412.58**, PF **1.524**, 114 trades, for about **5.51%** capture versus the constrained ex-post ceiling.

## Search families

The run tested the planned regime-aware directions rather than only moving one threshold:

- range-reversion router;
- volatility-normalized momentum router;
- alternative profit-lock / trailing / reversal exits;
- fast-trend router;
- slow-regime trend-harvest re-entry;
- standalone Donchian-style breakout;
- local gradient-boosted return router with expanding walk-forward retraining;
- a regime-adaptive V4.2 composite using realized range / efficiency to alter cooldown, breakout permission and exit behavior.

Deterministic searches covered about **6,800 random/configured candidates** across those rule families. The ML branch fitted 48 gradient-boosted models and evaluated more than 9,000 execution-parameter combinations on the internal research split before true expanding walk-forward tests.

## Strongest fixed adaptive candidate

The strongest fixed regime-adaptive candidate found in the cross-regime search used:

- high-activity regime: 300-second range >= $5 and 60-second efficiency >= 0.03;
- primary cooldown shortened to 450 s in that regime;
- secondary breakout cooldown shortened to 90 s;
- secondary breakout allowed inside the slow gate in that regime;
- 120-second breakout channel;
- breakout buffer max($0.50, 0.02 × channel range);
- channel range >= $4;
- |30 s momentum| >= $1.50;
- primary high-regime exit: no trailing, $25 cap, 900 s max hold, no momentum-reversal exit;
- secondary high-regime exit: trail after +$12 with $3 give-back, $8 cap, 1200 s max hold, no momentum-reversal exit;
- unchanged 3% planned risk and $4 stop.

Across five research segments with each segment reset to ₹500, it produced **+₹566.59** total. Run continuously over the complete first-80% research pool it produced:

- net: **+₹603.60**;
- final synthetic balance: **₹1,103.60**;
- PF: **1.456**;
- trades: **114**;
- max drawdown: **₹257.52**;
- best trade: +₹173.16;
- worst trade: -₹34.57;
- opportunity capture: **8.07%**.

That is better than V4.2's ~5.51% continuous capture, but still far below the required 20%, with substantially larger drawdown.

## Why the run stopped

A useful upper-bound diagnostic was performed across the tested strategy families: after the fact, choose the best tested profile separately for each of the five coarse research segments.

That hindsight profile oracle produced:

- segment 0: +₹587.11;
- segment 1: +₹170.50;
- segment 2: +₹94.65;
- segment 3: +₹194.08;
- segment 4: +₹245.73;
- total: **₹1,292.06**;
- capture versus the same opportunity ceiling: **17.27%**.

Even this non-causal, hindsight selection among the tested profiles failed to reach 20%.

That is the key stop condition. Continuing to parameter-fish the same information set would be much more likely to manufacture an overfit than to discover a credible >=20% system.

## ML branch

A local HistGradientBoosting return router was also tested using only past-derived features such as multi-horizon momentum, range, efficiency, z-score, expansion ratio, quote rate and spread.

Internal seed validation looked deceptively strong for several 600-second models, but true expanding walk-forward performance collapsed and was negative across the later research folds. The branch was rejected rather than promoted on its internal fit.

## Decision

**Do not create V4.3 from this run.**

The >=20% capture target was treated as the bar. The best causal/fixed candidate reached only ~8.07%, and even a hindsight segment-level oracle across the tested strategy families reached only ~17.27%.

Therefore:

- V4.2 remains the current experimental paper version;
- no `paper_challenge_v4_3.py` is created;
- the final 20% holdout remains sealed;
- the next attempt needs genuinely new predictive information or a materially different execution/position-management architecture, not more threshold search over the same features.
