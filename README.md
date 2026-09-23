# mt5-lab

A sandbox for testing **MetaTrader 5 trading ideas with real market data before they get anywhere near real money**.

The point of this repository is not to collect "winning bot" screenshots. It is to keep the ugly parts too: failed strategies, bad assumptions, spread damage, overfitting attempts, and the changes made after each run.

## Current lab

### [xau-lab](./xau-lab)

The first active experiment is an **XAUUSD paper-trading research track** built around live MT5 bid/ask data.

| Generation | Main idea | What happened |
| --- | --- | --- |
| V1 | Fixed 1 oz momentum trading | Sizing failure |
| V2 | Dynamic fractional exposure | Survived longer, still overtraded |
| V3 | Multi-horizon confirmed breakouts | More selective, fragile setup state |
| V3.1 | Persistent armed breakouts | Better state handling; full run still negative |
| V4 | Short-horizon pullback / resumption | Failed the seven-day development baseline |
| **V4.1** | **30m trend → 5m context → 60s pullback/resumption + risk sizing** | **Locked research candidate after positive development + validation** |

V4.1 is **not** a profitability claim. Its final holdout has not been evaluated, and validation contained only eight trades.

The full chronology, raw run logs, algorithm notes and runnable scripts live inside [`xau-lab/`](./xau-lab).

## Research workflow

```text
MT5 broker ticks
      ↓
chronological development
      ↓
candidate iteration
      ↓
validation rejection / promotion
      ↓
execution stress tests
      ↓
lock algorithm + parameters
      ↓
untouched holdout
      ↓
live paper validation
```

## Design rules

- **Paper first.** Current strategy scripts do not call `mt5.order_send()`.
- **Use bid/ask, not fantasy mid-price fills.**
- **Spread is part of the strategy.**
- **Risk exits stay deterministic.**
- **Keep the failures.**
- **Do not confuse backtest improvement with proof of profitability.**

## Repository layout

```text
mt5-lab/
├── README.md
└── xau-lab/
    ├── README.md
    ├── docs/
    │   ├── algorithms/
    │   ├── experiments/
    │   └── plans/
    ├── results/
    │   └── simulations/
    └── scripts/
        ├── paper_challenge_v4.py
        └── paper_challenge_v4_1.py
```

## Status

**Research / paper trading only.**

Nothing in this repository should be treated as a claim of profitability, financial advice, or a production-ready trading system.
