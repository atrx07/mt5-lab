# Experiment 00 — Capital-efficiency model

**Date:** 2026-10-08
**Status:** COMPLETE
**Tool:** `tools/mcx_cost_model.py`
**Output:** `results/cost_model/exp0.json`

## Hypothesis

Before any strategy code: the cheapest lawful container for small-capital gold
exposure in India is an MCX micro-contract, and costs (not capital) determine
which one.

## Method

Priced one round trip per contract under the Zerodha-published MCX schedule
(brokerage Rs 20 or 0.03% lower; CTT 0.01% sell; txn 0.0021%; stamp 0.002% buy;
SEBI Rs 10/crore; GST 18%), 7% margin (6% + 1% ELM), gold Rs 12,000/g.
Computed: margin/lot, round-trip cost, cost as % of notional, breakeven ticks,
and account fit under a 3%-per-trade risk rule with a 100-tick reference stop.

## Results

| Contract | Notional | Margin | RT cost | Cost % | Breakeven |
|---|---|---|---|---|---|
| GOLDPETAL (1 g) | Rs 12,000 | Rs 840 | Rs 10.56 | 0.088% | 10.6 ticks |
| GOLDGUINEA (8 g) | Rs 96,000 | Rs 6,720 | Rs 63.70 | 0.066% | 63.7 ticks |
| GOLDM (100 g) | Rs 12,00,000 | Rs 84,000 | Rs 253.50 | 0.021% | 25.4 ticks |

Account fit: Petal tradable from ~Rs 10k (3 lots by risk rule); Guinea needs
~Rs 25k+ to be comfortable; GOLDM needs ~Rs 100k.

## Conclusions

1. **Costs are NOT the binding constraint on MCX.** Contrast crypto's 31.2%
   winners-only tax: here a strategy must clear ~Rs 10.56/trade on Petal —
   an achievable bar *if* edge exists.
2. **Spread is the real microstructure tax.** At Rs 1 ticks, a Rs 2-3 spread
   costs Rs 2-4 per round trip per lot: 20-40% on top of the fee schedule.
   It is part of the strategy, per lab rules.
3. **Petal primary / Guinea secondary.** Petal wins absolute minimum capital;
   Guinea wins efficiency above ~Rs 25k.
4. This model prices the container only. It is necessary, not sufficient.

## Verdict

PROMOTE the venue decision. Proceed to Phase 1 (data pipeline).
