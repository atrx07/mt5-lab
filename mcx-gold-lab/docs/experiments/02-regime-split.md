# Experiment 02 — Regime Split: Where Does Donchian's P&L Come From?

**Date:** 2026-10-08 · **Status:** COMPLETE · **Verdict: PATTERN FOUND, NOT AN EDGE**
(textbook regime dependence — the research question just got sharper)

## 1. Question

Experiment 01's DonchianBreakout(20) printed +Rs 1,855 on the full year.
Was that uniform, or concentrated in certain market regimes? If the P&L
comes only from trending months, the "strategy" is a regime bet wearing a
breakout costume — and the real research target is regime detection.

## 2. Method

Split the 12 months by trend-efficiency =
|month return| / sum(|daily returns|). Efficiency > 0.30 → "trending",
≤ 0.30 → "choppy". Ran Donchian(20) per calendar month with 25-bar warmup,
attributing each month its incremental net (full-run minus warmup-only run —
positions opened in warmup and closed in-month attribute to the closing month,
so monthly trades/P&L don't sum exactly to the full-sample run; the
directional split is the robust finding, not the rupee amounts).

## 3. Results (GOLDPETAL, 1 lot, real MCX bhavcopy)

| Month | Efficiency | Month ret | Donchian net | Note |
|---|---|---|---|---|
| 2025-10 | 0.04 | +0.9% | Rs 0 | chop, no trades |
| 2025-11 | 0.38 | +4.9% | Rs 0 | trend, no signal fired |
| 2025-12 | 0.41 | +6.5% | +Rs 768 | |
| 2026-01 | 0.42 | +18.8% | +Rs 3,183 | the year's big trend month |
| 2026-02 | 0.08 | −2.7% | −Rs 489 | chop bleed |
| 2026-03 | 0.28 | −9.5% | −Rs 790 | chop bleed (whipsaw) |
| 2026-04 | 0.01 | +0.1% | Rs 0 | dead chop, flat |
| 2026-05 | 0.26 | +3.9% | +Rs 386 | |
| 2026-06 | 0.43 | −10.2% | +Rs 1,167 | DOWN-trend captured short — system working as designed |
| 2026-07 | 0.04 | +0.7% | −Rs 142 | chop bleed |
| 2026-08 | 0.46 | +9.0% | +Rs 852 | |
| 2026-09 | 0.28 | −4.0% | −Rs 70 | |
| 2026-10* | 0.49 | +0.5% | −Rs 241 | *partial month (3 bars) — ignore |

**Trending months (6): +Rs 5,729 · Choppy months (7): −Rs 1,105**

## 4. Reading

This is the textbook breakout signature: it harvests trends (both
directions — June's −10.2% month paid +Rs 1,167 on the short side) and
donates back in chop (Feb/Mar/Jul bleeds). Two consequences:

1. **The breakout rule is not the edge.** It is a trend-exposure vehicle.
   The entire game is regime classification: trade it only when efficiency
   is high, stand down otherwise. A regime filter is now the highest-value
   research target in the daily-bar track.
2. **The full-sample +Rs 1,855 is regime luck.** The year happened to contain
   6 trending months including a +18.8% monster (Jan 2026). In a choppy year
   this same system prints red. Still not evidence of edge — but it IS a
   clean, falsifiable hypothesis: *a Donchian system gated on a real-time
   regime filter outperforms the ungated version out-of-sample.*

## 5. Next (Experiment 03)

Build a CAUSAL regime filter (efficiency estimated on trailing data only —
no look-ahead), gate Donchian on it, and run the walk-forward gate. If the
gated version survives 4+ OOS windows with <30% Sharpe degradation, it
becomes the first real candidate. If not, the daily track stays in
"no edge found" and all effort goes to tick capture.
