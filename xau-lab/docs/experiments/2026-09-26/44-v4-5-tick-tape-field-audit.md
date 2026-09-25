# 44 — V4.5 MT5 tick-tape field audit

Date: 2026-09-26
Status: **frozen; representation audit pending**

Experiments 42-43 exposed a remaining information question: the current causal feature sets use bid/ask quote paths but ignore the archived MT5 `last`, `volume`, `volume_real`, and `flags` fields.

Experiment 44 audits those fields without P&L labels or strategy changes.

Frozen plan:
`docs/plans/V4_5_TICK_TAPE_FIELD_AUDIT.md`

Implementation:
`research/v4_5_tick_tape_field_audit.py`

Evidence:
`results/simulations/2026-09-26-v4_5-tick-tape-field-audit/`

Final20 remains sealed.
