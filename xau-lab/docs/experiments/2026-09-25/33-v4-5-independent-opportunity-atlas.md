# 33 — V4.5 independent engine opportunity atlas

Date: 2026-09-25

Status: **diagnostic design frozen; execution pending**

## Question

Do PRIMARY, SECONDARY, MICRO and BURST actually contain **different profitable opportunities** when market conditions change, or are we asking a router to choose among four versions of the same failing edge?

Experiment 32 showed that router fall-through almost never fired. On the canonical first80 every Router-v3 veto was a PRIMARY-only opportunity. The current shared-slot path therefore hides an important fact: we do not yet know each engine's independent opportunity surface.

## Method

No strategy is promoted or tuned.

Each existing engine is replayed in its own independent one-position **shadow lane**:

- same raw signal definition;
- same engine-specific cooldown;
- same entry/exit lifecycle;
- same spread/executable-price handling;
- same 3%-of-₹500 sizing formula;
- no cross-engine shared slot;
- no cross-engine cooldown history;
- no compounding between shadow trades.

Every realized opportunity therefore receives a fixed-size outcome label that is not contaminated by an earlier router decision or balance path.

Censored end-of-range positions are marked and excluded from realized engine summaries.

Each shadow trade is enriched with the frozen `xau-state-v2` feature vector.

## Outputs

- `shadow_opportunities.csv` — independent engine trade ledger with state-v2;
- `engine_summary.csv` — fixed-size P&L, win rate, PF and drawdown by engine/window/grid;
- `four_hour_blocks.csv` and `engine_block_robustness.csv` — chronological robustness;
- `simultaneous_opportunities.csv` — how often independent engine entries actually coincide;
- `cross_window_engine_summary.csv` — historical vs recent sign/quality transfer;
- `state_outcome_profiles.csv` — descriptive win/non-win state medians only;
- `summary.json`.

## Anti-overfit rule

This atlas may answer whether the existing engine family has enough complementarity. It must **not** be used to hand-pick a state-v2 threshold from known winners.

If all or nearly all engines lose independently on the hostile recent window, the next architecture must add a genuinely complementary opportunity generator or a pre-registered walk-forward adaptive meta-labeler.

If one or more engines retain independent edge across both windows, a later router can be designed around that structural evidence and then frozen before unseen validation.

Final20 remains sealed.
