# 2026-09-24-00-btc-spot-baseline result

Dataset: `data/manifests/2026-09-24-00-btc-spot-baseline.json` (SHA-256 `f850f249f14afee110de865a65a6d7f9ba93629a82ff6104e3e0ed18f22f2ff5`).
Reproduce: `python scripts/replay_baseline.py --config configs/2026-09-24-00-btc-spot-baseline.json` after restoring the raw capture.

Evaluation at 10 bp fee + 5 bp adverse penalty per side: rule -1.25 USDT (15 trades); buy-and-hold +19.52 USDT; no trade 0.00 USDT.

Candle-only historical paper replay. Spread and actual fills are not observed; the penalty is assumed. The final 20% was not evaluated. This run cannot establish a live trading edge.
