# Experiment 44 — MT5 tick-tape field audit

Status: **completed; quote flags useful, trade-tape fields empty**

This experiment audits `last`, `volume`, `volume_real`, and `flags` without reading P&L labels or changing strategy logic.

Expected evidence:
- field_support.csv
- tape_opportunities.csv
- cross_grid_strict_matches.csv
- cross_grid_broad_matches.csv
- cross_grid_stability.csv
- summary.json

Final20 remains sealed.


## Main result

The XAUUSD archive has no usable deal tape from this broker:

- `last`, `volume`, and `volume_real` are zero throughout both audited windows;
- LAST/VOLUME/BUY/SELL flags never occur.

BID/ASK change flags are populated and produce stable 2s/10s quote-update features. Strict matched-opportunity median Spearman is 0.940 historical and 0.956 recent.

Decision: retain exact quote-update-mask features for future representation work; do not invent trade-flow features from empty fields. No strategy change. Final20 remains sealed.
