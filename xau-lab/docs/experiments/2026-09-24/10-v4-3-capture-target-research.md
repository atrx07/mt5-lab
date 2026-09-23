# 10 — V4.3 >=20% capture-target research

## Goal

Attempt the next fractional experiment with a hard research objective: **capture at least 20% of the constrained ex-post opportunity ceiling** while preserving the 3% planned-risk discipline and without opening the final 20% holdout.

The run explicitly avoided treating the ₹50/hour goal as a forced-trading quota.

## Data discipline

Only the first 80% of the seven-day broker export was loaded. The final 20% holdout was not read.

The research pool was divided chronologically into an initial 0–40% seed/search block followed by four 10%-of-full-dataset evaluation blocks.

The constrained ex-post opportunity ceiling over the first 80% is **₹7,482.60**, so the 20% target corresponds to **₹1,496.52**.

## Baseline parity

The reconstructed V4.2 replay matched the recorded V4.2 development/validation results exactly before any new search.

Continuous V4.2 performance across the first 80%:

- +₹412.58;
- PF 1.524;
- 114 trades;
- capture ~5.51%.

## Families tested

The run did not merely tweak one threshold. It tested range reversion, normalized momentum, alternative exits, fast-trend routing, repeated trend harvesting, Donchian breakout, a local gradient-boosted return router, and a regime-adaptive V4.2 composite.

Approximately 6,800 deterministic candidate configurations were evaluated, plus 48 gradient-boosted model fits and more than 9,000 execution variants inside the ML branch's research search.

## Best fixed candidate

The strongest fixed adaptive candidate improved continuous research capture to **8.07%**:

- +₹603.60;
- final ₹1,103.60;
- PF 1.456;
- 114 trades;
- max DD ₹257.52.

The improvement is real relative to V4.2, but it is nowhere near the >=20% requirement and it buys some of that gain with substantially higher drawdown.

## Upper-bound diagnostic

A deliberately non-causal diagnostic then chose the best already-tested profile separately for each of five coarse research segments after seeing the results.

Even that hindsight profile oracle captured only **17.27%**:

- total +₹1,292.06;
- required for 20%: +₹1,496.52.

This was treated as the stop signal. If even after-the-fact profile selection across the tested families cannot cross 20%, further threshold fishing on the same information set is not a credible path to the target.

## ML result

The local gradient-boosted return router looked strong on its internal seed validation, especially at a 600-second horizon, but collapsed on expanding walk-forward tests. It was rejected.

This is useful negative evidence: the current hand-engineered tick-state features do not appear to contain a stable enough predictive mapping for that model family across this short dataset.

## Decision

**No V4.3 version is recorded from this run.**

The user-set >=20% capture target was treated as the bar for this attempt.

V4.2 remains the current experimental paper version. The final holdout remains sealed.

The next V4.3 attempt should change the information set or execution architecture materially rather than perform another broad threshold search on the same momentum/range/efficiency features.

## Evidence

Machine-readable summaries:

[`results/simulations/2026-09-24-v4_3-capture-target/`](../../../results/simulations/2026-09-24-v4_3-capture-target/)
