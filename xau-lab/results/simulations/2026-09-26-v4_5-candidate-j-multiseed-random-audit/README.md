# Experiment 47R — Candidate J multi-seed random-window audit

Status: **pre-run evidence bundle; frozen before rerun**

Three additional deterministic random batches are run without changing Candidate J:
- batch A
- batch B
- batch C

Each batch uses 40 real contiguous four-hour windows per grid with the same 50/50 historical-first80 vs recent24h source balance as Experiment 47.

Expected evidence:
- window_results.csv
- batch_summary.csv
- baseline_shadow_parity.csv
- summary.json

This is known-data robustness evidence only. Experiment 48 remains the fresh prospective gate. Final20 remains sealed.
