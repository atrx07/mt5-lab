# V4.5 second simulation — additive BURST candidate B

Date: 2026-09-24

Status: **promising research candidate; not locked as V4.5.**

## Why this pass exists

V4.5-A tightened MICRO admission and reduced useful trades and capture. This pass deliberately learned the opposite lesson:

- do **not** strangle the existing V4.4 engines;
- leave PRIMARY / SECONDARY / MICRO unchanged;
- add a fourth, independent **BURST** candidate only after all three existing engines decline the current market state.

The final 20% holdout remains unopened.

## Candidate B

BURST entry requirements:

- existing PRIMARY / SECONDARY / MICRO must all decline the sample;
- BURST cooldown: 60 s;
- 10 s momentum >= +$0.60 / <= -$0.60;
- 30 s momentum >= +$1.50 / <= -$1.50;
- 60 s momentum >= +$2.00 / <= -$2.00;
- 120 s momentum direction agrees;
- 60 s path efficiency >= 0.12;
- 10s/30s raw quote-rate ratio >= 1.20;
- directional raw tick imbalance >= 0.20;
- 60 s range >= $4;
- spread <= 18% of the 60 s range;
- BURST absolute spread cap: $0.28.

BURST exit:

- $4 emergency stop;
- $12 take profit;
- max hold 120 s;
- 30 s momentum zero-cross failure exit;
- stagnation after 60 s if peak favorable move < $0.80;
- trail after +$5.50 with $2 give-back.

One shared position slot remains in force; there is no pyramiding.

## Same-harness comparison

The current V4.5 research harness still does not reproduce the official locked V4.4 1-second headline exactly, so absolute capture remains non-promotable. The valid result is the relative comparison against V4.4 reconstructed in the **same** harness.

| Metric | Reconstructed V4.4 | V4.5-B |
| --- | ---: | ---: |
| 500 ms compounded P&L | +₹1,097.66 | **+₹1,299.37** |
| 500 ms capture | 14.67% | **17.37%** |
| 500 ms trades | 148 | **163** |
| 500 ms median segment PF | 1.284 | **1.361** |
| 500 ms worst segment DD | ₹229.31 | **₹218.68** |
| 1 s compounded P&L | +₹333.27 | **+₹365.25** |
| 1 s capture | 4.45% | **4.88%** |
| 1 s trades | 145 | **156** |
| 1 s median segment PF | 1.367 | **1.382** |
| 1 s worst segment DD | **₹171.34** | ₹172.38 |

Relative to reconstructed V4.4:

- 500 ms P&L: +18.4%;
- 500 ms trades: +10.1%;
- 1 s P&L: +9.6%;
- 1 s trades: +7.6%;
- PF improves on both grids;
- 500 ms drawdown improves;
- 1 s drawdown increases by only about ₹1.

This is the first V4.5 candidate in the current research line that simultaneously increases **trades, capture and P&L on both sampling grids**.

## Chronological behavior

500 ms V4.5-B reset-segment P&Ls:

- 0–40%: +₹688.25
- 40–50%: +₹42.31
- 50–60%: -₹13.43
- 60–70%: +₹22.94
- 70–80%: +₹158.52

1 s V4.5-B:

- 0–40%: +₹169.47
- 40–50%: +₹42.42
- 50–60%: -₹45.95
- 60–70%: +₹73.74
- 70–80%: +₹64.93

The hostile 50–60% region is still negative. Candidate B improves it at 500 ms but does not solve it at 1 s.

## Cost diagnostic

Candidate B improves the base and +10% spread cases in the current harness. Under +25% spread and synthetic adverse-slippage shocks it can underperform reconstructed V4.4.

That means the new BURST engine is useful, but its cost gate is not yet robust enough for a V4.5 lock.

## Decision

**Keep Candidate B as the new V4.5 research leader, but do not lock it yet.**

The next pass should preserve the additive BURST idea and improve only its cost-aware admission / lifecycle behavior. Do not tighten the existing V4.4 MICRO engine again.

No `paper_challenge_v4_5.py` is created from this result.
