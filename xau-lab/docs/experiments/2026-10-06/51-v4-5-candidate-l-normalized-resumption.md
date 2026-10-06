# 51 — V4.5 Candidate L normalized structural resumption

Date: 2026-10-06

Status: **COMPLETE — frozen Candidate L rejected unchanged on development-survival screen.**

Frozen plan:  
`docs/plans/V4_5_CANDIDATE_L_NORMALIZED_RESUMPTION.md`

Implementation:  
`research/v4_5_candidate_l_normalized_resumption.py`

Evidence:  
`results/simulations/2026-10-06-v4_5-candidate-l-normalized-resumption/`

## Why Candidate L existed

Experiment 50 showed that multi-horizon price-shape quantities normalized by local range transferred much more closely between the original and current seven-day regimes than the inherited hard `$0.30` spread cap. Candidate L therefore tested a structurally new MT5-only trend -> pullback -> resumption architecture rather than another fitted admission overlay on Candidate D.

The complete Candidate-L rules and the development-survival screen were committed **before** Candidate-L P&L was evaluated. No post-result threshold tuning is allowed.

`Candidate K` was already the locked V4.4 MICRO management configuration, so this V4.5 candidate is correctly named **Candidate L**.

## Frozen architecture

Candidate L required:

- >=1800 s uninterrupted causal session history;
- 60 s / 300 s / 1800 s directional agreement;
- `abs(m60)/range60 >= 0.50` and `abs(m300)/range300 >= 0.50`;
- a real prior 10-second pullback of at least one current spread;
- resumption `m10 >= 1 spread`, `m30 >= 2 spreads`, `qacc >= 1.0` in the intended direction;
- MT5-native raw 2-second price and event-pressure confirmation;
- spread <= `$0.40` and <=20% of range60;
- one position, 3% planned entry risk, $4 stop, +$12 TP, 1800 s max hold;
- 300-second directional failure exit;
- Candidate-H-style two-confirmation raw-flow profit protection after +1R MFE and >=1R giveback.

No external feed, learned model, time-of-day/news table or P&L-fitted score was used. Final20 remained sealed.

## Comparator integrity

The evaluator reproduced the frozen D/H reference paths before Candidate-L interpretation:

- historical Candidate D: +₹1,430.31 / +₹385.25 at 500 ms / 1 s;
- historical Candidate H: +₹1,287.09 / +₹360.79;
- current-seven-day Candidate D: -₹216.16 / -₹229.17;
- current-seven-day Candidate H: -₹180.93 / -₹194.96;
- six-block pooled D/H values exactly matched Experiment 48.

Comparator parity therefore passed.

## Candidate-L result

### Historical first80

| Grid | P&L | Trades | Wins | Win rate | Worst segment DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **-₹153.11** | 258 | 82 | 31.78% | ₹224.57 |
| 1 s | **-₹162.70** | 226 | 73 | 32.30% | ₹260.91 |

Candidate L failed even on the historical development regime that made D/H strongly positive.

### Current seven-day regime

| Grid | Terminal-equity P&L | Trades | Wins | Win rate | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **-₹407.95** | 333 | 89 | 26.73% | 0.520 | ₹408.22 |
| 1 s | **-₹392.03** | 270 | 73 | 27.04% | 0.512 | ₹395.86 |

This was materially worse than both D and H on both grids.

### Six Experiment-48 blocks

Pooled terminal-equity P&L:

| Grid | D | H | L | Positive L blocks |
| --- | ---: | ---: | ---: | ---: |
| 500 ms | -₹165.32 | -₹97.91 | **-₹354.51** | 1 / 6 |
| 1 s | -₹130.27 | -₹74.46 | **-₹277.87** | 2 / 6 |

The hostile/random-state evidence therefore rejected L independently of the seven-day headline.

### Deterministic real four-hour windows

Eighty real contiguous four-hour windows per grid alternated between old and current seven-day continuity ranges.

| Grid | L mean | L median | Positive fraction | 5th pct | 95th pct |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **-₹36.58** | -₹39.24 | 17.5% | -₹114.26 | +₹100.17 |
| 1 s | **-₹25.25** | -₹40.16 | 20.0% | -₹110.54 | +₹175.24 |

This is the key random-situation rejection: Candidate L did not merely lose because one aggregate week was unfriendly. Most deterministic four-hour windows were negative and the mean was deeply negative on both execution grids.

For comparison, in this specific 80-window draw D mean was -₹0.53 / -₹1.59 and H mean was -₹1.89 / +₹4.09 at 500 ms / 1 s. These comparator random-window figures are diagnostic only; no promotion follows from them.

### Execution-cost stress

Current-seven-day Candidate-L P&L deteriorated monotonically under adverse slippage:

| Extra slippage / side | 500 ms | 1 s |
| --- | ---: | ---: |
| $0.00 | -₹407.95 | -₹392.03 |
| $0.05 | -₹427.96 | -₹410.02 |
| $0.10 | **-₹446.83** | **-₹426.42** |
| $0.20 | -₹465.97 | -₹452.35 |

Historical Candidate L was also negative at every stress level.

## Structural failure signature

The architecture produced far more entries than D/H while converting poorly:

- historical: 260 / 228 Candidate-L entries at 500 ms / 1 s;
- current seven-day: 334 / 271 entries;
- current win rate only ~27%.

Most completed trades exited through the 300-second trend-failure rule rather than TP or H-style profit protection:

- historical 500 ms: 206 trend-failure exits, 26 stops, 14 TPs, 12 flow exits;
- current 500 ms: 278 trend-failure exits, 29 stops, 9 TPs, 17 flow exits;
- historical 1 s: 178 trend-failure exits, 23 stops, 11 TPs, 14 flow exits;
- current 1 s: 226 trend-failure exits, 25 stops, 8 TPs, 11 flow exits.

This does **not** justify tuning the 0.50 dominance boundary, spread multiples, execution gate or m300 failure threshold against these outcomes. It says the frozen structural hypothesis itself is wrong: the normalized trend/pullback geometry creates too many apparent resumptions that do not persist as tradeable continuation.

## Frozen development-survival decision

Candidate L failed all performance gates on both grids except minimum trade count and comparator parity:

- historical P&L positive: **FAIL**;
- current-seven-day P&L positive: **FAIL**;
- random-window mean positive: **FAIL**;
- >=20 trades per seven-day source/grid: PASS;
- current +$0.10/side P&L positive: **FAIL**;
- comparator parity: PASS.

**Reject Candidate L unchanged. Do not tune its numeric boundaries against these known outcomes.**

## Next research implication

Experiment 50's representation result remains useful even though Candidate L failed. The failure says that normalized geometry alone is descriptive but does not establish *continuation persistence*. The next hypothesis must add a structurally different causal mechanism for commitment/persistence rather than simply tightening L's boundaries until past P&L turns green.

Any next candidate must again be frozen before outcome evaluation and must keep the random-window, dual-grid, six-block, cost-stress and continuity/shock checks. Passing known development evidence can only earn a new prospective test.

Final20 remains sealed.
