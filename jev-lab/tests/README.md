# Tests

`test_client.py` checks the Jev request/response contract, pinned model, deadline transport, failure behavior, and avoidance of key exposure. Add further focused tests for timestamp causality, fee/fill accounting, risk caps, stale-response handling, and paper/live separation when those components exist.

`test_paper.py` checks next-open entry timing, cost effects, flat no-trade behavior, and rejection of gaps in the captured candles.
