# 47R — V4.5 Candidate J multi-seed random-window robustness audit

Date: 2026-09-26
Status: **frozen; three additional random batches pending**

This audit reruns frozen Candidate J against Candidate D/H on three new deterministic random-window batches, 40 real contiguous four-hour windows per grid per batch.

It does not tune Candidate J and does not change the Experiment-48 fresh-data gate.

Frozen specification:
`docs/plans/V4_5_CANDIDATE_J_MULTISEED_RANDOM_AUDIT.md`

Implementation:
`research/v4_5_candidate_j_multiseed_random_audit.py`

Evidence:
`results/simulations/2026-09-26-v4_5-candidate-j-multiseed-random-audit/`

Final20 remains sealed.
