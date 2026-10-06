# 55 — V4.5 Candidate N dual price-acceptance continuation

Date: 2026-10-06

Status: **RUNNING — rules frozen before P&L evaluation.**

Frozen plan:  
`docs/plans/V4_5_CANDIDATE_N_DUAL_ACCEPTANCE.md`

Implementation:  
`research/v4_5_candidate_n_dual_acceptance.py`  
`research/v4_5_candidate_n_dual_acceptance_eval.py`

Evidence target:  
`results/simulations/2026-10-06-v4_5-candidate-n-dual-acceptance/`

## Hypothesis

Candidate M's pullback/reclaim path is retained unchanged. Candidate N adds a second, structurally separate continuation family for trends that never offer an M-style adverse pullback: a causal prior-30-second price breakout must establish and hold beyond the frozen breakout level by one frozen spread for two clock seconds, then pass the same execution and raw-flow confirmation used by M.

The new lane is designed to restore legitimately strong continuation opportunities without relaxing M's standards.

## Governance

- Plan committed before outcome evaluation.
- MT5/broker-native inputs only.
- No model or threshold search.
- No timestamp/news exclusions.
- Historical first80 only; final20 stays sealed.
- Known data may reject N, never promote it.
- Evaluation includes historical first80, recent24h, current7d, six Stage-1 blocks, three deterministic random-window seeds, and +$0.10/side stress.

Results and final decision are appended only after the frozen run completes.
