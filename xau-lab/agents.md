# xau-lab agent instructions

Status: **canonical project instructions for the XAUUSD lab**

This file exists so a new chat, agent, or coding session can recover the project rules without depending on conversation history.

## Read-first continuation protocol

When starting or resuming work on this project:

1. work from `main`; it is the canonical branch;
2. read this file;
3. read `structure.md`;
4. read `docs/replay/CANONICAL_REPLAY.md`;
5. read `results/regression/canonical_v4_4_reference.json`;
6. read `docs/algorithms/README.md` and the highest/current algorithm document;
7. read `docs/experiments/README.md` and the latest experiment record;
8. inspect the matching latest `results/simulations/<experiment>/` directory before proposing the next change;
9. prefer repository evidence over remembered chat context whenever they disagree.

Do not restart the research line from scratch just because a conversation ended.

## Project identity and objective

Project: `xau-lab` inside `atrx07/mt5-lab`.

Instrument: **XAUUSD** on MetaTrader 5 broker tick data.

The long-term engineering objective is to build a reliable automated XAUUSD trading algorithm/script that maximizes expected profit per unit time while keeping execution cost, drawdown, sampling fragility, and risk controlled.

For current research, "maximum profit in minimum time" must be measured rather than assumed. Important metrics include:

- net P&L;
- return and P&L per unit time;
- P&L per exposure hour;
- opportunity capture;
- profit factor;
- trade count and P&L per trade;
- holding time;
- max drawdown;
- chronological segment behavior;
- cost/slippage stress;
- 500 ms versus 1 s degradation;
- MFE/MAE where available.

Capture alone is not the optimization target.

## Current canonical state

As of the current research line:

