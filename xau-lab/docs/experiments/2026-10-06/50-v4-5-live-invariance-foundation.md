# 50 — V4.5 live-invariance foundation for Candidate L

Date: 2026-10-06

Status: **COMPLETE — outcome-blind diagnostic; no strategy change and no threshold selected.**

Frozen plan:  
`docs/plans/V4_5_LIVE_INVARIANCE_FOUNDATION.md`

Implementation:  
`research/v4_5_live_invariance_foundation.py`

Evidence:  
`results/simulations/2026-10-06-v4_5-live-invariance-foundation/`

## Naming correction

The next V4.5 strategy candidate will be **Candidate L**, not Candidate K. `Candidate K` was already the name of the locked V4.4 MICRO management configuration in Experiment 13 / `docs/algorithms/v4_4.md`.

## Discipline

This experiment loaded **no trade P&L labels, win/loss labels, MFE/MAE or future-path targets**. It changed no strategy rule and performed no threshold search.

Sources were limited to already-consumed development/diagnostic evidence:

- canonical historical dataset, first 80% research rows only;
- current-regime 2026-09-29 -> 2026-10-06 seven-day dataset;
- six Experiment-48 Stage-1 blocks, now explicitly outcome-known development data.

The historical final20 remained sealed.

## Main finding: price-shape normalization transfers far better than the fixed execution cap

The central market geometry was surprisingly stable between the old and current seven-day regimes once expressed relative to local range.

### 500 ms medians

| Metric | Historical first80 | Current 7d |
| --- | ---: | ---: |
| sampled spread | $0.32 | $0.36 |
| 60 s range | $1.85 | $1.63 |
| spread / 60 s range | 0.170 | 0.224 |
| `abs(m10)/range60` | 0.196 | 0.196 |
| `abs(m30)/range60` | 0.362 | 0.350 |
| `abs(m60)/range60` | 0.528 | 0.510 |
| `abs(m300)/range300` | 0.501 | 0.480 |
| ER60 | 0.105 | 0.096 |
| qacc | 1.024 | 1.024 |

### 1 s medians

| Metric | Historical first80 | Current 7d |
| --- | ---: | ---: |
| sampled spread | $0.33 | $0.36 |
| 60 s range | $1.745 | $1.520 |
| spread / 60 s range | 0.181 | 0.241 |
| `abs(m10)/range60` | 0.203 | 0.203 |
| `abs(m30)/range60` | 0.372 | 0.362 |
| `abs(m60)/range60` | 0.540 | 0.523 |
| `abs(m300)/range300` | 0.507 | 0.486 |
| ER60 | 0.131 | 0.123 |
| qacc | 1.036 | 1.037 |

The normalized displacement ratios moved only a few percent while execution cost relative to available movement worsened materially.

## The inherited $0.30 spread cap is brittle

Fraction of sampled rows passing the global `$0.30` cap:

| Grid | Historical first80 | Current 7d |
| --- | ---: | ---: |
| 500 ms | 38.97% | **17.26%** |
| 1 s | 38.68% | **16.67%** |

Across the six Stage-1 blocks the 500 ms pass fraction ranged from about **14.6% to 52.1%**; the 1 s range was similarly wide. A small shift in ordinary spread therefore causes a very large discontinuous change in admission availability.

This is not mainly an extreme-tail story. Raw median spread moved from about `$0.33` to `$0.36`, while raw p99 was approximately `$0.69` historically versus `$0.68` current and p99.9 was `$1.32` versus `$1.14`. The spectacular session-boundary spread spikes are real but rare; the more important live-transfer issue is the ordinary central spread regime moving across a hard binary cap.

## But simply raising the cap is not justified

The current regime also had lower typical 60 s movement, so spread consumed more of the local price opportunity:

- 500 ms median spread/range60: **0.170 -> 0.224**;
- 1 s median spread/range60: **0.181 -> 0.241**.

Therefore replacing `$0.30` with a larger fixed dollar cap would ignore the actual economics. Candidate L should judge execution cost relative to causal structural movement / structural stop distance, not merely permit wider spread.

For reference only, a simple execution-budget diagnostic `spread <= 10% of the existing $4 stop` passed 74.6% -> 65.6% of 500 ms sampled rows and 73.5% -> 63.7% at 1 s. Stage-1 blocks ranged roughly 74-95% depending on block. This diagnostic was **not selected as a Candidate-L gate**; it only illustrates that a risk-relative quantity is less discontinuous than the legacy `$0.30` cap.

## Horizon/state observations

Full 60/300/1800 sign agreement across all sampled rows moved only modestly:

- 500 ms: 41.36% historical -> 39.58% current;
- 1 s: 40.72% -> 39.32%.

The six Stage-1 blocks covered materially different states (roughly 35-41% horizon agreement, broad spread/range-gate variation), which is useful development diversity rather than a reason to fit each block independently.

## Candidate-L design implications

The next candidate should be structurally new rather than another D/J threshold overlay:

1. use normalized multi-horizon price geometry and causal raw-flow confirmation;
2. make `HOLD / no trade` an explicit safe state when trend structure or execution quality is poor;
3. price spread against the actual structural opportunity/risk distance instead of a fixed market-regime dollar cap;
4. use structural stop geometry with fixed account-risk sizing so dollar volatility changes do not silently change risk quality;
5. retain the useful Candidate-H idea of signal-confirmed profit protection, generalized in R units where possible;
6. include continuity/reopen and spread-shock guards that fail safe without synthesizing missing ticks;
7. avoid fitted P&L scores and avoid selecting a percentile from these known outcomes.

## Random-situation requirement

Candidate L is not allowed to pass merely because aggregate old/new seven-day P&L is positive. Development evaluation must include both grids, chronological regimes, all six Stage-1 blocks, deterministic real contiguous four-hour windows from multiple development sources, cost stress, continuity gaps and spread-shock intervals.

Those are rejection/development tests only. If Candidate L survives and is frozen, promotion still requires a new non-overlapping prospective capture.

Final20 remains sealed.
