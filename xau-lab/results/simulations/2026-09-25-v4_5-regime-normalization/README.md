# Experiment 23 — raw-event regime normalization

Status: **completed diagnostic; no candidate promoted**.

The strategy remained provisional Candidate D. No entry, exit, sizing, risk, canonical sampling or accounting rule changed.

V4.4 golden parity, Candidate B trace parity and Candidate D parity passed on both 500 ms and 1 s before the regime analysis. The final 20% was not read.

## Main result

119 Candidate D entries matched one-to-one across the two grids. Raw-event regime-category agreement was 92.44% for volatility, 89.92% for spread, 92.44% for efficiency, 95.80% for activity and 76.47% for the complete four-part key.

The four-hour engine audit shows BURST and MICRO as comparatively consistent on this historical episode, PRIMARY as aggregate-profitable but regime-dependent, and SECONDARY as the weakest engine with -₹51.80 aggregate P&L at 1 s. No engine is disabled from these same data.

The frozen representation is `xau-raw-event-regime-v1`. The next valid test is an unchanged replay on non-overlapping data.

Reproduce the diagnostic with:

```powershell
python research\v4_5_regime_normalization.py xau_ticks_7d.csv
```

See the experiment record for the causal feature definitions, fixed bins and interpretation.
