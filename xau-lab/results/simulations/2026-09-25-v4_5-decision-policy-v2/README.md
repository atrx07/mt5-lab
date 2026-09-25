# Experiment 39 — Decision Policy v2

Status: **completed diagnostic**

The learned policy is rejected, but the fixed profit-ratchet comparator exposed a narrower mechanism worth a separately frozen full-strategy test.

## Learned entry timing

Cooldown-free episode modeling produced 7,988 checkpoints across 6,501 signal episodes.

The model did not learn useful WAIT timing: median selected wait was 0 seconds, and historical OOS policy P&L was substantially worse than episode-onset entry.

## Learned exit timing

The 30-second target plus trajectory deltas remained effectively uncorrelated with historical OOS forward value. Two-negative confirmation still exited about 99% of represented historical trades and destroyed historical edge.

## Profit ratchet

A fixed +1R activation / 50%-of-MFE retention comparator improved historical OOS on both grids:

- 500 ms: +₹270.57 → +₹343.36;
- 1 s: +₹170.06 → +₹246.98.

Recent transfer was +₹27.04 at 500 ms but -₹34.91 at 1 s.

Post-run engine decomposition showed the recent 1 s damage came from SECONDARY. PRIMARY-only ratchet contribution was positive in all four window/grid comparisons. Because that decomposition is post-run, it is **not** candidate evidence.

## Next

Freeze a separate full shared-slot Candidate F using **Candidate D entries unchanged + PRIMARY-only +1R/50%-MFE ratchet** and evaluate its path-dependent effects without tuning.

Final20 remains sealed.
