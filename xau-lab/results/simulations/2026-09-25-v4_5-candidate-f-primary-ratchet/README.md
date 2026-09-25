# Experiment 40 — Candidate F PRIMARY profit ratchet

Status: **completed; Candidate F rejected**

Candidate F preserved Candidate D entries but added a PRIMARY-only +1R / 50%-MFE ratchet checked every five seconds.

## Main result

| Grid / window | Candidate D | Candidate F | Delta |
| --- | ---: | ---: | ---: |
| canonical first80 500 ms | **+₹1,430.31** | +₹562.07 | -₹868.24 |
| canonical first80 1 s | **+₹385.25** | +₹283.97 | -₹101.28 |
| recent24h 500 ms | -₹223.27 | -₹221.58 | +₹1.70 |
| recent24h 1 s | **-₹135.91** | -₹180.41 | -₹44.50 |

The ratchet reduced historical drawdown but early exits freed the shared slot, causing extra downstream entries and large path-dependent damage.

Random four-hour windows improved on average at both grids, which supports the profit-retention mechanism itself, but not this full integration architecture.

## Decision

Reject Candidate F unchanged. Candidate D remains leader.

Do not tune ratchet parameters on the same known data.

Next structural question: can the ratchet bank profit **while a virtual legacy PRIMARY continues to occupy the slot until Candidate D's original exit**, preserving downstream entry/cooldown path?

Final20 remains sealed.
