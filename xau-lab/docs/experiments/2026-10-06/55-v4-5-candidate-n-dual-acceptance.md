# 55 — V4.5 Candidate N dual price-acceptance continuation

Date: 2026-10-06

Status: **COMPLETE — frozen Candidate N rejected unchanged.**

Frozen plan:  
`docs/plans/V4_5_CANDIDATE_N_DUAL_ACCEPTANCE.md`

Implementation:  
`research/v4_5_candidate_n_dual_acceptance.py`  
`research/v4_5_candidate_n_dual_acceptance_eval.py`

Evidence:  
`results/simulations/2026-10-06-v4_5-candidate-n-dual-acceptance/`

## Hypothesis

Candidate M's pullback/reclaim path was retained in rule meaning and Candidate N added a second, structurally separate continuation family for trends that never offered an M-style adverse pullback. The new lane used a causal prior-30-second extreme, one frozen-spread price acceptance for two continuous clock seconds, and the same execution/raw-flow confirmation used by M.

Rules and survival gates were committed before Candidate-N P&L was inspected. No threshold/model search occurred and final20 remained sealed.

## Full-dataset result

Normal fills:

| Dataset | Grid | M | N | N trades | N WR | N breakout entries |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Historical first80 | 500 ms | -₹0.87 | **-₹86.24** | 188 | 37.23% | 171 |
| Historical first80 | 1 s | +₹59.60 | **-₹142.78** | 179 | 36.31% | 166 |
| Recent24h | 500 ms | -₹28.66 | **-₹148.14** | 62 | 24.19% | 58 |
| Recent24h | 1 s | -₹30.82 | **-₹115.80** | 52 | 26.92% | 49 |
| Current7d | 500 ms | -₹78.33 | **-₹363.51** | 239 | 28.45% | 224 |
| Current7d | 1 s | -₹67.12 | **-₹372.52** | 230 | 28.70% | 214 |

The added path succeeded only at increasing opportunity count. Breakout entries dominated N's trade population and destroyed Candidate M's selectivity.

## Six Stage-1 blocks

Pooled:

- 500 ms: D -₹165.32, H -₹97.91, M -₹95.12, **N -₹251.26**; N 84 trades, 17 wins, 1/6 positive blocks.
- 1 s: D -₹130.27, H -₹74.46, M -₹70.47, **N -₹204.21**; N 82 trades, 18 wins, 1/6 positive blocks.

Only the final Oct-05 block was positive for N on both grids; the pooled result remained decisively negative.

## Three-seed real four-hour audit

Each seed used 80 deterministic contiguous real four-hour windows per grid, alternating historical/current sources.

500 ms N:

- seed 55101 mean -₹50.18, median -₹46.79, positive 8.75%;
- seed 55102 mean -₹40.11, median -₹43.82, positive 22.50%;
- seed 55103 mean -₹31.92, median -₹37.49, positive 20.00%;
- pooled 240 windows: **mean -₹40.74, median -₹42.90, positive 17.08%**.

1 s N:

- seed 55101 mean -₹36.62, median -₹23.48, positive 12.50%;
- seed 55102 mean -₹40.61, median -₹37.09, positive 13.75%;
- seed 55103 mean -₹32.77, median -₹24.52, positive 15.00%;
- pooled 240 windows: **mean -₹36.67, median -₹27.48, positive 13.75%**.

This is not a marginal miss; the independent breakout family was structurally poor across all predeclared random batches.

## +$0.10 adverse slippage per side

N remained negative everywhere:

- historical first80: -₹174.97 / -₹225.31 (500 ms / 1 s);
- recent24h: -₹180.27 / -₹140.60;
- current7d: -₹403.63 / -₹406.27.

## Decision

**Reject Candidate N unchanged.**

The experiment answers the "make M take more trades" question clearly: generic trend-breakout continuation is not a safe additive lane. More trade count by itself was harmful; M's selectivity is valuable.

Do not tune N's 30-second breakout reference, timeout, two-second acceptance, structural dominance, spread gates or raw-flow confirmation against these outcomes.

The next hypothesis should preserve M's admission discipline and attack false-reclaim lifecycle failure directly rather than manufacturing more momentum entries. Candidate O is specified separately for that purpose.

Final20 remains sealed.
