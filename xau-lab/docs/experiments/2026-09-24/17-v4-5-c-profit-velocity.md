# 17 — V4.5-C profit-velocity lifecycle search

Date: 2026-09-24

Status: **research in progress; no V4.5 lock**

## Objective

The project objective is not to maximize capture in isolation. It is to maximize expected XAUUSD profit per unit time while keeping fixed risk, execution-cost sensitivity, drawdown and sampling robustness under control.

Candidate B remains the current V4.5 research leader:

- 500 ms canonical capture: 17.3652%;
- 1 s canonical capture: 4.8814%;
- final 20% holdout unopened.

The large 500 ms -> 1 s degradation is treated as a fragility diagnostic, not as a separate trading target. A materially stronger 1 s result is still desirable because it indicates less dependence on sub-second timing.

## Phase C1

Phase C1 changes **BURST lifecycle only**.

The following remain unchanged:

- V4.4 PRIMARY;
- V4.4 SECONDARY;
- V4.4 MICRO;
- Candidate B BURST admission;
- 3% planned risk;
- $4 emergency stop;
- one shared position slot;
- canonical first-80% research boundaries.

The search varies:

- BURST maximum hold: 120 / 180 s;
- trail trigger: $5.50 / $6.50 / $7.50;
- trail give-back: $2.00 / $2.50;
- optional raw-flow continuation extension;
- optional flow-decay early exit.

Raw-flow continuation uses the already-canonicalized quote acceleration and directional tick imbalance features. It does not add a new entry engine.

## Profit-velocity instrumentation

The new harness records:

- compounded P&L and capture;
- trade count and wins;
- median segment PF;
- worst segment drawdown;
- total exposure time;
- P&L per exposure hour;
- mean hold time;
- P&L per trade;
- BURST-only P&L, trade count and P&L per exposure hour;
- mean MFE / MAE;
- count of negative chronological segments.

The ranking heuristic weights:

- 40% canonical P&L at 500 ms;
- 20% canonical P&L at 1 s;
- 25% P&L per exposure hour at 500 ms;
- 15% P&L per exposure hour at 1 s;

with penalties for PF deterioration and drawdown expansion.

This score is a search heuristic only. It is not a promotion criterion.

## Anti-overfit protocol

The harness:

1. verifies the dataset SHA-256;
2. rebuilds and asserts canonical V4.4 at 500 ms and 1 s;
3. requires the instrumented simulator to reproduce Candidate B exactly;
4. searches all lifecycle variants only on the 0-40% seed segment;
5. evaluates only the top seed candidates on the chronological 40-80% region;
6. performs a full first-80% summary only for the strongest evaluation candidates;
7. never reads the final 20% holdout;
8. never promotes or locks a candidate automatically.

## Search command

From `xau-lab/` on canonical `main`:

```powershell
python scripts\v4_5_profit_velocity_search.py xau_ticks_7d.csv
```

Expected outputs:

```text
results/simulations/2026-09-24-v4_5-c-profit-velocity/
  seed_search.csv
  evaluation_shortlist.csv
  full_shortlist.csv
  run_metadata.json
```

## V4.5 lock direction

The desirable region remains approximately:

- 500 ms capture around 20% or better if achieved without fragility;
- a much smaller 500 ms -> 1 s degradation, with ~10% 1 s capture treated as an aspirational robustness level rather than a forced threshold;
- higher profit velocity than Candidate B;
- no material PF or drawdown deterioration;
- improvement or at least containment of the weak 50-60% regime;
- positive execution-cost stress before any lock.

Cost stress is intentionally a later gate after lifecycle candidates are narrowed.

## Canonical locations

All V4.5-C work is maintained directly on `main`:

- strategy/research documentation: `docs/algorithms/v4_5.md`;
- experiment record: `docs/experiments/2026-09-24/17-v4-5-c-profit-velocity.md`;
- runnable search harness: `scripts/v4_5_profit_velocity_search.py`;
- generated evidence: `results/simulations/2026-09-24-v4_5-c-profit-velocity/`.

No separate research branch is part of the canonical workflow.
