# 42 — V4.5 signal-fingerprint entry quality

Date: 2026-09-26
Status: **completed diagnostic; entry expert not promoted**

This experiment gives the entry decision layer the information missing from Experiments 38-39:

- complete frozen state-v2 and microstate-v1 context;
- exact engine-specific rule-margin fingerprints;
- one expert per engine;
- an exit-independent excursion-quality target instead of final realized P&L.

Frozen plan:
`docs/plans/V4_5_SIGNAL_FINGERPRINT_ENTRY_QUALITY.md`

Implementation:
`research/v4_5_signal_fingerprint_entry_quality.py`

Evidence:
`results/simulations/2026-09-26-v4_5-signal-fingerprint-entry-quality/`

Known data are diagnostic only. Candidate D remains the V4.5 leader and final20 stays sealed.


## Result

The full signal encyclopedia changed the learning problem in the intended way, but it still did not provide portable trade-level precision.

Historical walk-forward episode policy:

- 500 ms: onset fixed-size P&L +₹274.29 → selected-policy audit +₹638.78; selected mean excursion edge improved from 0.525R to 0.615R.
- 1 s: onset -₹75.80 → selected-policy audit -₹297.97; selected mean excursion edge moved only from 0.485R to 0.509R.

Recent transfer:

- 500 ms: -₹4,188.37 → -₹4,039.99;
- 1 s: -₹1,928.48 → -₹1,824.68.

The recent improvement came from only light filtering. The experts retained roughly 96% of recent episodes and, critically, recent PRIMARY predictions were positive on about 97% of checkpoints even though actual mean PRIMARY excursion edge was negative on both grids.

Checkpoint rank correlations remained weak. Historical PRIMARY Spearman was only 0.017 at 500 ms and 0.040 at 1 s. Recent PRIMARY Spearman was 0.131 / 0.066. BURST transfer was negative.

## Interpretation

The model now knows **what kind of signal fired and by how much**, so the failure is no longer simply missing engine identity or missing rule provenance.

What remains missing is a reliable mapping from that causal state to the future path of an individual trade. The known state is better at describing setup structure and broad regime hostility than at forecasting which particular episode will become a clean winner.

The 500 ms historical uplift is useful mechanism evidence but does not transfer strongly enough to justify a full shared-slot entry controller.

## Decision

**Do not promote the Experiment-42 entry expert.**

Retain the signal fingerprints as permanent diagnostics / future features. Do not tune the model or decision threshold against these same known windows. Candidate D remains the V4.5 leader. Final20 remains sealed.
