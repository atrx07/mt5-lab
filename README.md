# mt5-lab

A sandbox for testing **MetaTrader 5 trading ideas with real market data before they get anywhere near real money**.

The point of this repository is not to collect "winning bot" screenshots. It is to keep the ugly parts too: failed strategies, bad assumptions, spread damage, overfitting attempts, and the changes made after each run.

## Current lab

### [xau-lab](./xau-lab)

The first active experiment is an **XAUUSD paper-trading research track** built around live MT5 bid/ask data.

It started as a tiny-capital momentum challenge and quickly turned into a useful lesson in why gold, leverage and transaction costs are a mildly cursed combination.

| Generation | Main idea | What happened |
| --- | --- | --- |
| V1 | Fixed 1 oz momentum trading | Account sizing was catastrophically wrong |
| V2 | Dynamic fractional exposure | Survived, but overtraded and paid too much spread |
| V3 | Multi-horizon confirmed breakouts | More selective, but armed signals were too fragile |
| V3.1 | Persistent armed breakouts | Better state handling; still vulnerable to late entries and hostile spread regimes |
| **V4** | **Trend → pullback → resumption** | Current research candidate |

The full chronology, exact paper logs, algorithm notes and runnable scripts live inside [`xau-lab/`](./xau-lab).

## What makes this a lab

A strategy does not get promoted because one run looked pretty.

The workflow is moving toward:

```text
MT5 broker ticks
      ↓
historical export
      ↓
fast deterministic replay
      ↓
random 30-minute windows
      ↓
walk-forward / untouched holdouts
      ↓
failure-mode analysis
      ↓
live paper validation
      ↓
only then consider anything involving real execution
```

The repo currently includes tooling to export historical MT5 ticks and replay the latest XAUUSD strategy over many windows without waiting for the market in real time.

## Design rules

- **Paper first.** Current strategy scripts do not call `mt5.order_send()`.
- **Use bid/ask, not fantasy mid-price fills.** BUY enters at ask and exits at bid; SELL does the opposite.
- **Spread is part of the strategy.** On short XAUUSD trades it can dominate the expected edge.
- **Risk exits stay deterministic.** A future AI/JEV decision layer may help with entries, but it should never sit in the emergency exit path.
- **Keep the failures.** A bad run is research data, not something to quietly delete.
- **Do not confuse backtest improvement with proof of profitability.** Every tuned idea still needs unseen data.

## Repository layout

```text
mt5-lab/
├── README.md
└── xau-lab/
    ├── README.md
    ├── docs/
    │   ├── ALGORITHMS.md
    │   ├── EXPERIMENT_LOG.md
    │   └── PROVENANCE.md
    ├── results/
    │   ├── paper_trades_v3.csv
    │   └── paper_trades_v3_1.csv
    └── scripts/
        ├── paper_challenge.py
        ├── paper_challenge_v2.py
        ├── paper_challenge_v3.py
        ├── paper_challenge_v3_1.py
        ├── paper_challenge_v4.py
        ├── export_xau_ticks.py
        └── replay_lab.py
```

## Status

**Research / paper trading only.**

Nothing in this repository should be treated as a claim of profitability, financial advice, or a production-ready trading system. The interesting part is the iteration process—and whether the strategy survives increasingly unfair tests.
