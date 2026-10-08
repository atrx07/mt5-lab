# mcx-gold-lab agent instructions

Status: **canonical project instructions for the MCX gold lab**

This is an operational handoff, not an experiment log. Historical detail belongs
in numbered experiment documents under `docs/experiments/`.

## Read-first continuation protocol

When resuming:

1. work from `main`;
2. read this file;
3. read `structure.md`;
4. read `docs/plans/00-lab-bootstrap.md` for the phased plan and gates;
5. read `docs/experiments/README.md` and the latest experiment record;
6. inspect matching result evidence when present;
7. prefer repository evidence over remembered chat context.

Do not restart the research line because a conversation ended.

## Project objective

Project: `mcx-gold-lab` inside `atrx07/mt5-lab`.

Instrument: **MCX gold futures**, primary contract **GOLDPETAL (1 g)**,
secondary **GOLDGUINEA (8 g)**.

Goal: maximize expected **net** profit per rupee of deployed capital at low
capital input (Rs 10k-50k accounts), subject to: full MCX cost schedule on every
simulated order, bid/ask fills, margin enforcement, circuit bands, deterministic
risk exits, and chronological validation discipline.

Track: net P&L, gross P&L, total costs, cost ratio, P&L/trade, win rate, profit
factor, max drawdown, breakeven expectancy vs model, regime behavior, and
cost-stress (2x costs) survival.

Trade count alone is never the optimization target. Neither is gross P&L.

## Current canonical state — 2026-10-08

- **Experiment 0 COMPLETE**: capital-efficiency model (`tools/mcx_cost_model.py`).
  Key outputs (gold Rs 15,125/g (observed 2026-10-06)): Petal RT cost Rs 13.31 (breakeven 13.3 ticks),
  Guinea RT cost Rs 68.00, margin Rs 1,059 / Rs 8,470 per lot. Costs are NOT the
  binding constraint on MCX; spread (Rs 2-3 at Rs 1 ticks) and edge existence are.
- **Harness COMPLETE + smoke-tested** (`research/harness.py`): no-look-ahead
  (t+1 execution), bid/ask fills, MCX cost accounting, margin + circuit
  enforcement. 3/3 smoke tests pass on synthetic data.
- **Daily-bar adapter COMPLETE** (`research/daily_harness.py` +
  `tools/build_continuous.py`): next-day-open execution, explicit rollover
  costing, circuit-day flags, slippage parameter. Built for MCX bhavcopy data.
- **Walk-forward gate COMPLETE** (`research/walkforward.py`): rolling
  train/test with IS->OOS Sharpe degradation check (>30% = overfit warning).
- **Baselines**: tick MA crossover + grid prototype (known-negative
  calibration); daily DailyTrendMA + circuit-aware DonchianBreakout prototype.
  Donchian had a real bug caught in review (current bar in its own lookback
  made breakouts impossible) — fixed and re-verified. All baseline P&L on
  synthetic data is meaningless as evidence.
- **Experiment 1 COMPLETE**: first real data — 12 months MCX bhavcopy
  (GOLDPETAL + GOLDGUINEA, 2025-10-08→2026-10-06, 257 trading days, 7-8 rolls,
  manifests in `data/manifests/`). Pipeline: `tools/fetch_bhavcopy.py`
  (browser header profile defeats Akamai; date-wise endpoint dead) →
  `curate_bhavcopy.py` → `build_continuous.py` (front-month rule).
- **Experiment 2 COMPLETE**: regime split on real daily data. Donchian(20)
  made +Rs 5,729 in 6 trending months, lost −Rs 1,105 in 7 choppy months.
  Both daily baselines UNDERPERFORMED buy-and-hold (+1,720/+1,855 vs +2,873)
  in a +23.7% bull year — green ≠ edge. Verdict: no edge found; the research
  target is now a causal regime filter (Experiment 03).
- **No tick data yet.** `tools/capture_ticks.py` is specified, not built.
  No strategy conclusion may be drawn before real MCX ticks flow.
- **No execution adapter.** Live orders require separate explicit authorization
  plus SEBI-framework compliance (broker-approved algo, static IP, algo ID).

## Dataset rules

- Tick archives live under `data/raw/` as `.csv.gz` with a manifest in
  `data/manifests/`. Raw uncurated captures stay out of git (see `.gitignore`).
- Manifest records: schema version, instrument, contract, source, capture
  window, row count, SHA-256, column list, provenance notes.
- Synthetic data is ALWAYS labeled `SYNTHETIC_` and never mixed with real data.
- xau-lab's MT5 tick data is a different instrument/venue/microstructure and is
  NOT valid training or validation data here. Parameters don't transfer.

## Experiment workflow

1. Write the hypothesis BEFORE touching data (`docs/plans/` or experiment doc).
2. Freeze the candidate (code + parameters) before evaluation.
3. Evaluate on dev data -> record. Tune nothing after seeing dev results.
4. Validate on untouched holdout -> record. One shot.
5. Paper-trade the frozen candidate on live ticks before any live discussion.
6. Reject loudly. Rejection is the normal outcome; promotion is rare.

## Risk / execution discipline (paper AND future live)

- Inventory caps are hard (`max_lots` in harness; broker RMS in live).
- Margin is enforced in simulation exactly as a broker would enforce it.
- Circuit bands (3%/6%/9%) are part of every simulation.
- Kill switch: halt new entries at -10% session drawdown (paper rule; live rule
  to be set with the broker's RMS).
- API keys (when they exist): trade-only, no withdrawals, IP-whitelisted,
  rotated quarterly, never committed.

## Versioning

- `v0` = lab bootstrap (this state). Strategy versions start at `v1` only when
  the first real-data candidate is frozen. Never reuse a version number.

## Git workflow

- Canonical work lives on `main`. Push via batched commits.
- Review `agents.md` and `structure.md` before every push; update them when the
  canonical state changes.
