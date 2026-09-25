# Experiment 42 — signal-fingerprint entry quality

Status: **completed diagnostic; entry expert not promoted**

This diagnostic trains one fixed expert per engine on exit-independent excursion quality and gives each expert the complete frozen state-v2 + microstate-v1 context plus exact rule-margin fingerprints.

Expected evidence:
- entry_fingerprint_dataset.csv
- checkpoint_predictions.csv
- checkpoint_metrics.csv
- episode_policy.csv
- episode_policy_per_engine.csv
- episode_policy_metrics.csv
- simultaneous_ownership.csv
- summary.json

Known data are diagnostic only. Final20 remains sealed.


## Main result

The signal-fingerprint experts improved historical 500 ms episode quality but failed to transfer enough precision across grids/regimes.

- Historical 500 ms audit: +₹274.29 onset → +₹638.78 selected.
- Historical 1 s audit: -₹75.80 onset → -₹297.97 selected.
- Recent 500 ms: -₹4,188.37 → -₹4,039.99.
- Recent 1 s: -₹1,928.48 → -₹1,824.68.

Recent PRIMARY was still predicted positive on roughly 97% of checkpoints while its actual mean excursion edge was negative.

Decision: retain the signal encyclopedia, reject the learned entry policy, keep Candidate D as leader, and leave final20 sealed.
