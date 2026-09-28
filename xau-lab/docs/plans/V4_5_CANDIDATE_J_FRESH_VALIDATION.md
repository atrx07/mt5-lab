# Experiment 48 — fresh MT5-only prospective validation of Candidate J

Date: 2026-09-26

Status: **amended before the first scored prospective block; staged 4-hour capture replaces continuous 48-hour requirement**

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

## Fresh staged-capture contract

The original continuous 48-hour requirement is superseded **before the first scored prospective block** because the owner's laptop cannot reasonably remain powered and internet-connected continuously for two days.

The scientific constraint is preserved by using predeclared independent fresh blocks rather than one uninterrupted file.

### Stage 1

Capture **six fresh 4-hour scored blocks** using the same MT5/broker XAUUSD feed.

Requirements:

- each block is started deliberately before viewing Candidate-J outcomes;
- each block has **90 minutes of causal MT5 history available before score start**;
- the 90-minute history may be fetched immediately from MT5 tick history at launch and is context only, not scored;
- the scored block begins at launch and lasts exactly four wall-clock hours;
- no block may overlap another scored block;
- collect the six blocks across at least **three different market days** and, where practical, different times of day;
- all raw fields are retained: timestamp_utc, bid, ask, last, volume, flags, volume_real, spread, mid;
- raw data + manifest + SHA-256 are frozen per block;
- final20 remains sealed;
- no external market data.

Default capture tool:
`scripts/capture_candidate_j_4h_block.py`

### Stage 2

If Stage 1 passes the frozen gate below, collect **six additional fresh 4-hour blocks** under the same unchanged Candidate-J implementation and the same capture/evaluation contract.

Do not tune Candidate J between Stage 1 and Stage 2.

## Evaluation

Run Candidate D, Candidate H and frozen Candidate J on both 500 ms and 1 s for each scored block.

The 90-minute prehistory exists only to provide causal feature/history context. Performance accounting begins at the declared score-start boundary.

For every block/candidate report:

- terminal-equity P&L;
- profit factor;
- trades / wins / win rate;
- max drawdown.

For Candidate J additionally:

- immediate / delayed / skipped entries;
- quote-phase exits;
- baseline-shadow parity;
- action/phase counts.

Across the six blocks report per grid:

- mean and median block P&L;
- p05 / p95;
- positive-block fraction;
- aggregate trades / wins;
- Candidate-J vs Candidate-D block wins.

### Cost stress

Re-evaluate each scored block with:

- $0.00;
- $0.05;
- $0.10;
- $0.20 adverse slippage per side.

## Predeclared Stage-1 prospective pass gate

Candidate J passes Stage 1 only if **all** of the following hold across the six fresh blocks:

1. pooled Candidate-J P&L > 0 on both 500 ms and 1 s;
2. pooled Candidate-J P&L >= pooled Candidate-D P&L on both grids;
3. mean 4-hour Candidate-J P&L > 0 on both grids;
4. at least 3 of 6 blocks are positive for Candidate J on both grids;
5. Candidate J beats or equals Candidate D in at least 4 of 6 blocks on both grids;
6. pooled Candidate-J P&L under +$0.10 per-side stress remains >= 0 on both grids;
7. baseline-shadow opportunity parity passes for every block.

These criteria are frozen before the first scored four-hour block.

A Stage-1 pass advances the **unchanged** Candidate J to Stage 2. It does not authorize live-money execution.

A Stage-1 fail rejects this frozen Candidate J prospectively. Do not tune against these six blocks and relabel the tuned version as unseen.

## Predeclared Stage-2 confirmation

Stage 2 uses six additional fresh blocks and repeats the same seven pass conditions independently.

Only a clean Stage-2 pass may advance Candidate J to the final confirmation decision.

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