- V4.4 is the latest **locked fractional research version**.
- V4.5 is **research in progress; not locked**.
- V4.5 Candidate D (one-second confirmed BURST failure exit) is the provisional research leader; Candidate B remains the verified comparator.
- Experiment 17 / V4.5-C Phase C1 is complete and produced no distinct candidate: all 48 lifecycle variants reproduced Candidate B exactly.
- Experiment 18 diagnosed every Candidate B BURST exit as an immediate 30 s momentum zero-cross. Experiment 19 selected Candidate D after seed and chronological evaluation.
- Experiment 20 diagnosed non-BURST exposure and sampling fragility. Seven seed variants failed joint 500 ms / 1 s selection; Candidate D remains provisional.
- Experiment 21 tested an independent three-ticket trend/impulse/reversal architecture. Its full initial prototype lost on both grids, and two bounded seed revisions failed joint-grid selection. No multi-ticket candidate was promoted or reached ₹100 on an observed UTC quote day.
- Experiment 22 froze a separate recent 24-hour MT5 snapshot. Candidate D lost heavily in realized-only recent diagnostics. A seed-derived impulse-only multi-ticket ablation improved its seed but lost on both later evaluation grids and under adverse-fill stress. No candidate was promoted or reached ₹100 on a reported quote day; the MT5 tick clock was about three hours ahead of host UTC.
- Experiment 23 established a raw-event, pre-sampling regime-normalization diagnostic without changing strategy rules. V4.4/B/D parity passed; 119 matched Candidate D entries showed 92.44% volatility, 89.92% spread, 92.44% efficiency, 95.80% activity and 76.47% full-key agreement between 500 ms and 1 s. BURST and MICRO were the most consistently positive by 4-hour windows; PRIMARY remained regime-dependent and SECONDARY was negative at 1 s.
- Experiment 24 tested a bounded first regime-router family: 48 single-category engine vetoes selected only on the 0-40% seed under joint-grid P&L, win-rate, trade-retention and drawdown criteria. Two seed variants qualified. The preselected MICRO-low-volatility veto improved both seed grids but reduced full first-80% 500 ms compounded P&L from ₹1,430.31 to ₹1,407.86 while improving 1 s from ₹385.25 to ₹398.05. It is rejected; Candidate D remains provisional.
- Experiment 25 compared Candidate D engine attribution between the canonical seven-day history and Experiment 22's non-overlapping recent split ledgers with no tuning. PRIMARY reversed from strongly positive historical aggregate P&L to -₹184.37 / -₹118.65 recent realized attribution at 500 ms / 1 s. MICRO and BURST also lost in the fresh split on very small counts; SECONDARY remained unstable and near flat only at 1 s. No engine receives a global permission rule.
- Experiment 26 replayed the exact frozen Experiment 23 raw-event regime schema on the non-overlapping recent 24-hour raw snapshot. Dataset archive and decompressed raw hashes matched the committed manifest. The state representation itself remained sampling-stable across 27 same-engine/same-side matched entries (92.59% volatility, 92.59% spread, 96.30% efficiency, 100% activity, 85.19% full-key agreement), but historical positive engine+grid+four-part regime keys did not transfer: those keys lost ₹90.74 on 23 recent 500 ms trades and ₹123.88 on 21 recent 1 s trades. No router is promoted.
- Experiment 27 froze `xau-state-v2`, a richer causal continuous state layer with 20 features covering normalized volatility/spread/activity, direction-normalized 10/30/60/300 s momentum, acceleration/exhaustion, raw flow alignment, pullback/extension context, market/execution heat and session age. No feature threshold or router was selected from P&L. Coverage was 100% for all short-horizon features on both known windows; the 300 s-derived features covered 96.9% historical and 95.8% recent trades because of causal warm-up. Cross-grid rank stability remained strong: median Spearman 0.916 on 119 historical matched pairs and 0.940 on 27 recent matched pairs.
- Experiment 28 starts Router v2 implementation without using another P&L threshold search. The router now has a frozen structural stronghold-score definition per engine, evaluates simultaneous engine candidates instead of fixed priority, falls through to the next candidate when a higher-scoring setup does not clear neutral score, and preserves HOLD when none clears it. Score components are equal-weight and use only `xau-state-v2`; the neutral score floor is 0.0 because all components are centered on causal baseline/neutral values. No Router v2 performance claim or promotion exists yet.
- Experiment 29 ran a **trade-ledger gate proxy**, not the full raw-tick fall-through router. Applying the frozen Router-v2 score to Candidate D's realized entry ledger retained 97.5% / 96.8% of canonical 500 ms / 1 s trades but reduced canonical compounded P&L to ₹1,181.58 / ₹219.73 because the score rejected a few historically large winning PRIMARY trades. On the recent 24-hour ledger it rejected one losing PRIMARY trade on each grid, improving the combined realized split attribution by about ₹14.4 while remaining deeply negative. A 10,000-scenario empirical regime-mixture bootstrap likewise showed no general profitability improvement. This proxy is diagnostic only and does not model simultaneous-candidate fall-through.
- Experiment 30 completed the full raw-tick fall-through replay on a user-authorized GitHub worker. Candidate D parity passed exactly. Router v2 retained 100% of canonical trades but reduced compounded P&L from ₹1,430.31 to ₹851.27 at 500 ms and from ₹385.25 to ₹297.67 at 1 s, with fewer wins on both grids. On the whole recent 24-hour raw window it modestly improved 500 ms from -₹223.27 to -₹210.63 but worsened 1 s from -₹135.91 to -₹144.22. Corrected real four-hour random-window stress also had worse mean expectancy on both grids. Candidate D remains the current winning candidate; the current Router-v2 score is not promoted and must not be tuned against these known outcomes.
- Experiment 31 traced Router-v2 damage to path-dependent cooldown/slot/timing cascades rather than direct score substitution alone.
- Experiment 32 tested a pre-frozen priority-preserving/rejection-latched Router v3. It was not promoted: canonical first80 remained below Candidate D and random-window mean expectancy was worse on both grids. Vetoes were PRIMARY-only and fallback never fired.
- Experiment 33 removed shared-slot/cooldown/compounding contamination in independent fixed-size shadow lanes. Historical first80 was positive for all four engines, but on the recent 500 ms window **all four engines lost independently**; at 1 s only SECONDARY stayed positive on nine trades. Independent engine entries were simultaneous only ~2-4% of the time, so routing alone cannot manufacture much complementarity.
- Experiment 34 freezes SNAPBACK, a structurally different countertrend/failed-continuation engine using only inherited Candidate-D thresholds and short-lifecycle constants; no parameter search is allowed. Experiment 35 separately freezes the no-search chronological predictability test of `xau-state-v2`: ridge alpha 1.0, past-only preprocessing/training, expanding historical walk-forward and historical->recent transfer. Both are diagnostics; neither may be promoted from known data.
- The final 20% research holdout has not been opened by the canonical replay harness.
- All canonical work is maintained directly on `main`.

