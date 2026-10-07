# V4.5 — Candidate M acceptance-discrimination shadow plan

Date frozen: 2026-10-07

Status: **frozen before the first Experiment-58 prospective block; capture warmup amended outcome-blind before any valid block**

## Purpose

Candidate M is the strongest reusable entry architecture from Experiments 51-57, but it is not a promoted strategy. Its pullback -> reclaim -> price-acceptance state machine dramatically reduced the later-regime failure of Candidate L/D/H while remaining negative overall. Candidate P then showed that extra persistence can help in some regimes but a fixed second two-second confirmation is not portable.

Experiment 58 therefore does **not** define Candidate Q and does **not** tune M. It collects genuinely fresh broker-native evidence around frozen Candidate-M entries so the lab can answer one narrower question:

> At the instant frozen Candidate M would commit capital, what causal acceptance/flow characteristics distinguish durable continuation from a false reclaim?

## Governance

Before the first fresh block:

- Candidate M remains byte-for-byte unchanged in decision meaning;
- Candidate H-derived profit protection remains part of M's reference lifecycle;
- no Candidate-Q admission rule exists;
- no fitted classifier or score is authorized;
- no threshold may be selected from historical first80, recent24h, current7d, the six Candidate-J Stage-1 blocks, or Experiment-58 outcomes and then described as unseen;
- the canonical final20 stays sealed;
- no external market/news/session feed is used;
- capture is MT5 read-only and must contain no broker-order call.

Experiment-58 data are **prospective discovery/shadow evidence**, not promotion evidence. Any later Candidate Q derived from them must be frozen first and tested on a separate new unseen tranche.

## Capture contract

Tool:

`tools/capture_m_acceptance_shadow_4h_block.py`

Launcher:

`tools/start_m_acceptance_shadow_4h_block.ps1`

Each valid block:

- backfills at least 30 minutes of uninterrupted causal XAUUSD MT5 tick context under the same >5 s continuity-reset semantics used by Candidate M's sampled-session state;
- freezes the score start at the latest broker tick;
- captures four wall-clock hours of new raw ticks;
- preserves real quote gaps and synthesizes no ticks;
- reconstructs the exact frozen interval from MT5 history at completion, making local suspend/reconnect recoverable when broker history is available;
- stores warmup and score SHA-256 hashes plus a manifest;
- performs no strategy-P&L evaluation while capturing.

### Pre-outcome warmup amendment — 2026-10-07

The initial frozen draft inherited Candidate J's 90-minute uninterrupted warmup gate. The very first launch attempt failed that operational gate with **no scored block started and no Candidate-M outcome/P&L evaluated**. Inspection of the already-frozen Candidate-L/M implementation showed that Candidate M's actual structural continuity requirement is `CONTINUITY_SEC = 1800` seconds (30 minutes), with the existing >5-second sampled-session reset unchanged.

Therefore, before any valid Experiment-58 block existed, the canonical launcher was amended from 90 minutes to **30 minutes**. This amendment removes an irrelevant J-era over-gate; it does not loosen Candidate M, alter the >5-second reset rule, inspect strategy outcomes, or change any feature/label definition. The failed pre-capture diagnostic remains operational evidence only and is not an Experiment-58 score block.

Default storage:

`data/prospective_m_acceptance_shadow/<session_id>/`

A block is usable only when its manifest has `complete=true`, `valid_for_experiment58=true`, valid hashes, `candidate_m_reference_frozen=true`, `external_data_used=false`, and `final20_opened=false`.

## Discovery tranche

The first discovery tranche is frozen as:

- **8 sequential valid four-hour blocks**;
- spanning **at least 4 distinct market days**;
- no valid block may be dropped because of Candidate-M entry count, P&L, win/loss outcome, market direction, volatility, or apparent quality;
- operationally invalid/incomplete captures may be rerun, but the invalid artifact must remain identifiable as invalid rather than silently replaced.

After each block, `--count-only` may be used to inspect **only** score-window Candidate-M entry counts on 500 ms and 1 s. Outcome labels/P&L must not be opened for stopping decisions.

If the eight-block tranche contains fewer than **16 score-window Candidate-M entries on either grid**, extend the tranche by exactly four additional sequential valid blocks before opening labels. This extension rule depends only on opportunity count, not profitability. Maximum discovery tranche: **12 blocks**.

## Frozen causal feature schema

Offline extractor:

`research/v4_5_m_acceptance_discrimination.py`

The extractor must first reproduce frozen Candidate M exactly on the same combined warmup+score stream. Any mismatch in entries, exits, trade count, P&L, drawdown, or lifecycle counters is a hard parity failure and invalidates the extracted feature table.

Every actual frozen-M entry in the score window records only information available at that entry timestamp under `feature_*` columns.

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
- number of acceptance-timer resets during the current arm.

### Price-shape trajectory

- m10, m30, m60, m300, m1800;
- direction-normalized versions;
- m10/m30/m60 relative to range60;
- m300 relative to range300;
- direction-normalized sampled two-, five-, and ten-second movement;
- movement from arm time to entry.

### Flow / quote microstate

All 23 already-frozen `xau-microstate-v1` features at entry are recorded with the `feature_micro_` prefix, including raw event counts/rates, inter-arrival behavior, two/ten-second directional movement, event efficiency, event imbalance, quote sidedness, two-sided update fraction, spread dynamics and ten-second range position.

No future value may appear under `feature_*`.

## Frozen outcome-label schema

Only after the discovery tranche is frozen may the full extractor write `label_*` fields.

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

## Analysis discipline after collection

Experiment 58 is mechanism discovery, not a high-dimensional optimizer.

Allowed analysis after the discovery tranche closes:

- winner/loser and early-commit/early-failure descriptive comparisons;
- robust medians, quantiles and effect directions;
- 500 ms versus 1 s consistency;
- per-block/per-day direction stability;
- small univariate or low-dimensional diagnostic summaries;
- causal trajectory visualizations and failure taxonomy.

Not allowed for Candidate-Q definition:

- brute-force threshold grids across the recorded columns;
- unrestricted feature selection/model search against P&L;
- selecting a rule solely because it maximizes the eight/twelve-block P&L;
- repeatedly mutating Q after looking at the same discovery labels.

The desired output is a **small structural hypothesis** explaining false reclaim, not a backtest-fitting machine.

## Candidate-Q handoff rule

A later Candidate Q may be proposed only after Experiment-58 discovery closes. Its complete rules and prospective pass/fail contract must be committed before a new unseen validation tranche starts.

Candidate Q must preserve the project requirements that matter for live transfer: dual-grid robustness, realistic bid/ask fills, cost stress, continuity/shock safety, fixed risk discipline and no final20 use unless the user explicitly opens that milestone.
