# 33 — V4.5 independent engine opportunity atlas

Date: 2026-09-25

Status: **completed diagnostic; current engine family is not cross-window robust**

## Question

Do PRIMARY, SECONDARY, MICRO and BURST contain genuinely different profitable opportunities when conditions change, or are we asking a router to choose among mostly correlated trend-following edges?

Experiment 33 removes shared-slot competition, cross-engine cooldown cascades and compounding. Each engine runs in its own one-position shadow lane with fixed ₹500 sizing, its own original signal/cooldown/lifecycle, and executable bid/ask prices.

No strategy rule or router was selected.

Final20 remained sealed.

## Historical seven-day opportunity streams

All four engines are positive independently on the known historical development window.

500 ms:

| Engine | Trades | Wins | Win rate | Fixed-size P&L | PF |
| --- | ---: | ---: | ---: | ---: | ---: |
| PRIMARY | 84 | 35 | 41.7% | +₹297.86 | 1.47 |
| SECONDARY | 45 | 18 | 40.0% | +₹42.30 | 1.10 |
| MICRO | 77 | 35 | 45.5% | +₹222.27 | 1.71 |
| BURST | 28 | 15 | 53.6% | +₹74.21 | 3.17 |

1 s:

| Engine | Trades | Wins | Win rate | Fixed-size P&L | PF |
| --- | ---: | ---: | ---: | ---: | ---: |
| PRIMARY | 79 | 28 | 35.4% | +₹36.26 | 1.06 |
| SECONDARY | 62 | 24 | 38.7% | +₹46.69 | 1.08 |
| MICRO | 62 | 30 | 48.4% | +₹183.24 | 1.71 |
| BURST | 24 | 12 | 50.0% | +₹48.23 | 2.32 |

This explains why Candidate D can perform strongly on the historical benchmark: the opportunity family genuinely contains edge there.

## Recent 24-hour opportunity streams

The picture changes sharply when the engines are isolated from router/path effects.

500 ms:

| Engine | Trades | Wins | Win rate | Fixed-size P&L | PF |
| --- | ---: | ---: | ---: | ---: | ---: |
| PRIMARY | 27 | 4 | 14.8% | **-₹255.11** | 0.16 |
| SECONDARY | 6 | 1 | 16.7% | **-₹45.49** | 0.41 |
| MICRO | 8 | 1 | 12.5% | **-₹34.46** | 0.25 |
| BURST | 5 | 0 | 0% | **-₹17.44** | 0.00 |

At 500 ms **every existing engine is independently negative**.

At 1 s, PRIMARY (-₹148.99), MICRO (-₹45.60) and BURST (-₹15.94) are negative. SECONDARY is the lone positive stream at **+₹18.82 / 9 trades / 4 wins / PF 1.24**, but that sign does not survive to 500 ms.

## Chronological robustness

The recent four-hour block picture confirms this is not just a shared-slot artifact:

- BURST: 0% positive recent blocks at both grids;
- MICRO: 0% positive recent blocks at both grids;
- PRIMARY: 1/6 positive blocks at each grid;
- SECONDARY: 1/4 positive blocks at 500 ms and 2/4 at 1 s.

Historical MICRO and BURST were much more consistent: at 500 ms, 70.6% and 62.5% of their observed four-hour blocks were positive respectively.

## Simultaneous opportunities are rare

Exact simultaneous independent entry events:

- historical 500 ms: 8 / 226 = **3.54%**;
- historical 1 s: 8 / 219 = **3.65%**;
- recent 500 ms: 1 / 45 = **2.22%**;
- recent 1 s: 1 / 42 = **2.38%**.

This independently explains why Router-v3 fallback had nothing useful to do. Most of the time there is no second engine waiting at the same decision point.

## Decision

**The main variable-environment problem is upstream of the router.**

Three of four engines flip from positive historical P&L to negative recent P&L on both grids. SECONDARY is positive only on recent 1 s and negative recent 500 ms. The existing family does not contain enough cross-window complementarity for a router to manufacture robust positive performance.

Therefore we stop modifying the routing score around these two known datasets.

The next experiment adds a structurally different opportunity generator: a short-horizon **SNAPBACK** lane aimed at failed continuation / countertrend mean reversion. Its rules are defined from existing Candidate-D invariants and natural complements before any P&L is measured. No threshold search is allowed.

If SNAPBACK also fails to transfer, the next route should be a pre-registered walk-forward adaptive meta-labeler rather than hand-tuned state gates.

## Evidence

- `research/v4_5_independent_opportunity_atlas.py`
- `results/simulations/2026-09-25-v4_5-independent-opportunity-atlas/summary.json`
- `.../shadow_opportunities.csv`
- `.../engine_summary.csv`
- `.../four_hour_blocks.csv`
- `.../engine_block_robustness.csv`
- `.../simultaneous_opportunities.csv`
- `.../cross_window_engine_summary.csv`
- `.../state_outcome_profiles.csv`
