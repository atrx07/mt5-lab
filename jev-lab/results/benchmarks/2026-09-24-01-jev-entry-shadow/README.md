# 2026-09-24-01-jev-entry-shadow result

Reproduce from the local raw capture: `python scripts/export_jev_shadow.py`. The capture must match SHA-256 `f850f249f14afee110de865a65a6d7f9ba93629a82ff6104e3e0ed18f22f2ff5`. This command preserves an existing export; remove or archive it intentionally before rerunning.

Development only: 46 baseline entry candidates, one local Choice request each. The ignored JSONL has SHA-256 `b21b21da9a5ecee870d2271797241a7019b86c0272c25636633f112c3c7a0e0a`. The entire frozen development rule summary matched Experiment 00, including -16.25 USDT net P&L and 46 trades.

No Jev API call, response, trade decision, or live order was made. Evaluation and final holdout rows were not passed to bar parsing, feature construction, or replay. The decision timestamp marks theoretical candle close, not measured feed availability. This validates request construction only and supplies no evidence of Jev trading value.
