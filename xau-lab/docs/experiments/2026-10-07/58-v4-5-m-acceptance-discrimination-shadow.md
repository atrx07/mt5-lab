# 58 — V4.5 Candidate M prospective acceptance-discrimination shadow

Date opened: 2026-10-07

Status: **IN PROGRESS — prospective discovery capture not yet evaluated**

Frozen plan:  
`docs/plans/V4_5_M_ACCEPTANCE_DISCRIMINATION_SHADOW.md`

Capture tool:  
`tools/capture_m_acceptance_shadow_4h_block.py`

Windows launcher:  
`tools/start_m_acceptance_shadow_4h_block.ps1`

Offline extractor:  
`research/v4_5_m_acceptance_discrimination.py`

Analysis launcher:  
`tools/analyze_m_acceptance_shadow_block.ps1`

## Motivation

Experiments 51-57 narrowed the V4.5 problem substantially:

- Candidate L proved normalized trend/pullback geometry alone does not establish continuation persistence;
- its autopsy showed most losing trades never developed meaningful favorable excursion, making entry commitment the dominant problem;
- Candidate M's reclaim + price-acceptance state machine materially improved trade quality and later-regime loss containment but remained negative overall;
- Candidate N showed generic breakout expansion destroys M's useful selectivity;
- Candidate O showed the reclaimed anchor is retestable rather than a reliable hard post-entry invalidation boundary;
- Candidate P showed extra post-acceptance persistence can help in a narrow regime but a fixed second two-second confirmation is not portable.

The next step is therefore not rapid Candidate-Q/R/S search on the same consumed datasets. Experiment 58 collects fresh shadow evidence around frozen M entries before defining the next strategy candidate.

## Objective

Determine which **causal entry-time acceptance and quote-flow properties** are consistently associated with durable continuation versus false reclaim, while keeping Candidate M itself unchanged.

This experiment is successful if it produces a provenance-clean fresh dataset and a small, interpretable, cross-grid mechanism hypothesis suitable for freezing into a later Candidate Q. Positive Experiment-58 P&L is not itself a pass criterion.

## Data discipline

Discovery tranche is frozen before capture:

- 8 sequential valid four-hour score blocks;
- >=4 distinct market days;
- optional extension to 12 blocks only if either grid has <16 Candidate-M score entries after eight blocks;
- extension decision may use entry count only, via count-only extraction;
- no dropping blocks based on market state or outcomes;
- no external feed;
- final20 remains sealed.

Every captured block becomes outcome-known discovery data after its labels are opened and can never later be called unseen validation evidence.

## Safety

The capture runner is read-only MT5 market-data code and contains an AST-level guard against `order_send` / `trade_*` execution calls.

No paper or broker order is authorized by Experiment 58.

## Frozen extraction contract

The offline extractor replays Candidate M on the exact combined warmup+score raw stream and hard-fails if the instrumented implementation differs from frozen M in lifecycle/summary parity.

Causal entry-time fields are prefixed `feature_*`. Future-path and realized-trade fields are prefixed `label_*` and are never used to reconstruct the same entry.

The complete schema is frozen in the plan before the first block.

## Pre-capture continuity amendment — 2026-10-07

The first launcher attempt did **not** start a scored block. The read-only diagnostic showed 25.37 minutes of trailing continuity and rejected launch because the initial harness had inherited Candidate J's 90-minute uninterrupted warmup requirement. No Candidate-M P&L, win/loss outcome or Experiment-58 labels were evaluated.

Repository inspection then confirmed Candidate M inherits Candidate L's frozen `CONTINUITY_SEC = 1800` seconds. The >5-second sampled-session reset remains unchanged. The launcher was therefore amended outcome-blind to require **30 minutes** of uninterrupted causal continuity rather than 90 minutes. This changes capture readiness only; Candidate M and all Experiment-58 feature/label rules remain unchanged.

Operational diagnostic from the failed attempt:

- trailing continuity: **25.37 min**;
- last >5 s gap: **7.268 s** at `2026-10-07T08:32:41.223Z -> 08:32:48.491Z`;
- block status: **not started / not counted**.

## Collection log

No valid Experiment-58 block has been captured yet.

## Decision state

No Candidate Q exists yet. Candidate M remains a rejected-but-useful architecture reference, not a live/paper promotion.

Next action: run the first fresh Experiment-58 four-hour shadow block once the trailing >5-second-gap continuity reaches 30 minutes, preserve its manifest/hashes, and use count-only mode if inspecting opportunity count before the discovery tranche closes.
