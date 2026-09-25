# Experiment 27 — `xau-state-v2` freeze

Status: **feature representation frozen; no router or candidate promoted**.

This bundle records the richer causal state layer that will be used by the next stronghold-aware router experiment.

The formulas were frozen structurally. Historical and recent outcome profiles were inspected only after the feature list was fixed; no threshold was selected from those outcomes.

Headline diagnostics:

- historical Candidate D entries: 319;
- recent Candidate D entries: 71;
- matched historical 500 ms/1 s pairs: 119;
- matched recent pairs: 27;
- median cross-grid feature Spearman: 0.916 historical, 0.940 recent;
- all short-horizon features have 100% coverage;
- 300 s-derived features have 96.87% / 95.77% historical/recent coverage due to causal warm-up.

The next candidate-changing test requires a new non-overlapping raw XAU snapshot.
