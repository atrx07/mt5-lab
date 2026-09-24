# Experiment 00 — BTC/USDT spot paper baseline

Date: 2026-09-24

Status: **completed diagnostic; baseline lost after assumed costs; no promotion**

## Question

Can a simple, home-operable 30-minute BTC/USDT spot rule survive a realistic first-pass cost assumption? This establishes a comparator before asking Jev to filter any entries. A positive result alone will not promote this rule or authorize live trading.

## Predeclared setup

- Source: Binance public spot 30-minute `BTCUSDT` klines, the most recent 90 days ending at the last fully closed candle when captured. Freeze raw values and their SHA-256 in a manifest. Use no authenticated endpoint.
- Algorithm: [Baseline V1](../algorithms/baseline-v1.md), with exact parameters in [`configs/2026-09-24-00-btc-spot-baseline.json`](../../configs/2026-09-24-00-btc-spot-baseline.json). No Jev inference or mock Jev performance will be scored.
- Splits by chronological row index: 0–60% development, 60–80% one-time evaluation, 80–100% sealed final holdout. Reset paper cash and state at each evaluated split. Do not adjust parameters based on evaluation outcomes.
- Execution: signals from closed candles; fills at the next open, 10 bp taker fee plus 5 bp adverse price penalty per side; one long-only position with a 20% capital allocation cap. Force a costed close at a segment boundary for comparable terminal equity.
- Baselines: no trade and 20%-allocation buy-and-hold with identical fee and penalty assumptions.
- Metrics: net USDT P&L, return, max marked drawdown, trades, win rate, exposure bars, fees, cost sensitivity at 0/5/10 additional penalty bp per side, and segment comparison. Report data gaps and clock issues.

## Acceptance boundary

This is a diagnostic baseline, not a search. Run the frozen rule once on development and once on evaluation after data integrity checks. Retain any negative result. No tuning, model threshold search, or final holdout opening in this experiment. Subsequent Jev work needs its own predeclared protocol, actual Jev responses, and comparisons on the same source and fills.

## Sources reviewed

The [Binance Spot REST documentation](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market) describes public klines and the market-data host. The [Binance fee schedule](https://www.binance.com/en/fee/trading) lists a regular-user 0.100% maker/taker base rate at review time. The fee can change and may differ by account or promotion; the experiment freezes 10 bp as an assumption, not an account-specific guarantee.

## Outcome

The public capture contains 4,320 contiguous closed 30-minute candles. Its local raw SHA-256 is `f850f249f14afee110de865a65a6d7f9ba93629a82ff6104e3e0ed18f22f2ff5`, recorded in the [dataset manifest](../../data/manifests/2026-09-24-00-btc-spot-baseline.json). The Binance clock was 285 ms ahead of the host clock at capture. The first 2,592 rows were development, the next 864 were evaluated once, and the final 864 were not passed to the replay.

| Segment | Rule at 5 bp penalty | Trades / wins | Max marked drawdown | Buy-and-hold | No trade |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | -16.25 USDT | 46 / 10 | 30.12 USDT | +26.25 USDT | 0.00 USDT |
| Evaluation | -1.25 USDT | 15 / 4 | 20.66 USDT | +19.52 USDT | 0.00 USDT |

At zero additional penalty the rule lost 7.17 USDT in development and gained 1.75 USDT in evaluation. At 10 bp additional penalty, it lost 25.24 and 4.24 USDT. The trade ledger sums to each segment's reported net P&L. The rule did not beat no trade or the same-allocation buy-and-hold at the frozen 5 bp assumption. No tuning or promotion followed this result.

The evidence bundle is [results/backtests/2026-09-24-00-btc-spot-baseline/](../../results/backtests/2026-09-24-00-btc-spot-baseline/README.md). The raw capture is locally retained but Git-ignored; the manifest supplies acquisition metadata and hash. Historical OHLCV lacks bid/ask and actual fills, so this is a candle-based diagnostic, not executable profit evidence. The 20% holdout remains sealed. A later Jev entry-admission experiment must compare with this unchanged baseline on the same source and cost model.
