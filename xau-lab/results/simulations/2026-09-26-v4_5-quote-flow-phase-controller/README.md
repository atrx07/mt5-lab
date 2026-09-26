# Experiment 47 — MT5-native quote-flow phase controller

Status: **completed known-data diagnostic; Candidate J frozen for fresh validation, not promoted**

Variants:
- Candidate D
- Candidate H
- Quote-entry
- Quote-exit
- Candidate J

All new information is MT5-native and replayable from the archived broker feed. No external market data is used.

Expected evidence:
- candidate_j_config.json
- baseline_shadow_parity.csv
- canonical_segment_comparison.csv
- recent_split_comparison.csv
- random_real_windows.csv
- cost_stress.csv
- entry_phase_actions.csv
- quote_phase_exit_events.csv
- summary.json

Final20 remains sealed.


## Main result

| Grid / window | D | H | Candidate J |
| --- | ---: | ---: | ---: |
| canonical 500 ms | **+₹1,430.31** | +₹1,287.09 | +₹1,048.86 |
| canonical 1 s | **+₹385.25** | +₹360.79 | +₹273.18 |
| recent24h 500 ms | -₹223.27 | -₹208.47 | **-₹164.54** |
| recent24h 1 s | -₹135.91 | -₹128.63 | **-₹71.00** |
| random 4h mean 500 ms | -₹6.26 | -₹3.36 | **+₹3.75** |
| random 4h mean 1 s | -₹8.25 | -₹7.21 | **-₹2.82** |

Candidate J beat D in every 500 ms random window and 87.5% of 1 s random windows. Its max segment drawdown fell to ₹139.87 / ₹109.26.

Known-data canonical upside fell too much for promotion. The entry controller produced most of the improvement; the quote-phase exit did not consistently beat Candidate H.

Decision: freeze Candidate J unchanged for a genuinely fresh MT5-only snapshot. Do not tune the phase rules on these windows. Candidate D remains leader, Candidate H remains retained exit branch, final20 stays sealed.
