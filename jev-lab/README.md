# jev-lab

An independent research workspace for testing whether Jev can improve a practical, home-operated trading system **after fees, spread, slippage, latency, and model cost**. The aim is measurable trading performance, not a bot demonstration or a claim of income.

## Current stage

**Scaffold only (2026-09-24).** No market, venue, data feed, strategy, Jev integration, or trading account is configured. There are no experiments or results yet. The first research milestone is to choose a tradeable market/venue and establish a deterministic baseline with realistic costs. Jev can then be tested as a bounded decision layer against that baseline.

No script in this directory places an order. Research and paper trading are the default. A real-order path requires its own explicit milestone and controls described in [AGENTS.md](AGENTS.md).

## Start here

- [AGENTS.md](AGENTS.md) — research, evidence, and execution rules.
- [STRUCTURE.md](STRUCTURE.md) — canonical paths, naming, and artifact contracts.
- [docs/README.md](docs/README.md) — algorithms, experiments, plans, and external sources.
- [data/README.md](data/README.md) — capture and provenance rules.
- [results/README.md](results/README.md) — result-bundle and comparison rules.

The `xau-lab/` project is separate. Its datasets, strategies, and risk parameters do not automatically apply here.
