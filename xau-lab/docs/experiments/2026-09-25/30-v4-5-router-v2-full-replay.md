# 30 — V4.5 full raw-tick Router v2 replay

Date: 2026-09-25

Status: **completed known-data diagnostic; Router v2 score not promoted; Candidate D remains leader**

## Objective

Run the actual Experiment-28 Router v2 end to end instead of the Experiment-29 trade-ledger proxy.

The replay starts from raw ticks, builds the canonical sampled features, evaluates every simultaneously eligible engine while the shared slot is flat, computes `xau-state-v2` at the arbitration point, applies the frozen engine-specific stronghold score, performs fall-through/HOLD arbitration, and executes Candidate D's unchanged lifecycle/risk logic.

No score component, weight, scale, score floor, engine signal or lifecycle parameter was tuned from this result.

## Execution and parity

The local CAAS runtime was unavailable, so the user explicitly authorized a GitHub worker for this run. The canonical seven-day archive was restored and hash-verified, and the recent 24-hour archive verified both its gzip and decompressed SHA-256 values.

The worker exposed one pandas-3 datetime-resolution compatibility issue in the state overlay. The completed-bucket epsilon was changed from 1 ns to 1 us; because all resample bucket labels are whole-second aligned, this preserves which completed bucket is selected and does not change the state definition.

Candidate D parity then passed exactly:

| Grid | Candidate D P&L | Trades | Wins | Win rate |
| --- | ---: | ---: | ---: | ---: |
| 500 ms | **+₹1,430.31** | 163 | 81 | 49.69% |
| 1 s | **+₹385.25** | 156 | 71 | 45.51% |

The final 20% holdout remained sealed.

## Canonical seven-day first80

| Metric | Candidate D 500 ms | Router v2 500 ms | Candidate D 1 s | Router v2 1 s |
| --- | ---: | ---: | ---: | ---: |
| Compounded P&L | **+₹1,430.31** | +₹851.27 | **+₹385.25** | +₹297.67 |
| Trades | 163 | 163 | 156 | 156 |
| Wins | **81** | 78 | **71** | 70 |
| Win rate | **49.69%** | 47.85% | **45.51%** | 44.87% |
| Worst segment DD | ₹218.94 | **₹163.44** | **₹172.14** | ₹180.81 |

Router v2 retained 100% of the canonical trade count but lost **₹579.05** versus Candidate D at 500 ms and **₹87.59** at 1 s.

The damage was concentrated in the historical 0-40% seed segment:

- 500 ms: Candidate D **+₹696.84** versus Router v2 **+₹342.88**;
- 1 s: Candidate D **+₹169.92** versus Router v2 **+₹107.89**.

This is important: the failure is not simply excessive HOLD suppression. The router preserved the aggregate trade count while changing arbitration/timing enough to replace valuable opportunities with lower-quality ones. The 500 ms drawdown improvement does not compensate for the large loss of expectancy and win quality.

## Whole recent 24-hour raw window

Whole-window reporting uses terminal equity so a boundary-open position cannot silently disappear. In the completed run both strategies were flat at the end.

| Metric | Candidate D 500 ms | Router v2 500 ms | Candidate D 1 s | Router v2 1 s |
| --- | ---: | ---: | ---: | ---: |
| P&L | -₹223.27 | **-₹210.63** | **-₹135.91** | -₹144.22 |
| Trades | 39 | 38 | 34 | 36 |
| Wins | 5 | 5 | 8 | 8 |
| Win rate | 12.82% | **13.16%** | **23.53%** | 22.22% |
| Profit factor | 0.225 | **0.237** | **0.423** | 0.400 |
| Max DD | ₹230.22 | **₹217.90** | **₹143.89** | ₹152.02 |

At 500 ms the router improved P&L by **₹12.64**, retained 97.44% of trades and modestly improved win rate/drawdown, but remained deeply negative.

At 1 s it was **₹8.31 worse**, added two net trades, reduced win rate and worsened drawdown.

The historical 60/40 split explains the 1 s mismatch: the later evaluation portion improved from -₹52.31 to -₹43.66, but the seed portion worsened from -₹86.54 to -₹103.64.

## Random real-window stress

The final random stress uses deterministic seed `20260925`, 40 windows per grid and four-hour contiguous windows sampled **inside individual sampled continuity sessions** from the canonical first80 and recent 24-hour datasets. No synthetic price path or invented P&L is generated.

An earlier random-window attempt crossed invalid/gapped ranges and was discarded. The CSV in the evidence directory is the corrected run.

| Metric | D 500 ms | Router 500 ms | D 1 s | Router 1 s |
| --- | ---: | ---: | ---: | ---: |
| Median P&L/window | **-₹23.59** | -₹23.59 | **-₹27.86** | -₹46.29 |
| Mean P&L/window | **-₹6.26** | -₹8.89 | **-₹8.25** | -₹15.23 |
| Positive windows | 30.0% | 30.0% | 27.5% | **35.0%** |
| Aggregate win rate | **37.65%** | 37.08% | **35.71%** | 33.12% |
| Total trades | 417 | 418 | 420 | 462 |
| Router-better windows | — | **2.5%** | — | **22.5%** |

The higher 1 s positive-window fraction does not translate into better expectancy: median/mean P&L, aggregate win rate and the positive tail are worse.

The recent 24-hour source contains limited long continuous sessions, so many sampled recent windows overlap heavily. Therefore these 40 windows are a **stress diagnostic, not 40 statistically independent market days**.

## Decision

**Candidate D remains the current V4.5 research leader. Router v2's current stronghold score is not promoted.**

The full fall-through architecture did not rescue the frozen structural score:

- canonical P&L and win rate were materially worse on both grids;
- the recent 500 ms loss improved only modestly and stayed negative;
- the recent 1 s whole-window result worsened;
- corrected random real-window stress showed worse mean expectancy on both grids.

Do **not** tune the Experiment-28 score floor/weights against these known outcomes.

The next useful research step is a decision-level arbitration audit: log every point where Router v2 differs from Candidate D and distinguish engine substitution, HOLD-then-later-entry, changed cooldown history and same-engine timing shifts. Counterfactual lifecycle outcomes should identify which arbitration mechanics destroy high-value Candidate D trades before a new scoring design is proposed.

## Evidence

- `research/v4_5_router_v2_full_eval.py`
- `results/simulations/2026-09-25-v4_5-router-v2-full-replay/full_replay_summary.json`
- `results/simulations/2026-09-25-v4_5-router-v2-full-replay/random_real_windows.csv`
