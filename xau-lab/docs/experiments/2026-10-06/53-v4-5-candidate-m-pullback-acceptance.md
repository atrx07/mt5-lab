# 53 — V4.5 Candidate M pullback price acceptance

Date: 2026-10-06

Status: **COMPLETE — frozen Candidate M rejected unchanged on development-survival screen.**

Frozen plan:  
`docs/plans/V4_5_CANDIDATE_M_PULLBACK_ACCEPTANCE.md`

Implementation:  
`research/v4_5_candidate_m_pullback_acceptance.py`

Evidence:  
`results/simulations/2026-10-06-v4_5-candidate-m-pullback-acceptance/`

## Hypothesis

Experiment 52 showed that Candidate L's dominant failure was false continuation commitment: most losers never developed even +0.5R favorable excursion, so exit-management tuning could not rescue them.

Candidate M therefore changed the entry mechanism rather than retuning L. A qualifying pullback only armed a setup. Price then had to recover the causal pre-pullback level (`anchor = mid - m10`), remain beyond `anchor +/- frozen arm spread` for two clock seconds, and still pass qacc/raw-flow/execution checks before capital could enter.

The complete M rules and survival gates were committed before M P&L was evaluated. Final20 remained sealed.

## Comparator integrity

D/H historical, current-seven-day and six-block pooled references reproduced the frozen values, so comparator parity passed.

## Candidate-M results

### Historical first80

| Grid | Compounded P&L | Trades | Wins | Win rate | Max segment DD |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **-₹0.87** | 64 | 28 | 43.75% | ₹67.54 |
| 1 s | **+₹59.60** | 57 | 30 | 52.63% | ₹69.88 |

Price acceptance radically improved Candidate L's historical result (-₹153/-₹163) and reduced trade count, but 500 ms still failed the predeclared positive-P&L gate.

### Current seven-day regime

| Grid | P&L | Trades | Wins | Win rate | PF | Max DD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **-₹78.33** | 63 | 22 | 34.92% | 0.762 | ₹99.10 |
| 1 s | **-₹67.12** | 59 | 21 | 35.59% | 0.765 | ₹102.34 |

This was substantially less negative than D and H on both grids, but remained below zero and therefore failed the frozen current-regime gate.

For context only:

- current 500 ms H = -₹180.93, M = -₹78.33;
- current 1 s H = -₹194.96, M = -₹67.12.

This relative improvement is diagnostic, not promotion evidence.

## Six Experiment-48 blocks

Pooled P&L:

| Grid | D | H | M | Positive M blocks |
| --- | ---: | ---: | ---: | ---: |
| 500 ms | -₹165.32 | -₹97.91 | **-₹95.12** | 1 / 6 |
| 1 s | -₹130.27 | -₹74.46 | **-₹70.47** | 1 / 6 |

M slightly reduced the pooled H loss on both grids, but five of six blocks were still non-positive. The hostile-condition evidence therefore remains weak.

## Random-situation screen

The same deterministic 80 real contiguous four-hour windows per grid used for Candidate L were replayed, alternating historical/current continuity ranges.

| Grid | Mean | Median | Positive fraction | p05 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **-₹8.19** | **-₹3.86** | 45.0% | -₹45.35 | +₹32.10 |
| 1 s | **-₹4.76** | **-₹6.07** | 31.25% | -₹40.59 | +₹34.76 |

This is the decisive robustness rejection. Candidate M was much less fragile than Candidate L, but it still failed both the positive-mean and non-negative-median random-window gates on both grids, and the 1 s positive-window fraction also failed the >=45% gate.

## Execution-cost stress

### Current seven-day M

| Extra slippage / side | 500 ms | 1 s |
| --- | ---: | ---: |
| $0.00 | -₹78.33 | -₹67.12 |
| $0.05 | -₹92.51 | -₹95.21 |
| $0.10 | **-₹115.28** | **-₹112.26** |
| $0.20 | -₹156.28 | -₹151.34 |

Historical M at +$0.10/side was -₹42.52 at 500 ms and +₹15.46 at 1 s. Thus the frozen stress-survival rule also failed.

## State-machine behavior

Candidate M was intentionally selective:

- historical 500 ms: 744 arms -> 64 entries;
- current 500 ms: 871 arms -> 63 entries;
- historical 1 s: 561 arms -> 57 entries;
- current 1 s: 687 arms -> 59 entries.

Most arms were cancelled because the normalized macro-trend state disappeared before acceptance, not because the 60-second timer expired. That is consistent with the intended fail-safe behavior and helps explain the large reduction in false entries relative to Candidate L.

However, accepted setups still did not produce positive expectation across current/random conditions.

## Frozen development-survival decision

Candidate M failed the overall screen. The main failures were:

- 500 ms historical P&L not positive;
- current seven-day P&L negative on both grids;
- random-window means negative on both grids;
- random-window medians negative on both grids;
- 1 s random positive fraction below 45%;
- +$0.10/side current P&L negative on both grids;
- +$0.10/side historical 500 ms negative.

Minimum trade-count and comparator-parity gates passed.

**Reject Candidate M unchanged. Do not tune its numeric boundaries against these known outcomes.**

## Research implication

The price-acceptance state machine is a meaningful structural improvement over Candidate L: it cut exposure dramatically, reduced drawdown, and brought historical 500 ms close to flat while making historical 1 s positive. But acceptance beyond a 10-second pre-pullback anchor is still insufficient to establish transferable edge.

The next hypothesis, if pursued, should preserve the useful concept of explicit price acceptance while adding a different causal source of *persistence/quality* rather than merely lengthening the acceptance timer or changing its numeric buffer until these known datasets turn green.

Any next candidate keeps the same random-window, dual-grid, six-block, cost-stress, continuity/shock discipline. Passing known development evidence can only earn a genuinely fresh prospective test.

Final20 remains sealed.
