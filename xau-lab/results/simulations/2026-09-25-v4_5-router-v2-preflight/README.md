# Experiment 29 — Router v2 gate-proxy preflight

This bundle is **not** a full Router-v2 raw-tick replay.

It applies the frozen Router-v2 stronghold score to the already realized Candidate D state-v2 entry ledgers. Entries scoring below zero become HOLD. Same-time lower-priority fall-through cannot be reconstructed from these ledgers, so the result is a conservative gate proxy.

Headline result: the proxy keeps about 97% of trades but loses substantial seven-day benchmark P&L, while the hostile recent window improves by only about ₹14.4 per grid and remains negative. A 10,000-scenario variable-regime bootstrap also shows no central-profitability improvement.

Candidate D remains the current winner. Do not tune Router v2 from this known-data diagnostic.
