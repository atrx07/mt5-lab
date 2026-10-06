# 48 — V4.5 Candidate J fresh MT5-only prospective validation

Date opened: 2026-09-26  
Date closed: 2026-10-06

Status: **COMPLETE — Stage 1 FAIL; frozen Candidate J prospectively rejected. Stage 2 was not run.**

Candidate J was frozen unchanged after Experiment 47 and evaluated on six genuinely fresh MT5-only scored blocks. No external market data was used and the sealed historical final20 remained unopened.

Frozen plan:  
`docs/plans/V4_5_CANDIDATE_J_FRESH_VALIDATION.md`

Final Stage-1 validator:  
`research/v4_5_candidate_j_stage1_staged_validation.py`

Frozen block archive/index:  
`data/prospective_archives/candidate_j_stage1_index.json`

## Staged-capture amendment

Before the first scored prospective block, the original continuous-48-hour design was replaced with a practical staged design:

- Stage 1 = six independent fresh 4-hour scored blocks;
- each block gets 90 minutes of causal MT5 prehistory as feature/history context only;
- blocks span multiple market days;
- Candidate J remains frozen unchanged;
- no block is selected or discarded based on Candidate-J outcome.

Capture tool:  
`scripts/capture_candidate_j_4h_block.py`

Windows launcher:  
`scripts/start_candidate_j_4h_block.ps1`

The Stage-1 pass gate was frozen before the first scored result was inspected.

## Block-duration amendment

After Stage-1 Block #3 crossed a broker no-tick maintenance interval, and before any staged-block Candidate D/H/J outcomes were evaluated, the score-duration rule was amended outcome-blind:

- preserve the originally frozen block start;
- accumulate four **market-active** hours;
- pause the scored clock across MT5 no-tick gaps >=60 seconds;
- determine the end mechanically from timestamps only;
- use the same MT5/broker history for reconstruction;
- do not inspect candidate P&L when determining or repairing the endpoint.

Blocks without such a gap were unchanged.

## Accepted Stage-1 blocks

Exactly these six blocks were scored and later frozen as evidence:

- `20260928T150531Z`
- `20260929T132027Z`
- `20261001T171601Z`
- `20261002T071041Z`
- `20261002T132739Z`
- `20261005T132049Z`

Integrity checks passed for all six: manifest and SHA verification, no score-window overlap, five distinct market days, Candidate-J-frozen flag true, external-data flag false, final20 flag false, and Candidate-J baseline-shadow parity on both grids.

After scoring, these six blocks became **outcome-known diagnostic/development data**. They must never be relabeled as unseen evidence for a later candidate.

## Stage-1 results

### 500 ms

| Candidate | Pooled P&L (INR) | Trades | Wins | Win rate |
| --- | ---: | ---: | ---: | ---: |
| D | -165.3170 | 53 | 12 | 22.64% |
| H | -97.9096 | 53 | 13 | 24.53% |
| J | -139.0081 | 49 | 10 | 20.41% |

Candidate J mean 4-hour P&L: **-23.1680 INR**.  
Positive J blocks: **1/6**.  
J >= D blocks: **4/6**.  
J at +$0.10/side slippage stress: **-171.552 INR**.

### 1 s

| Candidate | Pooled P&L (INR) | Trades | Wins | Win rate |
| --- | ---: | ---: | ---: | ---: |
| D | -130.2671 | 46 | 12 | 26.09% |
| H | -74.4579 | 46 | 12 | 26.09% |
| J | -58.8979 | 40 | 10 | 25.00% |

Candidate J mean 4-hour P&L: **-9.8163 INR**.  
Positive J blocks: **2/6**.  
J >= D blocks: **3/6**.  
J at +$0.10/side slippage stress: **-114.456 INR**.

## Frozen gate outcome

Stage 1 required every gate to pass on both grids. It failed because:

- pooled J P&L was not positive on either grid;
- mean J 4-hour P&L was not positive on either grid;
- J did not produce >=3/6 positive blocks on either grid;
- the 1 s J>=D block-count gate failed at 3/6;
- +$0.10/side stressed J P&L was negative on both grids.

The D-baseline shadow parity gate passed on both grids.

Final decision: **FAIL Stage 1; reject this frozen Candidate J prospectively. Do not tune on these six blocks and relabel the result unseen.**

Stage 2 was therefore not started.

## Research consequence

The experiment did not validate Candidate J, but it produced useful architectural evidence: Candidate H's exit treatment repeatedly reduced losses relative to D, while J's entry filtering did not transfer reliably enough to create positive expectancy. Those observations may inform future development, but the six Stage-1 blocks are now development data only.

Final20 remains sealed.
