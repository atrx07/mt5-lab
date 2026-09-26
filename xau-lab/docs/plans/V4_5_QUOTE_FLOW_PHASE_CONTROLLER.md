# Experiment 47 — MT5-native quote-flow phase controller

Date: 2026-09-26

Status: **frozen before outcome evaluation**

## Objective

Build the next entry/exit controller using only causal information available from the same MT5/broker feed used for execution.

No external GC/CME/LMAX/Yahoo input is allowed.

The controller must distinguish five quote-flow phases around a legacy Candidate-D opportunity:

- IGNITION
- HEALTHY_TREND
- HEALTHY_PULLBACK
- DECAY
- REVERSAL

The goal is to improve *when* PRIMARY/SECONDARY entries receive capital and to stop Candidate-H profit protection from confusing a healthy pullback with terminal decay.

## Native quote-flow state

Source fields:

- raw MT5 `bid`, `ask`, `flags`, `timestamp_utc`;
- frozen microstate-v1 features for Candidate-H confirmation;
- ordinary Candidate-D sampled features already used by the strategy.

No `last`, trade volume or aggressor-side fields are used because Experiment 44 established that the broker does not supply them.

At each decision timestamp, use completed raw events from trailing 2 s and 10 s windows.

For each window derive:

- direction-normalized net mid movement;
- aligned move magnitude and adverse move magnitude;
- aligned/adverse nonzero move counts;
- path efficiency = abs(net movement) / gross absolute movement;
- trailing consecutive adverse nonzero quote moves;
- seconds since the last aligned quote move;
- seconds since the last adverse quote move;
- BID-only / ASK-only / both-side update fractions from the exact MT5 flags;
- exact BID-vs-ASK update imbalance;
- spread change over the window.

These are causal quote events available live and replayable from the archived MT5 ticks.

## Frozen phase rules

No P&L-derived thresholds are permitted.

### REVERSAL

- direction-normalized 2 s mid movement < 0;
- direction-normalized 10 s mid movement < 0;
- adverse move magnitude > aligned move magnitude in both 2 s and 10 s.

### DECAY

- direction-normalized 2 s mid movement < 0;
- adverse 2 s move magnitude > aligned 2 s move magnitude;
- trailing adverse nonzero-move run >= 2;
- the most recent nonzero quote move is adverse.

### HEALTHY_PULLBACK

- direction-normalized 10 s mid movement > 0;
- aligned 10 s move magnitude >= adverse 10 s move magnitude;
- direction-normalized 2 s mid movement < 0.

### HEALTHY_TREND

- direction-normalized 10 s mid movement > 0;
- aligned 10 s move magnitude >= adverse 10 s move magnitude;
- direction-normalized 2 s mid movement >= 0.

### IGNITION

- direction-normalized 2 s mid movement > 0;
- aligned 2 s move magnitude > adverse 2 s move magnitude;
- not already classified HEALTHY_TREND.

Everything else is UNCERTAIN.

## Entry controller

Only PRIMARY and SECONDARY admission changes.

At the exact Candidate-D opportunity:

- IGNITION / HEALTHY_TREND -> TAKE immediately;
- DECAY / REVERSAL -> SKIP;
- HEALTHY_PULLBACK / UNCERTAIN -> WAIT for at most 2 seconds.

The two-second wait is fixed because it is the short quote-flow observation horizon, not because of outcome search.

During WAIT:

- the original engine/side setup must still be mechanically eligible;
- TAKE at the first sampled quote classified IGNITION or HEALTHY_TREND;
- cancel immediately on DECAY or REVERSAL;
- otherwise SKIP when 2 seconds expire.

MICRO and BURST admission remain unchanged.

## Path-preserving baseline shadow

Candidate-D opportunity timing is simulated independently as a capital-free baseline shadow.

The shadow owns shared-slot occupancy and cooldown timing exactly as Candidate D would.

Modified real entries/exits never create new downstream opportunities. If a modified real trade is still open when a later Candidate-D opportunity occurs, that opportunity is skipped for real capital but remains in the baseline shadow path.

This generalizes the validated Candidate-G/H ghost principle and prevents path mutation from masquerading as entry/exit edge.

## Exit controller

Candidate H is the base.

Only PRIMARY receives the new quote-phase protection.

The extra profit-retention exit remains armed only after:

- live MFE >= +1R ($4);
- giveback from live MFE >= 1R ($4).

At each existing 5-second Candidate-H check, a bad confirmation requires BOTH:

1. Candidate-H frozen internal decay condition:
   - direction-normalized raw 2 s mid movement < 0;
   - direction-normalized raw event imbalance < 0;
2. quote-flow phase is DECAY or REVERSAL.

Two consecutive bad checks are required.

HEALTHY_PULLBACK, HEALTHY_TREND or IGNITION reset the confirmation count and explicitly protect the runner.

SECONDARY, MICRO and BURST exits remain Candidate D.

## Frozen variants

1. Candidate D.
2. Candidate H.
3. Quote-entry: phase-aware PRIMARY/SECONDARY entry, legacy exits.
4. Quote-exit: Candidate-D entries, phase-tamed Candidate-H PRIMARY exit.
5. Candidate J: Quote-entry + Quote-exit.

No threshold, phase-rule, horizon or engine-scope search is allowed.

## Required evaluation

- canonical first80, 500 ms and 1 s;
- recent24h whole and frozen 60/40 split;
- same 40 deterministic real contiguous four-hour windows per grid;
- $0.00/$0.05/$0.10/$0.20 per-side slippage stress;
- baseline opportunity-path parity;
- entry phase/action ledger;
- delayed-entry ledger;
- exit phase ledger;
- phase counts by engine/window;
- MFE/giveback capture for extra exits.

Known data may reject Candidate J but cannot promote it.

Final20 remains sealed.

## Acceptance direction

This experiment is promising only if the combined branch improves variable-window behavior on **both** grids while retaining materially more Candidate-D canonical edge than prior failed management candidates.

A merely prettier negative number is not a lock.

## Evidence contract

Experiment:
`docs/experiments/2026-09-26/47-v4-5-quote-flow-phase-controller.md`

Implementation:
`research/v4_5_quote_flow_phase_controller.py`

Evidence:
`results/simulations/2026-09-26-v4_5-quote-flow-phase-controller/`
