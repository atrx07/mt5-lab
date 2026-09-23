# V2 live paper — 2026-09-23

## Change from V1

Replace fixed 1 oz sizing with dynamic fractional exposure:

```text
capital_usd = balance_inr / INR_PER_USD
notional_usd = capital_usd * leverage
ounces = notional_usd / XAUUSD_price
```

At ₹500, 100x synthetic leverage, and gold around 4300, exposure was roughly 0.12 oz (~0.0012 synthetic lots).

## Recorded run

- starting balance: ₹500
- final balance: **₹475.48**
- trades: 6
- net: **-₹24.52 (-4.9%)**
- only one material winner: about +₹15.16
- total entry spread handicap was about ₹21.34

## Finding

Dynamic sizing stopped the instant account explosion, but the strategy over-traded. Transaction friction was of the same order as the whole drawdown.

## Related algorithm

[V2 algorithm](../../algorithms/v2.md)