Current Candidate B canonical results:

- 500 ms: +₹1,299.37, 17.3652% capture, 163 trades, median segment PF 1.361;
- 1 s: +₹365.25, 4.8814% capture, 156 trades, median segment PF 1.382.

Current provisional Candidate D canonical first-80% results:

- 500 ms: +₹1,430.31, 19.1152% capture, 163 trades, 81 wins, median segment PF 1.376;
- 1 s: +₹385.25, 5.1487% capture, 156 trades, 71 wins, median segment PF 1.378.

Candidate D is not locked. The 50–60% segment remains negative and the 1 s result remains fragile under cost stress. Do not create `paper_challenge_v4_5.py` from this evidence alone.

The 50% P&L-per-exposure-hour, 20% exposure-reduction and 20% compounded-P&L improvements are preferred strong-lock targets, not automatic discard or lock rules. A candidate narrowly missing one may remain lock-eligible pending review after a material overall Pareto improvement. Small practical PF/drawdown deterioration requires explicit, convincing compensation; no candidate locks automatically.

Current V4.5 direction:

- move 500 ms capture toward roughly 20% or better if it can be done robustly;
- reduce the very large 500 ms -> 1 s degradation;
- treat about 10% 1 s capture as an aspirational robustness level, not a forced optimization threshold;
- improve profit velocity;
- contain or improve the weak 50-60% chronological research segment;
- pass execution-cost stress before any V4.5 lock.

## Canonical truth hierarchy

When repository artifacts disagree, use this precedence:

1. this `agents.md` for project workflow and agent behavior;
2. `structure.md` for file-placement and naming rules;
3. `docs/replay/CANONICAL_REPLAY.md` for replay/preprocessing/accounting semantics;
4. `results/regression/canonical_v4_4_reference.json` for the current V4.4 regression oracle;
5. the current algorithm document under `docs/algorithms/`;
6. the latest experiment document under `docs/experiments/YYYY-MM-DD/`;
7. machine-readable evidence under `results/simulations/`;
8. historical prose and old ad-hoc replay numbers.

Historical evidence must never be deleted merely because a later canonical pipeline changes the comparison baseline.

## Canonical replay contract

All new V4.x candidate research must use the canonical replay path or explicitly extend it without changing its semantics.

Canonical harness:

`research/canonical_replay.py`

Canonical replay schema:

`xau-canonical-replay-v1`

Golden regression oracle:

`results/regression/canonical_v4_4_reference.json`

Before a non-baseline candidate result is accepted:

1. verify the dataset SHA-256;
2. build the canonical feature set;
3. replay locked V4.4 on the exact same feature arrays;
4. assert V4.4 against the golden oracle;
5. abort on any baseline drift;
6. only then run the candidate;
7. report candidate deltas against the same-harness V4.4 result.

The diagnostic `--no-baseline-assert` option must never be used as promotion/lock evidence.

If replay semantics genuinely need to change:

1. create a new replay schema version;
2. document the reason;
3. run old and new schemas side-by-side;
4. re-baseline locked strategies;
5. commit a new regression oracle;
6. only then make the new schema canonical.

Never silently edit the golden regression file just to make a candidate pass.

## Dataset contract

Canonical seven-day dataset:

- instrument: XAUUSD;
- source: MetaTrader 5 broker tick export;
- raw filename: `xau_ticks_7d.csv`;
- raw rows: 2,337,474;
- raw bytes: 220,449,602;
- raw SHA-256: `007e7ab10cc16519b544003dbe81521f46cf868bf267780932638d1e8cec86e5`;
- first timestamp: 2026-09-16T14:56:19.104000+00:00;
- last timestamp: 2026-09-23T14:56:18.226000+00:00.

Canonical archive:

`data/raw/xau_ticks_7d_2026-09-16_to_2026-09-23.csv.gz`

Archive manifest:

`data/manifests/xau_ticks_7d_2026-09-16_to_2026-09-23.json`

The raw ~220 MB CSV stays out of Git. The deterministic gzip archive plus manifest is the repository copy.

## Research split and holdout discipline

