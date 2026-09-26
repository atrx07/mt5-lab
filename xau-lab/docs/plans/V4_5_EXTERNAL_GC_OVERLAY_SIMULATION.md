# Experiment 46 — same-timeline external GC overlay simulation

Date: 2026-09-26
Status: **frozen before outcome evaluation**

## Objective

Use external COMEX Gold futures proxy information from the **same archived market dates** as the MT5 XAUUSD data, never current external data, and test whether it improves entry admission and Candidate-H profit retention in the full path-dependent simulator.

This is the first strategy simulation allowed to consume the Experiment-45 external bridge.

## External data discipline

External source: Yahoo Finance continuous Gold futures proxy `GC=F`, 5-minute bars.

For every run:
- derive the external request period directly from the MT5 archive timestamps;
- request only the matching historical window plus alignment padding;
- do not use any bar after the MT5 decision time;
- never substitute current/live GC data into an archived MT5 replay.

Clock alignment is fixed from Experiment 45:
`MT5 true UTC = MT5 reported timestamp - 10,797.910989 seconds`.

No lag search is performed in Experiment 46.

At each MT5 decision timestamp, only the **last fully completed GC five-minute bar** is visible.

Frozen external features:
- completed GC 5-minute return;
- completed GC 15-minute return;
- completed GC 30-minute return;
- completed-bar volume;
- 1-hour rolling median volume;
- volume / rolling-median-volume ratio;
- GC-minus-MT5 basis for diagnostics only.

Yahoo bars are an aggregated futures proxy, not trade tape/order-book depth.

## Entry overlay

Apply the external admission guard only to PRIMARY and SECONDARY.

A real entry is skipped when both:
- direction-normalized GC 5-minute return < 0;
- direction-normalized GC 15-minute return < 0.

No threshold search is used; zero is the natural direction boundary.

When a real entry is skipped, create a **capital-free legacy ghost** for that exact engine and let it follow Candidate D's unchanged lifecycle. The ghost occupies the shared slot and anchors cooldown at its legacy exit.

This preserves the downstream Candidate-D entry/cooldown path so admission value can be measured without the Experiment-40 path-mutation problem.

MICRO and BURST admission are unchanged because the 5-minute external proxy is too coarse to justify vetoing their short-horizon impulses.

## Exit overlay

Candidate H remains the exit base.

Candidate H's PRIMARY profit-retention exit is allowed only when:
- its existing +1R MFE and >=1R giveback conditions are armed;
- the existing two consecutive five-second internal raw-flow decay confirmations are present;
- AND both direction-normalized completed GC 5-minute and 15-minute returns are < 0.

If the external state is unavailable, fail open to the Candidate-D legacy exit rather than inventing confirmation.

Real exit still spawns Candidate-H capital-free ghost occupancy until the untouched legacy PRIMARY exit.

## Frozen variants

Run these without tuning:

1. **Candidate D** — current V4.5 leader.
2. **Candidate H** — internal flow-confirmed ghost exit from Experiment 43.
3. **GC-entry** — Candidate D + external PRIMARY/SECONDARY admission guard + entry ghosts.
4. **GC-exit** — Candidate H but requiring external GC confirmation for the H exit.
5. **Candidate I** — GC-entry + GC-exit combined.

Component variants are used for attribution. Candidate I receives the full stress suite.

## Required evaluation

Same known MT5 windows and same-timeline external bars:

- canonical seven-day first80, 500 ms and 1 s;
- recent24h whole and frozen 60/40 split;
- 40 deterministic real contiguous four-hour windows per grid;
- $0.00/$0.05/$0.10/$0.20 per-side slippage stress;
- exact downstream entry-path parity versus Candidate D for every ghost-preserving variant;
- admission-skip ledger;
- external-confirmed exit ledger;
- aligned external feature evidence.

Final20 remains sealed.

## Decision discipline

Known data may reject Candidate I but cannot promote it.

Do not alter the fixed clock correction, external return horizons, zero direction boundary, H exit thresholds, or engine scope based on these results.

If the same-timeline overlay is coherent, the next step is genuinely richer GC trades/depth data on the same dates and then a fresh non-overlapping snapshot.
