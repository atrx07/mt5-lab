# V4.1 proposal — evaluated

Status: **partially promoted / superseded by empirical V4.1 lock**

This document preserves the pre-simulation proposal. Experiment 08 tested these ideas instead of silently assuming they would work.

The optimization result diverged from the original plan:

- chronological development / validation separation was used;
- MFE/MAE and execution-cost behavior informed the search;
- risk-based sizing was promoted;
- short-horizon ER/chop filters improved V4 but did not create a positive edge;
- the winning candidate moved to much slower 1800 s / 300 s / 60 s structure rather than keeping V4's short-horizon state machine;
- spread/slippage and sampling stress tests were performed;
- the final holdout remains unopened.

The locked implementation is [V4.1](../algorithms/v4_1.md), and the promotion evidence is [experiment 08](../experiments/2026-09-23/08-v4-1-optimization.md).

---

## Original proposal summary

The original proposal called for regime-aware thresholds, chop detection, normalized pullbacks, risk-based sizing, MFE/MAE instrumentation, chronological development/validation/holdout separation, walk-forward testing, and execution stress tests.

Simulation showed that some of those ideas were useful, but the bigger improvement came from changing the strategy horizon itself.

### Promoted

- risk-based sizing;
- chronological split discipline;
- execution stress testing;
- instrumentation-driven iteration.

### Not promoted into locked V4.1

- short-horizon ER/chop gate;
- short-horizon normalized pullback architecture.

Those remain available as future research ideas rather than silently disappearing from history.

## JEV remains later

JEV should only be added after the deterministic baseline survives broker-tick testing, and it should not own emergency exits.
