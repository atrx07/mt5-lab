# 29 — V4.5 Router v2 gate-proxy and variable-regime preflight

Date: 2026-09-25

Status: **completed diagnostic proxy; not a full raw-tick Router-v2 replay; no promotion**

## Objective

Compare the frozen Experiment-28 stronghold score with current winner Candidate D on:

1. the canonical seven-day first-80% trade ledger;
2. the separate Experiment-22 recent 24-hour trade ledger; and
3. randomized variable-regime mixtures of those two observed environments.

This experiment does **not** tune Router v2.

## Critical scope limitation

The active code-execution runtime was unavailable for a full raw-tick Router-v2 replay during this run. The durable Experiment-27 state-v2 entry ledgers were therefore used for a deterministic trade-level proxy.

The proxy evaluates the exact Router-v2 score on each **realized Candidate D entry** and converts score < 0 into HOLD.

It cannot discover or execute a lower-priority engine that would have been simultaneously eligible after a higher-priority entry was rejected. Therefore it is conservative with respect to Router v2's intended fall-through behavior and **must not be treated as final Router-v2 performance**.

## Seven-day benchmark

Candidate D ledger parity is exact.

| Grid | Candidate D | Gate proxy | Trade retention | Candidate WR | Proxy WR |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **+₹1,430.31** / 163 trades | **+₹1,181.58** / 159 trades | 97.55% | 49.69% | 49.69% |
| 1 s | **+₹385.25** / 156 trades | **+₹219.73** / 151 trades | 96.79% | 45.51% | 45.70% |

The proxy rejected only PRIMARY entries. Those rejected historical entries had net positive realized P&L:

- 500 ms: 4 trades, 2 wins, **+₹163.99** raw trade P&L;
- 1 s: 5 trades, 2 wins, **+₹124.99** raw trade P&L.

Two of the rejected historical PRIMARY winners were large, approximately +₹95 and +₹97 at 500 ms; the 1 s set included approximately +₹107 and +₹61 winners. This explains why a near-neutral score floor can damage the historical benchmark despite high retention.

## Recent 24-hour ledger

The recent ledger retains Experiment 22's realized-only split accounting and boundary caveat.

| Grid / split | Candidate D | Gate proxy | Retention |
| --- | ---: | ---: | ---: |
| 500 ms seed | -₹92.48 / 19 trades / 3 wins | -₹92.48 / 19 / 3 | 100% |
| 500 ms evaluation | -₹149.92 / 19 / 2 | **-₹135.52 / 18 / 2** | 94.74% |
| 1 s seed | -₹86.54 / 16 / 3 | -₹86.54 / 16 / 3 | 100% |
| 1 s evaluation | -₹52.31 / 17 / 5 | **-₹37.90 / 16 / 5** | 94.12% |

Across both recent splits the proxy retained 37/38 = **97.37%** of 500 ms trades and 32/33 = **96.97%** of 1 s trades. It removed the same recent PRIMARY failure on both grids, worth roughly -₹14.4, so the combined realized attribution improved by only about ₹14.4 per grid and remained strongly negative.

## Random variable-regime simulation

Method:

- deterministic seeded bootstrap;
- 10,000 scenarios per grid;
- 40 trade opportunities per scenario;
- each scenario draws its recent-regime share uniformly from 0% to 100%;
- each opportunity is sampled with replacement from the corresponding historical or recent state-v2 ledger;
- trade return is inferred from realized P&L and entry ounces under the existing 3% / $4 risk sizing relationship, then compounded from ₹500;
- Router proxy skips entries with score < 0;
- no synthetic price path or invented P&L is generated.

| Grid | Candidate D median P&L | Proxy median P&L | Candidate profitable scenarios | Proxy profitable scenarios | Proxy median retention |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **-₹68.67** | -₹70.60 | **35.26%** | 34.04% | 97.5% |
| 1 s | **-₹58.96** | -₹58.97 | **33.06%** | 30.91% | 97.5% |

The proxy slightly improved the 5th-percentile loss tail:

- 500 ms: -₹237.50 → **-₹230.33**;
- 1 s: -₹198.20 → **-₹189.65**.

But it also reduced the 95th-percentile upside:

- 500 ms: +₹301.18 → **+₹269.62**;
- 1 s: +₹212.46 → **+₹177.44**.

When scenarios were stratified by hostile recent-regime share, the proxy hurt low-hostility mixtures and helped the most hostile mixtures modestly, but the high-hostility medians remained negative.

## Decision

Candidate D remains the current winning candidate.

The frozen Router-v2 score is not promoted, rejected, or tuned from this proxy. The diagnostic suggests its simple neutral floor trims both downside and upside and currently misses some historically valuable PRIMARY entries.

The intended fall-through architecture could recover some rejected opportunities, so the next valid comparison is still a **full raw-tick replay** on a genuinely new non-overlapping snapshot.

Do not modify score weights, floor or component list based on Experiment 29.

## Evidence

- `research/v4_5_router_v2_preflight.py`
- `results/simulations/2026-09-25-v4_5-router-v2-preflight/known_window_proxy.json`
- `results/simulations/2026-09-25-v4_5-router-v2-preflight/monte_carlo_regime_mix.csv`
- `results/simulations/2026-09-25-v4_5-router-v2-preflight/historical_state_v2_trades.csv`
- `results/simulations/2026-09-25-v4_5-router-v2-preflight/recent_state_v2_trades.csv`
