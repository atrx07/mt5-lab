# 54 — V4.5 Candidate M all-dataset comparison

Date: 2026-10-06

Status: **COMPLETE diagnostic rerun; Candidate M remains rejected unchanged.**

Implementation:  
`research/v4_5_candidate_m_all_dataset_comparison.py`

Evidence:  
`results/simulations/2026-10-06-v4_5-candidate-m-all-dataset-comparison/`

## Scope

Frozen Candidate M from Experiment 53 was rerun without parameter changes against every currently archived non-sealed XAU dataset:

- canonical Sep 16–23 seven-day archive, **first80 only**;
- frozen Sep 23–24 recent-24h archive;
- current Sep 29–Oct 06 seven-day archive;
- all six Experiment-48 Stage-1 four-hour blocks, individually and pooled.

Candidate D and Candidate H were rerun as comparators. The canonical final20 was not opened. No threshold/model search occurred.

Important: the current seven-day archive overlaps most of the six Stage-1 blocks. Their P&Ls must not be summed as independent evidence.

## Normal-fill comparison

### 500 ms

| Dataset | D | H | M | M vs H |
| --- | ---: | ---: | ---: | ---: |
| Historical first80 | +₹1,430.31 | +₹1,287.09 | **-₹0.87** | -₹1,287.96 |
| Recent 24h | -₹223.27 | -₹208.47 | **-₹28.66** | **+₹179.81** |
| Current 7d | -₹216.16 | -₹180.93 | **-₹78.33** | **+₹102.60** |
| Six Stage-1 blocks pooled | -₹165.32 | -₹97.91 | **-₹95.12** | **+₹2.79** |

### 1 s

| Dataset | D | H | M | M vs H |
| --- | ---: | ---: | ---: | ---: |
| Historical first80 | +₹385.25 | +₹360.79 | **+₹59.60** | -₹301.19 |
| Recent 24h | -₹135.91 | -₹128.63 | **-₹30.82** | **+₹97.81** |
| Current 7d | -₹229.17 | -₹194.96 | **-₹67.12** | **+₹127.85** |
| Six Stage-1 blocks pooled | -₹130.27 | -₹74.46 | **-₹70.47** | **+₹3.99** |

Candidate M therefore loses most of D/H's old historical upside, but strongly reduces losses on both independent later raw archives. On the six Stage-1 blocks M is only marginally better than H pooled and remains negative.

## Candidate M raw-window quality

Normal fills:

| Dataset / grid | P&L | Trades | Wins | Win rate | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Recent24h 500ms | -₹28.66 | 15 | 5 | 33.33% | 0.686 | ₹61.75 |
| Recent24h 1s | -₹30.82 | 15 | 6 | 40.00% | 0.683 | ₹64.34 |
| Current7d 500ms | -₹78.33 | 63 | 22 | 34.92% | 0.762 | ₹99.10 |
| Current7d 1s | -₹67.12 | 59 | 21 | 35.59% | 0.765 | ₹102.34 |

Historical first80 M used the canonical five-segment reset/compound accounting rather than a continuous full-window PF: -₹0.87 / 64 trades / 43.75% win rate / ₹67.54 max segment DD at 500 ms, and +₹59.60 / 57 trades / 52.63% / ₹69.88 at 1 s.

## +$0.10 adverse slippage per side

### 500 ms

| Dataset | D | H | M |
| --- | ---: | ---: | ---: |
| Historical first80 | +₹964.16 | +₹875.19 | **-₹42.52** |
| Recent24h | -₹232.59 | -₹219.15 | **-₹36.08** |
| Current7d | -₹232.31 | -₹198.59 | **-₹115.28** |

### 1 s

| Dataset | D | H | M |
| --- | ---: | ---: | ---: |
| Historical first80 | +₹248.12 | +₹240.97 | **+₹15.46** |
| Recent24h | -₹143.91 | -₹138.60 | **-₹39.29** |
| Current7d | -₹284.67 | -₹257.89 | **-₹112.26** |

The relative loss reduction survives cost stress on the later datasets, but absolute expectancy remains negative.

## Six Stage-1 blocks

Pooled M:

- 500 ms: **-₹95.12**, 28 trades, 8 wins, 28.57% win rate, 1/6 positive blocks;
- 1 s: **-₹70.47**, 25 trades, 8 wins, 32.00% win rate, 1/6 positive blocks.

The final Oct-05 block was positive for M on both grids (+₹10.41 / +₹22.18), but that isolated result does not change the pooled failure. Detailed block-by-block D/H/M results are in `stage1_block_comparison.csv`.

## Interpretation

Candidate M is a large structural improvement over Candidate L and materially less bad than D/H in both later full raw archives. Its price-acceptance mechanism appears to remove many low-quality commitments.

However, this rerun also confirms why Experiment 53 rejected it:

1. it destroys most of the old historical edge at 500 ms;
2. all later full-window P&Ls remain negative;
3. the six-block pooled test remains negative with only one positive M block per grid;
4. added execution cost remains damaging.

The useful retained result is the **price-acceptance mechanism**, not Candidate M itself. Any successor must be a new frozen hypothesis and must receive genuinely new prospective evidence before promotion.