Canonical V4.x research is restricted to the first 1,869,979 raw rows.

Frozen raw boundaries:

`[0, 934989, 1168737, 1402484, 1636231, 1869979]`

Interpretation:

- 0-40%: seed/search;
- 40-50%: chronological evaluation 1;
- 50-60%: chronological evaluation 2;
- 60-70%: chronological evaluation 3;
- 70-80%: chronological evaluation 4;
- 80-100%: final holdout.

Do not read or optimize against the final 20% unless the user explicitly decides to open it as a milestone.

Important provenance caveat: the final 20% overlaps a previously observed Sep 23 live-paper period. If/when it is opened, report that contamination honestly; do not describe it as a pristine blind holdout.

For search-heavy work:

- select/tune on the seed region;
- use later chronological segments for rejection/promotion evidence;
- avoid repeatedly tuning directly against all four evaluation segments;
- preserve rejected variants and negative results when materially informative;
- never use hindsight opportunity labels as signal inputs.

## Canonical accounting

For canonical V4.x headline comparison:

- each of the five chronological first-80% segments starts from ₹500;
- segment return factors are compounded in chronological order;
- the constrained first-80% opportunity ceiling is ₹7,482.60;
- capture = compounded P&L / ₹7,482.60.

Historical one-pass or ad-hoc results may remain in old experiment records but are not substitutes for canonical replay.

Current V4.4 regression oracle:

- 500 ms: +₹1,097.659652, 14.669495% capture, 148 trades, 68 wins;
- 1 s: +₹333.271059, 4.453947% capture, 145 trades, 63 wins.

Older V4.4 lock figures of 16.36% at 500 ms and 11.54% at 1 s are preserved historical evidence from the older replay pipeline. They are **not** the V4.5+ parity oracle.

## Execution model and risk discipline

Unless a documented experiment explicitly changes these rules:

- BUY enters at ask and exits at bid;
- SELL enters at bid and exits at ask;
- spread is always paid;
- no fantasy mid-price fills;
- risk exits are deterministic/local;
- planned entry risk remains 3%;
- emergency stop remains $4 for the current V4.4/V4.5 line;
- synthetic leverage cap remains 100x where the locked strategy uses it;
- one shared open-position slot remains in force for the current composite architecture.
- Experiment 21's separate multi-ticket research branch used at most three same-direction synthetic tickets, at most 1% planned risk each and at most 3% aggregate planned entry risk; it did not change Candidate D's one-slot architecture or authorize paper/live execution.

The INR/USD constant used by the historical/current research scripts is 95.7021 unless a future version explicitly documents a change.

The broker minimum observed during testing was 0.01 lot = 1 oz, while the ₹500 synthetic research size can be smaller than that. Backtest/paper sizing is therefore not automatically executable live.

## Paper/live boundary

Current strategy scripts are research and paper-trading code.

Do not silently add `mt5.order_send()`, real-money execution, broker credentials, or an unattended live executor to an existing paper script.

A move to real execution must be explicit, separately documented, and treated as a new milestone with:

- live-size feasibility;
- broker contract verification;
- spread/slippage protections;
- hard position/risk caps;
- emergency kill switch;
- reconnect/error handling;
- duplicate-order protection;
- paper/live mode separation;
- audit logging.

Never describe backtest or paper results as guaranteed future profitability.

## Versioning rules

Locked versions are immutable research baselines.

Do not edit a locked strategy in place to represent a new idea.

Examples:

- changes after locked V4.3 became V4.4;
- changes after locked V4.4 belong to V4.5.

For fractional research:

- candidate letters/names may be used inside a version before lock;
- rejected candidates stay recorded;
- do not create a final `paper_challenge_vX_Y.py` merely because a seed search looks good;
- create/promote the runnable locked paper version only after the research evidence supports the lock.

A major-version graduation requires stronger evidence than a fractional lock: realistic execution modeling, multiple regimes, drawdown checks, cost stress, holdout evidence, and live-paper validation.

## Code placement contract

Code placement is strict:

- `scripts/` contains **only final paper-challenge executors** (`paper_challenge*.py`) for historical/locked versions;
- `research/` contains canonical replay, diagnostics, feature/model experiments, candidate searches and all intermediate research harnesses;
- `tools/` contains broker probes, tick capture/export and dataset archive/restore helpers;
- never put a new intermediate experiment in `scripts/`;
- do not create `paper_challenge_v4_5.py` until V4.5 is actually selected and locked for paper execution.

