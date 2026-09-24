# TypeSafe Jev API contract

Reviewed: 2026-09-24. This is an external-source note, not a trading experiment.

- The [official API reference](https://docs.typesafe.ai/api) defines `POST https://api.typesafe.ai/v1/systemone` with `state`, `model`, and named typed `questions`. A Choice answer contains a selected option, an option probability map, confidence, model ID, and token usage.
- The [model reference](https://docs.typesafe.ai/models) lists `jev-1.13.0` as the current versioned ID and explains that `jev-latest` can move to a different version. Research requests pin the versioned ID.
- The [model limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) state that Jev struggles with numerical precision. Market arithmetic and risk controls therefore stay in deterministic code.
- The [confidence reference](https://docs.typesafe.ai/confidence) defines confidence from the option-probability distribution. It is not a measured probability of profitable BTC/USDT trading.

`src/jev_lab/client.py` implements this narrow Choice transport with a caller-controlled deadline and no automatic retry. The CLI defaults to local validation and requires an explicit `--send` plus an API key for one paid request. Recheck the official contract and model availability before any real API experiment.
