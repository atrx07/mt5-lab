# 31 — V4.5 Router v2 arbitration divergence audit

Date: 2026-09-25

Status: **completed known-data diagnostic; no strategy change; Candidate D remains leader**

## Objective

Explain **where the Experiment-30 Router v2 expectancy loss comes from** before proposing any new score, threshold or routing rule.

Experiment 30 showed that Router v2 preserved the canonical trade count while losing approximately ₹579 at 500 ms and ₹88 at 1 s versus Candidate D. Experiment 31 therefore instruments both strategies side-by-side and traces the path-dependent consequences of each divergent arbitration decision.

No score component, weight, score floor, engine signal, lifecycle rule, risk parameter or holdout boundary changed.

The final20 holdout remained sealed.

## Execution and parity

The client-side execution sandbox was still unavailable with an infrastructure-level client exception, so the previously authorized GitHub-worker fallback was used.

The instrumented simulator reproduced Experiment 30 **exactly** before any diagnostic was accepted:

| Grid | Candidate D | Router v2 | Trades |
| --- | ---: | ---: | ---: |
| 500 ms | +₹1,430.3111 | +₹851.2651 | 163 / 163 |
| 1 s | +₹385.2545 | +₹297.6667 | 156 / 156 |

Whole-recent parity also matched Experiment 30 exactly:

- 500 ms: Candidate D -₹223.2733, Router v2 -₹210.6307;
- 1 s: Candidate D -₹135.9095, Router v2 -₹144.2185.

## Core finding: the score is myopic in a path-dependent system

There were only **48 classified decision divergences** across both known datasets and both grids.

Historical first80:

- 500 ms: 2 direct score substitutions, 4 Router HOLDs, 1 cooldown-history divergence and 11 slot-occupancy cascades;
- 1 s: 4 direct substitutions, 5 HOLDs and 11 slot-occupancy cascades.

Recent 24 h:

- 500 ms: 1 HOLD and 2 cooldown-history divergences;
- 1 s: 1 direct substitution, 1 HOLD, 3 cooldown-history divergences and 2 slot-occupancy cascades.

The direct same-time substitutions themselves do **not** explain the large loss. Fixed-₹500 isolated counterfactuals gave only:

- historical 500 ms direct substitutions: **-₹2.33** aggregate Router-minus-D delta;
- historical 1 s direct substitutions: **-₹8.80** aggregate delta.

The much larger damage arrives **after** the first changed decision through engine-specific cooldowns, different holding periods, shared-slot occupancy, delayed re-entry and then balance-based 3% sizing.

## 500 ms: exact decomposition of the main damage

The historical 0-40% segment fell from **+₹696.8429 to +₹342.8760**, a **-₹353.9669** segment-level gap.

The trade-pair audit accounts for that gap:

| Mechanism | Count | Contribution to Router-minus-D segment P&L |
| --- | ---: | ---: |
| Same entry/engine/side | 90 | **-₹79.25** |
| Same engine, shifted entry time | 3 | **-₹51.06** |
| Candidate-D trades with no Router match | 4 | **-₹148.85** |
| Router-only trades with no D match | 4 | **-₹74.81** |
| Simultaneous substitution | 1 | ₹0.00 |
| **Total** | 102 pair rows | **-₹353.97** |

The **-₹79.25 on 90 literally identical trades** is not different market timing or exit logic. Once earlier arbitration mistakes reduced Router v2's balance, the unchanged 3%-of-balance sizing made the same later winners smaller. The risk model therefore **amplifies an earlier arbitration error**; it is not the root cause.

The four D-only trades netted **+₹148.85**, including:

- SECONDARY BUY +₹29.11;
- PRIMARY SELL **+₹95.03**;
- MICRO SELL -₹20.99;
- MICRO SELL +₹45.70.

The four Router-only trades all lost, totaling **-₹74.81**.

### Two high-value HOLD cascades

At timestamp 1789621006.398, Candidate D entered PRIMARY SELL. Router v2 scored it **-0.01635**, barely below the 0.0 floor, and HOLDed. The isolated fixed-₹500 lifecycle from that exact entry produced **+₹61.39**.

Router later entered the same PRIMARY direction 323.6 seconds later and lost about ₹12.15, then took an unmatched SECONDARY SELL that lost about ₹20.83. Candidate D's actual original PRIMARY trade made **+₹95.03**.

At timestamp 1789658224.968, Candidate D entered PRIMARY BUY. Router scored it **-0.03317** and HOLDed. The exact-entry fixed-₹500 counterfactual was **+₹43.16**. Router entered PRIMARY 56.46 seconds later; the delayed trade still won but produced only ₹52.78 versus Candidate D's ₹96.94 at their respective path-dependent sizes, and the shifted occupancy then caused Candidate D's later +₹45.70 MICRO SELL to be replaced by a Router-only SECONDARY loss of -₹28.13.

