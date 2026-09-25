# Candidate H — path-preserving flow-confirmed profit retention

Date: 2026-09-26
Status: frozen before outcome evaluation

Candidate H keeps Candidate D entries and Candidate G ghost occupancy, but replaces the blunt PRIMARY +1R/50%-MFE ratchet with a signal-aware decay exit.

PRIMARY learned/extra exit is armed only after live MFE reaches +1R ($4). It is evaluated every 5 seconds.

A decay warning requires BOTH:
- direction-normalized 2-second raw mid movement < 0;
- direction-normalized 2-second raw event imbalance < 0.

A real exit requires:
- MFE >= +1R;
- giveback from live MFE >= 1R;
- two consecutive 5-second decay warnings.

A positive/neutral check resets confirmation. This uses only natural zero-direction boundaries and the existing $4 risk unit; no threshold search is allowed.

When the real PRIMARY exits, a capital-free ghost continues the untouched Candidate-D lifecycle and keeps the shared slot occupied until the original legacy exit. PRIMARY cooldown anchors to that ghost release, preserving Candidate-D entry-path timing.

SECONDARY, MICRO and BURST exits are unchanged.

Required diagnostic:
- exact Candidate-D entry-path parity;
- canonical first80 500ms/1s;
- recent24h whole and split;
- 40 deterministic real four-hour windows per grid;
- $0/$0.05/$0.10/$0.20 per-side slippage stress;
- exit-event ledger including MFE, giveback and raw-flow state.

Known data can reject Candidate H but cannot promote it. Final20 stays sealed.
