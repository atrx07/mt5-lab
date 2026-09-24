# jev-lab

An independent research workspace for testing whether Jev can improve a practical, home-operated trading system **after fees, spread, slippage, latency, and model cost**. The aim is measurable trading performance, not a bot demonstration or a claim of income.

## Current stage

**Paper baseline built (2026-09-24).** The first target is BTC/USDT spot using Binance public market data. No live trading venue or account is selected. A pinned-model Jev Choice client exists; no TypeSafe key is configured and no real Jev decision has been measured. The first frozen 30-minute breakout baseline lost 16.25 USDT in development and 1.25 USDT in evaluation on separately reset 1,000 USDT paper accounts, after a 10 bp taker fee plus 5 bp adverse execution penalty per side. Buy-and-hold gained in both segments. This is a candle-only diagnostic; the final 20% remains sealed. See [Experiment 00](docs/experiments/2026-09-24-00-btc-spot-baseline.md).

The [Experiment 01 shadow export](docs/experiments/2026-09-24-01-jev-entry-shadow.md) generated 46 pinned Jev Choice requests from development entry candidates, with no model calls. The baseline replay remained identical. This prepares a narrow Jev decision test; it does not show that Jev improves trading results.

No script in this directory places an order. `scripts/probe_jev.py` validates a proposed Choice request locally by default; `--send` explicitly makes one TypeSafe API call when `TYPESAFE_API_KEY` is present. Research and paper trading are the default. A real-order path requires its own explicit milestone and controls described in [AGENTS.md](AGENTS.md).

Reproduce the baseline after restoring the locally held capture identified by the [manifest](data/manifests/2026-09-24-00-btc-spot-baseline.json):

```powershell
python scripts/replay_baseline.py
```

The development-only request export is already held locally in ignored `data/derived/`. To reproduce its request hash after archiving or intentionally removing that file and its existing result bundle, run `python scripts/export_jev_shadow.py` with the same raw capture. The command preserves existing output by default.

## Start here

- [AGENTS.md](AGENTS.md) — research, evidence, and execution rules.
- [STRUCTURE.md](STRUCTURE.md) — canonical paths, naming, and artifact contracts.
- [docs/README.md](docs/README.md) — algorithms, experiments, plans, and external sources.
- [data/README.md](data/README.md) — capture and provenance rules.
- [results/README.md](results/README.md) — result-bundle and comparison rules.

The `xau-lab/` project is separate. Its datasets, strategies, and risk parameters do not automatically apply here.
