# 24 — V4.5 bounded regime-router probe

Date: 2026-09-25

Status: **completed negative router probe; no candidate promoted**

## Objective

Begin turning Experiment 23's raw-event regime state into engine strongholds without solving robustness by simply killing trade count. Test the smallest useful router family first: a single regime-category veto applied to one engine, with rejected engines falling through to the next engine in the normal PRIMARY -> SECONDARY -> MICRO -> BURST arbitration.

The desired behavior is higher net expectancy and win consistency on both 500 ms and 1 s while retaining almost all of Candidate D's activity. This experiment does not change risk, exits, sizing, engine signal rules, replay semantics, or the sealed final 20%.

## Search discipline

Selection used only the canonical 0-40% seed. The later 40-80% segments were not used to choose the veto.

Exactly 48 seed variants were tested:

- 4 engines: PRIMARY, SECONDARY, MICRO, BURST;
- 4 Experiment 23 regime dimensions: volatility, spread, efficiency, activity;
- 3 categories per dimension.

Each variant blocked exactly one engine/category pair. All other regime states and engines remained Candidate D.

A seed variant was eligible only if, on **both** 500 ms and 1 s:

- P&L exceeded Candidate D seed P&L;
- win rate was not lower;
- at least 95% of Candidate D seed trades were retained;
- max drawdown was no more than 2% worse.

Eligible variants were ranked by the smaller of their two relative P&L improvements, so a one-grid spike could not dominate selection.

## Seed selection

Candidate D seed baseline:

| Metric | 500 ms | 1 s |
| --- | ---: | ---: |
| P&L | ₹696.84 | ₹169.92 |
| Trades / wins | 98 / 46 | 98 / 42 |
| Win rate | 46.939% | 42.857% |
| Max DD | ₹218.94 | ₹172.14 |

Only two of 48 variants passed all seed criteria:

| Veto | 500 ms P&L | 1 s P&L | Trades 500 ms / 1 s | Joint-min P&L gain |
| --- | ---: | ---: | ---: | ---: |
| **MICRO when raw volatility = low** | **₹709.36** | **₹179.60** | 97 / 97 | **+1.796%** |
| SECONDARY when raw efficiency = efficient | ₹700.22 | ₹170.80 | 98 / 98 | +0.485% |

The first variant was frozen before later evaluation. "Low volatility" here means Experiment 23's unchanged raw relative 60-second range category: `raw_range60_rel < 0.75`.

The second qualifier is preserved as seed evidence only. It must not be promoted merely because the selected variant later failed.

## Chronological evaluation

The frozen MICRO-low-volatility veto was replayed across the later four first-80% segments with exact shared-slot fall-through behavior.

500 ms segment P&L:

- 40-50%: unchanged at +₹44.10;
- 50-60%: unchanged at -₹13.58;
- 60-70%: unchanged at +₹34.32;
- 70-80%: fell from +₹212.82 to +₹197.23.

1 s later segments were unchanged by the veto.

Full first-80% comparison:

| Metric | Candidate D 500 ms | Router probe 500 ms | Candidate D 1 s | Router probe 1 s |
| --- | ---: | ---: | ---: | ---: |
| Compounded P&L | ₹1,430.31 | **₹1,407.86** | ₹385.25 | **₹398.05** |
| Capture | 19.1152% | 18.8151% | 5.1487% | 5.3197% |
| Trades | 163 | 161 | 156 | 155 |
| Wins | 81 | 80 | 71 | 71 |
| Win rate | 49.693% | 49.689% | 45.513% | 45.806% |
| Worst segment DD | ₹218.94 | ₹221.23 | ₹172.14 | ₹164.53 |

Trade retention remained high at 98.77% / 99.36%, so the failure is not caused by broadly suppressing activity. The gate simply removed value at 500 ms outside the seed while adding modest 1 s robustness.

## Decision

**Reject the router probe.** Candidate D remains the V4.5 provisional historical leader.

This is useful negative evidence: a regime category that looks like an engine weak spot on the seed can still contain profitable opportunities later. A one-dimensional veto is too crude to define an engine stronghold from the original seven-day episode alone.

Do not use the observed 40-80% miss to choose the second seed-qualified veto. The next valid step is independent cross-window regime validation on non-overlapping data, followed by a router family designed from multiple windows rather than repaired against this known evaluation pool.

## Evidence

- `research/v4_5_regime_router_probe.py`
- `results/simulations/2026-09-25-v4_5-regime-router-probe/README.md`
- `results/simulations/2026-09-25-v4_5-regime-router-probe/summary.json`
- `results/simulations/2026-09-25-v4_5-regime-router-probe/seed_eligible_candidates.csv`
- `results/simulations/2026-09-25-v4_5-regime-router-probe/selected_candidate_results.csv`
