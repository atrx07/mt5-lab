# Experiment 26 — frozen regime portability

Status: **completed no-tuning diagnostic; no candidate promoted**.

The exact Experiment 23 raw-event regime representation was replayed on the separate Experiment 22 recent 24-hour raw snapshot.

The representation remained highly sampling-stable: 27 same-engine/same-side cross-grid matches gave 92.59% volatility, 92.59% spread, 96.30% efficiency, 100% activity and 85.19% complete-key agreement.

However, the historical four-part key did not transfer as a profitability permission map. Recent trades whose exact engine/grid/key had positive historical P&L still lost ₹90.74 at 500 ms and ₹123.88 at 1 s.

PRIMARY's recent losses were dominated by emergency stops and momentum-zero-cross exits, while its max-hold exits remained profitable. That points toward admission/exhaustion context rather than globally disabling the engine.

No threshold is selected from the recent window.
