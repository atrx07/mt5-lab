# 49 — V4.5 current-regime seven-day D/H/J diagnostic

Date: 2026-10-06

Status: **COMPLETE — development diagnostic only; no candidate promoted.**

This experiment replayed the frozen V4.5 Candidate D, Candidate H and Candidate J implementations across a newly captured seven-calendar-day MT5 XAUUSD dataset after Experiment 48 Stage-1 outcomes were already known.

Because this dataset was captured after the prospective failure, it is **outcome-known development/diagnostic data**, not unseen validation evidence.

Dataset manifest:  
`data/manifests/xau_ticks_7d_2026-09-29_to_2026-10-06.json`

Archived dataset:  
`data/raw/xau_ticks_7d_current_2026-10-06.csv.gz`

Evaluator:  
`research/v4_5_current7d_candidate_eval.py`

Evidence summary:  
`results/simulations/2026-10-06-v4_5-current7d-candidate-eval/summary.json`

## Dataset

- Raw rows: **2,346,107**
- First tick: `2026-09-29T14:32:48.067000+00:00`
- Last tick: `2026-10-06T14:32:47.865000+00:00`
- Calendar span: approximately **168 h**
- Market-active time using gaps <60 s: approximately **110.0 h**
- Archive SHA-256: `9283df8c65979e6d91c67c734c7b57af3d3a8ceb658b50b3c499ba913580e177`

No external market data was used. No threshold search was performed. Final20 remained sealed.

Path checks passed:

- Candidate H entry path exactly matched Candidate D;
- Candidate J capital-free baseline shadow exactly matched Candidate D;
- both checks passed on 500 ms and 1 s grids.

## Full-week results

### 500 ms

| Candidate | P&L (INR) | Trades | Wins | Win rate | Profit factor | Max DD (INR) | Active-hour velocity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H | **-180.9270** | 137 | 48 | **35.04%** | **0.7428** | **218.06** | **-1.645 INR/h** |
| D | -216.1580 | 137 | 46 | 33.58% | 0.7245 | 237.89 | -1.965 INR/h |
| J | -229.0449 | 121 | 38 | 31.40% | 0.6407 | 249.79 | -2.082 INR/h |

Ranking by terminal-equity P&L: **H > D > J**.

Candidate H produced 19 PRIMARY flow exits and preserved D's entry path. Candidate J saw 137 D-shadow opportunities, took 121 trades, delayed 2 entries, skipped 16, and produced 10 phase exits.

### 1 s

| Candidate | P&L (INR) | Trades | Wins | Win rate | Profit factor | Max DD (INR) | Active-hour velocity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| H | **-194.9648** | 123 | 42 | **34.15%** | **0.7057** | **201.57** | **-1.772 INR/h** |
| J | -209.3879 | 104 | 33 | 31.73% | 0.6205 | 226.78 | -1.904 INR/h |
| D | -229.1745 | 123 | 40 | 32.52% | 0.6854 | 235.04 | -2.083 INR/h |

Ranking by terminal-equity P&L: **H > J > D**.

Candidate H produced 18 PRIMARY flow exits and preserved D's entry path. Candidate J saw 123 D-shadow opportunities, took 104 trades, delayed 1 entry, skipped 19, and produced 12 phase exits.

## +$0.10/side slippage stress

| Grid | D P&L | H P&L | J P&L |
| --- | ---: | ---: | ---: |
| 500 ms | -232.3083 | **-198.5895** | -235.8522 |
| 1 s | -284.6696 | **-257.8931** | -258.3114 |

All three remained negative under the cost stress.

## Interpretation

No D/H/J candidate demonstrated positive expectancy on the new current-regime week, so this experiment does not justify promotion of any of them.

The most transferable retained observation is that **Candidate H's path-preserving PRIMARY exit consistently improved D on both grids** in P&L, win rate and drawdown while using the same entry path. Candidate J's additional entry filtering reduced trade count but did not reliably select a profitable subset; it was worst at 500 ms and remained negative at 1 s.

The next candidate should therefore treat D/H/J as completed research components rather than continue threshold-tuning them. Future development may reuse the strongest ideas, but any new candidate developed using this week or the six Experiment-48 blocks must be frozen and judged on brand-new prospective data.

Final20 remains sealed.
