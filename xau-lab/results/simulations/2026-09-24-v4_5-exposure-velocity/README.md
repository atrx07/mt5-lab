# Experiment 20 — exposure velocity result bundle

Status: **completed negative experiment**. See the [experiment record](../../../docs/experiments/2026-09-24/20-v4-5-exposure-velocity.md) for interpretation. Candidate D remains the provisional leader.

From `xau-lab/`, reproduce with:

```powershell
python scripts/v4_5_exposure_velocity.py xau_ticks_7d.csv
```

The script verifies the raw SHA-256; reads only the first 1,869,979 rows; asserts the V4.4 golden oracle and exact Candidate B/D trace parity at 500 ms and 1 s; instruments Candidate D; and tests seven documented variants on segment 0 only. The flow variants were added after the entry diagnostic identified weaker short-horizon momentum and quote acceleration in unmatched 1 s SECONDARY trades. The final 20% holdout was not read. No variant was evaluated on segments 1–4 because none improved the joint seed P&L and profit-velocity frontier.

`run_config.json` contains frozen bounds and exact rule parameters. `diagnostic_metadata.json` contains parity records, Candidate D metrics, seed variant metrics and unmatched 1 s attribution. `seed_variant_summary.csv` makes the seed comparison compact. `candidate_d_*_trades.csv` and `candidate_d_*_checkpoints.csv` preserve the trade and 60/120/300 s path diagnostics. `primary_secondary_trade_matches.csv` records the same-engine, same-side, same-segment nearest-entry matching within 120 s; an unmatched trade is a diagnostic category, not proof that a single gate caused its outcome.

The negative finding is that sampled-grid exit checks and simple SECONDARY persistence/flow vetoes cannot be selected jointly: the rules that help 1 s damage 500 ms seed P&L substantially. No cost stress or later-segment evaluation was run for these rejected seed variants. Candidate D's existing cost-stress evidence remains in Experiment 19; a future serious candidate requires a full execution-aware stress replay.
