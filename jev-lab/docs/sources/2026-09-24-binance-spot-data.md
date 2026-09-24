# Binance public spot data and fee assumptions

Reviewed: 2026-09-24. This is a source note for paper research; Binance is **not** selected as a live trading venue.

- Binance's [Spot REST market endpoints](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market) provide `GET /api/v3/klines` with `symbol`, `interval`, `startTime`, `endTime`, and up to 1,000 rows per request. Times are Unix milliseconds. The [REST overview](https://developers.binance.com/en/docs/products/spot/rest-api) directs public market-data reads to `https://data-api.binance.vision`.
- Candles include OHLC, base and quote volume, trade count, and taker-buy volume. They do **not** give the historical bid/ask spread at each proposed fill. A candle-only backtest must disclose its synthetic execution penalty and cannot prove live fill quality.
- The [published trading fee table](https://www.binance.com/en/fee/trading) listed 0.100% maker and taker for a regular spot user at review time. Promotions, discounts, account tier and region may change an actual rate. First-pass paper replay freezes 10 bp per side plus an additional adverse-fill assumption; it does not assume a fee discount.

Read-only public data is used to build a local baseline. An exchange account, API key, regional eligibility check, symbol filters, and actual account commission verification are later live-milestone work.
