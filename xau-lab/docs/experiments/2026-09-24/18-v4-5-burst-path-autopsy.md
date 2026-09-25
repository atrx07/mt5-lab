# 18 — V4.5 BURST-path autopsy

Date: 2026-09-24

Status: **completed; diagnostic evidence accepted after both parity gates**

## Objective

Measure Candidate B's actual BURST admissions, exits, missed sampled opportunities and post-exit paths before selecting another V4.5 change. Candidate B remains the research leader; V4.4 is the locked baseline.

## Gates and data discipline

- Verify the raw CSV SHA-256 against the canonical dataset contract.
- Build canonical features at 500 ms and 1 s using `research/canonical_replay.py`.
- Assert locked V4.4 against the golden oracle on both grids.
- Require instrumented Candidate B to match the canonical Candidate B segment metrics exactly before interpreting any trace.
- Read only the first 1,869,979 raw rows with the frozen five research segments. The final 20% holdout stays sealed.

## Diagnostic scope

Record BURST trade identity, side, exact entry/exit time, exit reason, hold, P&L, MFE/MAE and time to MFE; entry and exit momentum, flow, spread and range; favorable/adverse 10/30/60 s post-exit paths; and 500 ms versus 1 s admission matching. Preserve bid/ask fills, 3% planned risk, the $4 stop and the shared slot.

Search or candidate changes must be justified from the measured dominant failure mode. Seed region 0–40% is for candidate design; later research segments provide chronological evaluation. Cost stress is required for a serious candidate.

## Evidence

- [Result bundle](../../../results/simulations/2026-09-24-v4_5-burst-path-autopsy/)
- [Diagnostic script](../../../research/v4_5_burst_path_autopsy.py)

## Findings

The raw SHA-256 matched `007e7ab10cc16519b544003dbe81521f46cf868bf267780932638d1e8cec86e5`. V4.4 reproduced its golden oracle at 500 ms and 1 s. The instrumented Candidate B reproduced all five segment P&L, PF, trade, win and drawdown values exactly on each grid. No final holdout row was read.

Every BURST trade exited on the **first 30 s momentum zero-cross**: 17/17 at 500 ms and 12/12 at 1 s. Mean hold was 53.08 s / 46.41 s. Neither stop, take profit, trail, stagnation nor max hold triggered on a BURST trade. This directly explains why Experiment 17's lifecycle grid made no difference.

Within 60 s of exit, mean maximum additional favorable move was $1.36 / $1.10, while mean maximum adverse move was $1.16 / $1.18. These are hindsight excursions, not an executable continuation rule. At 500 ms, 8/17 had at least $1 favorable continuation and 8/17 also had at least $1 adverse excursion; a blanket long hold is therefore not justified.

There were 28 raw BURST threshold episodes at 500 ms and 25 at 1 s. Twenty-two 500 ms episodes matched a 1 s episode within the defined 30 s tolerance; six did not. Ten of 17 actual 500 ms BURST trades matched a same-side 1 s BURST trade within 120 s. Of the seven unmatched trades, five lacked a nearby 1 s threshold episode, one had the shared slot occupied, and one had a signal episode but no BURST admission. Matched trade entry delay was at most 2.257 s. Episode and trade matching are diagnostic heuristics; they are not counterfactual P&L.

The much larger **overall** 500 ms to 1 s degradation is concentrated outside BURST. Summed segment PRIMARY P&L fell from ₹587.86 to ₹156.12 and SECONDARY from +₹83.78 to -₹52.57; BURST fell from +₹58.40 to +₹10.44. The 50–60% segment was -₹13.58 / -₹45.95, with only one 500 ms BURST trade and no 1 s BURST trade. A BURST-only exit change cannot by itself cure the weak region or the whole-system sampling gap.

## Decision and next step

The dominant **BURST lifecycle** failure mode is immediate zero-cross exit precedence. Test a short, confirmed zero-cross as Experiment 19. Sampling-dependent BURST admissions and the broader PRIMARY/SECONDARY fragility require separate research. Keep the holdout sealed and Candidate B as the leader until a parity-gated candidate earns promotion.
