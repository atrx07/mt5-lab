# V4.5 — Candidate M acceptance-discrimination shadow plan

Date frozen: 2026-10-07

Status: **amended before the first valid Experiment-58 block**

## Purpose

Candidate M is the strongest reusable entry architecture from Experiments 51-57, but it is not a promoted strategy. Its pullback -> reclaim -> price-acceptance state machine sharply reduced later-regime failure while remaining negative overall. Candidate P then showed that extra persistence can help in some regimes but that a fixed second two-second confirmation is not portable.

Experiment 58 separates **mechanism discovery** from **candidate validation** so the lab can move faster without pretending repeatedly observed development data are unseen.

Core question:

> At the instant frozen Candidate M would commit capital, what causal acceptance/flow characteristic distinguishes durable continuation from a false reclaim?

## Governance

Before the first valid block:

- Candidate M remains unchanged in decision meaning;
- Candidate H-derived profit protection remains part of M's reference lifecycle;
- no Candidate-Q rule exists yet;
- the canonical final20 stays sealed;
- no external market/news/session feed is used;
- capture is MT5 read-only and contains no broker-order call;
- discovery evidence may be heavily observed and is **never** called validation evidence;
- any Candidate Q must be completely frozen before its later fresh validation tranche starts.

The failed 2026-10-07 warmup attempt exposed no strategy outcome and started no valid block. Before any valid block, the capture gate was corrected from the inherited Candidate-J 90-minute continuity requirement to Candidate M's actual inherited structural continuity requirement: **30 uninterrupted minutes** (`CONTINUITY_SEC = 1800`). The existing >5-second session reset rule remains unchanged.

## Capture contract

Tool:

`tools/capture_m_acceptance_shadow_4h_block.py`

Launcher:

`tools/start_m_acceptance_shadow_4h_block.ps1`

Each valid block:

- backfills at least **30 minutes** of uninterrupted causal XAUUSD MT5 tick context;
- freezes the score start at the latest broker tick;
- captures four wall-clock hours of new raw ticks;
- preserves real quote gaps and synthesizes no ticks;
- reconstructs the exact frozen interval from MT5 history at completion when broker history is available;
- stores warmup and score SHA-256 hashes plus a manifest;
- performs no broker execution.

Default storage:

`data/prospective_m_acceptance_shadow/<session_id>/`

A block is usable only when its manifest has `complete=true`, `valid_for_experiment58=true`, valid hashes, `candidate_m_reference_frozen=true`, `external_data_used=false`, and `final20_opened=false`.

## Stage A — accelerated mechanism discovery

Discovery is allowed to use **already-consumed known datasets** because it is explicitly development evidence, not promotion evidence. Reusing known data here is preferable to wasting days pretending discovery itself is blind; the protection against overfitting comes from Stage B.

Fresh discovery addition:

- collect the **first 2 sequential valid four-hour Experiment-58 blocks**;
- do not drop either based on market state, M entry count or outcome;
- after both are complete, full labels may be opened and combined with the already-consumed historical first80, recent24h, current7d and Experiment-48 blocks for mechanism analysis;
- if one grid has **fewer than 4 score-window M entries across the two fresh blocks**, add one additional sequential valid discovery block before freezing Q. This extension uses entry count only.

Discovery may compare actual M entries using the frozen `feature_*` / `label_*` schema, but the goal is **one small structural hypothesis**, not maximizing development P&L.

### Candidate-Q complexity limit

Candidate Q may use:

- at most **one primary causal discriminator** plus **one optional tie-breaker**;
- existing M setup/acceptance logic as the base;
- existing H-derived exit lifecycle unless the discovered mechanism specifically concerns entry timing.

Not allowed:

- unrestricted feature/model search;
- brute-force threshold grids over all recorded columns;
- repeated Q->R->S mutation after seeing the same Stage-B validation blocks;
- selecting a complex rule solely because it maximizes known-data P&L.

After discovery, Candidate Q's complete decision rule, implementation and Stage-B pass/fail contract must be committed **before** any Stage-B block starts.

## Stage B — true prospective Candidate-Q validation

The next **4 sequential valid four-hour blocks captured after Q is frozen** are the untouched validation tranche.

Requirements:

- at least **2 distinct market days** where practical;
- Q cannot change between blocks;
- every valid sequential block is included;
- compare frozen Q directly with frozen M on both 500 ms and 1 s grids;
- use realistic bid/ask fills and the existing risk/accounting model;
- include +$0.10 per-side adverse-fill stress;
- no Final20 access.

### Minimum promotion gate for Q

Q passes Stage B only if all of the following hold on the four-block pooled validation:

1. pooled Q P&L is **> 0 on both 500 ms and 1 s**;
2. Q pooled P&L is **better than M on both grids**;
3. mean four-hour Q P&L is **> 0 on both grids**;
4. Q is positive in **at least 2 of 4 blocks on each grid**;
5. pooled Q P&L under **+$0.10/side stress remains >= 0 on both grids**;
6. no parity/provenance/safety gate fails.

Passing Stage B makes Q the strongest prospective V4.5 candidate; it does **not** by itself authorize real-money execution or open Final20.

If Q fails Stage B, reject it unchanged. Do not tune it against those four validation blocks and call the revision validated.

## Frozen causal feature schema

Offline extractor:

`research/v4_5_m_acceptance_discrimination.py`

The extractor must first reproduce frozen Candidate M exactly on the same combined warmup+score stream. Any mismatch in entries, exits, trade count, P&L, drawdown or lifecycle counters is a hard parity failure.

Every actual frozen-M entry records only information available at that entry timestamp under `feature_*` columns.

### Acceptance geometry

- arm age and acceptance age;
- frozen arm anchor and arm spread;
- current spread and spread/arm-spread ratio;
- range60 and range300;
- spread/range60;
- directional distance beyond the anchor;
- directional excess beyond the frozen acceptance level;
- min/mean/max acceptance excess during the active acceptance interval;
- anchor-cross and acceptance-level-cross counts over the preceding five seconds;
- acceptance-timer resets during the current arm.

### Price-shape trajectory

- m10, m30, m60, m300, m1800;
- direction-normalized versions;
- m10/m30/m60 relative to range60;
- m300 relative to range300;
- direction-normalized sampled two-, five-, and ten-second movement;
- movement from arm time to entry.

### Flow / quote microstate

All 23 frozen `xau-microstate-v1` features at entry are recorded with the `feature_micro_` prefix.

No future value may appear under `feature_*`.

## Frozen outcome-label schema

For 2, 5, 10, 30, 60 and 120 seconds after each entry:

- executable-price MFE;
- executable-price MAE;
- executable end move;
- midpoint MFE;
- midpoint MAE;
- midpoint end move;
- whether the full requested horizon is present;
- actually observed horizon seconds.

The frozen-M lifecycle outcome is also labeled when observed:

- actual exit timestamp/reason;
- exit move;
- trade MFE;
- holding time;
- INR P&L;
- win/loss flag.

Future/outcome columns are labels only. They may never be fed back into reconstruction of the same entry.

## Analysis discipline

Allowed in Stage A:

- robust medians/quantiles and effect directions;
- winner/loser and early-failure comparisons;
- 500 ms versus 1 s consistency;
- per-block/per-day direction stability;
- small univariate or low-dimensional diagnostic summaries;
- causal trajectory visualizations and failure taxonomy.

The desired output is a simple explanation of false reclaim that can be frozen into Q and then honestly tested in Stage B.
