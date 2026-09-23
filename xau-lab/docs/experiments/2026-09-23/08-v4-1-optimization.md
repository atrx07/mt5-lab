# 08 — iterative optimization and V4.1 lock

## Goal

Iteratively modify the algorithm on development data, compare candidates, use validation to reject false improvements, and lock the first change that improves profitability **and** risk behavior enough to justify a new version.

The final 20% holdout was not evaluated.

## Dataset

Same broker export and chronological split as experiment 07:

- source: `xau_ticks_7d.csv`;
- SHA-256: `007e7ab10cc16519b544003dbe81521f46cf868bf267780932638d1e8cec86e5`;
- development: first 60%;
- validation: next 20%;
- holdout: final 20%, still unopened by this optimization stage;
- replay cadence: 500 ms unless stress-testing another cadence.

## Iteration path

### 1. V4 baseline

Current short-horizon pullback/resumption:

- development P&L: **-₹490.04**;
- PF: 0.358;
- 591 trades.

Rejected.

### 2. Chop / efficiency filtering

A strong 30-second efficiency filter materially reduced damage but did not create an edge.

Example ER >= 0.40:

- development P&L: **-₹186.57**;
- PF: 0.525;
- 99 trades.

Improved, still rejected.

### 3. 5-minute swing experiments

Moving the strategy to slower momentum increased PF substantially.

Representative run:

- development P&L: **-₹298.18**;
- PF: 0.851;
- 277 trades.

Still rejected.

### 4. 30-minute trend / 5-minute context family

A new family was tested:

- 1800 s directional trend;
- 300 s trend confirmation;
- real 60 s counter-move in the prior 300 s;
- 60 s resumption entry.

This was the first family to generate multiple positive development configurations.

A strong early candidate produced:

- development: **+₹178.61**, PF 1.093;
- validation: **-₹100.30**, PF 0.505.

Rejected. This was important: a profitable development result alone was not enough.

### 5. First development + validation positive candidate

Changing the trend-reversal exit to a 300-second zero-cross produced:

- development: **+₹156.40**, PF 1.128;
- validation: **+₹23.57**, PF 1.151.

This crossed the first promotion threshold.

### 6. Reward / spread neighborhood search

A wider +$21 take-profit and $0.30 spread ceiling improved the opportunity capture:

Before risk normalization:

- development: **+₹290.31**, PF 1.210;
- validation: **+₹90.81**, PF 1.532.

However, development drawdown was roughly ₹335 on a ₹500 starting balance. Profitable, but too aggressive for promotion.

### 7. Risk-based sizing

The strategy was changed from 100x-first sizing to **3% planned account risk per trade** using a $4 XAU stop distance.

This became the locked V4.1 candidate.

## Locked result

| Metric | Development | Validation |
| --- | ---: | ---: |
| Start | ₹500.00 | ₹500.00 |
| Final | **₹627.52** | **₹538.79** |
| Net | **+₹127.52** | **+₹38.79** |
| Return | +25.50% | +7.76% |
| Trades | 69 | 8 |
| Win rate | 46.38% | 25.00% |
| Profit factor | **1.323** | **1.811** |
| Avg trade | +₹1.85 | +₹4.85 |
| Max drawdown | ₹87.29 | ₹40.18 |
| Max DD / peak equity | 12.96% | 6.95% |

The low validation win rate is not a typo: one large +$21 target winner and asymmetric payoff carried the result. This is one reason the sample still needs the locked holdout and more data.

## Development day-reset diagnostic

Each development date also started independently at ₹500:

| Date | Net | PF | Trades |
| --- | ---: | ---: | ---: |
| Sep 16 | +₹65.17 | 1.495 | 15 |
| Sep 17 | +₹2.40 | 1.017 | 27 |
| Sep 18 | +₹34.91 | 1.440 | 24 |
| Sep 21 partial | +₹16.45 | 2.720 | 3 |

All development dates were positive under the selected configuration.

## Stress tests

| Scenario | Development | Validation |
| --- | ---: | ---: |
| Base | +₹127.52 | +₹38.79 |
| Spread +10% | +₹73.34 | +₹36.95 |
| Spread +25% | +₹2.60 | **-₹21.15** |
| $0.02 adverse slippage / side | +₹118.14 | +₹37.50 |
| $0.05 adverse slippage / side | +₹100.12 | +₹35.59 |
| $0.10 adverse slippage / side | +₹72.46 | +₹32.89 |

At 1-second sampling:

- development: +₹82.53, PF 1.193;
- validation: +₹34.57, PF 1.695.

## Decision

**Lock V4.1.**

No more parameter tuning against development or validation for this exact version.

The next evaluation step should treat the algorithm and parameters as frozen. Any changes after that create another version.

The holdout remains reserved for that frozen evaluation.

## Evidence

Machine-readable files:

[`results/simulations/2026-09-23-v4_1-optimization/`](../../../results/simulations/2026-09-23-v4_1-optimization/)
