# Experiment 24 — bounded regime-router probe

Status: **completed; selected router probe rejected; Candidate D unchanged**.

Experiment 24 is the first attempt to use the frozen Experiment 23 raw-event regime state for engine routing. It searched 48 single-category vetoes on the 0-40% seed only. A veto had to improve P&L and preserve or improve win rate on both grids, retain at least 95% of trades and keep seed drawdown within 2% of Candidate D.

Two variants qualified. The stronger seed choice blocked MICRO when `raw_range60_rel < 0.75` and was frozen before later evaluation.

It improved seed P&L from ₹696.84 to ₹709.36 at 500 ms and from ₹169.92 to ₹179.60 at 1 s while removing one trade on each grid. But on the full first-80% record it produced ₹1,407.86 at 500 ms versus Candidate D's ₹1,430.31, while improving 1 s to ₹398.05 versus ₹385.25. Trade retention remained 98.77% / 99.36% and win rate was effectively unchanged at 500 ms.

The router probe is rejected because it does not improve the joint-grid frontier. Do not select the second seed qualifier using the now-known later evaluation. The next router research must first add independent non-overlapping windows.

Reproduce with:

```powershell
python scripts\v4_5_regime_router_probe.py xau_ticks_7d.csv
```
