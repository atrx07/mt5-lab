# 56 — V4.5 Candidate O acceptance-thesis invalidation

Date: 2026-10-06

Status: **RUNNING — rules frozen before P&L evaluation.**

Frozen plan:  
`docs/plans/V4_5_CANDIDATE_O_ACCEPTANCE_INVALIDATION.md`

Implementation:  
`research/v4_5_candidate_o_acceptance_invalidation.py`  
`research/v4_5_candidate_o_acceptance_invalidation_eval.py`

Evidence target:  
`results/simulations/2026-10-06-v4_5-candidate-o-acceptance-invalidation/`

## Hypothesis

Candidate M's entry is retained unchanged. Candidate O stores M's already-known pre-pullback anchor at entry and exits when price remains back on the adverse side of that anchor for two continuous clock seconds. The purpose is to cut failed reclaim trades when their exact entry thesis has invalidated, rather than loosening M or adding another generic momentum lane.

## Governance

- Frozen plan committed before P&L evaluation.
- MT5/broker-native inputs only.
- No threshold/model search.
- No news/time exclusions.
- Historical first80 only; final20 sealed.
- Three new predeclared random seeds: 56011, 56012, 56013.
- Known data may reject O, never promote it.

Results and final decision are appended only after the frozen run completes.
