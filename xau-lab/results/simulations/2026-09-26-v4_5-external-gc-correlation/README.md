# Experiment 45 — external GC futures correlation bridge

Status: **pre-run evidence bundle; frozen before external-data evaluation**

This experiment fetches public Yahoo Finance 5-minute `GC=F` bars as an aggregated COMEX Gold futures proxy and compares them with the already-known MT5 XAUUSD quote history.

It does **not** treat Yahoo bars as trade tape, does not use P&L labels, and does not open final20.

Expected evidence:
- external_source_manifest.json
- lag_scan.csv
- alignment_summary.csv
- summary.json
