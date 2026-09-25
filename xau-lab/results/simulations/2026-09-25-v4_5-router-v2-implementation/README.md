# Experiment 28 — Router v2 implementation

Status: **implementation/config frozen; unseen performance validation pending**.

No Router v2 performance numbers are accepted in this bundle yet.

The implementation uses Candidate D's existing engines and lifecycle, but replaces fixed-priority arbitration with a stronghold-aware score over the frozen `xau-state-v2` features. Simultaneous candidates are ranked, lower-priority candidates remain available through fall-through, and HOLD is allowed when every candidate scores below neutral.

Known datasets are restricted to implementation/parity diagnostics. The next new non-overlapping snapshot supplies the first promotion-relevant comparison.

Run the config freeze / implementation entry point with:

```powershell
python research\v4_5_router_v2.py xau_ticks_7d.csv
```

Optional known-data parity diagnostic:

```powershell
python research\v4_5_router_v2.py xau_ticks_7d.csv --implementation-check
```

The optional diagnostic is explicitly **not promotion evidence**.
