# Experiment 03 — Causal Regime Filter on Donchian (GATED)

**Date:** 2026-10-08 · **Status:** COMPLETE · **Verdict: HYPOTHESIS FALSIFIED**
(the walk-forward gate killed a plausible idea — the machine working as designed)

## 1. Hypothesis (from Exp 02)

Donchian made +Rs 5,729 in trending months and lost −Rs 1,105 in choppy
months. Gate its *entries* on a causal trailing-efficiency reading
(E > 0.30 over 20 days); never gate exits. Expected: chop bleed disappears,
trend harvest remains.

## 2. Method

`research/regime_filter.py`: `RegimeGatedDonchian` wraps `DonchianBreakout`.
Efficiency at bar t uses only closes ≤ t (causal); Donchian's lookback stays
warm while gated out so levels are correct on reopen. Walk-forward:
train=100d / test=25d / step=25d → 6 OOS windows on real GOLDPETAL data.

## 3. Results

| Version | Full-sample net | Trades | WF total OOS | WF positive | WF mean Sharpe | Degradation |
|---|---|---|---|---|---|---|
| Ungated Donchian(20) | +Rs 1,855 | 14 | +Rs 913 | 2/6 | 0.62 | 0.24 |
| Gated (eff > 0.30) | +Rs 1,855 | 14 | **+Rs 271** | **1/6** | **−0.03** | **1.05** ⚠ |

Walk-forward verdict on gated: **OVERFIT WARNING — DO NOT PROMOTE.**
Threshold sensitivity (0.25/0.30/0.35): identical results — the threshold
isn't binding; the gate adds no information.

## 4. Why the good idea failed

Breakouts are themselves trend detectors. By the time Donchian fires, the
market is already moving, so trailing efficiency is already high — the gate
is collinear with the entry signal and filters almost nothing (full-sample
P&L identical to the tick). The real bleed came from *false* breakouts in
chop, which look exactly like trend starts — a backward-looking efficiency
reading cannot distinguish them. The filter would need to predict regime
*persistence*, a much harder problem than classifying the recent past.

## 5. What this proves about the lab

This is the walk-forward gate doing its job: a plausible, well-motivated
idea died on out-of-sample data before it could cost real money. Negative
results are inventory — the regime-persistence question is now precisely
formulated instead of vaguely hoped for.

## 6. Next

- The daily dataset is thin (257 bars; most WF windows contain 0–1 trades).
  Extend bhavcopy history to 3+ years (free) before trusting any daily-bar
  conclusion — Exp 04.
- The tick question remains the main event: spread and intraday edge are
  invisible at daily resolution. Tick capture still blocked on broker API.
