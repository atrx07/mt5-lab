# 46 — V4.5 same-timeline external GC overlay simulation

Date: 2026-09-26
Status: **frozen; full simulation pending**

Experiment 46 integrates the Experiment-45 GC bridge into the path-dependent MT5 simulator while guaranteeing that every external observation comes from the **same historical timeline** as the replayed MT5 tick data.

It compares Candidate D, Candidate H, an external-entry-only branch, an external-exit-only branch, and combined Candidate I.

Frozen plan:
`docs/plans/V4_5_EXTERNAL_GC_OVERLAY_SIMULATION.md`

Implementation:
`research/v4_5_external_gc_overlay_simulation.py`

Evidence:
`results/simulations/2026-09-26-v4_5-external-gc-overlay-simulation/`

No current external market data may be mixed into historical replays. Final20 remains sealed.
