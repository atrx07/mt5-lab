# Experiment 18 — BURST-path autopsy evidence

The companion [experiment record](../../../docs/experiments/2026-09-24/18-v4-5-burst-path-autopsy.md) contains the interpretation and decision. Reproduce from `xau-lab/` with:

```powershell
python scripts/v4_5_burst_path_autopsy.py xau_ticks_7d.csv
```

The script verifies the raw SHA-256, reads only the first 1,869,979 rows, builds canonical 500 ms and 1 s features, asserts V4.4 against the frozen oracle, then requires instrumented Candidate B parity segment by segment before writing evidence. Both gates passed on both grids. The final 20% was not read.

`run_metadata.json` records gates, reference metrics, frozen boundaries and matching totals. `candidate_b_*_trades_instrumented.csv` records every completed trade, with BURST identity, exact canonical timestamps, exit reason, realized P&L, MFE/MAE, time to MFE, entry/exit momentum and flow state, spread/range and 10/30/60 s post-exit executable-side excursions. Excursions stop at the segment boundary. The continued-hold flag denotes a *hindsight maximum* above the exit quote; it is not a prospective fill or a recommendation to hold.

`burst_*_opportunity_episodes.csv` groups sampled BURST threshold passes of the same side with at most 10 s between passes. It measures the raw BURST gate before shared-slot and engine-priority arbitration. `burst_opportunity_matches.csv` uses same-side, same-segment overlap with 30 s tolerance. `burst_trade_matches.csv` greedily matches same-side, same-segment entries within 120 s. `burst_unmatched_500ms_trades.csv` classifies unmatched entries by a nearby 1 s episode and an occupied shared slot. These matching rules are diagnostic approximations, not causal counterfactuals.

All 17 500 ms and 12 1 s BURST trades exited by momentum zero-cross. The six unmatched sampled threshold episodes and seven unmatched actual 500 ms BURST trades show admission sampling sensitivity. The negative finding is that post-exit favorable excursions coexist with adverse excursions, so blindly extending every BURST hold is not justified. Candidate B remains the leader at the end of this diagnostic experiment; Experiment 19 evaluates a confirmed-failure exit.