### A substitution can be harmless now and expensive later

At timestamp 1789594424.963 the router replaced PRIMARY SELL with MICRO SELL. Both isolated tickets produced the same fixed-₹500 loss, so the immediate substitution cost was **₹0**.

But the different engine cooldown history caused Router v2 to take a PRIMARY SELL 29 seconds later. That position occupied the shared slot while Candidate D subsequently took a MICRO BUY and then a SECONDARY BUY; the SECONDARY trade ultimately made +₹29.11 for D.

This is direct evidence that **per-entry score quality is insufficient**. Engine identity changes the future opportunity set even when the immediate trade outcome is identical.

## 1 s: timing/occupancy dominates again

The historical 0-40% segment gap was **-₹62.0252**.

Key pair contributions:

- exact same actions: **+₹7.17** for Router;
- simultaneous substitutions: **+₹5.25**;
- same-engine timing shifts: **-₹24.30**;
- one nearby replacement: **-₹50.79**;
- D-only trades: +₹6.49 of D P&L omitted;
- Router-only trades: +₹7.13 added.

The single largest pair difference was a Candidate-D MICRO SELL that made **+₹28.33** versus a Router SECONDARY SELL 28 seconds later that lost **-₹22.46**, a **-₹50.79** swing. It occurred after a Router HOLD/delayed PRIMARY sequence changed slot availability.

So at 1 s too, raw score substitutions were not the main problem; **timing and occupancy cascades were**.

## Score-floor warning

Profitable and losing PRIMARY HOLDs occupy the same narrow negative-score region.

Examples of known profitable exact-entry counterfactuals rejected by the 0.0 floor:

- score -0.01635 -> +₹61.39 fixed-₹500;
- score -0.03317 -> +₹43.16;
- score -0.05363 -> +₹94.73;
- score -0.05737 -> +₹48.37.

Known losing rejected entries include scores around -0.026, -0.041, -0.057, -0.066 and -0.071.

Therefore simply lowering the score floor to "recover the winners" is not supported. The rejected winners and losers overlap too strongly, and choosing a convenient new floor from these known outcomes would be direct overfitting.

## Recent 24-hour interpretation

At 500 ms Router v2 improved by **₹12.64**. The trade-pair view shows why:

- it omitted two Candidate-D PRIMARY losses totaling **-₹20.67**;
- it added one Router-only loss of -₹4.36;
- identical later trades contributed about -₹3.67 from path-dependent balance sizing.

This is a genuine example of the HOLD behavior helping.

At 1 s, however, Router v2 was **₹8.31 worse**:

- one D-only loss of -₹11.72 was avoided;
- one nearby replacement improved by +₹9.07;
- same-action sizing contributed +₹3.43;
- but **three Router-only trades lost -₹32.52**.

So the same path-dependent re-entry/cooldown machinery that occasionally avoids a bad fresh trade can also manufacture extra losing trades.

## Decision

**Candidate D remains the V4.5 research leader. The frozen Router-v2 score remains unpromoted.**

Experiment 31 changes the diagnosis:

> The main defect is not simply "bad score values." The router treats each arbitration point independently even though engine choice changes cooldown history, holding time, shared-slot occupancy, subsequent eligible opportunities and future position size.

The next architecture should therefore be **path-aware and priority-preserving**, not another threshold sweep.

A defensible Experiment-32 design should be specified before running it and should consider:

1. preserving Candidate D's engine priority instead of globally re-ranking simultaneous engines by score;
2. defining a causal **signal episode** so a rejected setup cannot simply re-enter a few seconds/minutes later as the same underlying opportunity;
3. making any fallback decision aware of shared-slot opportunity cost rather than treating the replacement as an isolated ticket;
4. keeping state-v2 as descriptive context while avoiding a score-floor fit to the known winners above.

Any new Router candidate must be frozen before genuinely new non-overlapping raw data is used for promotion. The known seven-day and 24-hour sets can verify parity and explain mechanics, not select a convenient threshold.

## Evidence

- `research/v4_5_router_v2_arbitration_audit.py`
- `results/simulations/2026-09-25-v4_5-router-v2-arbitration-audit/summary.json`
- `.../arbitration_events.csv`
- `.../decision_category_summary.csv`
- `.../substitution_matrix.csv`
- `.../trade_pairs.csv`
- `.../trade_pair_summary.csv`
- `.../segment_pair_damage.csv`
- `.../candidate_d_trades.csv`
- `.../router_v2_trades.csv`
- `.../top_damage_events.csv`
