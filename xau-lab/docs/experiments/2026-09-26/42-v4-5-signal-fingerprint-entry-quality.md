# 42 — V4.5 signal-fingerprint entry quality

Date: 2026-09-26
Status: **frozen; diagnostic pending; no promotion**

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
