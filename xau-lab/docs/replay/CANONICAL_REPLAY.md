# Canonical replay harness

Status: **required source of truth for all new V4.x research**

The project previously accumulated several one-off replay scripts. Those scripts differed subtly in sampling, raw-flow construction, session resets and aggregation, which created recurring parity disputes even when the underlying strategy had not changed.

That is now intentionally stopped.

## Rule

Every new candidate must be evaluated through:

`scripts/canonical_replay.py`

Before the candidate result is accepted, the harness automatically replays the locked V4.4 baseline on the **same feature build** and compares it against:

`results/regression/canonical_v4_4_reference.json`

If the baseline differs beyond the stored tolerance, the run raises **CANONICAL BASELINE DRIFT** and the candidate result is invalid.

A candidate is therefore never compared against a number produced by a different resampler, feature builder or accounting function.

## Immutable data contract

The harness refuses a dataset whose SHA-256 differs from:

`007e7ab10cc16519b544003dbe81521f46cf868bf267780932638d1e8cec86e5`

Research remains limited to the original first 1,869,979 raw rows.

Frozen raw boundaries:

`[0, 934989, 1168737, 1402484, 1636231, 1869979]`

The final 20% holdout is not read by this harness.

## Canonical preprocessing

- timestamps parsed as UTC with mixed-format support;
- stable timestamp sort;
- raw quote gap >5 s starts a new raw session;
- sample buckets are floored to the requested 500 ms or 1 s interval;
- the last raw quote in each session/bucket pair is retained;
- empty buckets are not synthesized;
- a sampled quote gap >5 s resets all time-dependent state;
- raw quote counts and up/down events feed quote-rate and imbalance features;
- all momentum/range/efficiency/channel features are built once and reused by baseline and candidate.

## Canonical accounting

Each of the five chronological research segments starts from ₹500.

The five segment return factors are then compounded in chronological order.

Opportunity capture always uses the same first-80% constrained ceiling: **₹7,482.60**.

## V4.4 regression oracle

The reproducible canonical V4.4 reference is:

| Sampling | Compounded P&L | Capture | Trades |
| --- | ---: | ---: | ---: |
| 500 ms | +₹1,097.66 | 14.6695% | 148 |
| 1 s | +₹333.27 | 4.4539% | 145 |

These numbers are **not a strategy downgrade**. V4.4's locked parameters are unchanged. They are the regression values produced by the newly frozen, reproducible replay pipeline.

The earlier V4.4 lock record (16.36% at 500 ms / 11.54% at 1 s) is preserved as historical evidence from the older research pipeline, but it is not used as the future parity oracle because that pipeline could not be reproduced consistently.

## Candidate runs

Example:

```powershell
python scripts\canonical_replay.py data\raw\xau_ticks_7d.csv --interval 500ms --strategy v4_5_b
python scripts\canonical_replay.py data\raw\xau_ticks_7d.csv --interval 1s --strategy v4_5_b
```

For any non-baseline strategy, the harness automatically:

1. builds one feature set;
2. runs V4.4;
3. asserts it against the golden regression file;
4. runs the candidate on the exact same arrays;
5. reports the candidate delta versus V4.4.

The diagnostic `--no-baseline-assert` escape hatch must never be used for promotion evidence.

## Change control

If preprocessing or accounting ever genuinely needs to change, do **not** silently replace the golden file.

Instead:

1. create a new replay schema version;
2. document why the change is necessary;
3. run old and new schemas side-by-side;
4. re-baseline every locked model under the new schema;
5. only then make the new schema canonical.

That makes parity a test, not a recurring research task.


## Runtime portability

Canonical timestamp conversion must explicitly normalize datetime arrays to nanosecond resolution before converting them to epoch seconds.

This preserves identical replay timing across supported pandas runtimes, including pandas 3 where parsed datetime storage may use microsecond resolution internally. This is an implementation portability rule, not a replay-schema change. The V4.4 golden regression oracle must still reproduce exactly after any runtime or dependency change.
