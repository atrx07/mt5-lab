# 47 — V4.5 MT5-native quote-flow phase controller

Date: 2026-09-26

Status: **frozen; full simulation pending**

Experiment 47 is the first post-external-branch strategy experiment under the MT5-only live-practicality gate.

It adds a causal quote-flow phase state machine using only raw MT5 bid/ask ticks, exact tick-change flags, and the already-frozen Candidate-H microstate confirmation.

Entry tests PRIMARY/SECONDARY TAKE / WAIT / SKIP behavior. Exit tests a tamed Candidate-H controller that protects healthy pullbacks and only banks profit after persistent quote-flow decay/reversal.

Frozen plan:
`docs/plans/V4_5_QUOTE_FLOW_PHASE_CONTROLLER.md`

Implementation:
`research/v4_5_quote_flow_phase_controller.py`

Evidence:
`results/simulations/2026-09-26-v4_5-quote-flow-phase-controller/`

Candidate D remains leader. Candidate H remains the strongest retained exit branch until this diagnostic completes. Final20 remains sealed.
