# 45 — V4.5 external GC futures correlation bridge

Date: 2026-09-26
Status: **frozen; external-data evaluation pending**

This experiment tests whether public 5-minute COMEX Gold futures proxy data (`GC=F`) is sufficiently aligned with the existing MT5 XAUUSD quote history to justify a later richer external-tape integration.

It does not use P&L labels, does not change strategy logic, and keeps final20 sealed.

Frozen plan:
`docs/plans/V4_5_EXTERNAL_GC_CORRELATION.md`

Implementation:
`research/v4_5_external_gc_correlation.py`

Evidence:
`results/simulations/2026-09-26-v4_5-external-gc-correlation/`
