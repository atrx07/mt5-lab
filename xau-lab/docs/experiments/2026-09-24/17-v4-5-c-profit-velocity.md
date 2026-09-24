# 17 — V4.5-C profit-velocity lifecycle search

Date: 2026-09-24

Status: **completed; no V4.5-C promotion. Candidate B remains the V4.5 research leader.**

## Objective

The project objective is not to maximize capture in isolation. It is to maximize expected XAUUSD profit per unit time while keeping fixed risk, execution-cost sensitivity, drawdown and sampling robustness under control.

Candidate B entered this experiment as the verified V4.5 research leader:

- 500 ms canonical capture: 17.3652%;
- 1 s canonical capture: 4.8814%;
- final 20% holdout unopened.

The large 500 ms -> 1 s degradation is treated as a fragility diagnostic, not as a separate trading target.

## Phase C1

Phase C1 changed **BURST lifecycle only**.

The following remained unchanged:

- V4.4 PRIMARY;
- V4.4 SECONDARY;
- V4.4 MICRO;
- Candidate B BURST admission;
- 3% planned risk;
- $4 emergency stop;
- one shared position slot;
- canonical first-80% research boundaries.

The search varied:

- BURST maximum hold: 120 / 180 s;
- trail trigger: $5.50 / $6.50 / $7.50;
- trail give-back: $2.00 / $2.50;
- optional raw-flow continuation extension;
- optional flow-decay early exit.

This produced 48 lifecycle combinations.

## Canonical gates

The successful full run used the canonical dataset SHA-256:

`007e7ab10cc16519b544003dbe81521f46cf868bf267780932638d1e8cec86e5`

Before any candidate comparison:

- V4.4 500 ms canonical parity: **PASS**;
- Candidate B 500 ms instrumentation parity: **PASS**;
- V4.4 1 s canonical parity: **PASS**;
- Candidate B 1 s instrumentation parity: **PASS**.

The final 20% holdout was not read.

## Profit-velocity instrumentation

The harness records:

- compounded P&L and capture;
- trade count and wins;
- median segment PF;
- worst segment drawdown;
- total exposure time;
- P&L per exposure hour;
- mean hold time;
- P&L per trade;
- BURST-only P&L, trade count and P&L per exposure hour;
- mean MFE / MAE;
- count of negative chronological segments.

The ranking heuristic weights:

- 40% canonical P&L at 500 ms;
- 20% canonical P&L at 1 s;
- 25% P&L per exposure hour at 500 ms;
- 15% P&L per exposure hour at 1 s;

with penalties for PF deterioration and drawdown expansion.

The score is only a search heuristic, not a promotion criterion.

## Search outcome

All **48 of 48** lifecycle variants produced exactly the same 0-40% seed outputs as Candidate B on both sampling grids.

Every seed score was exactly `1.0000`.

The top eight therefore entered the chronological 40-80% evaluation as ties. All eight again reproduced Candidate B exactly.

The top three full first-80% summaries were also exact Candidate B reproductions.

There is therefore **no distinct Candidate C from Phase C1**.

## Full first-80% result

| Metric | 500 ms | 1 s |
| --- | ---: | ---: |
| Compounded P&L | +₹1,299.37 | +₹365.25 |
| Capture | 17.3652% | 4.8814% |
| Trades | 163 | 156 |
| Wins | 79 | 70 |
| Median segment PF | 1.3614 | 1.3823 |
| Worst segment DD | ₹218.68 | ₹172.38 |
| Exposure | 15.823 h | 17.248 h |
| P&L / exposure hour | ₹58.36 | ₹18.06 |
| Mean hold | 349.47 s | 398.03 s |
| P&L / trade | ₹5.67 | ₹2.00 |

BURST-only attribution:

- 500 ms: +₹58.40 across 17 BURST trades, ₹232.98 per exposure hour;
- 1 s: +₹10.44 across 12 BURST trades, ₹67.49 per exposure hour.

The weak 50-60% research region remains negative:

- 500 ms: -₹13.58;
- 1 s: -₹45.95.

## Interpretation

The tested lifecycle controls are effectively inactive on the observed Candidate B BURST trade paths.

Changing max hold, trail trigger, trail give-back, conditional flow extension and the tested decay exit did not alter a completed trade in the seed region. The later evaluation/full replays confirmed that tied variants also leave Candidate B unchanged.

This suggests that earlier BURST exit conditions and/or the entry path dominate before the tested lifecycle controls can affect realized trades.

Phase C1 therefore does not justify more grid search around these same controls.

## Runtime portability correction

The first automated execution exposed a pandas-version portability bug in the canonical timestamp conversion.

Pandas 3 may store parsed datetimes internally at microsecond resolution, while the previous implementation assumed nanoseconds before dividing the raw integer representation by `1e9`. On that runtime the first replay therefore produced a false baseline drift with zero trades.

`scripts/canonical_replay.py` was corrected to explicitly normalize timestamps to `datetime64[ns]` before epoch conversion.

This is a runtime portability fix, not a replay-schema change. After the fix, the stored V4.4 golden oracle reproduced exactly at both intervals and Candidate B instrumentation parity passed.

## Decision

- **Reject Phase C1 as a V4.5-C promotion.**
- Candidate B remains the V4.5 research leader.
- Do not create `paper_challenge_v4_5.py`.
- Keep the final 20% holdout sealed.
- Do not spend more search budget on these max-hold/trail/flow-decay ranges until the active BURST exit path is measured directly.

## Next research implication

Before another optimization pass, instrument BURST trades with:

- exact exit reason;
- entry/exit timestamps and side;
- MFE/MAE and time-to-MFE;
- state at exit;
- which of zero-cross, stagnation, TP, stop, trail or max-hold actually fired;
- short-window post-exit favorable excursion;
- matched/missed opportunity identity between 500 ms and 1 s.

The next V4.5 candidate should be designed from those diagnostics rather than another blind lifecycle grid.

## Evidence

- [Result bundle](../../../results/simulations/2026-09-24-v4_5-c-profit-velocity/)
- [Result interpretation](../../../results/simulations/2026-09-24-v4_5-c-profit-velocity/README.md)
- [Search harness](../../../scripts/v4_5_profit_velocity_search.py)
