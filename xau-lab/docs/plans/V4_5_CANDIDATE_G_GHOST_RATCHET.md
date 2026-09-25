# V4.5 Candidate G — path-preserving PRIMARY ratchet specification

Date: 2026-09-25

Status: **frozen before Experiment 41 outcome evaluation**

## Basis

Experiment 40 rejected Candidate F even though its random-window behavior improved. The full shared-slot replay exposed the mechanism:

- the PRIMARY ratchet banks some favorable excursion;
- but the earlier real exit frees the shared slot;
- that changes later entries, cooldowns and balance-dependent sizing;
- the path mutation destroyed much of Candidate D's canonical edge.

This is the same path-dependence class identified in Experiment 31.

Experiment 41 does **not** alter the ratchet trigger, retention fraction, cadence or entry logic. It changes only how slot/cooldown state behaves after a ratchet exit.

## Candidate G

Candidate G = Candidate D + the frozen Candidate-F PRIMARY ratchet + **virtual legacy occupancy**.

### Real PRIMARY management

The real account uses the exact Candidate-F ratchet:

1. activate after live MFE reaches +1R = +$4;
2. retain at least 50% of live MFE;
3. check every 5 wall-clock seconds;
4. emergency stop and take profit remain higher-priority exits.

### Ghost occupancy after a ratchet exit

If the ratchet closes a PRIMARY trade before Candidate D's legacy lifecycle would have closed it:

1. bank the real ratchet P&L immediately;
2. create a virtual **ghost PRIMARY** with the original entry price, side, entry time, opening regime and already-observed peak;
3. the ghost carries **no capital, P&L or risk**;
4. while the ghost is active, the shared strategy slot remains unavailable exactly as it would under Candidate D;
5. continue evaluating the untouched Candidate-D PRIMARY legacy lifecycle on the ghost:
   - $4 emergency-stop condition;
   - legacy PRIMARY TP;
   - legacy m300 reversal where applicable;
   - legacy max-hold;
6. when the ghost reaches the legacy exit condition:
   - release the shared slot;
   - start PRIMARY cooldown from the **ghost legacy-exit timestamp**, not the real ratchet timestamp;
7. the next entry may be evaluated only from the following sampled quote, matching Candidate D's exit-loop semantics.

No ghost P&L is booked.

## Required path-preservation invariant

For canonical first80 at zero added slippage, Candidate G must reproduce Candidate D's **entry path** exactly:

- same number of entries;
- same engine;
- same side;
- same entry timestamp for every entry within each independently reset segment.

If entry-path parity fails, Candidate G is rejected as an implementation/architecture failure before P&L interpretation.

Balance-dependent position size may differ because Candidate G realizes different P&L; that is intended.

## Unchanged

- all Candidate D entry conditions and engine priority;
- SECONDARY/MICRO/BURST lifecycle;
- BURST confirmed-failure exit;
- PRIMARY legacy TP/reversal/max-hold used by the ghost;
- 3% planned-risk sizing;
- leverage cap;
- spread rule;
- executable bid/ask accounting.

## Known-data diagnostic

Run Candidate D and Candidate G through:

- canonical first80 five segments at 500 ms and 1 s;
- exact Candidate D parity;
- exact Candidate-D/Candidate-G entry-path parity;
- recent24h whole;
- recent 60/40 split;
- 40 deterministic real contiguous four-hour windows per grid;
- $0.00/$0.05/$0.10/$0.20 adverse slippage per side;
- ratchet exits and ghost releases.

Final20 stays sealed.

## Decision discipline

Known data may reject Candidate G but cannot promote it.

No search over +1R, 50%, five seconds, ghost rules or cooldown behavior is allowed.

If Candidate G preserves the entry path and improves/preserves known-data economics coherently, it becomes a **prospective candidate only**. Promotion still requires a genuinely new non-overlapping raw XAU snapshot.

## Evidence contract

Experiment:
`docs/experiments/2026-09-25/41-v4-5-candidate-g-ghost-ratchet.md`

Implementation:
`research/v4_5_candidate_g_ghost_ratchet.py`

Evidence:
`results/simulations/2026-09-25-v4_5-candidate-g-ghost-ratchet/`
