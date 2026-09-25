# 30 — V4.5 full raw-tick Router v2 replay

Date: 2026-09-25

Status: **in progress — harness frozen; execution pending**

## Objective

Run the actual Experiment-28 Router v2 end to end instead of the Experiment-29 trade-ledger proxy.

The replay uses raw ticks to build the canonical sampled features, evaluates all simultaneously eligible engines while the shared slot is flat, computes `xau-state-v2` for those opportunities, applies the frozen engine-specific stronghold score, performs fall-through/HOLD arbitration, then executes Candidate D's unchanged lifecycle and risk logic.

No score component, weight, scale, score floor, engine signal or lifecycle parameter may be changed from Experiment 28 because of these known-data results.

## Test matrix

1. **Canonical seven-day first80** — parity-gated against V4.4 and Candidate D's exact 163/81/+₹1,430.3111 at 500 ms and 156/71/+₹385.2545 at 1 s.
2. **Recent 24-hour raw snapshot** — whole-window run plus the historical 60/40 split for comparison. Whole-window reporting includes terminal mark-to-market so an open final ticket does not silently disappear from P&L.
3. **Random variable situations** — deterministic seeded four-hour windows drawn directly from the real canonical first80 and recent24h raw environments. No synthetic price path or invented P&L is generated. The random-window stress is diagnostic only because both source datasets are already known.

## Interpretation discipline

This experiment can answer whether the implemented fall-through router actually behaves better than the gate proxy on the known raw datasets.

It still cannot promote Router v2 as generalized/unseen. Promotion evidence requires a new non-overlapping raw snapshot.

## Reproduction

```powershell
python research\v4_5_router_v2_full_eval.py xau_ticks_7d.csv xau_ticks_recent_24h_2026-09-24.csv.gz
```

## Evidence

- `research/v4_5_router_v2_full_eval.py`
- `results/simulations/2026-09-25-v4_5-router-v2-full-replay/full_replay_summary.json` after execution
- `results/simulations/2026-09-25-v4_5-router-v2-full-replay/random_real_windows.csv` after execution
