# Experiment 39 — Decision Policy v2

Status: **pre-run evidence bundle; architecture frozen**

Experiment 39 changes the decision representation rather than tuning Experiment 38:

- cooldown-free signal episodes for TAKE / WAIT / SKIP entry timing;
- episode-level weighting;
- 30-second incremental continuation target;
- causal trajectory-delta features;
- two-negative-prediction exit confirmation;
- fixed +1R / 50%-MFE profit-ratchet comparator.

Known data are diagnostic only. No Candidate F is created by this bundle and final20 remains sealed.
