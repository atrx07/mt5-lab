# jev-lab

An independent research workspace for testing whether Jev can improve a practical, home-operated trading system **after fees, spread, slippage, latency, and model cost**. The aim is measurable trading performance, not a bot demonstration or a claim of income.

## Current stage

**Initial build (2026-09-24).** The first paper-research target is liquid BTC/USDT spot using Binance public market data. No live trading venue or account is selected. A pinned-model Jev Choice client and a local validation probe exist; no TypeSafe key is configured and no real Jev decision has been measured. A baseline and paper simulator are the next components. There are no trading results yet.

No script in this directory places an order. `scripts/probe_jev.py` validates a proposed Choice request locally by default; `--send` explicitly makes one TypeSafe API call when `TYPESAFE_API_KEY` is present. Research and paper trading are the default. A real-order path requires its own explicit milestone and controls described in [AGENTS.md](AGENTS.md).

## Start here

- [AGENTS.md](AGENTS.md) — research, evidence, and execution rules.
- [STRUCTURE.md](STRUCTURE.md) — canonical paths, naming, and artifact contracts.
- [docs/README.md](docs/README.md) — algorithms, experiments, plans, and external sources.
- [data/README.md](data/README.md) — capture and provenance rules.
- [results/README.md](results/README.md) — result-bundle and comparison rules.

The `xau-lab/` project is separate. Its datasets, strategies, and risk parameters do not automatically apply here.
