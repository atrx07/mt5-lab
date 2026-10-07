# Provenance

Records where lab artifacts came from, so future sessions can distinguish
original evidence from reconstruction.

- **2026-10-08 — Lab bootstrap.** `mcx-gold-lab/` scaffolded by the agent as
  the lawful small-capital sibling of `xau-lab`, per user instruction
  ("make a directory in the mt5-lab beside the xau-lab directory").
  Conventions mirrored from `xau-lab/agents.md` + `xau-lab/structure.md`
  (read 2026-10-08).
- **Experiment 00 (cost model):** built and run 2026-10-08. Cost schedule from
  Zerodha's published MCX charges (verified via web 2026-10-08); contract specs
  from MCX circulars (Gold Petal; Gold Guinea tick marked VERIFY against live
  feed). Output: `results/cost_model/exp0.json`.
- **Harness + baselines:** written 2026-10-08; 3/3 smoke tests pass on
  synthetic GBM ticks (`tools/synth_ticks.py`). Synthetic P&L is harness
  evidence only, never strategy evidence.
- **No real MCX tick data exists in this lab yet.** No strategy conclusion has
  been drawn. The venue-selection rationale (`docs/plans/01-venue-selection.md`)
  cites web-verified 2026-10-08 sources; re-verify before money moves.
