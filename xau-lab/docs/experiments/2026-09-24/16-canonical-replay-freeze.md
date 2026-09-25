# 16 — Canonical replay freeze

Date: 2026-09-24

## Problem

V4.3, V4.4 and early V4.5 research used several temporary replay implementations.

Small differences in sampling, feature construction, continuity resets and aggregation caused the same locked strategy to produce different baseline numbers in different experiments.

That made every new candidate waste time re-investigating parity.

## Permanent fix

A single canonical replay harness is now frozen:

[`research/canonical_replay.py`](../../../research/canonical_replay.py)

Golden V4.4 regression oracle:

[`results/regression/canonical_v4_4_reference.json`](../../../results/regression/canonical_v4_4_reference.json)

Full contract:

[`docs/replay/CANONICAL_REPLAY.md`](../../replay/CANONICAL_REPLAY.md)

## Enforcement

Every non-baseline candidate run automatically:

1. verifies the source dataset SHA-256;
2. uses the frozen first-80% raw-row boundaries;
3. builds one feature set;
4. runs locked V4.4 on those same arrays;
5. asserts V4.4 against the golden regression values;
6. aborts on any drift;
7. only then runs the candidate and reports deltas.

The diagnostic no-assert switch is explicitly non-promotional.

## Canonical V4.4 regression values

- 500 ms: +₹1,097.66, 14.6695% capture, 148 trades.
- 1 s: +₹333.27, 4.4539% capture, 145 trades.

These are a measurement re-baseline under the reproducible pipeline. The V4.4 strategy itself was not changed.

Earlier V4.4 historical lock outputs remain preserved, but future candidate comparisons use the canonical regression oracle only.

## First verified candidate

V4.5 Candidate B passed the parity gate at both intervals:

- 500 ms: +₹1,299.37, 17.3652% capture, 163 trades.
- 1 s: +₹365.25, 4.8814% capture, 156 trades.

## Change control

If replay semantics ever need to change, the project must create a new replay schema version and re-baseline locked strategies. The golden file must never be silently edited to make a failing run pass.

This converts parity from a recurring research problem into a regression test.
