# Experiment 46 — same-timeline external GC overlay simulation

Status: **completed full simulation; Candidate I rejected**

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


## Main result

The external data was fetched only for the archived MT5 timeline and consumed causally from the last fully completed GC five-minute bar.

| Grid / window | D | H | GC-entry | GC-exit | Candidate I |
| --- | ---: | ---: | ---: | ---: | ---: |
| canonical 500 ms | **+₹1,430.31** | +₹1,287.09 | +₹1,044.62 | **+₹1,430.31** | +₹1,044.62 |
| canonical 1 s | +₹385.25 | +₹360.79 | +₹344.61 | **+₹386.61** | +₹345.91 |
| recent 500 ms | -₹223.27 | **-₹208.47** | -₹233.16 | -₹223.27 | -₹233.16 |
| recent 1 s | -₹135.91 | **-₹128.63** | -₹137.53 | -₹135.91 | -₹137.53 |

Random four-hour mean P&L:

- 500 ms: D -₹6.26, H -₹3.36, Candidate I **-₹14.73**.
- 1 s: D -₹8.25, H -₹7.21, Candidate I **-₹15.09**.

The five-minute/fifteen-minute GC entry-conflict guard removed useful trades, while requiring the same coarse GC reversal for Candidate-H exits suppressed nearly every useful H exit.

Decision: reject Candidate I and this coarse external overlay. Retain the GC bridge itself; higher-resolution GC trades/depth or sub-five-minute data are required for individual trade decisions. Candidate D remains leader, Candidate H remains retained exit branch, final20 stays sealed.
