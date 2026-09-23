# V2 live paper — 2026-09-23

## Change from V1

Replace fixed 1 oz sizing with dynamic fractional exposure:

```text
capital_usd = balance_inr / INR_PER_USD
notional_usd = capital_usd * leverage
ounces = notional_usd / XAUUSD_price
```

At ₹500, 100x synthetic leverage, and gold around 4300, exposure was roughly 0.12 oz (~0.0012 synthetic lots).

## Recovered full run

The earlier live discussion stopped to inspect the run after six completed trades, at which point the balance was **₹475.48**.

Recovery of the original local CSV later showed that the same V2 run continued:

- starting balance: ₹500
- completed trades: **14**
- balance after trade 6: **₹475.48**
- final recovered balance: **₹439.40**
- final net: **-₹60.60 (-12.12%)**
- winners: 3
- losers: 11

Notable winners in the recovered log include approximately **+₹15.16**, **+₹2.82**, and **+₹9.69**.

The exact recovered CSV is [`results/paper_trades_v2.csv`](../../../results/paper_trades_v2.csv).

## Finding

Dynamic sizing stopped the instant account explosion, but the strategy still over-traded badly. The longer recovered run makes the problem clearer than the original six-trade checkpoint: repeated spread payment plus short-horizon momentum reversals steadily eroded the account.

## Related algorithm

[V2 algorithm](../../algorithms/v2.md)
