# 56 — V4.5 Candidate O acceptance-thesis invalidation

Date: 2026-10-06

Status: **COMPLETE — frozen Candidate O rejected unchanged.**

Frozen plan:  
`docs/plans/V4_5_CANDIDATE_O_ACCEPTANCE_INVALIDATION.md`

Implementation:  
`research/v4_5_candidate_o_acceptance_invalidation.py`  
`research/v4_5_candidate_o_acceptance_invalidation_eval.py`

Evidence:  
`results/simulations/2026-10-06-v4_5-candidate-o-acceptance-invalidation/`

## Hypothesis

Candidate M's entry was retained unchanged. Candidate O retained M's pre-pullback anchor at entry and exited when price remained back on the adverse side of that anchor for two continuous clock seconds. The goal was to cut false-reclaim exposure without loosening M or manufacturing another entry family.

The rules, new random seeds and survival gates were committed before Candidate-O P&L was inspected. Final20 remained sealed.

## Full-dataset result

Normal fills:

| Dataset | Grid | M | O | O trades | O WR | Thesis exits |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Historical first80 | 500 ms | -₹0.87 | **-₹100.74** | 71 | 28.17% | 43 |
| Historical first80 | 1 s | +₹59.60 | **rejected / negative** | — | — | — |
| Recent24h | 500 ms | -₹28.66 | **-₹16.96** | 16 | 18.75% | 13 |
| Current7d | 500 ms | -₹78.33 | **-₹100.02** | 67 | 17.91% | 50 |

At 500 ms the new exit slightly improved the separate recent24h loss but made both historical and current-seven-day results worse. The 1 s survival gates also failed; exact machine results are preserved in `summary.json` / `full_dataset_comparison.csv`.

The exit fired frequently: 43/71 historical 500 ms trades and 50/67 current-seven-day 500 ms trades. Losing the pre-pullback anchor was therefore **not** a reliable terminal invalidation signal; many eventually useful trades revisited that level.

## Six Stage-1 blocks

Pooled:

- 500 ms: M -₹95.12 → **O -₹56.41**, 31 trades, 5 wins, 1/6 positive blocks;
- 1 s: M -₹70.47 → **O -₹41.20**, 29 trades, 5 wins, 2/6 positive blocks.

This is a meaningful loss reduction on those known blocks, but still fails the predeclared nonnegative pooled gate and positive-block gate.

## Cost stress

At +$0.10 adverse slippage per side, 500 ms O remained negative on all three full archives:

- historical first80: **-₹140.20**;
- recent24h: **-₹28.45**;
- current7d: **-₹137.75**.

The 1 s stress gates also failed. Exact results are preserved in the machine evidence.

## Random-situation audit

All three newly predeclared seeds (56011, 56012, 56013) failed the required positive-mean condition on at least one/both grids; pooled random median and positive-window-fraction gates also failed. No seed or random threshold was selected after seeing outcomes.

## Decision

**Reject Candidate O unchanged.**

The structural lesson is useful: Candidate M's reclaim anchor behaves more like a level that can be retested than a hard post-entry invalidation barrier. Exiting simply because price revisits/loses it for two seconds overreacts and destroys too many trades.

Do not tune the two-second invalidation clock, anchor level, stop/TP, M entry rules or H flow-exit rules against these outcomes.

Combined with Candidate N, this narrows the next direction sharply:

- adding generic continuation entries is harmful;
- hard early exit on the reclaimed anchor is also harmful;
- preserve M's admission discipline;
- if another candidate is attempted, it should require **persistent confirmation before capital entry**, rather than trying to fix the trade after commitment.

Final20 remains sealed.
