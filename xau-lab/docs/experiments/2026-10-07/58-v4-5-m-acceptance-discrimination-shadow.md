# 58 — V4.5 Candidate M acceptance-discrimination sprint

Date opened: 2026-10-07

Status: **IN PROGRESS — Stage-A block 1 frozen, interrupted locally, exact-window recovery pending**

Frozen/amended plan:  
`docs/plans/V4_5_M_ACCEPTANCE_DISCRIMINATION_SHADOW.md`

Capture tool:  
`tools/capture_m_acceptance_shadow_4h_block.py`

Windows launcher:  
`tools/start_m_acceptance_shadow_4h_block.ps1`

Recovery tool:  
`tools/recover_m_acceptance_shadow_block.py`

Recovery launcher:  
`tools/recover_m_acceptance_shadow_block.ps1`

Offline extractor:  
`research/v4_5_m_acceptance_discrimination.py`

Analysis launcher:  
`tools/analyze_m_acceptance_shadow_block.ps1`

## Motivation

Experiments 51-57 narrowed the V4.5 problem substantially:

- L showed normalized trend/pullback geometry alone does not establish continuation persistence;
- its autopsy showed entry commitment is the dominant problem because most losers never developed meaningful favorable excursion;
- M's reclaim + price-acceptance state machine materially improved trade quality and later-regime loss containment but remained negative overall;
- N showed generic breakout expansion destroys M's selectivity;
- O showed the reclaimed anchor is retestable rather than a reliable hard invalidation boundary;
- P showed extra persistence contains useful information in some regimes but a fixed second two-second confirmation is not portable.

The lab therefore needs better discrimination around M's commitment point, but it also needs a faster iteration cadence.

## Objective

Find **one small causal acceptance/flow discriminator** that plausibly separates durable continuation from false reclaim, freeze it into Candidate Q, then test Q on fresh untouched blocks.

## Accelerated protocol amendment — before first valid block

The original Experiment-58 draft treated all fresh collection as a large discovery tranche. Before any valid score block existed, this was replaced with a cleaner and faster train/test separation:

### Stage A — discovery

- already-consumed historical first80, recent24h, current7d and Experiment-48 blocks may be reused as development evidence;
- add the **first 2 sequential valid fresh four-hour blocks**;
- after both are complete, full labels may be opened for discovery;
- if either grid has <4 M entries across those two blocks, add one extra sequential discovery block based on entry count only;
- use at most one primary discriminator plus one optional tie-breaker when defining Q;
- no brute-force high-dimensional P&L search.

Discovery evidence is explicitly **not validation evidence**.

### Stage B — untouched Candidate-Q validation

After Q is fully frozen and committed, the **next 4 sequential valid four-hour blocks** become the true prospective validation tranche. Q cannot change between them.

Minimum Q pass gate:

1. pooled Q P&L > 0 on both 500 ms and 1 s;
2. pooled Q P&L > M on both grids;
3. mean four-hour Q P&L > 0 on both grids;
4. at least 2/4 positive Q blocks on each grid;
5. pooled Q P&L under +$0.10/side adverse-fill stress remains >=0 on both grids;
6. all parity/provenance/safety checks pass.

If Q fails, it is rejected unchanged. Those validation blocks become known data and cannot be reused to claim a tuned revision is validated.

## Safety / holdout discipline

- capture is read-only MT5 market-data access;
- no broker or paper order is authorized;
- no external feed;
- Final20 remains sealed;
- realistic bid/ask accounting remains mandatory.

## Frozen extraction contract

The extractor replays Candidate M on the exact combined warmup+score stream and hard-fails on lifecycle/summary parity drift.

Causal entry-time fields use `feature_*`; future-path and realized-trade fields use `label_*`. Future labels can never participate in reconstruction of the same entry.

## Pre-capture continuity correction — 2026-10-07

The first launcher attempt did **not** start a scored block. The diagnostic showed 25.37 minutes of trailing continuity and rejected launch because the harness had inherited Candidate J's 90-minute uninterrupted warmup requirement.

Repository inspection confirmed Candidate M actually inherits `CONTINUITY_SEC = 1800` seconds. The >5-second session reset remains unchanged. The capture readiness gate was therefore corrected outcome-blind to **30 minutes** before any valid Experiment-58 block or M outcome existed.

Failed-attempt diagnostic:

- trailing continuity: **25.37 min**;
- last >5 s gap: **7.268 s** at `2026-10-07T08:32:41.223Z -> 08:32:48.491Z`;
- block status: **not started / not counted / no outcomes exposed**.

## Stage-A block 1 interruption — session `20261007T061312Z`

The first real Stage-A capture froze session `20261007T061312Z` and progressed normally to approximately 2.71 hours / 57,840 locally written score ticks. The collector then stopped printing after `08:55:44Z`; manifest and CSV timestamps also stopped advancing. Windows process inspection showed the MT5 terminal process had restarted at approximately 14:26 local time, immediately after the collector stall, while the Python process remained blocked in a native MT5 call.

The user sent one normal `Ctrl+C`; the collector escaped cleanly, executed its `finally` block and wrote:

- `Block status: INCOMPLETE`;
- warmup/score/manifest paths preserved under `data/prospective_m_acceptance_shadow/20261007T061312Z/`;
- no Candidate-M labels/P&L were opened;
- the frozen score start/end were not changed.

This is treated as an **operational interruption, not a discarded research block**. Because the original score window was frozen before outcomes, Experiment 58 preserves it and reconstructs the same four-wall-clock-hour interval from the same MT5 broker history after the original endpoint passes.

Recovery intentionally does **not** borrow Candidate J's market-active-hour extension rule. Real quote gaps remain in the data; the Experiment-58 frozen wall-clock end does not move.

Recovery command after the frozen endpoint has passed in broker time:

```powershell
.\tools\recover_m_acceptance_shadow_block.ps1 -SessionId 20261007T061312Z
```

A successful recovery atomically replaces the partial `score_ticks.csv`, preserves `score_ticks.pre_recovery.csv`, recomputes hashes/gap metadata and marks `valid_for_experiment58=true` only if broker history covers the original endpoint within the frozen tolerance.

## Collection log

- Stage-A block 1: `20261007T061312Z` — **frozen; local capture interrupted; exact-window recovery pending**.
- Stage-A block 2: not started.

## Decision state

No Candidate Q exists yet. Candidate M remains the strongest reusable entry kernel, not a promoted strategy. H-derived flow-confirmed profit protection remains the strongest retained exit component.

## Immediate next action

Do **not** start a replacement Block 1. After the original four-hour endpoint for session `20261007T061312Z` has passed, recover that exact frozen block:

```powershell
.\tools\recover_m_acceptance_shadow_block.ps1 -SessionId 20261007T061312Z
```

If recovery passes, this becomes Stage-A block 1. Then capture Stage-A block 2 normally. Do not open full labels until both Stage-A discovery blocks are complete.
