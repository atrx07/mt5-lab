# 20 — V4.5 PRIMARY/SECONDARY exposure velocity

Date: 2026-09-24

Status: **completed; no candidate promoted. Candidate D remains the provisional V4.5 leader.**

## Objective

Candidate D uses 15.88 / 17.28 exposure hours at 500 ms / 1 s. PRIMARY and SECONDARY consume most of that time. Diagnose their trade paths, then test a small, conditional release rule that may reduce unproductive exposure without cutting profitable long holds indiscriminately.

The preferred strong-lock region is at least 50% more P&L per exposure hour, at least 20% less exposure and at least 20% more compounded P&L on both grids. A candidate that narrowly misses one target can remain lock-eligible pending review if it materially improves the overall Pareto frontier. Small PF/drawdown changes can be tolerated when clearly compensated; none causes an automatic lock.

## Data and parity

Use the first 1,869,979 raw rows and frozen five-segment boundaries only. Verify SHA-256. Assert V4.4 golden parity and exact Candidate B/D trace parity at both grids before interpreting diagnostics or variants. Select on 0–40%; use the later segments once for chronological evaluation. Keep the final 20% sealed.

## Diagnostic and candidate scope

At 60/120/300 s record executable move, favorable/adverse path, directional momentum and tick imbalance for PRIMARY/SECONDARY, along with final outcome. Match trade admissions across grids by time, side and engine to separate admission from lifecycle differences.

Test conditional release at the first quote after 120 or 300 s only if the position is nonpositive and both 60 s momentum and 10 s raw-tick imbalance oppose its side. Also test a two-second persistence requirement for SECONDARY's existing breakout condition if unmatched 1 s admissions are materially loss-making. The entry diagnostics additionally separate unmatched 1 s SECONDARY trades by weaker directional 10 s momentum and quote acceleration. Test a bounded flow-veto ablation using directional m10 >= $2 and qacc >= 1.0: both required, either sufficient, m10 only and qacc only. These tests only tighten admission. Preserve the $4 emergency stop, 3% planned risk, all other exit/entry rules, one shared slot and bid/ask fills. Use no final-holdout labels as signals.

## Canonical gates and diagnostics

The local raw SHA-256 matched `007e7ab10cc16519b544003dbe81521f46cf868bf267780932638d1e8cec86e5`. V4.4 reproduced the golden oracle and the new diagnostic reproduced Candidate B and D segment metrics exactly at 500 ms and 1 s. Only the frozen first-80% rows were read.

At 500 ms, Candidate D's PRIMARY and SECONDARY exposure totals 10.33 and 3.90 hours; at 1 s, 11.08 and 4.68 hours. The 120-second proposed release condition was met by 11 / 15 observed PRIMARY/SECONDARY trades at 500 ms / 1 s, but those groups' eventual P&L was +₹6.31 / -₹72.02. At 300 seconds, the condition caught only 6 / 5 trades, with eventual P&L +₹64.72 / -₹47.08. These are path diagnostics, not realizable counterfactual strategies; they show that the early-failure signature is not stable across grids.

The same-engine, same-side entry matching diagnostic found **nine 1 s PRIMARY trades** unmatched within 120 seconds of a 500 ms trade: -₹174.04 and 2.46 exposure hours, six emergency stops. It found **22 unmatched 1 s SECONDARY trades**: -₹141.28 and 1.86 exposure hours, 16 emergency stops. Matching is heuristic and shared-slot interactions prevent causal P&L attribution, but it identifies a substantial sampling-sensitive admission problem.

The unmatched 1 s SECONDARY entries had lower median directional 10 s momentum and quote acceleration than matched entries on the seed, motivating one bounded flow-veto ablation. The thresholds were directional m10 >= $2 and qacc >= 1.0; AND, OR, m10-only and qacc-only versions were tested. No threshold was loosened.

## Seed results and decision

All variants were selected/rejected on the 0–40% seed. No variant passed a joint 500 ms and 1 s profit-velocity improvement gate, so none was run on later evaluation segments or cost stress.

| Variant | 500 ms seed P&L | 1 s seed P&L | Main finding |
| --- | ---: | ---: | --- |
| Candidate D | ₹696.84 | ₹169.92 | comparator |
| Release at 120 s | ₹571.39 | ₹14.59 | harmful on both grids |
| Release at 300 s | ₹560.73 | ₹185.24 | small 1 s gain, large 500 ms loss |
| SECONDARY persistence 2 s | ₹369.56 | ₹18.91 | removes profitable admissions too |
| Flow veto: both strong | ₹479.16 | ₹282.27 | 1 s gain, major 500 ms loss |
| Flow veto: either strong | ₹512.57 | ₹209.25 | 500 ms loss |
| Flow veto: m10 strong | ₹418.10 | ₹317.74 | 1 s velocity gain, major 500 ms loss |
| Flow veto: qacc strong | ₹580.55 | ₹219.86 | 500 ms loss |

The m10-only veto did improve 1 s seed P&L per exposure hour from ₹15.45 to ₹36.69 and cut seed exposure from 11.00 to 8.66 hours, but reduced 500 ms seed P&L from ₹696.84 to ₹418.10. It is not a Pareto improvement and cannot be made lock-eligible by accepting a small PF or drawdown tolerance. The full seed metrics, exact configs and negative variants are retained.

The 50% velocity / 20% exposure / 20% compounded-P&L targets remain a **preferred strong-lock region**, not an automatic filter. A future candidate narrowly missing one may be lock-eligible pending review if its combined profitability, exposure, PF, drawdown, chronology and sampling stability materially improve. Minor PF/drawdown deterioration requires explicit compensation and never causes automatic lock. The variants here miss the joint profitability requirement by a wide margin.

## Evidence and next step

- [Result bundle](../../../results/simulations/2026-09-24-v4_5-exposure-velocity/)
- [Research script](../../../research/v4_5_exposure_velocity.py)

Candidate D stays provisional. The next bounded research step is a raw-event admission feature built from the underlying first-80% tick stream identically for both execution grids, with V4.4/B/D parity retained and no canonical replay-schema change. The result here does **not** establish that such a feature will work. Do not open the holdout or create `paper_challenge_v4_5.py`.
