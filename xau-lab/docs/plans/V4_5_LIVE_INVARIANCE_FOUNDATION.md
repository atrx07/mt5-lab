# V4.5 live-invariance foundation for the next candidate

Date: 2026-10-06

Status: **frozen diagnostic plan; no strategy change and no P&L-based selection**

## Naming

Do **not** call the next V4.5 candidate `Candidate K`: that label was already used by the locked V4.4 MICRO management configuration. The next V4.5 strategy candidate will therefore be **Candidate L**.

## Purpose

Experiments 33-49 show that the current D/H/J family can look strong on the original development week and still fail on later live-market data. Before defining Candidate L, measure which market/execution quantities are stable when expressed causally and relatively, and which old fixed-dollar assumptions drift across environments.

This experiment is deliberately **outcome-blind**. It may inspect market data and frozen strategy entry timestamps, but it must not load trade P&L, win/loss labels, MFE/MAE, or future path labels to define/select a feature or threshold.

## Data roles

Use only already-consumed development/diagnostic data:

1. canonical historical dataset, first 80% research rows only; final20 stays sealed;
2. current-regime 2026-09-29 -> 2026-10-06 seven-day dataset;
3. the six Experiment-48 Stage-1 blocks, now explicitly outcome-known development data.

No result from this diagnostic can promote a candidate.

## Questions

For 500 ms and 1 s execution grids, measure:

- absolute spread versus spread as a fraction of local 60 s range;
- spread as a fraction of the current $4 emergency-stop distance;
- 60 s and 300 s realized range distributions;
- normalized directional displacement: |m60|/range60 and |m300|/range300;
- ER60 and quote-rate acceleration (`qacc`);
- sign agreement across 60 s / 300 s / 1800 s horizons;
- pressure imposed by the inherited fixed spread caps ($0.30 globally and $0.28 BURST);
- pressure imposed by the existing relative MICRO/BURST spread-to-range gates;
- distribution of the same quantities at frozen Candidate-D entry timestamps, split by engine;
- four-hour-window variation of the above state variables.

## Interpretation rule

The objective is **not** to find the percentile or threshold that would have made past P&L green. The output may justify structural choices only when those choices have a market/execution interpretation that can be computed live from past data.

Candidate L should prefer:

- scale-free or locally normalized state over fixed-dollar market-regime assumptions;
- structural price geometry over fitted outcome thresholds;
- explicit execution-cost and continuity guards;
- H-style signal-confirmed profit protection where applicable;
- fixed account-risk budgeting even if structural stop distance changes;
- no external feed and no future-looking information.

## Random-situation discipline

Candidate L must eventually be tested on:

- both 500 ms and 1 s grids;
- chronological old/new regimes;
- the six outcome-known Stage-1 blocks;
- deterministic real contiguous random four-hour windows drawn from multiple development sources;
- adverse execution-cost stress;
- session reopen / continuity gaps and spread-shock periods.

Known-data tests are rejection/development evidence only. Once Candidate L is frozen, promotion requires a new non-overlapping prospective capture that was not used to design it.

Final20 remains sealed.
