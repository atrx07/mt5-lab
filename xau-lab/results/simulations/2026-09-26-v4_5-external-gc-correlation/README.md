# Experiment 45 — external GC futures correlation bridge

Status: **completed; strong GC↔MT5 correlation confirmed after clock alignment**

This experiment fetches public Yahoo Finance 5-minute `GC=F` bars as an aggregated COMEX Gold futures proxy and compares them with the already-known MT5 XAUUSD quote history.

It does **not** treat Yahoo bars as trade tape, does not use P&L labels, and does not open final20.

Expected evidence:
- external_source_manifest.json
- lag_scan.csv
- alignment_summary.csv
- summary.json


## Main result

After correcting the approximately three-hour MT5 timestamp offset, 5-minute COMEX Gold futures proxy returns and MT5 XAUUSD returns are extremely closely aligned.

| Window | Best lag | Pearson returns | Spearman returns | Direction agreement |
| --- | ---: | ---: | ---: | ---: |
| historical first80 | +180 min GC shift | 0.9921 | 0.9890 | 95.05% |
| recent24h | +180 min GC shift | 0.9915 | 0.9911 | 95.83% |

The median GC-minus-MT5 price basis was +$38.34/oz historically and +$34.83/oz on recent24h, with low within-window basis dispersion.

Decision: cross-market correlation is strong enough to justify acquiring real GC trades/depth next. These aggregated bars are not trade tape and no strategy rule is promoted. Final20 remains sealed.
