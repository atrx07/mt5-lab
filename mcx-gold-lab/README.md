# mcx-gold-lab

Experimental MCX gold-futures research and paper-trading lab — the lawful,
small-capital sibling of `xau-lab`.

> **Safety / scope:** every script in this lab is paper-only by default. No script
> places live orders. There is no execution adapter committed; order placement
> against a broker API is a separate, explicitly authorized future step that
> requires SEBI-framework compliance (broker-approved algo, static IP, algo ID).

## Why this lab exists

`xau-lab` researches XAUUSD on MT5 demo ticks. Two structural facts block that
line from ever taking real money from an Indian resident:

1. The broker minimum ticket (0.01 lot = 1 oz ≈ Rs 3.9 lakh notional) makes the
   Rs 500 synthetic experiments non-executable live.
2. Funding an offshore MT5 XAUUSD account from India breaches FEMA.

MCX gold futures solve both: **Gold Petal (1 g)** needs ~Rs 1,059 margin per lot (at Rs 15,125/g, 2026-10-06),
costs ~Rs 13.31 per round trip (at Rs 15,125/g), and trades on a SEBI-regulated Indian exchange
through Indian brokers. Same underlying (gold), lawful venue, honest ticket size.

## What this lab is not

- It is not a profitable strategy. No candidate exists yet. Experiment 0 (the
  cost model) prices the *container*; edge, if it exists, must be discovered by
  the research process documented in `docs/plans/`.
- Strategy P&L on the synthetic smoke data in `research/` is **not evidence** of
  anything except that the harness accounts correctly.

## Quick start

```bash
pip install -r requirements.txt

# Gate 0 — the capital-efficiency model (run this before anything else):
python tools/mcx_cost_model.py

# Harness smoke test (SYNTHETIC data, accounting validation only):
python research/run_baselines.py --ticks 100000 --account 25000
```

## Repository layout

```text
mcx-gold-lab/
├── README.md
├── agents.md
├── structure.md
├── requirements.txt
├── .gitignore
├── data/            # tick archives + manifests (raw ticks stay out of git)
├── docs/
│   ├── plans/       # phased research plan, venue selection
│   └── experiments/ # numbered experiment records
├── research/        # harness, baselines, intermediate experiment code
├── results/         # cost-model output, smoke-test logs (synthetic labeled)
├── scripts/         # paper-challenge executors (paper only)
└── tools/           # cost model, tick capture, data utilities
```

## Design rules (inherited from mt5-lab, adapted)

- **Paper first.** Nothing here implies authorization to place live orders.
- **Use bid/ask, not fantasy mid-price fills.** Buys fill at ask, sells at bid.
- **Spread is part of the strategy.** At Rs 1 ticks, a Rs 2-3 spread is 20-40%
  on top of the fee schedule. Model it or lose to it.
- **Costs are real.** Every simulated order pays the MCX schedule.
- **Circuits exist.** MCX enforces 3%/6%/9% daily bands — MT5 gold has none.
  Breakout logic must be circuit-aware.
- **Risk exits stay deterministic.** Inventory caps, margin enforcement, kill switch.
- **Keep the failures.** Rejected candidates are evidence, not embarrassment.
- **Do not confuse backtest improvement with proof of profitability.**
- **Parameters don't transfer.** xau-lab's edge (if any) lives in XAUUSD
  microstructure. Everything is re-validated here from zero.

## Status

**Research / paper only. Experiment 0 (cost model) complete. No tick data yet —
the capture pipeline (`tools/capture_ticks.py`) is the next build.**
