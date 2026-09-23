# V4.1 optimization results

Machine-readable outputs for experiment 08.

- `iteration_summary.csv` — major candidate generations and rejection/promotion decisions.
- `locked_summary.csv` — frozen V4.1 development and validation metrics.
- `v4_1_development_trades.csv` — detailed 69-trade ledger for the locked development replay.
- `v4_1_validation_trades.csv` — detailed 8-trade ledger for the locked validation replay.
- `daily_reset_summary.csv` — per-development-date fresh-₹500 diagnostic.
- `stress_summary.csv` — spread and slippage stress tests.
- `sampling_stress.csv` — 500 ms vs 1 s cadence comparison.
- `locked_config.json` — exact frozen parameters and dataset identity.

The raw tick export is intentionally not committed.

Human-readable analysis:
[`docs/experiments/2026-09-23/08-v4-1-optimization.md`](../../../docs/experiments/2026-09-23/08-v4-1-optimization.md)
