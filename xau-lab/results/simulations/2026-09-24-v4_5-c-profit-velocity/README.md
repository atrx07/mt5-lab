# V4.5-C profit-velocity lifecycle search — results

Date: 2026-09-24

Status: **completed; no V4.5-C promotion. Candidate B remains the V4.5 research leader.**

## Canonical gates

The successful full run used the canonical seven-day dataset:

- raw SHA-256: `007e7ab10cc16519b544003dbe81521f46cf868bf267780932638d1e8cec86e5`;
- research rows: 1,869,979;
- final 20% holdout: **not evaluated**.

Before the lifecycle search ran, all required parity gates passed:

- V4.4 500 ms canonical parity: **PASS**;
- Candidate B 500 ms instrumentation parity: **PASS**;
- V4.4 1 s canonical parity: **PASS**;
- Candidate B 1 s instrumentation parity: **PASS**.

## Search

Phase C1 tested 48 BURST lifecycle combinations over the 0-40% seed region:

- max hold: 120 / 180 s;
- trail trigger: $5.50 / $6.50 / $7.50;
- trail give-back: $2.00 / $2.50;
- raw-flow continuation: off / on;
- flow-decay early exit: off / on.

Candidate B admission, PRIMARY, SECONDARY, MICRO, 3% planned risk, $4 emergency stop and the shared position slot were unchanged.

## Result

All **48 of 48** lifecycle variants produced exactly the same seed metrics as Candidate B at both 500 ms and 1 s.

Every seed score was exactly `1.0000`.

The top eight therefore entered 40-80% evaluation as ties; all eight again reproduced Candidate B exactly. The top three full first-80% summaries were also exact Candidate B reproductions.

There is therefore **no distinct Candidate C from Phase C1**.

### Full first-80% result

| Metric | 500 ms | 1 s |
| --- | ---: | ---: |
| Compounded P&L | +₹1,299.37 | +₹365.25 |
| Capture | 17.3652% | 4.8814% |
| Trades | 163 | 156 |
| Wins | 79 | 70 |
| Median segment PF | 1.3614 | 1.3823 |
| Worst segment DD | ₹218.68 | ₹172.38 |
| Exposure | 15.823 h | 17.248 h |
| P&L / exposure hour | ₹58.36 | ₹18.06 |
| Mean hold | 349.47 s | 398.03 s |
| P&L / trade | ₹5.67 | ₹2.00 |

### BURST attribution

| Metric | 500 ms | 1 s |
| --- | ---: | ---: |
| BURST P&L | +₹58.40 | +₹10.44 |
| BURST trades | 17 | 12 |
| BURST exposure | 0.251 h | 0.155 h |
| BURST P&L / exposure hour | ₹232.98 | ₹67.49 |

The 50-60% research segment remains negative:

- 500 ms: **-₹13.58**;
- 1 s: **-₹45.95**.

## Interpretation

The tested lifecycle knobs are effectively inactive on the observed Candidate B BURST trade paths.

Changing max hold, trail trigger, trail give-back, conditional flow extension and the tested decay exit never changed a completed trade on the seed region. The later evaluation/full replays confirm that the selected tied variants also do not alter Candidate B.

This strongly suggests that earlier BURST exit conditions and/or the entry path dominate before these lifecycle controls can affect realized trades. Phase C1 therefore does not justify more grid search around these same controls.

## Runtime portability correction

The first automated execution exposed a pandas-version portability bug in the canonical timestamp conversion: pandas 3 may store parsed datetimes internally at microsecond resolution, while the old code assumed nanoseconds before dividing integer timestamps by `1e9`.

`research/canonical_replay.py` was corrected to explicitly normalize datetime arrays to `datetime64[ns]` before epoch conversion.

This is a runtime portability fix, not a replay-schema change. After the fix, the stored V4.4 golden oracle reproduced exactly at both intervals and Candidate B instrumentation parity passed.

## Decision

- **Do not promote or lock V4.5-C from Phase C1.**
- Candidate B remains the V4.5 research leader.
- Keep the final 20% holdout sealed.
- Do not spend more search budget on max-hold/trail/flow-decay ranges until the active BURST exit path is measured directly.

## Next research implication

Before another optimization pass, instrument BURST at trade level with at least:

- exact exit reason;
- entry/exit timestamps and side;
- MFE/MAE and time-to-MFE;
- state at exit;
- whether 30 s momentum zero-cross, stagnation, TP, stop, trail or max-hold actually fired;
- post-exit favorable excursion over short windows;
- matching/missing opportunity identity between 500 ms and 1 s.

The next candidate should be designed from those diagnostics rather than from another blind lifecycle grid.

## Files

- `seed_search.csv` — all 48 seed variants;
- `evaluation_shortlist.csv` — top-eight chronological evaluation;
- `full_shortlist.csv` — top-three first-80% summaries;
- `run_metadata.json` — canonical baseline, segment, profit-velocity and BURST attribution metadata.
