# Experiment 48 — fresh MT5-only prospective validation of Candidate J

Date: 2026-09-26

Status: **frozen before fresh-data capture**

## Objective

Validate Candidate J unchanged on a genuinely new MT5-only XAUUSD snapshot captured after Experiment 47 was frozen.

This experiment is prospective. It is not allowed to reuse the canonical seven-day first80, recent24h, external GC data, or final20.

## Frozen candidate set

Compare exactly:

1. Candidate D — current formal V4.5 leader.
2. Candidate H — strongest retained exit branch.
3. Candidate J — Experiment-47 MT5-native quote-flow phase controller.

Candidate J logic is frozen at:
- implementation commit `a846baabd6cb37f0a3441cd3121ac16250bd5381`;
- Experiment-47 frozen plan and completed known-data evidence.

No phase rule, wait horizon, engine scope, exit confirmation, threshold, sizing, spread rule or lifecycle rule may be changed before or during this validation.

## Fresh snapshot contract

Capture a new **48-hour MT5 XAUUSD tick snapshot** only after at least 48 live market hours have elapsed after the weekend reopen.

Use:
`tools/capture_recent_xau_ticks.py --hours 48`

Requirements:

- source: same MT5 terminal/broker feed used by the strategy;
- all raw fields retained: timestamp_utc, bid, ask, last, volume, flags, volume_real, spread, mid;
- immutable CSV + manifest + SHA-256;
- timestamp range must not overlap the existing recent24h snapshot ending 2026-09-24;
- final20 remains sealed;
- no external market data.

The manifest must reference:
`docs/experiments/2026-09-26/48-v4-5-candidate-j-fresh-validation.md`

## Evaluation

Run both 500 ms and 1 s grids.

For each candidate:

- whole-snapshot terminal-equity P&L;
- profit factor;
- trades / wins / win rate;
- max drawdown;
- trade count and engine attribution where available.

For Candidate J additionally:

- immediate / delayed / skipped entries;
- quote-phase exits;
- baseline-shadow parity;
- action/phase counts.

### Non-overlapping variable windows

Partition each continuity session into deterministic **non-overlapping four-hour blocks**.

Do not randomly resample the fresh snapshot.

Report per grid:

- mean four-hour terminal-equity P&L;
- median;
- p05 / p95;
- positive-block fraction;
- aggregate trades / wins.

### Cost stress

Whole fresh window only:

- $0.00;
- $0.05;
- $0.10;
- $0.20 adverse slippage per side.

## Predeclared prospective pass gate

Candidate J passes Experiment 48 only if **all** of the following hold on the fresh snapshot:

1. whole-window terminal-equity P&L > 0 on both 500 ms and 1 s;
2. whole-window Candidate-J P&L >= Candidate D on both grids;
3. non-overlapping four-hour mean P&L > 0 on both grids;
4. at least 50% of non-overlapping four-hour blocks are positive on both grids;
5. +$0.10 per-side stress remains >= 0 on both grids;
6. baseline-shadow opportunity path parity passes.

These criteria are frozen before data capture.

A pass does not automatically authorize live money. It only justifies advancing Candidate J to the next validation stage.

A fail rejects this frozen Candidate J on prospective data. Do not tune Candidate J against the failed fresh snapshot and call it unseen again.

## Next step after a pass

Only after a clean Experiment-48 pass may the project decide whether to:

- open the sealed historical final20 once as an additional confirmation;
- begin paper/live shadow execution;
- or both.

## Evidence contract

Experiment:
`docs/experiments/2026-09-26/48-v4-5-candidate-j-fresh-validation.md`

Validator:
`research/v4_5_candidate_j_fresh_validation.py`

Future evidence:
`results/simulations/<fresh-date>-v4_5-candidate-j-fresh-validation/`
