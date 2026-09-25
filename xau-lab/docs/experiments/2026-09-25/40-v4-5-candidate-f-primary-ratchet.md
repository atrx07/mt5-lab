# 40 — V4.5 Candidate F PRIMARY profit-ratchet full replay

Date: 2026-09-25

Status: **completed full shared-slot diagnostic; Candidate F rejected; Candidate D remains leader**

## Objective

Move the strongest Experiment-39 mechanism into the real Candidate-D simulator without changing entries.

The frozen plan was committed before outcome evaluation:

`docs/plans/V4_5_CANDIDATE_F_PRIMARY_RATCHET.md`

## Frozen Candidate F

Candidate F = Candidate D + PRIMARY-only profit ratchet:

- activate at +1R MFE = +$4;
- retain 50% of live MFE;
- evaluate every 5 wall-clock seconds;
- no SECONDARY/MICRO/BURST ratchet;
- all entry/risk/lifecycle rules otherwise unchanged.

Candidate D parity reproduced exactly before interpretation. Final20 remained sealed.

## Canonical first80

| Grid | Candidate D | Candidate F | F - D | Trades D → F | Max segment DD D → F |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **+₹1,430.31** | +₹562.07 | **-₹868.24** | 163 → 175 | ₹218.94 → ₹118.58 |
| 1 s | **+₹385.25** | +₹283.97 | **-₹101.28** | 156 → 165 | ₹172.14 → ₹159.45 |

The ratchet reduced drawdown and slightly increased raw win rate, but early exits freed the shared slot and changed downstream cooldown/occupancy history. The result was **more trades** and a large path-dependent loss of historical compounded edge.

The damage was concentrated in the earliest high-opportunity segment:

- 500 ms segment 0: +₹696.84 → **+₹128.48**, with trades 98 → 110;
- 1 s segment 0: +₹169.92 → **+₹66.75**, with trades 98 → 106.

Later untouched segments remained identical.

## Recent24h

Whole-window terminal-equity P&L:

| Grid | Candidate D | Candidate F | F - D |
| --- | ---: | ---: | ---: |
| 500 ms | -₹223.27 | -₹221.58 | +₹1.70 |
| 1 s | **-₹135.91** | -₹180.41 | **-₹44.50** |

Recent split behavior was inconsistent:

- 500 ms seed: -₹92.48 → -₹106.75;
- 500 ms evaluation: -₹149.92 → -₹135.00;
- 1 s seed: -₹86.54 → -₹110.55;
- 1 s evaluation: -₹52.31 → -₹82.80.

Candidate F did not turn the hostile window profitable.

## Random real four-hour windows

The random-window diagnostic was the one genuinely encouraging piece:

500 ms:

- mean: -₹6.26 → **-₹3.18**;
- median: -₹23.59 → **-₹18.81**;
- positive-window fraction: 30.0% → **35.0%**;
- Candidate F beat D in **87.5%** of windows.

1 s:

- mean: -₹8.25 → **-₹4.54**;
- median: -₹27.86 → **-₹26.92**;
- positive-window fraction: 27.5% → **35.0%**;
- Candidate F beat D in **82.5%** of windows.

So the ratchet itself is not useless. The problem is that the **full strategy reacts to the earlier exit** by opening a different future path.

## Cost stress

Candidate F remained below Candidate D on historical first80 at every tested adverse-slippage level.

At +$0.20 per side:

- historical 500 ms: D +₹335.09 vs F +₹158.84;
- historical 1 s: D +₹35.88 vs F **-₹61.84**.

Recent 500 ms remained slightly less negative than D under stress, but recent 1 s remained worse at every level.

## Mechanism

Experiment 39's independent-lane PRIMARY-only ratchet decomposition was positive in all four historical/recent grid comparisons.

Experiment 40 shows why that did not survive full integration:

> **the exit itself can save profit, but changing the moment the shared slot becomes free changes the entire later strategy path.**

At 500 ms canonical segment 0, the ratchet created 12 additional completed trades. At 1 s segment 0 it created 8 additional trades.

This is the same class of path dependence identified in Experiment 31, now triggered by an exit-management improvement rather than router arbitration.

## Decision

**Reject Candidate F unchanged. Candidate D remains the V4.5 leader.**

Do not tune the +1R trigger, 50% retention fraction or 5-second cadence against these known outcomes.

The next structural test should preserve Candidate D's slot/cooldown path while allowing the real account to bank the ratchet exit. A viable architecture is a **shadow/ghost occupancy**:

1. real PRIMARY exits when the frozen ratchet triggers;
2. a virtual copy of the original PRIMARY continues under the untouched Candidate-D legacy lifecycle;
3. the shared slot remains unavailable exactly as if Candidate D were still holding;
4. when the virtual legacy trade would exit, release the slot and start PRIMARY cooldown from that legacy exit time.

That directly tests whether profit retention can be separated from downstream path mutation.

Final20 remains sealed.

## Evidence

`results/simulations/2026-09-25-v4_5-candidate-f-primary-ratchet/`

Key files:

- `candidate_f_config.json`
- `summary.json`
- `canonical_segment_comparison.csv`
- `recent_split_comparison.csv`
- `random_real_windows.csv`
- `cost_stress.csv`
- `primary_ratchet_events.csv`
