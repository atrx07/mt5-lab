# V4.5 second simulation — additive BURST candidate B

Date: 2026-09-24

Status: **promising research candidate; not locked as V4.5.**

## Why this pass exists

V4.5-A tightened MICRO admission and reduced useful trades and capture. Candidate B deliberately learns the opposite lesson:

- leave locked V4.4 PRIMARY / SECONDARY / MICRO untouched;
- add a fourth independent BURST engine;
- BURST only gets the shared slot after the three existing engines decline the sample.

The final 20% holdout remains unopened.

## Permanent parity gate

Candidate B has now been rerun through `research/canonical_replay.py`.

The harness first rebuilt V4.4 on the exact same feature arrays and successfully matched the frozen V4.4 regression oracle before Candidate B was evaluated.

That removes the recurring parity ambiguity for this and future V4.5 tests.

Schema: `xau-canonical-replay-v1`

## Candidate B

BURST entry requirements:

- existing PRIMARY / SECONDARY / MICRO must all decline;
- BURST cooldown: 60 s;
- |10 s momentum| >= $0.60;
- |30 s momentum| >= $1.50;
- |60 s momentum| >= $2.00;
- 120 s momentum must agree in direction;
- ER60 >= 0.12;
- 10s/30s raw quote-rate ratio >= 1.20;
- directional 10 s raw tick imbalance >= 0.20;
- 60 s range >= $4;
- spread <= 18% of 60 s range;
- BURST absolute spread cap: $0.28.

BURST exit:

- $4 emergency stop;
- $12 take profit;
- max hold 120 s;
- 30 s momentum zero-cross failure exit;
- stagnation after 60 s if peak favorable move < $0.80;
- trail after +$5.50 with $2 give-back.

One shared position slot remains in force.

## Canonical comparison

| Metric | Canonical V4.4 | V4.5-B |
| --- | ---: | ---: |
| 500 ms compounded P&L | +₹1,097.66 | **+₹1,299.37** |
| 500 ms capture | 14.6695% | **17.3652%** |
| 500 ms trades | 148 | **163** |
| 500 ms median segment PF | 1.284 | **1.361** |
| 500 ms worst segment DD | ₹229.31 | **₹218.68** |
| 1 s compounded P&L | +₹333.27 | **+₹365.25** |
| 1 s capture | 4.4539% | **4.8814%** |
| 1 s trades | 145 | **156** |
| 1 s median segment PF | 1.367 | **1.382** |
| 1 s worst segment DD | **₹171.34** | ₹172.38 |

Relative improvement:

- +₹201.71 and +2.696 capture points at 500 ms;
- +15 completed trades at 500 ms;
- +₹31.98 and +0.427 capture points at 1 s;
- +11 completed trades at 1 s;
- PF improves on both grids;
- 500 ms drawdown improves;
- 1 s worst segment drawdown increases by ~₹1.04.

This is the first V4.5 candidate in the current research line that increases **trades, capture and P&L on both canonical sampling grids**.

Canonical machine-readable outputs:

- [500 ms](canonical_500ms.json)
- [1 s](canonical_1s.json)

## Chronological weakness

The 50–60% region remains negative under both V4.4 and Candidate B.

Candidate B is therefore not treated as a solved or universally robust system.

## Cost diagnostic

The earlier cost probes showed that BURST can become a liability under sufficiently hostile spread/slippage assumptions.

The next V4.5 pass should preserve the additive BURST opportunity set while improving its cost-aware admission or lifecycle management.

## Decision

**Keep Candidate B as the V4.5 research leader, but do not lock V4.5 yet.**

No `paper_challenge_v4_5.py` is created from this candidate.
