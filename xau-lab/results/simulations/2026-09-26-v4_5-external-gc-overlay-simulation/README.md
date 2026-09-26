# Experiment 46 — same-timeline external GC overlay simulation

Status: **pre-run evidence bundle; frozen before outcome evaluation**

This experiment uses external `GC=F` data from the **same archived dates** as the MT5 replay. It never mixes current GC data into historical MT5 ticks.

Variants:
- Candidate D
- Candidate H
- GC-entry
- GC-exit
- Candidate I (combined)

Expected evidence:
- candidate_i_config.json
- external_source_manifest.json
- gc_features_5m_used.csv
- entry_path_parity.csv
- canonical_segment_comparison.csv
- recent_split_comparison.csv
- random_real_windows.csv
- cost_stress.csv
- external_entry_skip_events.csv
- external_confirmed_exit_events.csv
- ghost_release_events.csv
- summary.json

Final20 remains sealed.
