# xau-lab agent instructions

Status: **canonical project instructions for the XAUUSD lab**

This is an operational handoff, not an experiment log. Historical detail belongs in numbered experiment documents and preserved result bundles.

## Read-first continuation protocol

When resuming:

1. work from `main`;
2. read this file;
3. read `structure.md`;
4. read `docs/replay/CANONICAL_REPLAY.md`;
5. read `results/regression/canonical_v4_4_reference.json`;
6. read `docs/algorithms/v4_5.md`;
7. read `docs/experiments/README.md` and the latest experiment record;
8. inspect matching result evidence when present;
9. prefer repository evidence over remembered chat context.

Do not restart the research line because a conversation ended.

## Project objective

Project: `xau-lab` inside `atrx07/mt5-lab`.

Instrument: **XAUUSD** using MetaTrader 5 broker tick data.

Goal: maximize expected profit per unit time while controlling execution cost, drawdown, sampling fragility and risk. Track net P&L, P&L/exposure hour, capture, PF, trade count, P&L/trade, holding time, drawdown, regime behavior, cost stress, 500 ms vs 1 s degradation and MFE/MAE where available.

Trade count alone is never the optimization target.

## Current canonical state — 2026-10-07

- V4.4 is the latest locked fractional research version.
- V4.5 remains research in progress; nothing in V4.5 is approved for live/paper promotion.
- Candidate J failed genuine fresh six-block prospective validation in Experiment 48.
- Experiment 49 showed D/H/J all negative in the current seven-day regime; H's path-preserving flow-confirmed exit still improved D, while J entry filtering did not transfer.
- Candidate L was rejected; its autopsy showed the dominant problem was **bad entry commitment**, not merely bad exits.
- Candidate M's reclaim + price-acceptance state machine is rejected as a strategy but remains the **strongest reusable entry kernel** because it sharply reduced later-regime failure.
- Candidate N's breakout expansion, Candidate O's anchor invalidation and Candidate P's fixed second persistence confirmation were all rejected.
- Candidate H-derived flow-confirmed profit protection remains the strongest retained exit component.
- **Experiment 58 is the active research line. No Candidate Q exists yet.**
- Final20 remains sealed.

## Experiment 58 — accelerated discovery / validation split

Plan:

`docs/plans/V4_5_M_ACCEPTANCE_DISCRIMINATION_SHADOW.md`

Experiment:

`docs/experiments/2026-10-07/58-v4-5-m-acceptance-discrimination-shadow.md`

Capture:

`tools/capture_m_acceptance_shadow_4h_block.py`

Launcher:

`tools/start_m_acceptance_shadow_4h_block.ps1`

Extractor:

`research/v4_5_m_acceptance_discrimination.py`

Supporting modules:

- `research/v4_5_m_acceptance_discrimination_features.py`
- `research/v4_5_m_acceptance_discrimination_sim.py`

Analysis launcher:

`tools/analyze_m_acceptance_shadow_block.ps1`

### Capture continuity

Candidate M inherits `CONTINUITY_SEC = 1800`, so Experiment-58 launch readiness requires **30 uninterrupted minutes** under the existing >5-second session-reset semantics.

The first 2026-10-07 attempt failed before any scored block started because the harness still inherited Candidate J's 90-minute warmup. That requirement was corrected outcome-blind before any M outcome/label was exposed. The failed attempt is not an Experiment-58 evidence block.

### Stage A — mechanism discovery

Discovery may use already-consumed historical first80, recent24h, current7d and Experiment-48 blocks because discovery is explicitly development evidence, not validation evidence.

Fresh Stage-A addition:

- first **2 sequential valid four-hour blocks**;
- after both complete, full labels may be opened;
- if either grid has fewer than **4 score-window M entries** across the two blocks, add one extra sequential discovery block based on entry count only;
- define at most **one primary causal discriminator plus one optional tie-breaker**;
- no unrestricted feature/model search and no brute-force threshold sweep.

Candidate Q must be fully frozen and committed after Stage A before any Stage-B block starts.

### Stage B — true prospective Candidate-Q validation

Use the **next 4 sequential valid four-hour blocks captured after Q is frozen**.

Q cannot change between blocks.

Minimum pass gate:

1. pooled Q P&L > 0 on both 500 ms and 1 s;
2. pooled Q P&L > M on both grids;
3. mean four-hour Q P&L > 0 on both grids;
4. at least 2/4 positive Q blocks on each grid;
5. pooled Q P&L under +$0.10/side adverse-fill stress remains >=0 on both grids;
6. parity/provenance/safety gates all pass.

