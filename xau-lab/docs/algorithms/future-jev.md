# Future Jev integration — research assessment

Status: **proposed shadow experiment; no Jev strategy or live executor**

Reviewed: 2026-09-24

## What the trending bot demonstrates

The widely shared [jarrodwatts/jev-trader](https://github.com/jarrodwatts/jev-trader) is a MON/USDC maker-order demonstration on Kuru/Monad. It sends an order-book and recent-trade snapshot to TypeSafe AI's Jev decision model, asks for `buy` or `sell`, and posts a limit order each block. The [public deployment and repository default to a mock momentum model](https://github.com/jarrodwatts/jev-trader#run); real Jev requires `MODEL=jev` and an API key. The repo reports loop latency for the **mock dry run**, not an independently verified profitable Jev strategy. Its simulated fills occur when a later trade print crosses the quote, without modeling our MT5 taker execution or XAUUSD spread/slippage.

The [model question](https://github.com/jarrodwatts/jev-trader/blob/main/src/model.ts) offers only buy and sell. `hold` occurs when the loop is late; the [trader loop](https://github.com/jarrodwatts/jev-trader/blob/main/src/trader.ts) can quote the opposite side when a position cap blocks the chosen side. Its question text describes an immediate-or-cancel market order, while the loop posts a post-only limit order. These details make its action probability and displayed P&L unsuitable as evidence for our XAUUSD entry policy.

The transferable idea is architectural: compute market state in code, ask a narrow typed question, then apply local risk and execution rules. TypeSafe's [official API](https://docs.typesafe.ai/api) accepts `state` plus typed `Choice`, `Score` or `Noul` questions; its [Python SDK](https://docs.typesafe.ai/sdk/python) fits this project's language. An answer's [confidence](https://docs.typesafe.ai/confidence) measures concentration of its own option probabilities. It is **not** a calibrated probability of profitable XAUUSD execution until tested on our data. TypeSafe also [warns](https://docs.typesafe.ai/model-jaggedness/jev-1.13) that Jev 1.13 struggles with arithmetic and numeric precision; spread, sizing, P&L and risk calculations must stay in code.

## Fit with the current lab

Our V4.4 baseline is locked; V4.5 Candidate D is provisional and recently lost on a fresh MT5 snapshot. The canonical seven-day final 20% is still sealed. Adding a remote call to every 500 ms tick would be a different execution architecture, introduce stale-decision risk, and confound the current 500 ms versus 1 s robustness problem. The broker's 0.01-lot minimum also makes the current ₹500 synthetic sizing non-executable as-is. None of these issues is solved by a fast decision API.

The first plausible use is **entry admission as a shadow meta-labeler**, called only when an existing deterministic engine proposes an entry. The primary comparison should be unchanged V4.4 versus V4.4 plus a Jev veto. A V4.5 Candidate D comparison can be diagnostic, but must not turn an unpromoted candidate into a new baseline. Jev must never create an entry on its own in this experiment.

```text
MT5 bid/ask ticks -> canonical local features -> existing entry candidate
                                               -> Jev shadow judgment + audit log
existing strategy + local risk/exits -> unchanged paper/replay result
```

The proposed question should be small and explicit, such as whether a **specified candidate direction** is more likely to persist or fail over a fixed short horizon, with an `uncertain`/`skip` option. The state should contain only information known at the decision timestamp: engine, side, spread, recent signed returns/momentum, range/efficiency, raw quote rate and imbalance, session-gap flag, and current exposure. Calculate these fields locally. Do not send future returns, opportunity labels, eventual trade outcomes, or the sealed holdout. Freeze the exact state schema, question wording, option definitions and model version before evaluation.

## Test sequence

1. **Feasibility:** obtain authorized API access and measure real end-to-end latency, timeout rate and request cost on a small, non-trading sample. The model is remote; choose a deadline shorter than the remaining freshness budget. On timeout, error, stale state or malformed response, record `NO_DECISION` and leave the baseline action unchanged in shadow mode. Never delay emergency exits for inference.
2. **Shadow capture:** on the 0–40% seed only, call a pinned Jev version at eligible entry events and save each immutable input, event timestamp, model/version, response, latency, API usage, and a stable request hash. Cache responses for replay. Report coverage and whether Jev's judgments are meaningfully variable rather than near-constant. Do not call the API using hindsight labels in the state.
3. **Offline selection:** choose at most one simple veto threshold/policy on the seed. Reuse the canonical feature arrays and V4.4 golden parity gate. Replay baseline and gated candidate with identical bid/ask fills and local exits. Include API latency as an entry delay or missed-opportunity model, plus spread/slippage stress. Keep the five chronological research segments and 500 ms/1 s views separate.
4. **Frozen evaluation:** apply the fixed model/prompt/policy once to the 40–80% evaluation segments and then to additional non-overlapping recent sessions. Compare net P&L, P&L per exposure hour, drawdown, trade count, segment behavior, 500 ms/1 s degradation, and adverse-fill sensitivity. Log vetoed trades so any change can be attributed to specific rejected entries. Do not tune against the existing Experiment 22 later segment.
5. **Promotion gate:** require a material, repeatable improvement after costs without unacceptable drawdown or latency sensitivity. Keep the canonical final 20% sealed until the user explicitly opens it as a milestone. If there is no robust gain, retain the negative experiment and leave execution unchanged.

Any later paper integration must place the remote model **outside** deterministic stops, sizing, spread caps, one-slot/risk limits and connectivity safeguards. Live broker orders remain a separate milestone under `agents.md`; this assessment authorizes no `mt5.order_send()` path.
