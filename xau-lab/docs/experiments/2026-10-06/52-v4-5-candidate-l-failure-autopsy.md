# 52 — V4.5 Candidate L structural failure autopsy

Date: 2026-10-06

Status: **COMPLETE — outcome-known diagnostic after Candidate L rejection; no retuning allowed.**

Implementation:  
`research/v4_5_candidate_l_failure_autopsy.py`

Evidence:  
`results/simulations/2026-10-06-v4_5-candidate-l-failure-autopsy/`

## Purpose

Candidate L had already failed its predeclared development-survival screen in Experiment 51. This experiment uses its frozen trade ledger only to determine whether the dominant problem was poor entry commitment or profit-management behavior.

No Candidate-L threshold was searched or changed. Final20 remained sealed.

## Main result: this was an entry-quality / commitment failure

Across old, current and six-block development evidence, most losing Candidate-L trades never developed meaningful favorable excursion.

### All Candidate-L trades

| Source | Grid | Trades | Win rate | Median MFE | Median exit move | Losers with MFE < +$2 | Losers that reached +$4 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| historical first80 | 500 ms | 258 | 31.8% | $1.36 | -$1.15 | **85.8%** | 2.8% |
| historical first80 | 1 s | 226 | 32.3% | $1.34 | -$1.09 | **86.2%** | 0.7% |
| current 7d | 500 ms | 333 | 26.7% | $1.14 | -$1.23 | **86.0%** | 3.7% |
| current 7d | 1 s | 270 | 27.0% | $1.03 | -$1.41 | **85.2%** | 4.1% |
| Stage-1 pooled | 500 ms | 123 | 25.2% | $0.87 | -$1.36 | **82.6%** | 8.7% |
| Stage-1 pooled | 1 s | 107 | 24.3% | $1.03 | -$1.55 | **77.8%** | 11.1% |

Only about 19-24% of seven-day trades ever reached +1R MFE, and roughly 6-10% reached +2R. For losing trades specifically, reaching +1R was extremely uncommon.

This means Candidate H-style profit protection cannot rescue the architecture: most bad trades never become profitable enough for the H mechanism to arm.

## Current-seven-day exit attribution

### 500 ms

- `M300_FAILURE`: 278 trades, **-₹411.09**, mean -₹1.48, median MFE ~$1.04;
- `STOP`: 29 trades, **-₹208.88**, mean -₹7.20, median MFE $0.00;
- `FLOW_EXIT`: 17 trades, **+₹49.46**, mean +₹2.91, median MFE ~$6.43;
- `TP`: 9 trades, **+₹163.63**, mean +₹18.18.

### 1 s

- `M300_FAILURE`: 226 trades, **-₹378.07**, mean -₹1.67, median MFE ~$1.01;
- `STOP`: 25 trades, **-₹212.50**, mean -₹8.50, median MFE $0.25;
- `FLOW_EXIT`: 11 trades, **+₹29.87**, mean +₹2.72, median MFE ~$6.43;
- `TP`: 8 trades, **+₹169.92**, mean +₹21.24.

The H-derived flow exit is therefore doing useful work when it gets the chance. The dominant loss pool is the huge set of apparent resumptions that enter but never commit to continuation.

## It is not primarily rapid re-entry churn

Median inter-entry spacing was roughly 500-585 seconds on the seven-day sources. Same-side re-entry within 60 seconds occurred only once at historical 500 ms and once at current 500 ms; none at current 1 s. Therefore a simple cooldown patch would not address the main failure.

## Structural conclusion

The frozen L definition treats an aligned multi-horizon trend plus pullback plus short raw-flow resumption as sufficient evidence of continuation. The trade ledger shows that this is false across multiple regimes: a large number of these signals are only temporary local recoveries inside a move that soon loses its 300-second directional state.

Do **not** respond by optimizing L's `0.50` dominance boundary, spread multiples, qacc boundary, stop or m300 exit against these known outcomes. The next candidate needs a different commitment mechanism.

A defensible next hypothesis is a **price-acceptance state machine**: after a qualifying pullback, do not enter merely because short-horizon flow turns favorable; require price to reclaim and remain beyond the pre-pullback level for a causal clock-time interval before capital is committed. This tests actual market acceptance rather than another fitted score.

Random-window, dual-grid, six-block, cost-stress and continuity/shock testing remain mandatory for the next candidate. Passing known data can only earn new prospective validation.

Final20 remains sealed.
