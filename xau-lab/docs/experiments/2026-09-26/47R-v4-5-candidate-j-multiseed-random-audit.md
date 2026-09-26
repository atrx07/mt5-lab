# 47R — V4.5 Candidate J multi-seed random-window robustness audit

Date: 2026-09-26
Status: **completed; 500 ms positive mean replicated across all three new seeds; 1 s remains near break-even**

This audit reruns frozen Candidate J against Candidate D/H on three new deterministic random-window batches, 40 real contiguous four-hour windows per grid per batch.

It does not tune Candidate J and does not change the Experiment-48 fresh-data gate.

Frozen specification:
`docs/plans/V4_5_CANDIDATE_J_MULTISEED_RANDOM_AUDIT.md`

Implementation:
`research/v4_5_candidate_j_multiseed_random_audit.py`

Evidence:
`results/simulations/2026-09-26-v4_5-candidate-j-multiseed-random-audit/`

Final20 remains sealed.


## Result

Candidate J was rerun unchanged on three new deterministic random seeds. Each batch contained 40 real contiguous four-hour windows per grid with the same deliberately hostile 50/50 historical-first80 vs recent24h source balance used in Experiment 47.

Baseline-shadow opportunity parity passed for every sampled Candidate-J window.

### Mean four-hour terminal-equity P&L

| Grid | Batch | Candidate D | Candidate H | Candidate J |
| --- | --- | ---: | ---: | ---: |
| 500 ms | A | -₹2.59 | -₹7.78 | **+₹0.97** |
| 500 ms | B | +₹3.20 | +₹0.02 | **+₹8.13** |
| 500 ms | C | -₹3.17 | -₹4.75 | **+₹3.92** |
| 500 ms | pooled 120 | -₹0.85 | -₹4.17 | **+₹4.34** |
| 1 s | A | -₹8.75 | -₹6.38 | **+₹0.54** |
| 1 s | B | -₹10.65 | -₹8.47 | **-₹2.85** |
| 1 s | C | -₹5.15 | -₹2.71 | **+₹1.83** |
| 1 s | pooled 120 | -₹8.18 | -₹5.85 | **-₹0.16** |

### Pooled three-batch robustness

500 ms Candidate J:
- mean +₹4.34;
- median -₹19.42;
- p05 -₹19.42;
- p95 +₹90.28;
- positive-window fraction 36.67%;
- 1,136 total trades, 385 wins, aggregate win rate 33.89%;
- beat Candidate D in 92.5% of windows;
- beat Candidate H in 81.67%.

1 s Candidate J:
- mean -₹0.16;
- median -₹12.96;
- p05 -₹26.88;
- p95 +₹54.03;
- positive-window fraction 32.5%;
- 1,155 total trades, 437 wins, aggregate win rate 37.84%;
- beat Candidate D in 87.5% of windows;
- beat Candidate H in 64.17%.

### Interpretation

The original Experiment-47 500 ms positive random-window mean was **not a one-seed accident**. Candidate J remained positive on all three new 500 ms batches (+₹0.97, +₹8.13, +₹3.92), and pooled +₹4.34 across 120 new sampled windows.

The result is not equivalent to a majority-win strategy: the 500 ms median remains negative and only 36.67% of pooled windows are positive. Positive expectancy is carried by a smaller number of larger winners. That payoff shape must survive prospective data before it is trusted for live use.

The 1 s result is materially improved but **not confirmed positive**. Two of three new batches were slightly positive, one was negative, and the pooled mean is effectively break-even at -₹0.16. It would be incorrect to claim 1 s profitability from this audit.

## Decision

The multi-seed audit materially strengthens confidence that Candidate J's **500 ms mean-expectancy improvement is structurally repeatable on the known datasets**, while 1 s remains unresolved.

Candidate J stays frozen unchanged. Do not tune it from these results.

Experiment 48 remains the decisive fresh MT5-only prospective validation gate.

Candidate D remains formal leader until that prospective test. Final20 remains sealed.
