# 36 — V4.5 raw-event microstate-v1 foundation

Date: 2026-09-25

Status: **completed representation diagnostic; retained as causal feature foundation**

## Objective

Introduce genuinely new causal market information after Experiments 33–35 showed that neither current engine routing, frozen SNAPBACK, nor the current state-v2 ridge admission test solved cross-window robustness.

This experiment made **no trading-strategy change** and used **no outcome label** to define or select a feature.

The exact schema was frozen beforehand in:

`docs/plans/V4_5_MICROSTATE_FOUNDATION.md`

## Frozen representation

`xau-microstate-v1` contains 23 raw-event features covering:

- 2 s / 10 s event counts and rate acceleration;
- raw inter-arrival timing;
- 2 s / 10 s mid movement and direction-normalized movement;
- raw event-path efficiency;
- raw signed event imbalance;
- direction-normalized short-vs-long imbalance change;
- bid-vs-ask update sidedness;
- two-sided quote-update fraction;
- short spread level/change/compression;
- direction-normalized location inside the prior 10 s raw range.

Every feature is past-only and clipped at raw continuity gaps >5 s.

## Coverage

The overlay produced 551 opportunity-state rows:

- historical first80: 461;
- recent 24 h: 90.

All 23 features had **100% finite coverage** on both grids and both windows.

## Cross-grid stability

Same-engine, same-side opportunities were paired without using outcome labels.

Strict <=10 s matching:

- historical: 163 pairs;
- recent: 33 pairs.

Median feature Spearman:

- historical: **0.869**;
- recent: **0.935**.

Broad <=120 s matching retained 181 historical and 36 recent pairs and remained broadly stable, as expected with somewhat lower short-window correlation when entry times are farther apart.

Most features were strongly stable. The weakest strict feature was `spread_change_rel2` (0.648 historical, 0.482 recent), which is plausible because a 2-second spread-change measure is highly timing-sensitive. It is retained as context but should not be treated as a standalone gate without future evidence.

## Distribution drift

The representation captures real cross-window differences rather than collapsing them.

Examples:

- median raw inter-arrival time shifted from about 52 ms historically to about 54 ms recent;
- historical/recent 10 s raw movement and flow distributions changed;
- recent two-sided quote-update fraction was somewhat higher;
- spread-relative and compression distributions moved but remained well-covered.

These are descriptive state changes only. No profitable/losing label was consulted.

## Decision

**Retain xau-microstate-v1 as a causal feature foundation. Do not build a known-data winner from it now.**

This is exactly where overfitting discipline matters: the representation is stable enough to be useful, but we have already consumed the seven-day and recent-24h windows heavily.

The next strategy-changing test should therefore be **prospective**:

1. freeze the future microstructure hypothesis before seeing its outcomes;
2. obtain a genuinely new non-overlapping raw XAU snapshot;
3. run Candidate D and the frozen hypothesis unchanged;
4. compare P&L, win rate, opportunity retention, drawdown, costs and 500 ms/1 s robustness;
5. reject it if it fails rather than retuning against the new day.

Final20 remains sealed.

## Evidence

- `docs/plans/V4_5_MICROSTATE_FOUNDATION.md`
- `research/v4_5_microstate_v1_freeze.py`
- `results/simulations/2026-09-25-v4_5-microstate-v1-freeze/summary.json`
- `.../coverage.csv`
- `.../cross_grid_stability.csv`
- `.../cross_grid_strict_matches.csv`
- `.../cross_grid_broad_matches.csv`
- `.../distribution_drift.csv`
- `.../microstate_opportunities.csv`
