# Experiment 37 — Candidate E microstate confirmation

Status: **completed known-data diagnostic; Candidate E rejected unchanged**

Candidate E kept Candidate D intact except for one frozen PRIMARY-only raw-event rule:

`HOLD this sampled PRIMARY quote iff dir_mid_move2 < 0 AND dir_event_imb2 < 0`.

The gate did not mutate cooldowns and did not fall through to another engine. No P&L-selected threshold, feature search or model fitting was performed.

## Main comparison

| Grid / window | Candidate D | Candidate E | Delta |
| --- | ---: | ---: | ---: |
| canonical first80 500 ms | **+₹1,430.31** | +₹1,163.47 | -₹266.84 |
| canonical first80 1 s | **+₹385.25** | +₹374.58 | -₹10.67 |
| recent24h whole 500 ms | -₹223.27 | **-₹216.77** | +₹6.50 |
| recent24h whole 1 s | -₹135.91 | **-₹94.08** | +₹41.83 |

The recent 1 s evaluation split improved from -₹52.31 to -₹2.29, but the already-known recent snapshot cannot promote the candidate and neither recent whole-window result became profitable.

## Random real windows

Forty deterministic contiguous four-hour windows were run per grid.

- 500 ms mean: D -₹6.26, E -₹6.48; positive-window fraction 30% for both.
- 1 s mean: D -₹8.25, E -₹8.96; positive-window fraction 27.5% for both.
- Candidate E therefore did not restore positive variable-window expectancy.

## Cost stress

Candidate E stayed below Candidate D on historical first80 at every tested $0.00/$0.05/$0.10/$0.20 per-side slippage level. Its recent relative improvement persisted but both recent grids stayed negative.

## Decision

**Reject Candidate E unchanged. Candidate D remains the V4.5 leader.**

Do not tune this rule on the same known windows. Experiment 36's `xau-microstate-v1` remains a feature foundation; this experiment rejects only this specific PRIMARY joint-contradiction use.

Final20 was not opened.

Machine evidence:

- `candidate_e_config.json`
- `summary.json`
- `canonical_segment_comparison.csv`
- `recent_split_comparison.csv`
- `random_real_windows.csv`
- `cost_stress.csv`
- `primary_veto_events.csv`
