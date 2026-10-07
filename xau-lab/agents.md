# xau-lab agent instructions

Status: **canonical project instructions for the XAUUSD lab**

This file is an operational handoff, not an experiment log. Detailed historical evidence belongs in the numbered experiment documents and result bundles; Git history preserves older versions of this file.

## Read-first continuation protocol

When starting or resuming work:

1. work from `main`; it is the canonical branch;
2. read this file;
3. read `structure.md`;
4. read `docs/replay/CANONICAL_REPLAY.md`;
5. read `results/regression/canonical_v4_4_reference.json`;
6. read `docs/algorithms/README.md` and `docs/algorithms/v4_5.md`;
7. read `docs/experiments/README.md` and the latest numbered experiment record;
8. inspect the matching latest `results/simulations/<experiment>/` directory when evidence exists;
9. prefer repository evidence over remembered chat context whenever they disagree.

Do not restart the research line from scratch because a conversation ended.

## Project objective

Project: `xau-lab` inside `atrx07/mt5-lab`.

Instrument: **XAUUSD** using MetaTrader 5 broker tick data.

Long-term objective: build a reliable automated XAUUSD system that maximizes expected profit per unit time while controlling execution cost, drawdown, sampling fragility and risk.

Track at minimum:

- net P&L and return;
- P&L per active/exposure hour;
- opportunity capture;
- profit factor;
- trade count and P&L/trade;
- holding time;
- max drawdown;
- chronological/regime behavior;
- cost/slippage stress;
- 500 ms versus 1 s degradation;
- MFE/MAE where available.

Trade count alone is never the optimization target.

## Current canonical state — 2026-10-07

- V4.4 remains the latest **locked fractional research version**.
- V4.5 remains **research in progress; not locked and not approved for live/paper promotion**.
- Candidate J failed its genuinely fresh six-block Stage-1 prospective validation in Experiment 48. Those six blocks are now outcome-known development data and must never be relabeled unseen.
- Experiment 49 replayed D/H/J on the Sep-29→Oct-06 current-regime seven-day archive. All three were negative on both grids. Candidate H's path-preserving flow-confirmed exit consistently improved D; Candidate-J entry filtering did not transfer.
- Experiment 50 showed normalized price-shape geometry transfers substantially better than the inherited fixed `$0.30` spread cap. Execution quality should be judged relative to local opportunity/risk rather than by blindly increasing a fixed dollar cap.
- Candidate L (Experiment 51) tested a normalized trend → pullback → resumption architecture and was decisively rejected on historical/current/six-block/random-window/cost-stress evidence.
- Experiment 52 established that L's dominant failure was **entry commitment**: most losers developed very little favorable excursion, so exit tuning cannot rescue the architecture.
- Candidate M (Experiments 53-54) added pullback reclaim + explicit price acceptance before capital entry. It is **rejected as a strategy candidate**, but it is the strongest reusable entry architecture found in the L→P line because it sharply reduced later-regime losses and exposure while retaining a simple causal mechanism.
- Candidate N (Experiment 55) added a generic accepted-breakout lane and was hard rejected; increasing opportunity count destroyed M's useful selectivity.
- Candidate O (Experiment 56) treated loss of M's reclaimed anchor as an early invalidation exit and was rejected; the anchor behaves as a retestable level rather than a reliable hard terminal barrier.
- Candidate P (Experiment 57) required a second fixed persistence confirmation. It was positive on the narrow recent24h archive but negative across historical/current/six-block/random-window evidence and was hard rejected as too regime-specific.
- **Do not run rapid P→Q→R threshold/architecture search on the already-consumed datasets.** Experiment 57 explicitly closes that loop.
- **Experiment 58 is now the active research line:** fresh prospective Candidate-M acceptance-discrimination shadow evidence. No Candidate Q exists yet.
- Experiment 58 freezes M unchanged and records causal `feature_*` state at actual M would-enter events, with future/outcome values isolated under `label_*` only after capture.
- Experiment-58 discovery tranche: 8 sequential valid four-hour blocks across at least 4 market days. After 8 blocks, extension to exactly 12 is allowed only if either grid has fewer than 16 score-window M entries. The extension decision may use entry counts only, never P&L/outcomes.
- Candidate H-derived flow-confirmed profit protection remains the strongest retained exit mechanism/component. Candidate M remains the strongest reusable entry kernel. Neither is a promoted live system.
- The canonical final20 remains sealed.
- All canonical work is maintained directly on `main`.

### Active Experiment-58 files

Plan:

`docs/plans/V4_5_M_ACCEPTANCE_DISCRIMINATION_SHADOW.md`

Experiment record:

`docs/experiments/2026-10-07/58-v4-5-m-acceptance-discrimination-shadow.md`

Read-only capture:

`tools/capture_m_acceptance_shadow_4h_block.py`

Windows capture launcher:

`tools/start_m_acceptance_shadow_4h_block.ps1`

Offline extractor:

`research/v4_5_m_acceptance_discrimination.py`

Supporting frozen feature/parity modules:

- `research/v4_5_m_acceptance_discrimination_features.py`
- `research/v4_5_m_acceptance_discrimination_sim.py`

Analysis launcher:

`tools/analyze_m_acceptance_shadow_block.ps1`

Default fresh data root:

`data/prospective_m_acceptance_shadow/<session_id>/`

Default extracted evidence root:

`results/simulations/2026-10-07-v4_5-m-acceptance-discrimination-shadow/<session_id>/`

Before the discovery tranche closes, use only `-CountOnly` / `--count-only` if entry counts are needed for the predeclared 8→12-block extension rule. Do not inspect the outcome labels or P&L to decide whether to keep collecting.

## Canonical truth hierarchy

When artifacts disagree, use this precedence:

1. this `agents.md` for project workflow/current handoff;
2. `structure.md` for file placement and naming;
3. `docs/replay/CANONICAL_REPLAY.md` for replay/preprocessing/accounting semantics;
4. `results/regression/canonical_v4_4_reference.json` for the V4.4 regression oracle;
5. current algorithm document under `docs/algorithms/`;
6. latest numbered experiment record;
7. matching machine-readable evidence under `results/simulations/`;
8. older prose/ad-hoc replay numbers.

Historical evidence must not be deleted because a later canonical pipeline changes the comparison baseline.

## Canonical replay contract

Canonical harness:

`research/canonical_replay.py`

Canonical schema:

`xau-canonical-replay-v1`

Golden oracle:

`results/regression/canonical_v4_4_reference.json`

Before accepting non-baseline candidate performance evidence on the canonical historical data:

1. verify dataset SHA-256;
2. build canonical features;
3. replay locked V4.4 on the exact same feature arrays;
4. assert V4.4 against the golden oracle;
5. abort on baseline drift;
6. only then run the candidate;
7. report candidate deltas against the same-harness baseline.

`--no-baseline-assert` is diagnostic only and can never support promotion/lock.

If replay semantics genuinely change, create a new replay schema, document the reason, run old/new side-by-side, re-baseline explicitly, preserve the old oracle, then make the new schema canonical. Never edit a golden file merely to make a candidate pass.

## Dataset and holdout contract

Canonical historical seven-day dataset:

- instrument: XAUUSD;
- source: MetaTrader 5 broker tick export;
- raw rows: 2,337,474;
- raw bytes: 220,449,602;
- raw SHA-256: `007e7ab10cc16519b544003dbe81521f46cf868bf267780932638d1e8cec86e5`;
- first timestamp: `2026-09-16T14:56:19.104000+00:00`;
- last timestamp: `2026-09-23T14:56:18.226000+00:00`;
- archive: `data/raw/xau_ticks_7d_2026-09-16_to_2026-09-23.csv.gz`;
- manifest: `data/manifests/xau_ticks_7d_2026-09-16_to_2026-09-23.json`.

Canonical V4.x historical research is restricted to the first 1,869,979 rows unless the owner explicitly opens the final20 milestone.

Frozen raw boundaries:

`[0, 934989, 1168737, 1402484, 1636231, 1869979]`

Interpretation:

- 0-40% seed/search;
- 40-50% chronological evaluation 1;
- 50-60% chronological evaluation 2;
- 60-70% chronological evaluation 3;
- 70-80% chronological evaluation 4;
- 80-100% final holdout.

The final20 has **not** been opened by the canonical replay harness. It also overlaps a previously observed Sep-23 live-paper period, so if it is eventually opened, disclose that contamination and never call it pristine blind evidence.

Known datasets—including historical first80, recent24h, current7d and the six Experiment-48 blocks—may reject frozen ideas, support parity/diagnostics and inform mechanism understanding, but repeated same-data mutation must not be relabeled validation.

## Canonical accounting

For canonical V4.x historical headline comparison:

- each of the five first80 chronological segments starts from ₹500;
- segment return factors compound chronologically;
- constrained first80 opportunity ceiling is ₹7,482.60;
- capture = compounded P&L / ₹7,482.60.

Current V4.4 regression oracle:

- 500 ms: +₹1,097.659652, 14.669495% capture, 148 trades, 68 wins;
- 1 s: +₹333.271059, 4.453947% capture, 145 trades, 63 wins.

Older V4.4 lock figures remain historical evidence, not the V4.5+ parity oracle.

## Execution and risk discipline

Unless a frozen experiment explicitly changes a rule:

- BUY enters at ask and exits at bid;
- SELL enters at bid and exits at ask;
- spread is paid;
- no fantasy mid fills;
- planned entry risk is 3%;
- current emergency stop is $4;
- synthetic leverage cap is 100x where inherited;
- one shared open-position slot applies to the current composite architecture;
- INR/USD constant is 95.7021 unless explicitly changed/documented.

Observed broker minimum during testing was 0.01 lot = 1 oz, while ₹500 synthetic research sizing can be smaller. Backtest/paper sizing is therefore not automatically live-executable.

## MT5-only live-practicality gate