If Q fails, reject it unchanged. Do not tune against those four blocks and call the revision validated.

## Canonical truth hierarchy

1. `agents.md` for workflow/current handoff;
2. `structure.md` for file placement;
3. `docs/replay/CANONICAL_REPLAY.md` for replay semantics;
4. `results/regression/canonical_v4_4_reference.json` for V4.4 parity;
5. current algorithm doc;
6. latest experiment record;
7. machine-readable result evidence;
8. older prose/ad-hoc numbers.

Historical evidence is preserved even when later pipelines supersede its interpretation.

## Canonical historical dataset / holdout

Historical seven-day raw SHA-256:

`007e7ab10cc16519b544003dbe81521f46cf868bf267780932638d1e8cec86e5`

Archive:

`data/raw/xau_ticks_7d_2026-09-16_to_2026-09-23.csv.gz`

Frozen research boundaries:

`[0, 934989, 1168737, 1402484, 1636231, 1869979]`

Interpretation:

- 0-40% seed/search;
- 40-50%, 50-60%, 60-70%, 70-80% chronological research evaluation;
- 80-100% final holdout.

Final20 has not been opened by the canonical replay harness. It also overlaps a previously observed Sep-23 live-paper period, so if opened later, disclose that contamination.

Known data may support mechanism discovery, parity and rejection. Repeatedly observed development outcomes must never be relabeled unseen validation.

## Canonical replay / accounting

Canonical harness:

`research/canonical_replay.py`

Golden oracle:

`results/regression/canonical_v4_4_reference.json`

Before accepting canonical historical candidate evidence, verify dataset hash, build canonical features, replay V4.4, assert the golden oracle, then run the candidate on the same harness. Abort on parity drift.

Current V4.4 oracle:

- 500 ms: +₹1,097.659652, 14.669495% capture, 148 trades, 68 wins;
- 1 s: +₹333.271059, 4.453947% capture, 145 trades, 63 wins.

## Execution / risk discipline

Unless a frozen experiment explicitly changes a rule:

- BUY enters at ask and exits at bid;
- SELL enters at bid and exits at ask;
- spread is paid;
- no fantasy mid fills;
- planned entry risk is 3%;
- current emergency stop is $4;
- synthetic leverage cap remains 100x where inherited;
- one shared open-position slot applies;
- INR/USD constant remains 95.7021 unless explicitly changed/documented.

Observed broker minimum during testing was 0.01 lot = 1 oz, while ₹500 synthetic sizing can be smaller. Backtest sizing is not automatically live-executable.

## MT5-only live-practicality gate

Do not integrate external GC/Yahoo/CME/LMAX feeds into the active V4.5 execution algorithm unless the owner explicitly reopens that line. Active decision features should be causally available from the same MT5/broker feed and replayable from archived MT5 fields.

## Paper/live boundary

Experiment 58 and current candidates are research/shadow code. Do not silently add `mt5.order_send()`, real-money execution, credentials or an unattended live executor.

A real-execution milestone requires explicit owner authorization plus live-size feasibility, broker-contract verification, spread/slippage guards, hard risk caps, kill switch, reconnect handling, duplicate-order protection, paper/live separation and audit logging.

Never describe backtest/shadow results as guaranteed future profitability.

## Repository placement / workflow

Canonical work goes directly to `main` unless the owner requests a branch/PR workflow.

- `scripts/` — final paper-challenge executors only;
- `research/` — replay/diagnostics/features/candidate experiments;
- `tools/` — broker/data capture and operational utilities;
- durable evidence — `results/simulations/...`;
- plans — `docs/plans/`;
- chronological records — `docs/experiments/`.

Preserve failed candidates, parity failures, cost-stress failures, raw logs, configs, dataset hashes and rejection reasons.

## Immediate next action

Pull latest `main` and start Stage-A block 1:

```powershell
.\tools\start_m_acceptance_shadow_4h_block.ps1
```

Do not open full labels after block 1. Capture Stage-A block 2 as the next sequential valid block. After both complete, run the discovery analysis, freeze one small Q rule, and then begin the four untouched Stage-B blocks.

## New-chat handoff

A new chat should read the canonical files, state the recovered current status briefly, and continue from the latest unfinished Experiment-58 Stage-A/Stage-B step without asking the user to reconstruct history.
