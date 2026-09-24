# Experiment 01 — prepare Jev entry shadow requests

Date: 2026-09-24

Status: **development export complete; no model key or inference yet**

## Question

Can the exact baseline V1 entry candidates be represented as compact, timestamp-causal, reproducible Jev Choice requests without changing any trades? This phase tests input construction and logging only. It cannot test Jev's trading value.

## Predeclared contract

- Source: the unchanged [Experiment 00 dataset and algorithm](2026-09-24-00-btc-spot-baseline.md), identified by raw SHA-256 `f850f249f14afee110de865a65a6d7f9ba93629a82ff6104e3e0ed18f22f2ff5`.
- Scope: generate candidates only from the first 2,592 development candles. Reserve rows 2,592–3,455 for a later fixed-policy evaluation and keep rows 3,456–4,319 sealed.
- Frozen [shadow config](../../configs/2026-09-24-01-jev-entry-shadow.json): model `jev-1.13.0`, state schema, question and two options (`take`, `skip`). The model will not be called in this phase because no key is configured.
- State at each candidate: symbol, source venue, candle timestamp and decision-available timestamp, close, prior 20-bar high, 48-bar average, past 3/12-bar returns, current range, current volume versus prior 20 bars, and estimated round-trip friction. All numbers are calculated locally from candles closed no later than the signal candle. No future price, trade outcome, or holdout value is included.
- Record one immutable request hash and JSON payload per candidate in ignored `data/derived/`. Publish only the candidate count, SHA-256 of the generated JSONL, source hash, and a matching result bundle. Confirm that baseline P&L and trade count remain exactly equal to Experiment 00 at the frozen 5 bp penalty.

## Acceptance boundary

Only causal request construction and baseline parity can pass here. No `take` threshold or Jev outcome is selected, no evaluation rows are inspected, and no candidate is promoted. A later actual-model experiment will need a key, a response cache, latency and cost logging, and a frozen comparison against unchanged baseline V1.

## Outcome

The [result bundle](../../results/benchmarks/2026-09-24-01-jev-entry-shadow/README.md) records 46 baseline entry candidates and 46 full Choice request payloads in the local, ignored JSONL. Its SHA-256 is `b21b21da9a5ecee870d2271797241a7019b86c0272c25636633f112c3c7a0e0a`. The full development rule summary matched Experiment 00, including 46 trades and −16.25 USDT net P&L at the frozen 5 bp penalty. No model calls occurred; evaluation and final holdout rows were not passed to bar parsing, feature construction, or replay. The request's decision timestamp denotes theoretical candle close, not measured feed availability.

**Decision:** request construction passed its narrow acceptance check. The Jev candidate remains untested and unpromoted. A future model-response experiment needs a key and a separately frozen policy before evaluation.
