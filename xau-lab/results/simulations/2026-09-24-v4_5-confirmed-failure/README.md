# Experiment 19 — confirmed BURST failure evidence

See the [experiment record](../../../docs/experiments/2026-09-24/19-v4-5-confirmed-failure.md) for interpretation and decision. Reproduce the full first-80% runs from `xau-lab/` with:

```powershell
python research/v4_5_confirmed_failure.py xau_ticks_7d.csv --seed-probe
python research/v4_5_confirmed_failure.py xau_ticks_7d.csv --confirm-sec 1
python research/v4_5_confirmed_failure.py xau_ticks_7d.csv --confirm-sec 2
python research/v4_5_confirmed_failure.py xau_ticks_7d.csv --confirm-sec 3
```

`candidate_d_config.json` specifies the selected one-second rule and the unchanged Candidate B/risk configuration. `seed_confirmation_probe.json` preserves 0/1/2/3/5 s seed outcomes; the 5 s variant was rejected on the seed. `confirm_*s_metadata.json` records V4.4 and Candidate B gates, segment results, aggregate metrics, BURST attribution and fixed-size additional slippage at $0/$0.05/$0.10/$0.20 per side. `confirm_*s_*_trades.csv` preserves every completed candidate trade for the three full-run durations.

The raw SHA-256 matched the dataset contract; the first 1,869,979 rows and frozen five segments were used. V4.4 golden parity and exact Candidate B instrumentation parity passed at 500 ms and 1 s before each candidate. The final 20% holdout was not read.

One second improved the seed on both grids and produced ₹1,430.31 / ₹385.25 compounded P&L on the full first-80% pool, compared with Candidate B's ₹1,299.37 / ₹365.25. It improved P&L per exposure hour to ₹61.38 / ₹18.79. The 50–60% segment stayed negative and the 1 s capture remained only 5.15%. Two and three seconds were not selected; five seconds was seed-negative.

The cost schedule is an **additional adverse-slippage debit** on recorded entry ounces, twice per trade for entry and exit. It holds observed trade sizes and paths fixed; it is a sensitivity test, not a full slippage-aware resimulation. At $0.20 per side, the 1 s result is close to breakeven (₹51.42 compounded). Candidate D is a provisional research leader, **not** a locked or live-executable strategy. Do not create `paper_challenge_v4_5.py` from this evidence alone.
