# Experiment 44 — MT5 tick-tape field audit

Date: 2026-09-26
Status: frozen before evaluation

Purpose: audit causal raw fields that existing state-v2/microstate-v1 do not use even though the archived MT5 ticks contain them: `last`, `volume`, `volume_real`, and `flags`.

No strategy or P&L label is used.

Official MT5 flag semantics are treated mechanically:
- BID changed: bit 2
- ASK changed: bit 4
- LAST changed: bit 8
- VOLUME changed: bit 16
- buy trade: bit 32
- sell trade: bit 64

Audit:
1. full first80/recent24h field support and bit frequencies;
2. nonzero/finite last and volume support;
3. 2s/10s tape features at the same independent opportunity metadata used by microstate-v1;
4. strict <=10s and broad <=120s cross-grid stability.

Frozen tape features:
- bid/ask/both update fractions;
- bid-vs-ask update imbalance;
- trade-tick counts;
- buy/sell trade counts and count imbalance;
- buy/sell volume and volume imbalance;
- LAST-price movement over 2s/10s, direction-normalized;
- trade/quote event ratio.

If broker trade fields are structurally empty, record that and do not manufacture signal from them. No feature selection or trading rule is allowed in this experiment.

Evidence:
- research/v4_5_tick_tape_field_audit.py
- results/simulations/2026-09-26-v4_5-tick-tape-field-audit/
