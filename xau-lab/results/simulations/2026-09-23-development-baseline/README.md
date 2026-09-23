# Development baseline simulation results

Comparison of current V3.1 and current V4 on the **development 60%** of the seven-day MT5 XAUUSD tick export.

No V4.1 tuning was applied, and neither validation nor holdout strategy performance was evaluated.

Files:

- `continuous_summary.csv` — continuous ₹500 replay metrics;
- `daily_reset_summary.csv` — per-UTC-day fresh-₹500 diagnostic;
- `daily_reset_aggregate.csv` — aggregate daily-reset trade statistics including MFE/MAE;
- `exit_reason_summary.csv` — exit reason performance;
- `split_manifest.json` — dataset hash, exact split boundaries and simulation assumptions.

Human-readable interpretation lives in [experiment 07](../../../docs/experiments/2026-09-23/07-seven-day-development-baseline.md).
