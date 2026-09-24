# 12 — V4.4 manager / exit optimization

Date: 2026-09-24

## Goal

Starting from provisional V4.4 Candidate A, test whether better position management, engine arbitration and partial realization can improve profit without increasing the 3% planned-risk fraction or opening the final 20% holdout.

## Candidate A reference

Same reconstructed 500 ms harness:

- +₹1,063.48;
- PF 1.600;
- 151 trades;
- max DD ₹198.08;
- provisional capture 14.21%.

## Tests run

This pass evaluated:

- PRIMARY / SECONDARY / MICRO priority permutations;
- a deterministic quality-score arbitrator;
- SECONDARY lost-breakout exits;
- engine-specific stagnation exits;
- PRIMARY trailing;
- MICRO MFE-based stagnation exits;
- MICRO partial profit-taking;
- 300-second momentum guards;
- shadow logging for signals blocked by the single-position slot;
- spread/slippage stress;
- a fresh 1-second sampled replay.

## Important results

### Arbitration did not earn promotion

PRIMARY -> MICRO -> SECONDARY priority was slightly worse than Candidate A.

A hand-built quality-score arbitrator was materially worse. The shared slot is therefore not changed based on this pass.

### Early SECONDARY failure logic was fragile

Returning inside the old breakout channel after entry was not a useful generic exit. The best tested 30-second version fell to roughly +₹507 / PF 1.39.

A 60-second SECONDARY stagnation exit looked excellent in the 500 ms replay, but collapsed under 1-second sampling. It is rejected for now.

### MICRO management was more robust

A MICRO early-stagnation exit at 60 seconds when peak favorable move remained below $0.50 improved both the 500 ms and 1-second research replays.

Partial MICRO profit-taking was also useful.

The strongest sampling-robust combination in this pass was:

- exit a MICRO trade after 60 seconds if peak favorable move < $0.50;
- once a MICRO trade reaches +$6, realize 67% of its synthetic exposure;
- let the remaining 33% continue under the existing Candidate A MICRO TP / trail / stop logic.

This is recorded as provisional **Candidate J**.

## Candidate J comparison

500 ms:

- Candidate A: +₹1,063.48, PF 1.600, 151 trades, DD ₹198.08, 14.21% capture.
- Candidate J: **+₹1,179.81, PF 1.662, 151 trades, DD ₹197.76, 15.77% capture.**

1-second sampling:

- Candidate A: +₹673.25, PF 1.339, DD ₹233.02, 9.00% capture.
- Candidate J: **+₹734.24, PF 1.362, DD ₹224.26, 9.81% capture.**

So Candidate J improves P&L, PF and drawdown relative to Candidate A under both sampling rates, although absolute performance remains highly sampling-sensitive.

## Shadow opportunity diagnostic

Blocked PRIMARY and MICRO structural signals were positive in aggregate in the diagnostic replay, while blocked SECONDARY signals were negative overall.

That supports treating SECONDARY as the weakest engine, but direct priority and arbitration changes did not improve enough to justify a routing change yet.

## Cost stress

Candidate J remained positive under $0.02 / $0.05 / $0.10 adverse slippage per side and +10% / +25% spread stress.

At +25% spread it degraded heavily and underperformed Candidate A, so cost sensitivity remains a material weakness.

## Decision

**Do not lock V4.4 yet.**

Candidate J is the strongest robust management follow-up from this pass.

Remaining blockers:

1. canonical locked V4.3 replay parity is still unresolved;
2. Candidate J reaches about 9.81% capture at 1-second sampling, just below the 10% research objective;
3. the final 20% holdout remains unopened.

Evidence:

[`results/simulations/2026-09-24-v4_4-manager-optimization/`](../../../results/simulations/2026-09-24-v4_4-manager-optimization/)
