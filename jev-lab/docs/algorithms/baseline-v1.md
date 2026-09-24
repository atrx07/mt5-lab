# Baseline V1 — BTC/USDT spot breakout

Status: **frozen first paper baseline; no Jev calls or orders**. Protocol: [Experiment 00](../experiments/2026-09-24-00-btc-spot-baseline.md). Settings: [`configs/2026-09-24-00-btc-spot-baseline.json`](../../configs/2026-09-24-00-btc-spot-baseline.json).

The market is Binance public BTC/USDT spot 30-minute candles. This is a simple comparator for later Jev admission tests, not a claim that breakouts are profitable.

At each fully closed candle after 48 candles of warmup, while flat, an entry candidate exists when its close exceeds the highest high of the preceding 20 candles and exceeds the current 48-candle simple moving average of closes. Buy at the **next** candle open. While holding, exit at the next candle open if a fully closed candle ends below its current 48-candle average or if the position has been held for 48 bars. No same-candle signal and fill. No shorting, leverage, adding, or more than one position.

Use at most 20% of paper equity for an entry. Start each comparison segment from 1,000 USDT. Model a 10 bp taker fee and an additional 5 bp adverse execution penalty on **each** buy and sell. Fees are paid from proceeds/cash. At a segment boundary, liquidate any open position at the final closed price with the same sell costs and disclose that terminal assumption. Drawdown uses marked equity at each close before a potential terminal liquidation.

Compare against no trade and a 20%-allocation buy-and-hold opened at the first eligible next-bar open, both under the same cost model. The 5 bp penalty is a sensitivity assumption because historical candles contain no bid/ask; the experiment cannot establish executable spread or fill quality. The final 20% of the frozen dataset remains sealed.
