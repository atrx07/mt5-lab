# 13 — V4.4 parity fix, >10% robustness and lock

Date: 2026-09-24

## Objective

Resolve the V4.3 replay discrepancy, push the V4.4 capture result above 10% under slower 1-second sampling, and lock V4.4 only if both conditions are satisfied.

## V4.3 parity resolution

The major discrepancy was methodological rather than a mysterious P&L calculation bug.

The canonical V4.3 +₹603.60 result is reproduced exactly by compounding the five recorded reset-segment returns:

- +₹530.623358
- -₹3.857973
- -₹7.154873
- +₹5.072782
- +₹41.903627

Each segment was simulated from a fresh ₹500 balance. The five return factors were then compounded chronologically.

Some later V4.4 research harnesses instead reported a literal one-pass continuous replay. Comparing those two numbers created the apparent parity failure.

A second parity issue was found in the prose/implementation description: the V4.3 archived search row applies the $4 minimum secondary range, |m30| >= $1.50 and max($0.50, 0.02 × range) breakout buffer globally. Earlier documentation incorrectly described those geometry parameters as high-regime-only.

The V4.3 script, algorithm documentation and locked config were corrected.

The corrected reconstructed V4.3 harness still has a small legacy residual versus the archived row: approximately +₹619.64 / 8.28% versus +₹603.60 / 8.07%. This is about ₹16.03 (0.21 capture points), far smaller than the earlier one-pass-continuous mismatch, and is recorded as a reconstruction limitation.

## 10% robustness search

Starting from V4.4 Candidate J, a tight MICRO-management search was run around:

- stagnation timing and minimum early MFE;
- partial-profit trigger;
- partial fraction.

The best robust configuration was Candidate K:

- MICRO stagnation check after 45 seconds;
- exit if peak favorable movement is still < $0.75;
- partial trigger at +$5.50;
- realize 75% of MICRO synthetic exposure;
- leave 25% running under the existing $10 TP / +$4 trail trigger / $2 give-back / $4 stop management.

No planned-risk increase was used.

## Canonical 500 ms result

Five independently reset research segments, compounded afterward:

- +₹653.43
- +₹82.25
- -₹19.09
- +₹27.41
- +₹132.56

Compounded net: **+₹1,224.01**

Capture: **16.36%**

Trades across reset segments: **148**

Median segment PF: **1.734**

Worst segment max DD: **₹201.25**

## 1-second robustness

Five independently reset 1-second segments:

- +₹581.00
- +₹45.47
- -₹62.87
- +₹93.40
- +₹57.04

Compounded net: **+₹863.22**

Capture: **11.54%**

Trades across reset segments: **152**

Median segment PF: **1.508**

Worst segment max DD: **₹224.18**

The requested >=10% robustness threshold is therefore cleared.

## Stress

Candidate K remained positive under $0.02 / $0.05 / $0.10 adverse slippage per side and +10% / +25% spread shocks.

The +25% spread case remains a major degradation, so cost sensitivity is still an important limitation.

## Decision

**Lock Candidate K as V4.4.**

- V4.4 becomes the current experimental paper version.
- V4.3 remains the previous locked fractional version.
- Any further change becomes V4.5.
- The final 20% holdout remains unopened.
- No real order execution was added.

Evidence:

[`results/simulations/2026-09-24-v4_4-lock/`](../../../results/simulations/2026-09-24-v4_4-lock/)
