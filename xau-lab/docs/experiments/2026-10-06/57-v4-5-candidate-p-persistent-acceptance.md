# 57 — V4.5 Candidate P persistent price + flow acceptance

Date: 2026-10-06

Status: **RUNNING — rules frozen before P&L evaluation.**

Frozen plan:  
`docs/plans/V4_5_CANDIDATE_P_PERSISTENT_ACCEPTANCE.md`

Implementation:  
`research/v4_5_candidate_p_persistent_acceptance.py`  
`research/v4_5_candidate_p_persistent_acceptance_eval.py`

Evidence target:  
`results/simulations/2026-10-06-v4_5-candidate-p-persistent-acceptance/`

## Hypothesis

Candidate M's setup and exits are unchanged. At the point M would enter, Candidate P instead records confirmation A and requires price to remain continuously accepted for another full two-second acceptance clock, then requires the same execution/qacc/raw-flow test again as confirmation B before committing capital.

This is intended to reject transient false reclaims before entry rather than adding more opportunity lanes or imposing a post-entry hard anchor exit.

## Governance

- Plan frozen before outcome evaluation.
- MT5/broker-native only.
- No threshold/model search.
- No news/time exclusions.
- Historical first80 only; final20 sealed.
- New random seeds 57011, 57012, 57013 frozen in advance.
- If P fails, the plan explicitly stops rapid candidate search on these same known datasets to avoid meta-overfitting.

Results and final decision are appended after the frozen run completes.
