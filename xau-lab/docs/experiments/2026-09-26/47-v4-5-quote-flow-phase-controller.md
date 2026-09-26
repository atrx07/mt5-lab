# 47 — V4.5 MT5-native quote-flow phase controller

Date: 2026-09-26

Status: **completed known-data diagnostic; Candidate J frozen for fresh MT5-only validation, not promoted**

Experiment 47 is the first post-external-branch strategy experiment under the MT5-only live-practicality gate.

It adds a causal quote-flow phase state machine using only raw MT5 bid/ask ticks, exact tick-change flags, and the already-frozen Candidate-H microstate confirmation.

Entry tests PRIMARY/SECONDARY TAKE / WAIT / SKIP behavior. Exit tests a tamed Candidate-H controller that protects healthy pullbacks and only banks profit after persistent quote-flow decay/reversal.

Frozen plan:
`docs/plans/V4_5_QUOTE_FLOW_PHASE_CONTROLLER.md`

Implementation:
`research/v4_5_quote_flow_phase_controller.py`

Evidence:
`results/simulations/2026-09-26-v4_5-quote-flow-phase-controller/`

Candidate D remains leader. Candidate H remains the strongest retained exit branch until this diagnostic completes. Final20 remains sealed.


## Result

The full MT5-only diagnostic completed with exact Candidate-D baseline-shadow opportunity parity on canonical first80 and recent24h for all modified branches.

The new controller used only broker-native bid/ask ticks, exact BID/ASK update flags and the already-frozen Candidate-H microstate decay confirmation. No external feed was used.

### Canonical first80

| Grid | Candidate D | Candidate H | Quote-entry | Quote-exit | Candidate J |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **+₹1,430.31** | +₹1,287.09 | +₹1,261.04 | +₹1,256.26 | +₹1,048.86 |
| 1 s | **+₹385.25** | +₹360.79 | +₹307.41 | +₹370.30 | +₹273.18 |

Candidate J reduced max segment drawdown materially:

- 500 ms: D ₹218.94 → J **₹139.87**;
- 1 s: D ₹172.14 → J **₹109.26**.

The cost is substantial historical upside loss, especially from the entry controller.

Canonical entry behavior:

- 500 ms: 163 baseline opportunities → 145 real trades; 4 delayed; 18 skipped.
- 1 s: 156 baseline opportunities → 136 real trades; 2 delayed; 20 skipped.

### Recent24h

| Grid | Candidate D | Candidate H | Quote-entry | Quote-exit | Candidate J |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | -₹223.27 | -₹208.47 | **-₹172.28** | -₹212.29 | **-₹164.54** |
| 1 s | -₹135.91 | -₹128.63 | **-₹71.00** | -₹129.41 | **-₹71.00** |

Recent drawdown also improved sharply:

- 500 ms: D ₹230.22 → J **₹172.96**;
- 1 s: D ₹143.89 → J **₹92.58**.

The entry controller, not the exit controller, produced most of the recent improvement.

### Real contiguous random-window stress

Forty deterministic four-hour windows were evaluated per grid using the same historical/recent sources as prior experiments.

| Grid | D mean | H mean | J mean | D positive | H positive | J positive |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 500 ms | -₹6.26 | -₹3.36 | **+₹3.75** | 30.0% | **35.0%** | 32.5% |
| 1 s | -₹8.25 | -₹7.21 | **-₹2.82** | 27.5% | 30.0% | 30.0% |

Candidate J beat Candidate D in:

- **100%** of the 500 ms random windows;
- **87.5%** of the 1 s random windows.

It beat Candidate H in 80.0% / 62.5% of random windows, with additional ties.

This is the first MT5-only branch in the V4.5 line to move the 500 ms random-window **mean above zero** while also materially improving the 1 s random mean.

The result is not independent validation: these random windows are contiguous resamples from already-known datasets and many recent-window samples overlap heavily.

### Entry phase behavior

Across recorded entry-controller actions:

- 408 immediate HEALTHY_TREND takes;
- 20 immediate IGNITION takes;
- 30 direct REVERSAL skips;
- 20 direct DECAY skips;
- 66 HEALTHY_PULLBACK waits;
- 2 UNCERTAIN waits;
- 14 delayed HEALTHY_TREND takes after waiting;
- 28 waits canceled by DECAY/REVERSAL;
- 26 waits expired without a healthy confirmation.

The two-second delayed-entry mechanism therefore activated only rarely; most of the behavior came from immediate healthy-state acceptance versus bad/persistent-pullback rejection.

### Exit behavior

The phase-tamed exit did **not** improve Candidate H overall.

- 500 ms canonical: Quote-exit +₹1,256.26 versus H +₹1,287.09.
- 1 s canonical: Quote-exit +₹370.30 versus H +₹360.79.
- Recent: Quote-exit remained close to D/H and contributed little to Candidate J's large recent improvement.

The controller did explicitly protect 11 canonical healthy pullbacks on each grid, but its remaining phase exits still did not dominate Candidate H consistently.

### Cost stress

Candidate J retains positive historical P&L at 500 ms through the full tested +$0.20 per-side adverse-slippage stress, but at 1 s the +$0.20 stress turns J slightly negative (-₹28.42).

Recent Candidate-J losses remain materially smaller than D/H at every tested slippage level, but still negative.

## Interpretation

Experiment 47 produced a real structural step on the **entry side**:

1. exact MT5 quote-event state can remove a meaningful subset of hostile-regime trades;
2. the improvement transfers directionally across both grids;
3. the 500 ms random-window mean crossed above zero;
4. the 1 s random-window mean moved much closer to zero;
5. all of this remained MT5-native and live-replayable.

However, known-data canonical edge fell too much to promote Candidate J, and the random-window evidence is not independent.

The exit refinement is weaker. Candidate H remains the preferred exit branch on current evidence; the quote-phase exit is not promoted separately.

## Decision

**Do not promote Candidate J from known data. Freeze it unchanged for fresh MT5-only prospective validation.**

No phase rules, wait horizon, engine scope or thresholds may be adjusted from these results.

Candidate D remains the formal V4.5 leader until prospective evidence exists.

Candidate H remains the strongest retained exit-management branch.

Candidate J is the strongest **prospective entry-management challenger** so far because it is the first branch to produce positive 500 ms random-window mean while materially improving 1 s random-window mean and hostile recent performance.

Final20 remains sealed.
