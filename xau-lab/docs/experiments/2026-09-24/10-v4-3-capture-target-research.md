# 10 — V4.3 capture-target research and lock

## Goal

Search for a regime-aware successor to V4.2 with an aspirational objective of **>=20% constrained ex-post opportunity capture**, while preserving the 3% planned-risk discipline and keeping the final 20% holdout unopened.

## Data discipline

Only the first 80% of the seven-day broker export was used for this research process.

The research pool was divided chronologically into an initial 0–40% search block followed by four 10%-of-full-dataset evaluation blocks.

The constrained ex-post opportunity ceiling over the first 80% is **₹7,482.60**.

## Baseline

V4.2 was reconstructed exactly before the search.

Continuous V4.2 result on the first 80%:

- +₹412.58;
- PF 1.524;
- 114 trades;
- capture ~5.51%.

## Search

The run explored:

- range-reversion routing;
- normalized momentum;
- alternative exits;
- fast-trend routing;
- repeated trend harvesting;
- Donchian breakout;
- local gradient-boosted return routing;
- regime-adaptive V4.2 composites.

Approximately 6,800 deterministic configurations were evaluated, plus 48 gradient-boosted fits and more than 9,000 execution variants inside the ML branch.

## Strongest fixed candidate

The best fixed regime-adaptive composite produced:

- +₹603.60;
- final ₹1,103.60;
- PF 1.456;
- 114 trades;
- max DD ₹257.52;
- capture **8.07%**.

High activity is defined by 300-second range >= $5 and ER60 >= 0.03. In that state the strategy shortens cooldowns, relaxes the secondary routing restriction, uses a range-normalized breakout buffer, and changes high-regime exits.

## 20% objective outcome

The 20% aspiration was not reached.

A deliberately non-causal hindsight selector choosing the best tested profile separately for each coarse research segment reached only **17.27%**, so the broad search was stopped to avoid increasingly severe overfit.

## Exit-harvest follow-up

A later $30/$15 high-regime take-profit tweak looked better on aggregate research data but underperformed the 8.07% adaptive candidate on the internal 60–80% validation band and both subfolds.

The tweak was rejected.

## Lock decision

The user explicitly selected the strongest 8.07% adaptive candidate as **V4.3**.

This establishes:

- V4.3 = locked fractional research version;
- V4.2 = previous experimental version;
- V4.1 = locked slow-strategy baseline;
- final 20% holdout = still unopened;
- any subsequent parameter or structural change = V4.4.

The lock does not convert the research result into proof of future profitability. It preserves the exact candidate as the next version in the experimental lineage.

## Evidence

Machine-readable evidence is stored under:

[`results/simulations/2026-09-24-v4_3-capture-target/`](../../../results/simulations/2026-09-24-v4_3-capture-target/)