When an experiment needs a helper, feature implementation or model harness, add it under `research/` and link it from the experiment/evidence docs.

## Experiment workflow

For each material experiment:

1. determine the next chronological experiment number from `docs/experiments/README.md`;
2. create/update `docs/experiments/YYYY-MM-DD/NN-slug.md`;
3. state objective, baseline, allowed changes, data discipline, and status before treating results as canonical;
4. implement the research harness in `research/`;
5. write generated evidence to `results/simulations/YYYY-MM-DD-slug/`;
6. include a result-directory `README.md` when the experiment produces a durable evidence bundle;
7. save machine-readable configs/metrics as JSON/CSV;
8. record negative findings and parity caveats;
9. update `docs/experiments/README.md`;
10. update `docs/algorithms/<version>.md` only when the architecture/current leader/lock meaningfully changes;
11. update `docs/algorithms/README.md` when a new algorithm document is added;
12. update root/xau-lab overview docs when the current project status changes materially.

Do not scatter canonical experiment evidence into arbitrary new folders.

## Search and optimization rules

Prefer deterministic, interpretable rules first.

If ML is introduced later:

- use it as a meta-labeler or clearly documented component rather than silently replacing the whole signal path;
- train only on past data;
- use chronological walk-forward evaluation;
- freeze scaler/model/config before each next fold;
- report accepted and rejected candidate outcomes;
- do not optimize win rate alone;
- optimize net expectancy/profit velocity after execution costs under risk/drawdown constraints.

Do not keep adding new engines simply to raise trade count. A new engine needs evidence that it captures a distinct opportunity class.

Do not force numeric targets such as 20% capture or 10% 1 s capture by loosening thresholds until the backtest complies. Targets are research goals; robustness decides promotion.

## Evidence and provenance rules

Preserve:

- failed algorithms;
- rejected candidates;
- parity failures;
- cost-stress failures;
- raw historical trade logs;
- machine-readable configs;
- dataset hashes/splits;
- notes explaining why a candidate was or was not promoted.

When a later pipeline corrects an earlier result:

- keep the historical artifact;
- document the correction;
- mark which value is canonical now;
- never rewrite history to make earlier experiments look cleaner.

For historical V1-V3.1 source and logs, consult `docs/PROVENANCE.md`.

## Git workflow

Canonical project work goes directly to `main`.

Do not create a feature/research branch unless the user explicitly asks for one.

Do not require a PR for ordinary canonical xau-lab research unless the user explicitly asks for a PR workflow.

Prefer the active client-side execution environment for XAU simulations, diagnostics, validation and candidate development. If that runtime is unavailable because of infrastructure/tooling errors (for example a CAAS internal client exception), the user has authorized GitHub Actions as a **fallback compute worker**.

Fallback-worker rules:

- use Actions only when the normal execution runtime is unavailable or unsuitable for the required run;
- prefer a temporary manual-only `workflow_dispatch` workflow rather than a push-triggered loop;
- smoke-test the worker/runtime before launching an expensive replay when practical;
- never change strategy logic merely to make the worker environment pass;
- persist the resulting evidence under the normal `results/` paths and document any runtime-only compatibility fix;
- remove temporary worker workflows after the run unless they have clear ongoing value;
- GitHub-worker output is subject to the same dataset hashes, replay parity gates, holdout discipline and evidence rules as local execution.

Commit the resulting algorithm/research scripts, experiment documentation and durable result artifacts back to their canonical locations on `main`.

Do not commit the ~220 MB raw CSV itself. Preserve the existing compressed archive/manifest policy for repository data.

Keep commits focused and descriptive.

Do not delete historical evidence simply to reduce clutter.

### Mandatory reference synchronization before every push

Before pushing completed XAU-lab research to `main`, review **both** this file and `structure.md` against the exact state being pushed. Update this file whenever the research state, provisional or locked leader, latest completed experiment, next step, workflow, replay or risk rule, holdout status, or other project-wide instruction changes. Update `structure.md` when layout/naming changes **or** its current script examples, result-directory examples, experiment references, or new-chat recovery path become stale.

