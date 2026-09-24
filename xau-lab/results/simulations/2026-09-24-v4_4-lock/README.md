# V4.4 lock — Candidate K

Date: 2026-09-24

Status: **V4.4 locked as the current fractional experimental paper version.**

## Parity discrepancy resolved

The large V4.3 discrepancy came from comparing two different accounting methods.

The archived V4.3 +₹603.60 / 8.07% headline is exactly the result of compounding the five recorded reset-segment returns:

- +₹530.6234
- -₹3.8580
- -₹7.1549
- +₹5.0728
- +₹41.9036

It was previously described as "continuous" in some documentation, which was incorrect.

The archived V4.3 search row also used its $4 channel-range / $1.50 m30 / range-normalized breakout geometry globally. The V4.3 paper script and algorithm documentation were corrected accordingly.

V4.4 headline metrics now use the same reset-segment / compounded-return convention, so the comparison is methodologically aligned.

A small legacy reconstruction residual remains: with the corrected search-row geometry, the rebuilt V4.3 feature harness compounds to about +₹619.64 (8.28%) versus the archived +₹603.60 (8.07%), a difference of about ₹16.03 / 0.21 capture points. The large +₹683-vs-₹603 discrepancy is resolved; this smaller residual is preserved as a reconstruction limitation rather than hidden.

## Locked Candidate K

V4.4 keeps the corrected V4.3 PRIMARY/SECONDARY engines and adds the MICRO structural engine from Candidate A.

Candidate K then changes MICRO management:

- stagnation exit at 45 s if peak favorable move < $0.75;
- partial realization at +$5.50;
- realize 75% of MICRO exposure;
- leave 25% running under the existing $10 TP / +$4 trigger / $2 give-back trail / $4 stop logic.

No entry-risk increase was used.

## 500 ms canonical result

Using five reset research segments and compounding their returns:

| Segment | P&L |
| --- | ---: |
| 0–40% | +₹653.43 |
| 40–50% | +₹82.25 |
| 50–60% | -₹19.09 |
| 60–70% | +₹27.41 |
| 70–80% | +₹132.56 |

Compounded:

- **+₹1,224.01**
- **16.36% capture**
- 148 completed trades across reset segments
- median segment PF 1.734
- worst segment DD ₹201.25

## 1-second robustness result

| Segment | P&L |
| --- | ---: |
| 0–40% | +₹581.00 |
| 40–50% | +₹45.47 |
| 50–60% | -₹62.87 |
| 60–70% | +₹93.40 |
| 70–80% | +₹57.04 |

Compounded:

- **+₹863.22**
- **11.54% capture**
- 152 completed trades across reset segments
- median segment PF 1.508
- worst segment DD ₹224.18

The requested >=10% capture threshold is therefore cleared under the slower 1-second robustness replay.

## Cost stress

Candidate K stayed positive in the same-harness full-pool stress diagnostics:

| Stress | Net P&L | PF |
| --- | ---: | ---: |
| Base | +₹1,285.88 | 1.775 |
| $0.02 adverse slip / side | +₹1,149.41 | 1.687 |
| $0.05 | +₹1,062.44 | 1.628 |
| $0.10 | +₹812.80 | 1.503 |
| Spread +10% | +₹1,092.08 | 1.638 |
| Spread +25% | +₹442.46 | 1.440 |

## Decision

**Lock Candidate K as V4.4.**

- V4.4 is now the current experimental paper version.
- V4.3 remains the previous locked fractional version.
- Any tuning after this point becomes V4.5.
- The final 20% holdout remains unopened.
- No real-order execution is introduced.
