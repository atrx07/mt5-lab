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
- The next V4.5 step is a narrowly scoped raw-event admission test built identically before 500 ms and 1 s execution sampling, without changing canonical replay semantics.
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

`scripts/canonical_replay.py`

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

## Experiment workflow

For each material experiment:

1. determine the next chronological experiment number from `docs/experiments/README.md`;
2. create/update `docs/experiments/YYYY-MM-DD/NN-slug.md`;
3. state objective, baseline, allowed changes, data discipline, and status before treating results as canonical;
4. implement the research harness in `scripts/`;
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

GitHub Actions is not part of the normal XAU research execution path. When the canonical raw dataset is available in the active execution environment, run iterative simulations, diagnostics, validation and candidate development there. Commit the resulting algorithm/research scripts, experiment documentation and durable result artifacts back to their canonical locations on `main`.

Do not commit the ~220 MB raw CSV itself. Preserve the existing compressed archive/manifest policy for repository data.

Keep commits focused and descriptive.

Do not delete historical evidence simply to reduce clutter.

### Mandatory reference synchronization before every push

Before pushing completed XAU-lab research to `main`, review **both** this file and `structure.md` against the exact state being pushed. Update this file whenever the research state, provisional or locked leader, latest completed experiment, next step, workflow, replay or risk rule, holdout status, or other project-wide instruction changes. Update `structure.md` when layout/naming changes **or** its current script examples, result-directory examples, experiment references, or new-chat recovery path become stale.

Verify both references against `docs/experiments/README.md`, the latest experiment document, `docs/algorithms/v4_5.md`, the latest `results/simulations/` bundle, active research scripts, and actual candidate status. If either file needs no textual change, explicitly verify that it is already current; do not edit merely to change its timestamp. Inspect the final Git diff and staged paths, commit useful code, evidence, documentation and necessary reference updates together, then push. A push is incomplete if either reference would send a fresh agent to an obsolete experiment or research direction.

## Current active work

Latest completed experiment:

`docs/experiments/2026-09-24/20-v4-5-exposure-velocity.md`

Latest evidence:

`results/simulations/2026-09-24-v4_5-burst-path-autopsy/`

`results/simulations/2026-09-24-v4_5-confirmed-failure/`

`results/simulations/2026-09-24-v4_5-exposure-velocity/`

Current research scripts:

- `scripts/canonical_replay.py` — mandatory V4.4 parity and feature source;
- `scripts/v4_5_confirmed_failure.py` — Candidate D research replay;
- `scripts/v4_5_exposure_velocity.py` — latest completed Experiment 20 diagnostic and rejected seed variants.

No raw-event admission script for the next experiment exists yet.

Phase C1 tested 48 BURST lifecycle combinations and every one reproduced Candidate B exactly at both sampling grids. No Candidate C was promoted.

Experiment 18 found that immediate 30 s momentum zero-cross exits dominate every observed BURST trade. Experiment 19 tested 0/1/2/3/5 s confirmation on the seed, evaluated 1/2/3 s on the first-80% pool and promoted one second as provisional Candidate D.

Experiment 20 found that simple 120/300 s conditional exits, two-second SECONDARY persistence and short-horizon flow vetoes do not improve both grids on the seed. The 1 s matched-trade diagnostic identifies loss-making admissions absent at 500 ms, but simple sampled-grid filters also remove valuable 500 ms trades. Retain Candidate B as comparator and D as provisional leader. Test a truly common raw-event admission feature next, preserving the V4.4 oracle and final-20% holdout boundary.

The canonical replay timestamp path now explicitly normalizes datetimes to nanosecond resolution before epoch conversion so pandas 3 and earlier supported pandas runtimes use the same replay semantics. Golden V4.4 parity must still pass before any candidate evidence is accepted.

## New-chat handoff rule

A new chat should not ask the user to reconstruct the project from memory.

Read this file and `structure.md`, inspect the latest canonical artifacts on `main`, state the recovered current status briefly, and continue from the latest unfinished experiment.