Do not integrate external GC/Yahoo/CME/LMAX feeds into the active V4.5 execution algorithm unless the owner explicitly reopens external-feed research. Experiments 45-46 are historical research evidence only.

Every active decision feature should be causally available from the same MT5/broker feed at trade time and replayable from archived MT5 fields. The Experiment-45 ~3-hour offset was a timestamp-label alignment issue, not a market lead/lag claim.

## Paper/live boundary

Current candidates and Experiment 58 are research/shadow code.

Do not silently add `mt5.order_send()`, real-money execution, credentials or an unattended live executor. A move to real execution is a separate explicit milestone requiring live-size feasibility, broker-contract verification, cost guards, hard risk caps, kill switch, reconnect handling, duplicate-order protection, paper/live separation and audit logging.

Never describe backtest/shadow results as guaranteed future profitability.

## Versioning and promotion rules

Locked versions are immutable baselines. Do not edit a locked strategy in place to represent a new idea.

Candidate letters/names may be used within V4.5 before lock. Rejected candidates remain recorded. Do not create `paper_challenge_v4_5.py` merely because a discovery/backtest slice looks good.

A future Candidate Q may be proposed only after Experiment-58 discovery closes. Its complete rule and prospective pass/fail contract must be frozen **before** a separate new unseen validation tranche starts. Do not mutate Q repeatedly after seeing that validation tranche.

Strong targets such as higher capture/profit velocity and lower exposure are research goals, not excuses to loosen gates until a backtest complies. Robustness decides promotion.

## Experiment workflow

For material experiments:

1. take the next chronological number from `docs/experiments/README.md`;
2. create/freeze the plan first when the experiment changes architecture or prospective rules;
3. create/update `docs/experiments/YYYY-MM-DD/NN-slug.md` before treating outcomes as canonical;
4. state objective, baseline, allowed changes, data discipline and status;
5. implement research logic under `research/` and broker/data utilities under `tools/`;
6. write durable machine evidence under `results/simulations/YYYY-MM-DD-slug/`;
7. preserve configs/metrics as JSON/CSV where applicable;
8. record negative findings and parity caveats;
9. update experiment/plan indexes;
10. update current algorithm documentation only when architecture/leader/lock meaningfully changes;
11. update this handoff when current state/next step changes.

Do not scatter canonical evidence into arbitrary folders. `scripts/` remains reserved for final paper-challenge executors; Experiment-58 capture/launcher utilities live under `tools/` and the discrimination logic lives under `research/`.

## Search and optimization rules

Prefer deterministic, interpretable mechanisms first.

Do not:

- optimize win rate alone;
- brute-force thresholds over heavily consumed datasets and call the winner robust;
- use hindsight opportunity labels as signal inputs;
- add engines merely to raise trade count;
- force capture/P&L targets by repeatedly loosening thresholds;
- use Experiment-58 future `label_*` fields as same-entry `feature_*` inputs.

If ML is introduced later, use strict past-only features, chronological walk-forward evaluation, frozen preprocessing/model/config before each next fold, and report rejected as well as accepted results. Optimize net expectancy/profit velocity after execution costs under risk/drawdown constraints.

Experiment 58 specifically seeks a **small structural hypothesis** for false reclaim, not a high-dimensional P&L optimizer.

## Evidence and provenance rules

Preserve failed candidates, parity failures, cost-stress failures, raw historical trade logs, machine configs, dataset hashes/splits and reasons for promotion/rejection.

When later work corrects an earlier result, preserve the historical artifact, document the correction and mark which value is canonical now. Do not rewrite history to make earlier experiments look cleaner.

## Git workflow

Canonical xau-lab work goes directly to `main` unless the user explicitly requests a branch/PR workflow.

Prefer the active client execution environment. GitHub Actions may be used as a fallback compute worker when local/client execution is unavailable or unsuitable, subject to the same hashes, replay gates, holdout rules and evidence discipline. Prefer temporary/manual workflows and remove them after use unless they have clear ongoing value.

Do not commit giant raw broker CSVs. Follow the compressed archive/manifest policy for curated datasets.

Keep commits focused and descriptive.

Before finishing a material research change, verify this file and `structure.md` against the actual repository state. Update them when they would otherwise send a fresh agent to an obsolete direction.

## Immediate next action

**Run the first Experiment-58 fresh four-hour shadow block.**

From `xau-lab` on the Windows machine:

```powershell
.\tools\start_m_acceptance_shadow_4h_block.ps1
```

After a valid block, if only the predeclared opportunity count is needed before the discovery tranche closes:

```powershell
.\tools\analyze_m_acceptance_shadow_block.ps1 -SessionId <SESSION_ID> -CountOnly
```

Do **not** run full label extraction merely to decide whether another block should be collected. Complete the frozen 8-block tranche (or the predeclared 12-block extension if the count condition triggers), then open labels for the discovery analysis.

## New-chat handoff rule

A new chat should not ask the user to reconstruct this project from memory. Read the canonical files, state the recovered status briefly, and continue from the latest unfinished Experiment-58 capture/discovery step.
