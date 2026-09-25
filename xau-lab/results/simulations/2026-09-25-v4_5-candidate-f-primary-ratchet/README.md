# Experiment 40 — Candidate F PRIMARY profit ratchet

Status: **pre-run evidence bundle; Candidate F frozen before outcome evaluation**

Candidate F keeps Candidate D's entry logic, engine priority, shared-slot behavior, sizing, cooldowns, spread controls and non-PRIMARY lifecycles unchanged.

The only strategy change is a PRIMARY-only profit ratchet:

- activates after +1R MFE = +$4 favorable XAU move;
- retains 50% of live MFE;
- evaluates every 5 wall-clock seconds;
- a ratchet exit uses the normal PRIMARY cooldown.

Known data are diagnostic only. Final20 remains sealed.

Expected evidence:

- `candidate_f_config.json`
- `summary.json`
- `canonical_segment_comparison.csv`
- `recent_split_comparison.csv`
- `random_real_windows.csv`
- `cost_stress.csv`
- `primary_ratchet_events.csv`

See the frozen Experiment-40 plan for the exact pre-run contract.
