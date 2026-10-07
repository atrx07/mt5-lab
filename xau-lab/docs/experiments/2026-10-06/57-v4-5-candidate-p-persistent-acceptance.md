# 57 — V4.5 Candidate P persistent price + flow acceptance

Date: 2026-10-06

Status: **COMPLETE — Candidate P rejected unchanged.**

Frozen plan:  
`docs/plans/V4_5_CANDIDATE_P_PERSISTENT_ACCEPTANCE.md`

Implementation:  
`research/v4_5_candidate_p_persistent_acceptance.py`  
`research/v4_5_candidate_p_persistent_acceptance_eval.py`

Evidence:  
`results/simulations/2026-10-06-v4_5-candidate-p-persistent-acceptance/`

## Hypothesis

Candidate M's setup and exits were left unchanged. At the point M would enter, Candidate P recorded confirmation A and required price to remain continuously accepted for another full two-second acceptance clock, then required the same execution/qacc/raw-flow test again as confirmation B before committing capital.

The intent was to reject transient false reclaims before entry without loosening M or adding another opportunity family.

## Governance

- Plan frozen before outcome evaluation.
- MT5/broker-native only.
- No threshold/model search.
- No news/time exclusions.
- Historical first80 only; final20 stayed sealed.
- New random seeds 57011, 57012, 57013 were frozen in advance.
- Known data could reject P, never promote it.

## Results

P was strongly regime-selective rather than portable.

Normal-fill P&L:

| Dataset | 500 ms | 1 s |
| --- | ---: | ---: |
| Historical first80 | -₹82.34 | -₹43.96 |
| Recent24h | **+₹5.32** | **+₹42.82** |
| Current7d | -₹67.10 | -₹110.84 |
| Six Stage-1 blocks pooled | -₹68.03 | -₹59.14 |

The recent24h slice was the only full dataset where P was positive on both grids. At 500 ms it made +₹5.32 from 8 trades (50% wins, PF 1.14); at 1 s it made +₹42.82 from 4 trades (75% wins, PF 3.82).

That did not transfer to the broader random-window audit. Across 240 deterministic real contiguous four-hour windows per grid:

- 500 ms pooled mean -₹11.83, median -₹12.23, positive fraction 25.0%;
- 1 s pooled mean -₹11.24, median -₹11.06, positive fraction 16.7%;
- every predeclared random seed mean was negative on both grids.

P also remained negative on the current seven-day regime, historical first80, and pooled Stage-1 blocks. +$0.10/side stress preserved the recent24h advantage but did not fix the broad failure.

P reduced trade count heavily versus M (for example current7d 63→35 trades at 500 ms and 59→29 at 1 s) without consistently selecting the better half of M opportunities.

Comparator parity passed. No final20 data were opened.

## Decision

**Hard reject Candidate P as a strategy candidate in its frozen form.**

Retain the post-acceptance persistence idea only as diagnostic mechanism evidence: it can be highly valuable in some regimes, but the fixed second two-second confirmation is too regime-specific and too destructive to opportunity coverage.

Per the predeclared governance rule, stop rapid P→Q→R candidate search on the same known datasets. Further architecture changes must not be selected by repeatedly watching these already-consumed outcomes. The next research step is fresh prospective discrimination / shadow evidence, with any later candidate frozen before a new unseen validation tranche.
