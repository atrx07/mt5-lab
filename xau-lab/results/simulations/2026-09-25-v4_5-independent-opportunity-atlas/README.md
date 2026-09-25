# Experiment 33 — independent engine opportunity atlas

Status: **completed diagnostic**.

The shared slot, cross-engine cooldown path and compounding were removed so each existing engine could be measured as a fixed-₹500 independent opportunity stream.

The result is decisive for architecture direction:

- historical seven-day: all four engines are positive independently on both grids;
- recent 500 ms: **all four engines are negative independently**;
- recent 1 s: only SECONDARY is positive (+₹18.82 across 9 trades), while PRIMARY/MICRO/BURST remain negative;
- exact simultaneous multi-engine entries occur on only about 2.2–3.7% of entry events.

This means the hostile recent result is not primarily a routing failure. The current engine family itself lacks enough cross-regime complementarity.

Candidate D remains the strategy leader. Further router-threshold tuning is paused. The next research branch adds a genuinely different short-horizon SNAPBACK/reversion opportunity generator, frozen before performance evaluation.
