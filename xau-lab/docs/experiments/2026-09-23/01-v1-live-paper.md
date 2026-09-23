# V1 live paper — 2026-09-23

## Goal

Try ₹100 → ₹150 using live XAUUSD prices.

## Design

- fixed synthetic exposure: 1.00 oz;
- sample interval: ~0.5 s;
- warmup: 30 s;
- spread ceiling: USD 0.35;
- 5 s momentum threshold: USD 0.30;
- breakout buffer: USD 0.05;
- cooldown: 15 s;
- max hold: 120 s.

## Recorded run

- SELL #1 entry bid: 4314.45
- spread: 0.22
- immediate spread handicap: about -₹21.05
- first trade exit: -₹72.73
- balance after trade: ₹27.27
- SELL #2 spread: 0.30
- immediate spread handicap: about -₹28.71
- final balance: **-₹13.89**
- elapsed from start to ruin: roughly **42 seconds**

## Finding

The dominant failure was not signal quality; it was sizing. One ounce against ₹100 was effectively thousands of times exposure relative to capital. Ordinary sub-dollar gold movement and spread were enough to destroy the account.

## Related algorithm

[V1 algorithm](../../algorithms/v1.md)
