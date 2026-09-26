# 48P — V4.5 Candidate J live-shadow harness preflight

Date: 2026-09-26
Status: **completed; archived parity and read-only safety preflight PASS**

This tooling milestone prepares a read-only MT5 XAUUSD shadow runner for Candidate D/H/J before the market reopens.

No live-market result can be claimed while XAUUSD is inactive.

Frozen plan:
`docs/plans/V4_5_CANDIDATE_J_LIVE_SHADOW_PREFLIGHT.md`

Runner:
`scripts/live_shadow_candidate_j.py`

Evidence:
`results/simulations/2026-09-26-v4_5-candidate-j-live-shadow-preflight/`

Experiment 48 remains the fresh prospective validation gate. Final20 remains sealed.


## Result

The read-only live-shadow runner is implemented at:

`scripts/live_shadow_candidate_j.py`

Archived preflight was run against the existing recent24h MT5 snapshot only to verify wrapper parity. It reproduced the exact Experiment-47 whole-window metrics:

| Grid | Candidate | Expected P&L | Actual P&L | Trades | Wins |
| --- | --- | ---: | ---: | ---: | ---: |
| 500 ms | D | -₹223.2733 | -₹223.2733 | 39 | 5 |
| 500 ms | H | -₹208.4690 | -₹208.4690 | 39 | 5 |
| 500 ms | J | -₹164.5399 | -₹164.5399 | 31 | 4 |
| 1 s | D | -₹135.9095 | -₹135.9095 | 34 | 8 |
| 1 s | H | -₹128.6265 | -₹128.6265 | 34 | 8 |
| 1 s | J | -₹70.9992 | -₹70.9992 | 28 | 8 |

All six parity checks passed exactly.

The runner also passed an AST-level safety audit:

- forbidden broker trade calls found: **0**;
- no `mt5.order_send()`;
- no `trade_*` execution calls;
- market-data read/capture only.

## Live-shadow behavior

The runner:

- reads and appends all valid XAUUSD MT5 ticks;
- preserves `last`, `volume`, `flags`, and `volume_real` even though this broker currently leaves trade-tape fields empty;
- runs frozen D/H/J on both 500 ms and 1 s using the same research implementations as Experiments 43/47;
- records Candidate-D opportunities, Candidate-H extra exits, Candidate-J TAKE/WAIT/SKIP phase events, and Candidate-J phase exits;
- writes rolling D/H/J paper metrics;
- marks inactive periods `MARKET_IDLE` and does not manufacture ticks;
- resets the trust warmup after any >5 s quote-continuity break.

Default local evidence:

`data/live_shadow/<session-id>/`

with:

- `ticks.csv`;
- `session_manifest.json`;
- `shadow_status.json`;
- `shadow_events.jsonl`.

The folder is gitignored until an explicit future freeze.

The rolling shadow uses a 4-hour bounded replay refreshed every 15 seconds by default. It is monitoring infrastructure, not a low-latency executor and not official Experiment-48 P&L evidence.

## Weekend status

No live-market result was generated. XAUUSD is currently inactive, so only the archived parity/safety preflight was run.

The terminal connectivity check may be run while the market is closed, but the actual shadow session should start after XAUUSD resumes producing fresh ticks.

## Decision

**Live-shadow infrastructure is ready.**

Candidate J remains frozen unchanged.

Experiment 48 remains the fresh 48-hour prospective gate. Final20 remains sealed.
