# mt5-lab

A research workspace for testing **trading automation with real market data before it gets anywhere near real money**.

The point of this repository is not to collect "winning bot" screenshots. It is to keep the ugly parts too: failed strategies, bad assumptions, spread damage, overfitting attempts, and the changes made after each run.

## Labs

### [xau-lab](./xau-lab)

The XAUUSD paper-trading research track uses live MT5 bid/ask data. Its own documentation records the current version, chronological experiments, and limitations.

The full chronology, raw run logs, algorithm notes and runnable scripts live inside [`xau-lab/`](./xau-lab).

## Research workflow

```text
market data
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

- **Paper first.** A new lab has no implied authorization to place live orders.
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
