# Contract probe — 2026-09-23

The MT5 symbol probe established the practical constraints that shaped every later experiment.

Observed around XAUUSD ~4315:

- contract size: 100 oz per lot;
- broker minimum: 0.01 lot = 1 oz;
- at 1:100 leverage, minimum margin was roughly USD 43;
- a USD 1 move in gold on 0.01 lot changes P&L by roughly USD 1;
- observed spread during the session varied from roughly USD 0.2 into the USD 0.5+ range.

This immediately showed that the intended ₹100 or ₹500 challenge sizes could not place the broker's minimum live XAUUSD contract. All subsequent small-account tests therefore used **synthetic fractional exposure** for research only.

## Recovered probe

The original probe script was recovered from the old local directory and is now archived at [`scripts/xau_probe.py`](../../../scripts/xau_probe.py).
