# 45 — V4.5 external GC futures correlation bridge

Date: 2026-09-26
Status: **completed; strong GC↔MT5 correlation confirmed after clock alignment**

This experiment tests whether public 5-minute COMEX Gold futures proxy data (`GC=F`) is sufficiently aligned with the existing MT5 XAUUSD quote history to justify a later richer external-tape integration.

It does not use P&L labels, does not change strategy logic, and keeps final20 sealed.

Frozen plan:
`docs/plans/V4_5_EXTERNAL_GC_CORRELATION.md`

Implementation:
`research/v4_5_external_gc_correlation.py`

Evidence:
`results/simulations/2026-09-26-v4_5-external-gc-correlation/`


## Result

Public Yahoo Finance 5-minute `GC=F` bars were fetched for the already-known MT5 research windows and compared with 5-minute MT5 mid returns.

The raw timestamps initially looked uncorrelated because the MT5 archive is approximately three hours ahead of UTC market time. A lag scan from -240 to +240 minutes found the same best alignment in both windows:

**shift GC +180 minutes to match MT5 reported timestamps**.

That is a timestamp-label alignment result, not predictive market lead.

### Historical first80

- matched 5-minute returns at best lag: 1,050;
- Pearson return correlation: **0.9921**;
- Spearman return correlation: **0.9890**;
- directional agreement: **95.05%**;
- price-level Pearson: **0.99910**;
- median GC-minus-MT5 basis: **+$38.34/oz**;
- basis standard deviation: **$1.30**.

Applying the independently observed recent MT5-vs-host clock correction (-10,797.91 s) instead of searching the lag still produced Pearson **0.9882**, Spearman **0.9832**, and 94.21% directional agreement.

### Recent24h

- matched 5-minute returns at best lag: 264;
- Pearson return correlation: **0.9915**;
- Spearman return correlation: **0.9911**;
- directional agreement: **95.83%**;
- price-level Pearson: **0.99898**;
- median GC-minus-MT5 basis: **+$34.83/oz**;
- basis standard deviation: **$0.67**.

Applying the recorded -10,797.91 s MT5 clock correction directly produced Pearson **0.9859**, Spearman **0.9859**, and 94.72% directional agreement.

## Interpretation

The external COMEX Gold futures proxy and the broker's XAUUSD CFD are extremely tightly linked in 5-minute return direction once the MT5 timestamp offset is corrected.

This validates the cross-market architecture concept:

- external GC data can be used as a signal/price-discovery sensor;
- MT5 can remain the execution venue and executable-price truth;
- the futures/spot basis must be normalized rather than comparing raw prices directly;
- the ~3-hour MT5 timestamp offset must be corrected before any sub-minute lead/lag or tape study.

The result does **not** prove that futures tape predicts MT5 at sub-second horizons. It only establishes that the two markets are aligned strongly enough to justify acquiring richer GC trades/order-book data for the same windows.

## Decision

**Proceed to richer external GC trade/depth acquisition.**

Do not create a trading rule from 5-minute `GC=F` bars. Candidate D remains leader, Candidate H remains the strongest retained exit branch, and final20 remains sealed.
