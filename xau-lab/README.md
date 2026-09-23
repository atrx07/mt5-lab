# xau-lab

Experimental XAUUSD research and paper-trading lab built around MetaTrader 5.

This directory records the full progression of the live-paper experiments from the first oversized ₹100 challenge through the V3/V3.1 momentum-breakout systems and the V4 research successor.

> **Safety / scope:** every script in this lab is paper-only by default. None of the live-paper scripts call `mt5.order_send()`. The synthetic position sizes used in the ₹500 experiments are below the broker's observed minimum live size and are not directly executable on that account.

## Environment observed during the experiments

- Instrument: `XAUUSD`
- MT5 account: MetaQuotes-Demo during testing
- Broker minimum volume observed: `0.01 lot`
- Contract size observed: `100 oz / lot`
- Minimum live position: `0.01 lot = 1 oz`
- Leverage used for synthetic sizing: `100x`
- INR/USD conversion used in the original scripts: `95.7021`
- Tick source: the locally running MT5 terminal
- Paper execution convention:
  - BUY enters at ask and exits at bid
  - SELL enters at bid and exits at ask
  - therefore spread is paid naturally in the simulated P&L

## Evolution

| Version | Main idea | Recorded outcome |
| --- | --- | --- |
| V1 | 1 oz fixed synthetic exposure on ₹100 | catastrophic sizing failure; ₹100 → -₹13.89 in ~42 s |
| V2 | dynamic fractional synthetic exposure on ₹500 | ₹500 → ₹475.48 after 6 trades |
| V3 | 5 s + 15 s breakout confirmation, hard stop, profit lock | ₹500 → ₹482.53 after 3 trades |
| V3.1 | persistent armed signals, fixed breakout level, fewer false resets | ₹500 → ₹463.46 after 18 trades |
| V4 research candidate | trend → pullback → resumption, no-chase, one trade per impulse, tighter spread/risk controls | successor for further replay and live-paper validation |

The V3.1 run is especially informative: the strategy was approximately flat after 14 trades, then four late losses caused nearly all of the final drawdown. Entry spread above roughly $0.30 correlated strongly with those losses in that single run, so V4 treats transaction cost and market regime as first-class filters rather than afterthoughts.

## Layout

```text
xau-lab/
├── README.md
├── requirements.txt
├── docs/
│   ├── ALGORITHMS.md
│   └── EXPERIMENT_LOG.md
├── scripts/
│   ├── paper_challenge.py
│   ├── paper_challenge_v2.py
│   ├── paper_challenge_v3.py
│   ├── paper_challenge_v3_1.py
│   ├── paper_challenge_v4.py
│   ├── export_xau_ticks.py
│   └── replay_lab.py
└── results/
    ├── paper_trades_v3.csv
    └── paper_trades_v3_1.csv
```

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\paper_challenge_v4.py
```

For historical replay from the exact broker feed:

```powershell
python scripts\export_xau_ticks.py --days 7
python scripts\replay_lab.py xau_ticks_7d.csv
```

## Research discipline

The aim of this repository is not to present a profitable trading system as proven. It is to keep the experiment reproducible and make failure modes visible.

A candidate only graduates when it survives:

1. realistic bid/ask or explicitly modelled spread;
2. untouched holdout windows;
3. multiple market regimes;
4. walk-forward testing rather than tuning and scoring on the same slice;
5. drawdown and loss-streak checks;
6. live-paper validation before any real execution layer is considered.

See [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md) for the chronology and [docs/ALGORITHMS.md](docs/ALGORITHMS.md) for the strategy logic.
