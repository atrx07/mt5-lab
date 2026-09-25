# Experiment 43 — Candidate H flow-confirmed ghost exit

Status: **completed diagnostic; not promoted; exit mechanism retained**

Candidate H preserves Candidate D's entry path through Candidate G-style ghost occupancy, but the PRIMARY real exit now requires:
- +1R MFE,
- at least 1R giveback,
- two consecutive 5-second checks where both immediate raw price movement and raw event pressure oppose the trade.

Expected evidence:
- candidate_h_config.json
- summary.json
- entry_path_parity.csv
- canonical_segment_comparison.csv
- recent_split_comparison.csv
- random_real_windows.csv
- cost_stress.csv
- primary_flow_exit_events.csv
- ghost_release_events.csv

Known data are diagnostic only. Final20 remains sealed.


## Main result

| Grid / window | Candidate D | Candidate H | Delta |
| --- | ---: | ---: | ---: |
| canonical first80 500 ms | **+₹1,430.31** | +₹1,287.09 | -₹143.22 |
| canonical first80 1 s | **+₹385.25** | +₹360.79 | -₹24.46 |
| recent24h 500 ms | -₹223.27 | **-₹208.47** | +₹14.80 |
| recent24h 1 s | -₹135.91 | **-₹128.63** | +₹7.28 |

Random four-hour mean improved on both grids:

- 500 ms: -₹6.26 → -₹3.36;
- 1 s: -₹8.25 → -₹7.21.

Positive-window fraction improved to 35.0% / 30.0%.

Candidate H preserved Candidate D entry-path parity, improved drawdown and recent/random robustness, and retained far more historical upside than Candidate G. It still did not beat Candidate D canonical P&L or turn variable-window mean expectancy positive.

Decision: do not promote; retain the mechanism for the next exit iteration. Final20 remains sealed.