Verify both references against `docs/experiments/README.md`, the latest experiment document, `docs/algorithms/v4_5.md`, the latest `results/simulations/` bundle, active research scripts, and actual candidate status. If either file needs no textual change, explicitly verify that it is already current; do not edit merely to change its timestamp. Inspect the final Git diff and staged paths, commit useful code, evidence, documentation and necessary reference updates together, then push. A push is incomplete if either reference would send a fresh agent to an obsolete experiment or research direction.

## Current active work

Latest completed diagnostic:

`docs/experiments/2026-09-25/33-v4-5-independent-opportunity-atlas.md`

Experiment 33 confirms the variable-environment problem is upstream of routing: all four existing engines are independently negative on recent 500 ms; only SECONDARY is positive on recent 1 s; exact simultaneous engine opportunities are only ~2–4%. Do not tune another router around this evidence.

Current frozen engine experiment:

`docs/experiments/2026-09-25/34-v4-5-snapback-foundation.md`

SNAPBACK is a structurally different countertrend/failed-continuation lane. Its signal is the natural low-efficiency complement of MICRO using existing Candidate-D thresholds; its short lifecycle reuses BURST constants with no countertrend-incompatible momentum-zero-cross. Rules are frozen before P&L evaluation. Known data may reject it but cannot promote it; no post-result threshold tuning is allowed.

Latest evidence:

`results/simulations/2026-09-24-v4_5-burst-path-autopsy/`

`results/simulations/2026-09-24-v4_5-confirmed-failure/`

`results/simulations/2026-09-24-v4_5-exposure-velocity/`

`results/simulations/2026-09-24-v4_5-multi-ticket-horizon/`

`results/simulations/2026-09-24-recent-micro-long-validation/`

`results/simulations/2026-09-25-v4_5-regime-normalization/`

`results/simulations/2026-09-25-v4_5-regime-router-probe/`

`results/simulations/2026-09-25-v4_5-cross-window-engine-robustness/`

`results/simulations/2026-09-25-v4_5-regime-portability/`

`results/simulations/2026-09-25-v4_5-state-v2-freeze/`

`results/simulations/2026-09-25-v4_5-router-v2-implementation/`

`results/simulations/2026-09-25-v4_5-router-v2-preflight/`

`results/simulations/2026-09-25-v4_5-router-v2-full-replay/`

`results/simulations/2026-09-25-v4_5-router-v2-arbitration-audit/`

Current research scripts:

- `research/canonical_replay.py` — mandatory V4.4 parity and feature source;
- `research/v4_5_confirmed_failure.py` — Candidate D research replay;
- `research/v4_5_exposure_velocity.py` — completed Experiment 20 diagnostic and rejected seed variants.
- `research/v4_5_multi_ticket_horizon.py` — completed negative Experiment 21 independent multi-ticket replay; exploratory research only.
- `tools/capture_recent_xau_ticks.py` — read-only, clock-audited MT5 quote snapshot capture.
- `research/v4_5_recent_validation.py` — Experiment 22 historical parity-gated recent synthetic validation and ledgers.
- `research/v4_5_regime_normalization.py` — Experiment 23 raw-event, pre-sampling normalized regime diagnostic and engine/window robustness audit.
- `research/v4_5_regime_router_probe.py` — Experiment 24 bounded single-category regime-veto search and one-time chronological evaluation; selected probe rejected.
- `research/v4_5_cross_window_engine_robustness.py` — Experiment 25 no-tuning comparison of Candidate D engine behavior across historical and recent preserved ledgers.
- `research/v4_5_regime_portability.py` — Experiment 26 exact frozen Experiment 23 regime replay on the recent raw snapshot plus historical-key portability and PRIMARY exit-state diagnostics.
- `research/v4_5_state_v2_freeze.py` — Experiment 27 frozen continuous raw-event state-v2 extraction, coverage, cross-grid stability and descriptive outcome profiling; no router selection.
- `research/v4_5_router_v2.py` — Experiment 28 stronghold-aware Router v2 implementation with dynamic engine arbitration, fall-through and HOLD; frozen before unseen validation.
- `research/v4_5_router_v2_preflight.py` — Experiment 29 reproducible trade-ledger gate proxy and seeded regime-mixture bootstrap; diagnostic only, not a full fall-through replay.
- `research/v4_5_router_v2_full_eval.py` — Experiment 30 full raw-tick Candidate D vs Router v2 replay across canonical/recent data and deterministic random real four-hour windows.
- `research/v4_5_router_v2_arbitration_audit.py` — Experiment 31 decision-level Router-v2/Candidate-D divergence and counterfactual arbitration audit; no strategy changes.
- `research/v4_5_router_v3_priority_latched.py` — Experiment 32 priority-preserving, rejection-latched Router v3 candidate; structurally frozen before known-data evaluation.
- `research/v4_5_independent_opportunity_atlas.py` — Experiment 33 fixed-size independent shadow-lane atlas for engine-family complementarity; diagnostic only.
- `research/v4_5_snapback_engine.py` — Experiment 34 pre-registered SNAPBACK countertrend engine foundation; independent fixed-size evaluation only.
- `tools/restore_dataset.py` — hash-verified restoration of ignored raw CSVs from committed archives.

