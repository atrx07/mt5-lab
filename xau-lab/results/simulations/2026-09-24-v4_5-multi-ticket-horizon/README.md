# Experiment 21 — multi-ticket horizon result bundle

Status: **completed negative research**. No prototype was promoted; provisional Candidate D remains the V4.5 leader. The [experiment record](../../../docs/experiments/2026-09-24/21-v4-5-multi-ticket-horizon.md) contains the interpretation.

From `xau-lab/`, reproduce the three bounded runs:

```powershell
& .venv/Scripts/python.exe scripts/v4_5_multi_ticket_horizon.py xau_ticks_7d.csv --mode 0
& .venv/Scripts/python.exe scripts/v4_5_multi_ticket_horizon.py xau_ticks_7d.csv --mode 1 --seed-only
& .venv/Scripts/python.exe scripts/v4_5_multi_ticket_horizon.py xau_ticks_7d.csv --mode 2 --seed-only
```

Mode 0 is the initial trend-first design and script default, mode 1 adds an active short-horizon impulse lane, and mode 2 tests short-horizon reversal. Modes 1 and 2 require `--seed-only`; the script rejects an attempt to run these rejected settings on later segments.

Each `prototype_*_metadata.json` records the exact risk and signal settings, dataset SHA-256, first-80% boundaries, V4.4 golden parity result, Candidate D comparison reference, candidate metrics and two-sided $0.20 adverse-fill stress. The matching trade ledgers contain each ticket's executable entry/exit quotes, size, P&L, horizon, holding time and reason. Daily CSVs sum realized trade P&L by UTC exit date and include observed quote days with zero exits. The first/last day are partial, and five segment account resets mean daily CSVs are diagnostics rather than a continuous-account return series.

Prototype 0 failed on the full first-80% at both grids (-₹22.14 / -₹52.92). Prototype 1 reached three concurrent tickets but failed joint seed selection (+₹29.15 / -₹23.13). Prototype 2 also failed joint seed selection (+₹13.72 / -₹37.90). No observed UTC quote day reached ₹100 in any tested run. Profit-confirmed exits were executable-price positive, but mandatory stops, gap closures, time limits and segment closures realized losses. All positions were synthetic and below the broker's observed minimum live size. The final 20% holdout was not read.

The replay inherits the canonical sampled-quote decision/fill convention and does not model broker latency, financing, margin liquidation or minimum-lot execution. The negative result gives no reason to advance these prototypes to an execution-aware replay or paper trading.
