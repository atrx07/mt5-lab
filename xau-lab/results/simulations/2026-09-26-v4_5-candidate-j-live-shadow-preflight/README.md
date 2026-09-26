# Experiment 48P — Candidate J live-shadow harness preflight

Status: **PASS**

The live-shadow runner is read-only and sends no broker orders.

Runner:
`scripts/live_shadow_candidate_j.py`

Preflight source:
`data/raw/xau_ticks_recent_24h_2026-09-24.csv.gz`

Expected evidence:
- `preflight.json`

The offline preflight must reproduce the already-recorded Experiment-47 recent24h D/H/J whole-window P&L, trade counts and win counts on both 500 ms and 1 s.

This is tooling parity only. It is not new strategy evidence and does not claim the market is live.

Experiment 48 remains the fresh prospective gate. Final20 remains sealed.


## Result

Archived wiring parity: **PASS**

- 500 ms D/H/J P&L, trades and wins: exact match to Experiment 47.
- 1 s D/H/J P&L, trades and wins: exact match to Experiment 47.
- Candidate-J baseline shadow parity: PASS.
- AST safety check: PASS.
- Broker execution calls in runner: 0.

No live-market result is claimed because XAUUSD is inactive.

See `preflight.json` for machine-readable evidence.
