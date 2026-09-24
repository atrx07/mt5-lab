# Results

Use `backtests/` for historical replay, `forward/` for timestamped shadow or paper observations, and `benchmarks/` for latency, cost, data, and execution diagnostics. Each experiment gets one directory with the same ID as its document and contains at least `README.md`, `config.json`, and `summary.json`.

- [Experiment 00 BTC/USDT baseline](backtests/2026-09-24-00-btc-spot-baseline/README.md): negative candle-only diagnostic; no Jev calls.
- [Experiment 01 Jev entry shadow export](benchmarks/2026-09-24-01-jev-entry-shadow/README.md): 46 development-only requests; baseline parity; no Jev calls.

Report net performance after all applicable costs and compare against a deterministic baseline and no-trade baseline under identical conditions. Preserve negative runs and distinguish simulated decisions, paper fills, and actual fills. Full bundle requirements are in [STRUCTURE.md](../STRUCTURE.md#results-and-evidence-bundles).
