# Experiment 45 — external GC futures correlation bridge

Date: 2026-09-26
Status: frozen before external-data evaluation

## Objective

Before building any cross-market signal, establish whether centralized COMEX Gold futures price discovery is sufficiently aligned with the MT5 XAUUSD quote stream already archived in xau-lab.

This experiment is representation/alignment only. It does not use P&L labels and does not change Candidate D/H.

## External source

Fetch public Yahoo Finance chart data for continuous COMEX Gold futures proxy `GC=F` at 5-minute resolution for the already-known date ranges only.

Why 5-minute bars:
- they are available far enough back to cover the seven-day archive;
- they are sufficient to test broad cross-market return correlation and timestamp alignment;
- this is only the first bridge test, not a substitute for trade-level CME tape/depth.

Do not call the Yahoo data "trade tape." It is an aggregated futures price proxy.

## MT5 ranges

Use:
- canonical seven-day **first80 research rows only**;
- separate recent24h snapshot.

The final20 historical holdout remains sealed.

## Alignment tests

For each window:

1. aggregate MT5 mid to 5-minute last observation;
2. compute 5-minute log returns for MT5 and GC;
3. evaluate raw timestamp alignment;
4. scan GC-vs-MT5 return correlation over lags from -240 to +240 minutes in 5-minute increments;
5. report the best lag by absolute Pearson return correlation;
6. report Spearman correlation and directional agreement at that lag;
7. report matched-row count;
8. report median and dispersion of price basis after best-lag alignment.

Also apply the recent snapshot's already-recorded MT5-vs-host clock offset (~10,798 s) as a separate derived alignment check without rewriting archived timestamps.

## Interpretation discipline

- Price-level correlation is secondary; return correlation is primary.
- A useful result means external GC direction/timing broadly tracks MT5 XAUUSD enough to justify acquiring richer GC trade/depth data later.
- No trading rule is selected from this experiment.
- No same-data threshold tuning.
- No final20 access.

## Evidence

Experiment:
`docs/experiments/2026-09-26/45-v4-5-external-gc-correlation.md`

Implementation:
`research/v4_5_external_gc_correlation.py`

Evidence:
`results/simulations/2026-09-26-v4_5-external-gc-correlation/`
