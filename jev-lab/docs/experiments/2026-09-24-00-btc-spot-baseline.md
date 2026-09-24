# Experiment 00 — BTC/USDT spot paper baseline

Date: 2026-09-24

Status: **protocol frozen before data acquisition or outcome inspection**

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

Pending capture and replay. Record results under `results/backtests/2026-09-24-00-btc-spot-baseline/` and update this section without changing the predeclared protocol.
