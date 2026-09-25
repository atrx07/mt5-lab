# Experiment 42 plan — signal-fingerprint entry quality

Date: 2026-09-26
Status: frozen before outcome evaluation

Goal: improve entry/engine selection without using final trade P&L as the training target.

Frozen changes:
- Reuse Experiment 39 cooldown-free signal episodes and 2-second checkpoints.
- Train one expert per engine (PRIMARY, SECONDARY, MICRO, BURST).
- Target entry quality with `excursion_edge_r = (MFE_USD - abs(MAE_USD)) / 4`; final counterfactual P&L is audit-only.
- Add rule-margin fingerprints that describe why the specific engine fired, plus the full frozen 20-feature state-v2 and 23-feature microstate-v1 causal state. This is the complete signal-context encyclopedia; no outcome-selected subset is used.
- Use the first checkpoint with predicted excursion edge > 0; otherwise skip the episode.
- No feature search, threshold search, model search, or final20 access.

Model: HistGradientBoostingRegressor per engine, fixed:
- learning_rate 0.05
- max_iter 140
- max_leaf_nodes 5
- min_samples_leaf 12
- l2_regularization 1.0
- random_state 20260926

Validation:
- expanding historical folds 0->1, 0-1->2, 0-2->3, 0-3->4;
- fit all historical first80, then predict recent24h unchanged;
- both grids stay in the same chronological fold.

Evidence:
- research/v4_5_signal_fingerprint_entry_quality.py
- results/simulations/2026-09-26-v4_5-signal-fingerprint-entry-quality/
