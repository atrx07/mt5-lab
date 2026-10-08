# Experiment 01 — First Real Data: MCX Bhavcopy → Daily Baselines

**Date:** 2026-10-08 · **Status:** COMPLETE (pipeline) · **Verdict: NO EDGE FOUND**
(market beta, not strategy alpha — see §4)

## 1. What was built

MCX's bhavcopy endpoint (`GET /market-data/bhavcopy/GetCommoditywiseBhavCopy`)
was confirmed working with a full browser header profile — Akamai 403s bare
scripts, HTTP 200 with browser headers. Date-wise endpoint is dead; the old
`backpage.aspx` POST is retired.

New pipeline: `tools/fetch_bhavcopy.py` → raw JSON → `tools/curate_bhavcopy.py`
→ canonical CSV.gz + manifest → `tools/build_continuous.py` → front-month
continuous series (nearest-expiry with volume > 0) + manifest.

## 2. Data inventory

| Symbol | Dates | Trading days | Bars | Rolls | Limit days |
|---|---|---|---|---|---|
| GOLDPETAL | 2025-10-08 → 2026-10-06 | 257 | 257 | 7 | 1 |
| GOLDGUINEA | 2025-10-08 → 2026-10-06 | 257 | 257 | 8 | 1 |

Gaps fully explained: 2025-12-25 (Christmas), 2026-01-26 (Republic Day),
2026-04-03 (Good Friday), 2026-10-02 (Gandhi Jayanti), 2026-10-07 (bhavcopy
not yet published at pull time). MCX lists Petal contracts selectively
(quarterly-ish + near months), not every calendar month — the front-month
builder handles this. Manifests: `data/manifests/`.

**Price regime note:** gold ran ₹12,225/g → ₹15,125/g (+23.7%) over the year,
56.2% up-days. A raging bull year. Any long-biased strategy printing green
here is the NULL HYPOTHESIS, not a discovery.

**Provenance limit (read before citing):** daily bars only — no intraday path,
no bid/ask, no spread beyond a 2-tick slippage parameter. Valid for
daily-bar regime/trend experiments and pipeline validation. NOT valid for
tick-level strategy research. The tick question is still open.

## 3. Results — daily baselines on real GOLDPETAL (1 lot, Rs 25k account)

| Strategy | Net | Trades | PF | Win | Exp/trade | MaxDD | Cost ratio |
|---|---|---|---|---|---|---|---|
| DailyTrendMA(10,30) | +Rs 1,720 | 7 | 1.85 | 57% | Rs 246 | Rs 5,293 | 0.02 |
| DonchianBreakout(20) | +Rs 1,855 | 14 | 1.53 | 36% | Rs 133 | Rs 4,410 | 0.03 |
| Buy-and-hold 1 lot | +Rs 2,873 | 1 | — | — | — | — | ~0.01 |

Walk-forward (train 150d / test 40d, 2 windows — thin, see §4):
- TrendMA: 1/2 windows positive (one window: 0 trades), total OOS +Rs 555
- Donchian: 2/2 positive, total OOS +Rs 1,542, mean OOS Sharpe 2.55

## 4. Honest reading — why this is NOT evidence of edge

1. **Both baselines underperformed buy-and-hold** (+1,720/+1,855 vs +2,873).
   They captured ~60% of the passive drift while taking timing risk.
2. **Trade counts are tiny** (7, 14). PF 1.85 on 7 trades is noise-shaped.
3. **The year was +23.7% with 56% up-days.** Long/flat and breakout-long
   strategies are SUPPOSED to be green here. Green ≠ edge.
4. **Only 2 walk-forward windows** fit in 257 bars. The gate needs 4+ windows
   before it means anything; treat current WF output as plumbing validation.
5. **Daily bars can't see the real enemy.** At daily holding periods the fee
   schedule is trivial (cost ratio 0.02). The spread — Rs 2–3 on Rs 1 ticks —
   only bites intraday, which this data cannot test.

**What Experiment 01 actually proved:** the full real-data pipeline works
end-to-end (fetch → curate → continuous → harness → walk-forward), the cost
model is re-priced to observed levels (Petal breakeven Rs 13.31/trade), and
the lab now runs on genuine market data instead of synthetic noise.

## 5. Next

- Experiment 02: regime-split analysis (bull vs chop months) on the daily
  series — does Donchian survive non-trending months?
- Phase 2 priority unchanged: real TICK capture (broker websocket) is the
  only route to answering the intraday edge question. Daily data cannot.
- Re-pull bhavcopy monthly to extend the series; the fetcher is the
  reproducible path (documented Akamai header requirement).
