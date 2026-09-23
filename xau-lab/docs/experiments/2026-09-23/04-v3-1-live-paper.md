# V3.1 live paper — 2026-09-23

## Main changes

- armed signals survive temporary spread widening;
- max armed lifetime: 6 s;
- breakout level is frozen at arm time;
- setup is cancelled only when direction genuinely invalidates;
- spread must be acceptable at actual entry;
- same hard-stop / reversal / profit-lock framework.

## Exact recorded CSV result

The original trade log is committed at [`results/paper_trades_v3_1.csv`](../../../results/paper_trades_v3_1.csv).

Summary from the 18 completed trades:

- start: ₹500
- end: **₹463.46**
- net: **-₹36.54 (-7.31%)**
- winners: 5
- losers: 13
- one strong early winner: +₹13.79
- another strong winner: +₹15.75
- the first 14 trades left the account at **₹499.91**
- the final four trades were:
  - -₹5.80
  - -₹14.44
  - -₹6.45
  - -₹9.77

Those four trades account for almost the entire final drawdown.

## Spread split observed in that run

This is descriptive of one run, not a universal law:

| Entry spread | Trades | Aggregate P&L |
| --- | ---: | ---: |
| <= USD 0.30 | 11 | about -₹0.43 |
| > USD 0.30 | 7 | about -₹36.11 |

The result strongly suggested that a USD 0.35 entry ceiling was too permissive for this scalp horizon.

## Other observed failure modes

1. **Late momentum chasing** — confirmation can happen after the best part of the impulse is already gone.
2. **Give-back** — several trades reached small positive P&L and later closed near flat or negative because the ₹8 profit-lock trigger was too high for the typical move size.
3. **Regime persistence** — the bot kept trading after conditions became hostile.
4. **Spread sensitivity** — a few tenths of a dollar are enormous relative to the expected edge of a 5–30 second trade.

## Related algorithm

[V3.1 algorithm](../../algorithms/v3_1.md)
