# 32 — V4.5 path-aware priority-preserving Router v3

Date: 2026-09-25

Status: **completed known-data diagnostic; not promoted**

## Frozen architecture

Router v3 was committed before measuring its P&L:

1. preserve Candidate D priority **PRIMARY → SECONDARY → MICRO → BURST**;
2. keep the Experiment-28 stronghold score unchanged;
3. keep the score floor at **0.0**;
4. use the score only as a veto, never a global ranker;
5. latch a vetoed engine for its already-existing Candidate-D cooldown horizon;
6. fall through to lower-priority candidates on the same tick;
7. HOLD only when none qualifies;
8. keep entry, exit, sizing, spread, leverage and lifecycle logic unchanged.

No score, threshold, weight or cooldown search was performed.

The final20 holdout remained sealed.

## Canonical first80

| Grid | Candidate D | Router v2 | Router v3 | V3 trades | V3 wins |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | +₹1,430.31 | +₹851.27 | **+₹1,162.46** | 159 | 79 |
| 1 s | +₹385.25 | +₹297.67 | **+₹214.06** | 155 | 70 |

Router v3 recovered a large fraction of the Router-v2 500 ms damage, but it still lost **₹267.85** versus Candidate D. At 1 s it was **₹171.20 worse** than Candidate D and also below Router v2.

Trade retention remained high: 97.55% at 500 ms and 99.36% at 1 s. Win rate was essentially unchanged from Candidate D at 500 ms and slightly lower at 1 s.

## What actually changed

The most important implementation result is that **fallback never fired**.

Across the canonical first80:

- 500 ms: 4 rejected candidates, all PRIMARY; 4 HOLDs; **0 fallback entries**;
- 1 s: 5 rejected candidates, all PRIMARY; 5 HOLDs; **0 fallback entries**.

So in the observed known data, priority-preserving fall-through did not create a new lower-priority opportunity at any veto point. Router v3 effectively became a sparse PRIMARY gate with rejection latching.

This is useful architecture evidence: simultaneous candidate competition is too rare to be the main route to robustness.

## Recent 24-hour window

| Grid | Candidate D | Router v2 | Router v3 |
| --- | ---: | ---: | ---: |
| 500 ms | -₹223.27 | -₹210.63 | **-₹210.63** |
| 1 s | -₹135.91 | -₹144.22 | **-₹128.87** |

Router v3 improved versus Candidate D by ₹12.64 at 500 ms and ₹7.04 at 1 s, but **both grids remained negative**.

At 500 ms Router v3 was exactly the same whole-window result as Router v2. At 1 s it removed Router-v2's extra follow-on damage and modestly improved on Candidate D, but not enough to establish a positive edge.

## Known real-window stress

Forty deterministic contiguous four-hour windows per grid were sampled from the already-known canonical/recent data. These are stress diagnostics, not independent validation.

500 ms:

- Candidate D mean terminal-equity P&L: -₹6.26;
- Router v3: -₹6.53;
- Router v3 beat D in 15% of windows;
- trade retention: 98.08%.

1 s:

- Candidate D mean: -₹8.25;
- Router v3: -₹12.70;
- Router v3 beat D in only 2.5% of windows;
- trade retention: 99.52%.

## Decision

**Router v3 is not promoted. Candidate D remains the V4.5 leader.**

The experiment rejects a tempting but weak direction: repeatedly modifying a router around the same fixed data.

The current engine family gives the router very few simultaneous alternatives, and the frozen state score is not selective enough to distinguish the sparse profitable/losing PRIMARY veto cases. More router mechanics will not create a missing edge.

The next experiment therefore changes the research question rather than tuning the gate:

> What profitable opportunities do PRIMARY, SECONDARY, MICRO and BURST produce **independently of the shared slot and each other's cooldown path**, and does the current engine family contain enough genuinely different edge to survive changing regimes?

Experiment 33 will build a fixed-size independent shadow-lane opportunity atlas. It changes no trading strategy and selects no rule. If all four engines lose together in the hostile window even when observed independently, the next productive step is a genuinely complementary opportunity generator or adaptive meta-labeler—not another router threshold.

## Evidence

- `research/v4_5_router_v3_priority_latched.py`
- `results/simulations/2026-09-25-v4_5-router-v3-priority-latched/summary.json`
- `results/simulations/2026-09-25-v4_5-router-v3-priority-latched/random_real_windows.csv`
