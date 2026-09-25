# 33 — V4.5 independent engine opportunity atlas

Date: 2026-09-25

Status: **completed diagnostic; no strategy change**

## Question

Do PRIMARY, SECONDARY, MICRO and BURST actually contain **different profitable opportunities** when market conditions change, or are we asking a router to choose among four versions of the same failing edge?

Experiment 32 showed that router fall-through almost never fired. The shared-slot path therefore hid whether the engine family itself had enough independent cross-regime edge.

## Method

Each engine was replayed in its own independent one-position shadow lane with:

- its original signal, cooldown and lifecycle;
- executable bid/ask fills;
- fixed ₹500 sizing;
- no shared cross-engine slot;
- no cross-engine cooldown interference;
- no compounding between shadow trades.

Censored range-end positions were excluded from realized summaries.

Every opportunity was enriched with frozen `xau-state-v2`.

The final20 holdout remained sealed.

## Main result

The historical first80 shadow lanes were positive for every engine on both grids, but the recent 24-hour window showed a broad regime failure.

### Historical fixed-size P&L

| Engine | 500 ms | 1 s |
| --- | ---: | ---: |
| PRIMARY | +₹297.86 | +₹36.26 |
| SECONDARY | +₹42.30 | +₹46.69 |
| MICRO | +₹222.27 | +₹183.24 |
| BURST | +₹74.21 | +₹48.23 |

### Recent fixed-size P&L

| Engine | 500 ms | 1 s |
| --- | ---: | ---: |
| PRIMARY | **-₹255.11** | **-₹148.99** |
| SECONDARY | **-₹45.49** | **+₹18.82** |
| MICRO | **-₹34.46** | **-₹45.60** |
| BURST | **-₹17.44** | **-₹15.94** |

At 500 ms **all four engines independently lost** on the recent window.

At 1 s only SECONDARY stayed positive, on just nine trades. PRIMARY, MICRO and BURST all flipped from positive historical P&L to negative recent P&L.

The recent four-hour block results tell the same story:

- BURST: 0% positive blocks on both grids;
- MICRO: 0% positive blocks on both grids;
- PRIMARY: 16.7% positive blocks on both grids;
- SECONDARY: 25% positive at 500 ms and 50% positive at 1 s.

## Engines are also rarely simultaneous

Independent entry overlap was sparse:

- historical 500 ms: 8 multi-engine events out of 226 entry events (**3.54%**);
- historical 1 s: 8 / 219 (**3.65%**);
- recent 500 ms: 1 / 45 (**2.22%**);
- recent 1 s: 1 / 42 (**2.38%**).

That explains why Router-v3 fall-through was nearly irrelevant. Most opportunities are not simultaneous choices at all.

## Interpretation

The current problem is **not just routing**.

The existing engine family is mostly momentum/trend-family exposure. When the hostile recent regime arrives, there often is no alternate profitable engine for a router to choose.

This means another hand-built priority rule or score threshold is unlikely to solve the cross-window problem by itself.

The next valid direction is one of:

1. prove that frozen state-v2 contains transferable predictive information and use a pre-registered adaptive admission layer; or
2. add a genuinely complementary opportunity generator, such as a structurally different reversal/mean-reversion family, then validate it independently.

To avoid designing yet another fixed rule around the same two windows, the two follow-ups were separated and frozen independently: Experiment 34 tested a structural SNAPBACK complement, while Experiment 35 ran the **no-search chronological state-v2 walk-forward predictability test**.

## Decision

No router or threshold is selected from this atlas.

Candidate D remains the V4.5 research leader.

Experiment 35 trains only on past shadow opportunities and predicts later opportunities using a fixed regularized model and natural zero expected-P&L threshold. Experiment 34's SNAPBACK branch is a separate pre-registered complementary-engine test. Neither known-data result can promote a strategy; promotion still requires a future frozen candidate and genuinely new unseen data.

## Evidence

- `research/v4_5_independent_opportunity_atlas.py`
- `results/simulations/2026-09-25-v4_5-independent-opportunity-atlas/shadow_opportunities.csv`
- `.../engine_summary.csv`
- `.../engine_block_robustness.csv`
- `.../simultaneous_opportunities.csv`
- `.../cross_window_engine_summary.csv`
- `.../state_outcome_profiles.csv`
- `.../summary.json`
