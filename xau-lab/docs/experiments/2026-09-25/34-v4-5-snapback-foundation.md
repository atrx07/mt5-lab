# 34 — V4.5 SNAPBACK complementary-engine foundation

Date: 2026-09-25

Status: **completed known-data diagnostic; rejected unchanged; no tuning**

## Why a new engine instead of another router

Experiment 33 showed that on the recent 500 ms window every existing engine is independently negative and simultaneous multi-engine opportunities occur only about 2–4% of the time.

Experiment 34 therefore tested a structurally different countertrend/failed-continuation lane whose rules were frozen before P&L evaluation.

## Frozen rules

SNAPBACK kept the same established 60/120 s background-move gates as the current short-horizon family, but required:

- ER60 < 0.12, the direct complement of MICRO's >=0.12 efficiency split;
- current 10 s momentum to reverse against the background move;
- 10 s flow imbalance to agree with that reversal;
- the existing range, activity and spread-quality gates.

All numeric thresholds were inherited from Candidate D / MICRO rather than selected from SNAPBACK outcomes.

The lifecycle was frozen at:

- $4 emergency stop;
- $12 take profit;
- 120 s max hold;
- stagnation after 60 s when peak < $0.80;
- trail after +$5.50 with $2 giveback;
- no BURST m30 zero-cross failure because this lane is countertrend by design.

## Result

SNAPBACK failed immediately on the known historical research pool:

| Grid | Trades | Wins | P&L | PF | +$0.20/side stress |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | 17 | 3 | **-₹153.04** | 0.236 | **-₹178.54** |
| 1 s | 7 | 2 | **-₹44.78** | 0.374 | **-₹55.28** |

Only seven entries matched across grids; their P&L signs agreed 100%, so this was not merely a sampling-grid artifact.

The frozen signal produced **zero realized recent-24h opportunities** on either grid. That absence is itself evidence: this particular structural complement does not address the hostile regime that motivated the experiment.

## Decision

**Reject SNAPBACK unchanged. Do not tune its constants to either known window.**

There is no basis for threshold loosening such as changing ER60, reversal momentum, range or spread gates simply to manufacture recent trades. That would turn a pre-registered complementary idea into another fixed-window fit.

Experiment 35 therefore proceeds independently with the already-frozen no-search state-v2 predictability test. If that also fails, stop trying to rescue the current state/engine family with local parameter edits and require either genuinely new information/features or genuinely new unseen data before another candidate can be promoted.

Final20 remains sealed.

## Evidence

- `research/v4_5_snapback_foundation.py`
- `results/simulations/2026-09-25-v4_5-snapback-foundation/summary.json`
- `.../summary_by_window.csv`
- `.../four_hour_blocks.csv`
- `.../block_robustness.csv`
- `.../cross_grid_matches.csv`
- `.../snapback_opportunities.csv`
