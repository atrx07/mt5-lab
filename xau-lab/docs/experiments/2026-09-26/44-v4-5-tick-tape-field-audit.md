# 44 — V4.5 MT5 tick-tape field audit

Date: 2026-09-26
Status: **completed representation audit; quote-flag features retained, trade-tape fields unavailable**

Experiments 42-43 exposed a remaining information question: the current causal feature sets use bid/ask quote paths but ignore the archived MT5 `last`, `volume`, `volume_real`, and `flags` fields.

Experiment 44 audits those fields without P&L labels or strategy changes.

Frozen plan:
`docs/plans/V4_5_TICK_TAPE_FIELD_AUDIT.md`

Implementation:
`research/v4_5_tick_tape_field_audit.py`

Evidence:
`results/simulations/2026-09-26-v4_5-tick-tape-field-audit/`

Final20 remains sealed.


## Result

The archived MT5 feed contains the fields, but this broker's XAUUSD history does **not** contain deal-tape information in them.

Historical first80 raw rows: 1,869,979.

- nonzero `last`: 0%;
- nonzero `volume`: 0%;
- nonzero `volume_real`: 0%;
- LAST flag: 0 rows;
- VOLUME flag: 0 rows;
- BUY flag: 0 rows;
- SELL flag: 0 rows.

Recent24h (476,535 rows) shows the same: all deal/trade fields and trade flags are zero.

The useful part is the quote-change mask:

- historical BID-change flag: 78.96%; ASK-change: 78.20%;
- recent BID-change: 79.58%; ASK-change: 79.43%.

Flag-derived 2s/10s quote-update features were very sampling-stable at matched opportunities: strict cross-grid median Spearman was **0.940 historical / 0.956 recent**.

## Interpretation

The current broker archive cannot provide true aggressor-side trade flow, last-deal movement or traded volume. Those fields are present in the CSV schema because MT5 exposes them, but the XAUUSD feed leaves them empty.

This explains an important ceiling in the current "flow" vocabulary: current microstructure models infer pressure from quote changes; they do not observe actual buyer/seller-initiated deals.

The exact BID/ASK change flags are still useful causal information and are more authoritative than reconstructing update type only from value differences. They may be retained in a future microstate representation, especially at both 2s and 10s horizons.

## Decision

- true LAST/volume/buy/sell tape features: **unavailable on this broker feed; do not fabricate them**;
- BID/ASK update-mask features: **retained as causal representation candidates**;
- no strategy rule promoted;
- final20 remains sealed.

A materially better entry discriminator may require either genuinely new price behavior on fresh snapshots or a data source/broker that exposes actual deal/trade-flow fields, rather than additional model complexity on the same quote-only history.
