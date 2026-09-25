# V4.5 Candidate E microstate confirmation — frozen pre-run specification

Status: **frozen before Candidate E outcome evaluation**

Date: 2026-09-25

## Why this candidate exists

Experiments 31-33 showed that changing engine arbitration creates large path-dependent damage and that simultaneous engine alternatives are rare. Experiment 34 rejected the frozen SNAPBACK complement. Experiment 35 did not demonstrate transferable outcome prediction from `xau-state-v2`. Experiment 36 then retained `xau-microstate-v1`, a 23-feature raw-event representation with full known-data coverage and strong 500 ms / 1 s cross-grid stability.

Candidate E therefore does **not** add another router, learned model, new engine, or threshold search. It makes one bounded admission change to the existing Candidate D control.

## Frozen hypothesis

The recent PRIMARY failure diagnosed in Experiments 22/26 is partly an admission/exhaustion problem. A legacy PRIMARY signal should be deferred on a sampled quote when both of these frozen raw-event measurements contradict the intended trade direction:

- `dir_mid_move2 < 0`
- `dir_event_imb2 < 0`

Both are direction-normalized features from the already-frozen `xau-microstate-v1` schema. Zero is the natural neutral boundary; no P&L-derived cutoff is introduced.

This is intentionally a conservative **joint contradiction veto**. One disagreeing field alone is not enough.

## Candidate E behavior

Candidate E is Candidate D except:

1. inspect `xau-microstate-v1` only when Candidate D's highest-priority eligible engine is PRIMARY;
2. if both frozen contradiction tests are true, HOLD for that sampled quote;
3. do **not** fall through to SECONDARY/MICRO/BURST on that tick;
4. do **not** start, extend, or mutate any cooldown because of the veto;
5. if the legacy PRIMARY setup remains valid on a later sampled quote and the raw contradiction clears, it may enter then;
6. missing/non-finite microstate values fail open and preserve Candidate D behavior.

Unchanged:

- PRIMARY → SECONDARY → MICRO → BURST priority;
- every signal threshold;
- every exit/lifecycle rule, including Candidate D's one-second confirmed BURST failure;
- shared one-position slot;
- 3% planned-risk sizing/leverage cap;
- $4 emergency stop;
- spread rules and executable bid/ask accounting.

## Pre-registered known-data diagnostic

The already-observed seven-day first80 and recent 24-hour snapshots may be used to verify implementation and reject a broken candidate, but **cannot promote Candidate E**.

Run unchanged at 500 ms and 1 s:

- canonical five-segment first80 replay with Candidate D parity;
- recent 24-hour whole-window terminal-equity replay;
- frozen 60/40 recent split;
- 40 deterministic real contiguous four-hour stress windows per grid, alternating historical-first80 and recent24h sources;
- adverse execution stress at $0.00, $0.05, $0.10 and $0.20 per side;
- PRIMARY veto counts and trade/opportunity retention.

The final 20% historical holdout remains sealed.

## Promotion discipline

Even an attractive known-data result remains diagnostic. Promotion requires:

1. candidate and evaluation contract frozen before outcomes;
2. a genuinely new non-overlapping raw XAU snapshot;
3. Candidate D and Candidate E replayed unchanged on both 500 ms and 1 s;
4. net P&L, win rate, drawdown, opportunity/trade retention and cost robustness compared;
5. rejection rather than retuning if the frozen candidate fails that prospective snapshot.

No feature subset search, logical-rule search, threshold sweep, or model fitting is allowed inside Experiment 37.

## Evidence contract

Experiment record:
`docs/experiments/2026-09-25/37-v4-5-candidate-e-microstate-confirmation.md`

Implementation:
`research/v4_5_candidate_e_microstate_confirmation.py`

Evidence:
`results/simulations/2026-09-25-v4_5-candidate-e-microstate-confirmation/`
