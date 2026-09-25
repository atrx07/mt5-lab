# 19 — V4.5 confirmed BURST failure exit

Date: 2026-09-24

Status: **completed; Candidate D (one-second confirmation) is the provisional V4.5 research leader, not locked**

## Objective and evidence

Experiment 18 found that every Candidate B BURST trade exits on the first 30 s momentum zero-cross. The Phase C1 lifecycle controls never engaged. This experiment tests one small structural response: require the zero-cross to persist briefly before the BURST failure exit. The $4 stop, take profit, trail, stagnation, max hold, admission, priority and all V4.4 engines retain their canonical rules.

## Gates and discipline

Verify the dataset SHA-256, assert V4.4 against its golden oracle on both grids, and assert exact Candidate B instrumentation parity before reading candidate outcomes. Use only the frozen first-80% research rows and five segments. Treat the 0–40% seed as the design region; the four later segments are chronological evaluation, not tuning targets. Do not open the final holdout or alter fixed risk.

Evaluate compounded P&L, capture, exposure, P&L per exposure hour, trades, wins, PF, drawdown, segment behavior, BURST attribution, 500 ms versus 1 s degradation and additional execution-cost stress. Preserve negative variants and do not call the candidate locked on a seed improvement.

## Seed selection

Tested zero-cross persistence of 0, 1, 2, 3 and 5 s on the 0–40% seed. Candidate B is 0 s. The one-second rule was selected as the shortest confirmation that improved seed P&L on **both** grids: 500 ms ₹690.22 → ₹696.84 and 1 s ₹169.47 → ₹169.92. Two seconds gained more at 500 ms (₹698.93) but slipped at 1 s (₹169.13). Three seconds slipped at 1 s; five seconds damaged both grids and was rejected before full evaluation. The exact seed outputs remain in `seed_confirmation_probe.json`.

One-, two- and three-second variants were then replayed over all five first-80% segments. Their machine-readable outputs and trade ledgers are retained. One second remained the best balanced result; the latter two were not promoted.

## Canonical outcome

Both grids passed the V4.4 golden oracle and exact instrumented Candidate B parity before candidate interpretation. The dataset hash matched the contract; the final holdout was not read.

| Metric | Candidate B 500 ms | Candidate D 500 ms | Candidate B 1 s | Candidate D 1 s |
| --- | ---: | ---: | ---: | ---: |
| Compounded P&L | ₹1,299.37 | **₹1,430.31** | ₹365.25 | **₹385.25** |
| Capture | 17.3652% | **19.1152%** | 4.8814% | **5.1487%** |
| Trades / wins | 163 / 79 | 163 / 81 | 156 / 70 | 156 / 71 |
| Median segment PF | 1.361 | **1.376** | **1.382** | 1.378 |
| Worst segment drawdown | **₹218.68** | ₹218.94 | ₹172.38 | **₹172.14** |
| P&L / exposure hour | ₹58.36 | **₹61.38** | ₹18.06 | **₹18.79** |
| BURST P&L | ₹58.40 | **₹100.85** | ₹10.44 | **₹22.04** |

The 50–60% segment remained -₹13.58 at 500 ms and -₹45.95 at 1 s. The increase at 500 ms was concentrated in the seed and 70–80% segment; the latter rose from ₹169.62 to ₹212.82. The 1 s improvement was small compared with the still large sampling gap. Median 1 s PF dipped slightly, and 500 ms worst-segment drawdown rose by ₹0.26.

Additional adverse slippage of $0.10 per side, debited from each filled trade at its recorded size, leaves compounded first-80% P&L of ₹1,077.12 / ₹207.32 for D versus ₹968.43 / ₹191.07 for B at 500 ms / 1 s. At $0.20 per side, D falls to ₹768.19 / ₹51.42. This is a fixed-size post-trade sensitivity calculation: it does not resize later positions or alter signal/stop paths, so it is insufficient as final execution validation. The full 0, $0.05, $0.10 and $0.20 schedules, PF and drawdown sensitivities are in the JSON bundle.

## Evidence

- [Result bundle](../../../results/simulations/2026-09-24-v4_5-confirmed-failure/)
- [Candidate runner](../../../research/v4_5_confirmed_failure.py)

## Decision

Promote the **one-second confirmed-failure rule as provisional Candidate D research leader** because it improves compounded P&L and profit velocity on both grids, keeps the fixed risk model, and survives the initial cost debit relative to B. Keep B as the verified comparator and preserve the 2/3/5 s negatives. Do not lock V4.5 or create a paper script. The weak 50–60% segment, PRIMARY/SECONDARY sampling fragility, and 1 s cost sensitivity still block a lock. The next focused research should diagnose the large non-BURST sampling loss without tuning to the holdout or loosening admission thresholds just to reach a numeric target.
