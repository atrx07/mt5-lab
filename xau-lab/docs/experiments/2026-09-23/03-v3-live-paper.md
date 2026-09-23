# V3 live paper — 2026-09-23

## Main changes

- 5 s and 15 s momentum must agree;
- 2 s breakout confirmation;
- max loss per trade reduced to ₹25;
- profit lock activates at ₹8;
- 20 s cooldown;
- reversal requires persistence across multiple samples.

## Exact recorded CSV result

The original trade log is committed at [`results/paper_trades_v3.csv`](../../../results/paper_trades_v3.csv).

| Trade | Side | P&L |
| --- | --- | ---: |
| 1 | BUY | -₹0.58 |
| 2 | BUY | -₹9.04 |
| 3 | SELL | -₹7.85 |

Final balance: **₹482.53**.

## Finding

V3 became much more selective, but the confirmation logic was too brittle: one temporary spread widening could completely erase an armed signal. The system repeatedly looked ready to enter, then forgot the setup.

## Related algorithm

[V3 algorithm](../../algorithms/v3.md)
