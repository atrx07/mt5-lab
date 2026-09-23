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
| **V4.1 locked** | **30m trend → 5m context → 60s pullback/resumption + 3% risk sizing** | **development ₹500 → ₹627.52; validation ₹500 → ₹538.79; holdout unopened** |
| V4.2 research | V4.1 primary + secondary breakout outside slow directional gate | stronger research replay, but **not promoted**; hourly objective and spread robustness still insufficient |

V4.1 remains the locked research candidate. The 2026-09-24 V4.2 research run found a materially stronger aggregate composite replay, but it did not meet the new hourly/capture promotion standard and validation was used during composite selection. No V4.2 live-paper script was created and the final holdout remains unopened.

## Current paper candidate

```powershell
python scripts\paper_challenge_v4_1.py
```

Historical tick export:

```powershell
python scripts\export_xau_ticks.py --days 7
```

## Dataset preservation

The seven-day broker-tick dataset used by the baseline and V4.1/V4.2 research is tracked under [`data/`](data/).

The raw ~220 MB CSV remains ignored. A lossless gzip archive plus a SHA-256 manifest is the canonical repository copy.

See [`data/README.md`](data/README.md) for the exact archive/push workflow.

## Documentation

- [Algorithm index](docs/algorithms/README.md)
- [Experiment index](docs/experiments/README.md)
- [V4.1 optimization evidence](docs/experiments/2026-09-23/08-v4-1-optimization.md)
- [V4.2 hourly-capture research](docs/experiments/2026-09-24/09-v4-2-hourly-capture-research.md)
- [Dataset archive policy](data/README.md)
- [Provenance](docs/PROVENANCE.md)

## Research discipline

A candidate only graduates when it survives realistic bid/ask execution, untouched holdout data, multiple regimes, drawdown checks, stress tests and live-paper validation. Hourly earning targets are evaluation benchmarks, not instructions to force trades or increase risk.
