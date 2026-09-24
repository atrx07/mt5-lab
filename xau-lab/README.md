# xau-lab

Experimental XAUUSD research and paper-trading lab built around MetaTrader 5.

> **Safety / scope:** every script in this lab is paper-only by default. None of the live-paper scripts call `mt5.order_send()`. The synthetic position sizes used in the ₹500 experiments are below the broker's observed minimum live size and are not directly executable on that account.

## Environment observed during the experiments

- Instrument: `XAUUSD`
- MT5 account: MetaQuotes-Demo during testing
- Broker minimum volume observed: `0.01 lot`
- Contract size observed: `100 oz / lot`
- Minimum live position: `0.01 lot = 1 oz`
- INR/USD conversion used in the original scripts: `95.7021`
- Tick source: the locally running MT5 terminal
- BUY enters at ask and exits at bid; SELL enters at bid and exits at ask.

## Evolution

| Version | Main idea | Recorded outcome |
| --- | --- | --- |
| V1 | 1 oz fixed synthetic exposure on ₹100 | catastrophic sizing failure; ₹100 → -₹13.89 |
| V2 | dynamic fractional synthetic exposure | recovered full 14-trade run ₹500 → ₹439.40 |
| V3 | confirmed 5 s + 15 s breakouts | ₹500 → ₹482.53 |
| V3.1 | persistent armed breakouts | ₹500 → ₹463.46 |
| V4 | short-horizon pullback / resumption | seven-day development baseline remained strongly negative |
| V4.1 locked baseline | 30m trend → 5m context → 60s pullback/resumption + 3% risk sizing | development ₹500 → ₹627.52; validation ₹500 → ₹538.79 |
| V4.2 experimental | V4.1 primary + secondary breakout outside slow directional gate | first-80% continuous capture ~5.51% |
| **V4.3 locked** | **regime-adaptive V4.2 composite** | **canonical five-segment compounded result +₹603.60; ~8.07% capture** |
| **V4.4 locked** | **V4.3 + MICRO structural engine + Candidate K management** | **historical lock: 16.36% / 11.54%; reproducible replay oracle: 14.67% / 4.45%; final holdout unopened** |

V4.4 is now the current experimental paper version. It is a locked fractional research version, not a major-generation graduation and not a claim of proven future profitability.

Starting with V4.5 research, all candidate simulations must use the parity-gated canonical replay harness. V4.4's strategy parameters are unchanged; the 14.67% / 4.45% regression values are a reproducible measurement re-baseline used only as the future comparison oracle. The earlier 16.36% / 11.54% lock outputs remain preserved as historical research evidence.

V4.3 replay-parity documentation was corrected during the V4.4 lock: its canonical +₹603.60 figure is the compounded result of five independently reset research segments, not a literal one-pass continuous replay.

Any change to the locked V4.4 configuration becomes V4.5.

The final 20% research holdout remains unopened.

## Current experimental paper version

```powershell
python scripts\paper_challenge_v4_4.py
```

Previous versions remain available:

```powershell
python scripts\paper_challenge_v4_3.py
python scripts\paper_challenge_v4_2.py
python scripts\paper_challenge_v4_1.py
```

Historical tick export:

```powershell
python scripts\export_xau_ticks.py --days 7
```

## Dataset preservation

The seven-day broker-tick dataset used by the research is tracked under [`data/`](data/).

The raw ~220 MB CSV remains ignored. A lossless gzip archive plus a SHA-256 manifest is the canonical repository copy.

See [`data/README.md`](data/README.md) for the exact archive/push workflow.

## Documentation

- [Algorithm index](docs/algorithms/README.md)
- [Experiment index](docs/experiments/README.md)
- [V4.1 optimization evidence](docs/experiments/2026-09-23/08-v4-1-optimization.md)
- [V4.2 algorithm](docs/algorithms/v4_2.md)
- [V4.3 algorithm](docs/algorithms/v4_3.md)
- [V4.4 algorithm](docs/algorithms/v4_4.md)
- [V4.3 capture-target research and lock](docs/experiments/2026-09-24/10-v4-3-capture-target-research.md)
- [V4.4 parity fix and lock](docs/experiments/2026-09-24/13-v4-4-parity-and-lock.md)
- [Canonical replay contract](docs/replay/CANONICAL_REPLAY.md)
- [Canonical replay freeze](docs/experiments/2026-09-24/16-canonical-replay-freeze.md)
- [Dataset archive policy](data/README.md)
- [Provenance](docs/PROVENANCE.md)

## Canonical replay gate

Every new V4.x candidate must pass the locked V4.4 regression assertion inside `scripts/canonical_replay.py` before its result is considered valid. If preprocessing, sampling, features, boundaries or accounting drift, the run fails instead of silently producing a new baseline.

## Research discipline

Major-version graduation requires realistic bid/ask execution, untouched holdout evidence, multiple regimes, drawdown checks, stress tests and live-paper validation. Fractional versions may be locked as experimental iterations when they show a distinct measurable improvement while preserving fixed risk discipline. Hourly earning targets are evaluation benchmarks, not instructions to force trades or increase risk.
