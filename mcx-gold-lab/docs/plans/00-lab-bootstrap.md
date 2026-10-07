# Phased research plan — mcx-gold-lab

Each phase has a gate. A gate not passed = stop, not proceed-with-hope.

## Phase 0 — Price the container (COMPLETE, 2026-10-08)

Build the capital-efficiency model before any strategy code.
Tool: `tools/mcx_cost_model.py`. Record: `docs/experiments/00-cost-model.md`.

Gate: model runs, numbers are sane, contract choice is justified on paper.
Result: **GOLDPETAL primary / GOLDGUINEA secondary.** Costs are not the binding
constraint on MCX; spread and edge existence are.

## Phase 1 — Data pipeline

Build `tools/capture_ticks.py` against a broker websocket (Kite Connect default;
Upstox/Angel One alternatives documented in `docs/plans/01-venue-selection.md`).
Capture live GOLDPETAL ticks into `data/raw/` with manifests. Target: 4+ weeks
of ticks before any strategy evaluation, split into dev / holdout at capture
time (holdout sealed, never opened during development).

Gate: manifest-complete archive, bid/ask spread distribution measured, session
coverage verified (9:00-23:55 IST, rollover days flagged).

## Phase 2 — Harness + baselines on real data (COMPLETE on synthetic)

`research/harness.py` is built and smoke-tested (3/3 pass). Re-run the smoke
suite against the first real tick archive (parity: accounting must be identical
in behavior; only the data changes).

Baselines on real data: MA crossover (known-negative calibration) first. Its
real-data loss profile is the floor every candidate must demonstrably beat.

Gate: harness smoke passes on real ticks; baseline metrics recorded as the
calibration reference.

## Phase 3 — Strategy research

Hypothesis-first candidates, frozen before evaluation, dev -> holdout -> paper.
Port NOTHING parametric from xau-lab; port the workflow. Priority research
questions:

1. Does any microstructure edge exist in GOLDPETAL ticks net of the Rs 2-3
   spread? (Spread is 20-40% on top of fees here — it is the strategy.)
2. How do 3%/6%/9% circuit days interact with momentum/breakout logic?
3. Does the INR basis (MCX vs XAUUSD x USDINR) create tradeable dislocations,
   or just noise?
4. Session structure: does the 9:00-23:55 IST window (no weekend) change
   regime behavior vs 24h XAUUSD?

Gate per candidate: frozen plan -> dev metrics (profit factor, expectancy vs
the Rs 10.56/trade breakeven, max drawdown, cost ratio < 0.5, 2x-cost stress
still positive) -> ONE holdout shot -> paper trade >= 4 weeks.

## Phase 4 — Paper trading

Frozen candidate on live ticks, paper fills at bid/ask, full cost accounting,
kill-switch drill (halt new entries at -10% session drawdown). Minimum 4 weeks
/ 200+ trades.

Gate: paper profit factor within 40% of holdout; zero manual overrides; kill
switch tested and logged.

## Phase 5 — Tiny live (separate explicit authorization required)

Rs 10k-25k account, GOLDPETAL only, 3-6 months. SEBI-framework compliance first:
broker-approved algo, static IP, algo ID, audit trail. Then and only then.

Gate: net positive after all costs over 6 months and 500+ trades before any
scale-up discussion. Scale-up contract: GOLDGUINEA.
