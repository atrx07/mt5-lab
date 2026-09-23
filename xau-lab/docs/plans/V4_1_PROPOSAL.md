# V4.1 proposal — not yet applied

Status: **planned / frozen for review**

This document captures the next changes discussed after the first V4 design. None of these changes should be treated as implemented until a later commit explicitly promotes them into code and experiment records.

## 1. Regime-aware thresholds

V4 currently relies heavily on absolute USD thresholds such as:

- M5 impulse threshold;
- M15 impulse threshold;
- maximum spread;
- fixed pullback range.

V4.1 should make the strategy aware of current market conditions instead of treating the same dollar move as equally meaningful in calm and violent regimes.

Candidate features:

- short-window realized range;
- short-window realized volatility;
- momentum normalized by recent volatility;
- spread relative to expected move size.

A spread should pass both an absolute ceiling and a relative transaction-cost test.

Conceptually:

```text
spread <= absolute cap
AND
spread / recent expected move <= acceptable fraction
```

## 2. Chop / directional-efficiency filter

Add a regime filter that can explicitly refuse noisy conditions.

Candidate efficiency ratio:

```text
ER = abs(price_now - price_30s_ago) / sum(abs(each price change))
```

High ER means price movement is efficiently directional.

Low ER means price travelled a lot but made little net progress — the exact type of whipsaw environment that repeatedly damaged V3.1.

Other candidate chop signals:

- frequent momentum sign changes;
- elevated spread variability;
- poor directional efficiency despite high raw movement.

The intended behavior is simple:

> if the market is moving a lot but going nowhere, do not trade.

## 3. Normalize pullback by impulse size

Replace the fixed pullback-dollar band with a structural ratio.

Instead of:

```text
pullback must be USD 0.20–0.85
```

prefer something like:

```text
pullback_fraction = pullback_distance / impulse_distance
```

The acceptable range should be evaluated together with current volatility.

This prevents the same fixed retracement from meaning "healthy pullback" in one regime and "the entire impulse has failed" in another.

## 4. Risk-based position sizing

Current research sizing begins from account capital and synthetic leverage.

V4.1 should instead couple position size to the actual stop distance:

```text
account balance
    ↓
risk fraction per trade
    ↓
risk amount in INR
    ↓
structure/volatility/spread-aware stop distance
    ↓
derive ounces from allowed loss
```

Candidate stop-distance inputs:

- pullback structure;
- recent volatility;
- spread multiplied by a safety factor.

The current ₹8 hard stop on ₹500 is about 1.6% of synthetic capital, but V4.1 should derive size and stop together rather than treating them as independent constants.

## 5. MFE / MAE instrumentation before exit tuning

Do not guess the next stop or profit-lock thresholds from a handful of visible trades.

Every replay/live-paper trade should log at least:

- entry;
- final P&L;
- MFE — maximum favorable excursion;
- MAE — maximum adverse excursion;
- time to MFE;
- time to MAE;
- peak P&L;
- spread at entry;
- spread at exit;
- stop distance;
- impulse size;
- pullback fraction;
- regime/efficiency metrics.

Questions this should answer:

- How much adverse movement do eventual winners normally survive?
- When a trade reaches +₹4, how often does it later reach +₹8 versus return below zero?
- Does the current profit lock cut normal winners too early?
- Are losses concentrated in a particular spread/volatility/chop regime?

Only after this analysis should exits be retuned.

## 6. Proper development / validation / holdout separation

The earlier short replay clips were useful for idea discovery, not proof of profitability.

For a larger broker-tick dataset, use chronological separation rather than random row splitting.

Proposed research split:

```text
60% development
20% validation
20% locked holdout
```

Rules:

- design/tune on development only;
- compare candidates on validation;
- do not inspect or optimize against the holdout until the strategy is frozen;
- preserve the holdout result even if it is ugly.

## 7. Walk-forward testing

Add rolling time-based evaluation, for example:

```text
Days 1–3 -> tune / establish parameters
Day 4     -> test

Days 2–4 -> tune / establish parameters
Day 5     -> test

Days 3–5 -> tune / establish parameters
Day 6     -> test
```

The purpose is to test whether behavior survives changing regimes instead of memorizing one session.

## 8. Execution stress testing

A candidate should also survive worse-than-ideal execution assumptions.

Stress dimensions to test independently and in combinations:

### Spread

- observed spread;
- +10%;
- +25%.

### Added latency

- 0 ms;
- 100 ms;
- 250 ms;
- 500 ms.

### Adverse slippage

- normal fill;
- +USD 0.02;
- +USD 0.05;
- +USD 0.10.

### Sampling interval

- 250 ms;
- 500 ms;
- 1000 ms.

A strategy whose apparent edge vanishes under tiny execution degradation should not advance.

## 9. Proposed V4.1 architecture

```text
MT5 ticks
    ↓
market features
    ↓
regime filter ───── cost filter
    ↓                   ↓
    └─────────┬─────────┘
              ↓
directional impulse
              ↓
wait for pullback
              ↓
pullback / impulse ratio
              ↓
wait for resumption
              ↓
structural entry
              ↓
risk-based position sizing
              ↓
deterministic risk + profit management
              ↓
impulse lockout
```

## 10. JEV comes later

JEV should only be added after the deterministic baseline survives multi-day broker-tick testing.

Proposed role:

```text
Python feature/state engine finds a valid candidate
        ↓
JEV returns BUY / SELL / HOLD + confidence
        ↓
local cost/risk engine may still veto
        ↓
paper execution
```

JEV should **not** own emergency exits.

Hard stops, profit protection, connectivity failure handling and future broker-native protective orders should remain deterministic.

## Promotion rule

Do not call this "V4.1" in the runnable strategy until the deterministic baseline, instrumentation and replay harness changes are actually implemented.

Until then this file is the frozen proposal.