No regime router is promoted. Experiment 24's selected veto is rejected. Experiments 25-26 show that neither engine identity nor the four-part historical regime key is sufficient as a portable permission rule. Experiment 27 freezes `xau-state-v2`; Experiment 28 freezes Router v2; Experiment 29's proxy is negative; Experiment 30's full raw-tick replay confirms the frozen Router-v2 score does not beat Candidate D; Experiment 31 shows the dominant failure is path-dependent cooldown/slot/timing cascade rather than direct score substitution alone. Candidate D remains the provisional historical leader. Next specify a path-aware, priority-preserving architecture without tuning the known score floor.

Phase C1 tested 48 BURST lifecycle combinations and every one reproduced Candidate B exactly at both sampling grids. No Candidate C was promoted.

Experiment 18 found that immediate 30 s momentum zero-cross exits dominate every observed BURST trade. Experiment 19 tested 0/1/2/3/5 s confirmation on the seed, evaluated 1/2/3 s on the first-80% pool and promoted one second as provisional Candidate D.

Experiment 20 found that simple 120/300 s conditional exits, two-second SECONDARY persistence and short-horizon flow vetoes do not improve both grids on the seed. The 1 s matched-trade diagnostic identifies loss-making admissions absent at 500 ms, but simple sampled-grid filters also remove valuable 500 ms trades. Retain Candidate B as comparator and D as provisional leader.

Experiment 21 followed the user's separate multi-position direction under the unchanged 3% basket-risk ceiling. Three prototypes were preserved: the initial full-run design lost on both grids, and impulse-first and reversal seed revisions failed joint 500 ms / 1 s selection. None met the ₹100-per-observed-UTC-day research target. Do not promote or deploy this branch; Candidate D remains provisional.

Experiment 22 captured and archived 476,535 recent quotes after the seven-day dataset. Its historical V4.4 parity gates passed. The recent Candidate D and independent trend tickets lost; disabling trend tickets in a bounded mode 3 yielded +₹3.73/+₹7.92 seed P&L but -₹1.83/-₹1.81 later evaluation P&L at 500 ms/1 s, worse with $0.20 adverse fill per side. Mode 3 is rejected. Single-slot recent segment figures are realized-only and may omit open boundary positions; compare them only after a fair terminal-equity diagnostic. The terminal-reported tick clock was about three hours ahead of host UTC, so reported date labels need caution.

Experiment 23 then froze a raw-event regime representation before execution-grid sampling. The diagnostic uses relative rolling volatility/range, spread, path efficiency and quote activity rather than P&L-selected absolute regime thresholds. It does not disable any engine or change Candidate D. Its first purpose is to stop designing each successive rule around quirks of the same seven-day episode. Reuse this exact representation on non-overlapping snapshots before selecting a router. Candidate D remains provisional, V4.4 locked, and the final 20% sealed.

The canonical replay timestamp path now explicitly normalizes datetimes to nanosecond resolution before epoch conversion so pandas 3 and earlier supported pandas runtimes use the same replay semantics. Golden V4.4 parity must still pass before any candidate evidence is accepted.

## New-chat handoff rule

A new chat should not ask the user to reconstruct the project from memory.

Read this file and `structure.md`, inspect the latest canonical artifacts on `main`, state the recovered current status briefly, and continue from the latest unfinished experiment.
