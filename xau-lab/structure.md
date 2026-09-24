# xau-lab canonical structure

Status: **canonical file-placement and repository-layout contract**

This file defines where XAUUSD lab work belongs so future chats and agents can continue the project without inventing new folders or scattering evidence.

All paths below are relative to `xau-lab/` unless otherwise stated.

Repository-level GitHub Actions infrastructure may live under `/.github/workflows/`. It is execution infrastructure only; canonical XAU research code, documentation and evidence still belong inside `xau-lab/`.

Current workflow:

`/.github/workflows/xau-v4-5-c-full-run.yml`

It restores the canonical archived dataset, runs the V4.5-C harness, uploads the result bundle and commits generated evidence back to `main`. Do not use workflow directories as research storage.

## Top-level contract

```text
xau-lab/
├── agents.md
├── structure.md
├── README.md
├── requirements.txt
├── .gitignore
├── data/
├── docs/
├── results/
└── scripts/
```

Use these existing directories. Do not create parallel structures such as `research/`, `experiments-v2/`, `new-results/`, `archive2/`, or version-specific top-level folders unless the user explicitly changes the project structure.

Canonical work lives on `main`.

## Root files

### `agents.md`

Purpose: operational instructions for any assistant/agent working on xau-lab.

Contains:

- project objective;
- current version/research state;
- replay and dataset rules;
- risk/execution discipline;
- experiment workflow;
- versioning rules;
- holdout rules;
- Git workflow;
- new-chat recovery instructions.

Update this file only when a project-wide instruction changes.

Do not use it as an experiment log.

### `structure.md`

Purpose: this file-placement contract.

Update it when the canonical repository structure or naming convention changes.

Do not put strategy results here.

### `README.md`

Purpose: human-facing project overview and current high-level status.

It should summarize:

- what xau-lab is;
- current locked/experimental version;
- important run commands;
- dataset/documentation entry points;
- major safety/research caveats.

When current project status changes materially, update this overview.

### `requirements.txt`

Purpose: Python runtime dependencies.

Current dependencies:

- MetaTrader5;
- pandas;
- numpy;
- numba.

Add a dependency here when a committed script requires it.

Avoid hidden undeclared package dependencies.

### `.gitignore`

Purpose: local-only/generated/noise policy.

Current important rule:

- raw `xau_ticks_*.csv` broker exports stay out of Git;
- deterministic curated `.csv.gz` archives under `data/raw/` are allowed.

## `data/` — canonical market-data storage

```text
data/
├── README.md
├── manifests/
│   └── <dataset-manifest>.json
└── raw/
    ├── .gitkeep
    └── <curated-lossless-dataset>.csv.gz
```

### `data/README.md`

Owns dataset archival policy and the archive workflow.

### `data/manifests/`

Store one manifest per curated dataset.

A manifest should record at minimum:

- schema version;
- dataset ID;
- instrument;
- source/platform/exporter;
- raw filename;
- raw SHA-256;
- raw byte size;
- row count;
- first/last timestamp;
- column list;
- archive relative path;
- archive format/compression;
- archive SHA-256;
- archive size;
- experiment references;
- provenance/contamination notes.

Current canonical manifest:

`data/manifests/xau_ticks_7d_2026-09-16_to_2026-09-23.json`

### `data/raw/`

Store curated lossless compressed market-data archives only.

Current canonical archive:

`data/raw/xau_ticks_7d_2026-09-16_to_2026-09-23.csv.gz`

Do not commit the ~220 MB raw CSV.

For future large/recurring datasets, prefer Git LFS or external object storage instead of allowing normal Git history to grow indefinitely.

### Dataset naming

Preferred:

`<instrument>_<kind>_<range>.csv.gz`

with an adjacent manifest under `data/manifests/`.

Keep names stable once referenced by experiment evidence.

## `docs/` — canonical human-readable research documentation

```text
docs/
├── README.md
├── PROVENANCE.md
├── algorithms/
├── experiments/
├── plans/
└── replay/
```

Do not create one giant append-only research file. The project intentionally uses small files with clear ownership.

### `docs/README.md`

Index/description of the documentation sections.

### `docs/PROVENANCE.md`

Owns source provenance and historical-recovery notes.

Use it for questions such as:

- was a script recovered from the original local lab or reconstructed later?
- which logs are original run evidence?
- did line-ending transport or reconstruction affect source history?
- was an earlier result later corrected?

Do not bury provenance corrections only inside chat.

## `docs/algorithms/` — strategy-generation documentation

```text
docs/algorithms/
├── README.md
├── common-execution.md
├── v1.md
├── v2.md
├── v3.md
├── v3_1.md
├── v4.md
├── v4_1.md
├── v4_2.md
├── v4_3.md
├── v4_4.md
├── v4_5.md
└── future-jev.md
```

### Purpose

One file per strategy generation or stable research line.

Algorithm documents describe:

- status: historical / experimental / locked / research in progress;
- architecture;
- entry logic;
- exit/management logic;
- risk model;
- canonical research evidence;
- limitations;
- implementation script;
- replay/parity notes when relevant.

### Naming

Use:

- `v4_5.md`, not `v4.5.md`;
- lowercase version files;
- one canonical file per generation.

Candidate-specific detail normally belongs in experiment/result evidence, not a new algorithm file for every candidate.

Example:

- V4.5 Candidate B and V4.5-C remain documented under `v4_5.md` plus their experiment records until V4.5 is locked.

### `docs/algorithms/README.md`

Must index every canonical algorithm document.

Update it when a new algorithm file is added.

### `common-execution.md`

Owns execution assumptions shared across versions, such as bid/ask fill direction and synthetic sizing conventions.

When a shared assumption changes globally, update this file and document the change in the relevant experiment.

### `future-jev.md`

Reserved future-integration note. Do not mix speculative future architecture into locked algorithm documents unless promoted.

## `docs/experiments/` — chronological lab notebook

```text
docs/experiments/
├── README.md
├── YYYY-MM-DD/
│   ├── NN-slug.md
│   ├── NN-slug.md
│   └── ...
└── ...
```

Current sessions use:

- `2026-09-23/` for experiments 00-08;
- `2026-09-24/` for experiments 09 onward.

### Naming

Use:

`docs/experiments/YYYY-MM-DD/NN-short-descriptive-slug.md`

Examples:

- `13-v4-4-parity-and-lock.md`
- `15-v4-5-burst-candidate-b.md`
- `17-v4-5-c-profit-velocity.md`

Experiment numbers are chronological across the project, not reset each day.

Before creating a new experiment, inspect `docs/experiments/README.md` and use the next number.

### Experiment document contents

A durable experiment record should normally include:

- title and date;
- status;
- objective;
- baseline/reference;
- data/split discipline;
- exact allowed change;
- methodology/search scope;
- canonical/same-harness comparisons;
- chronological segment behavior;
- cost/sampling stress where relevant;
- rejected ideas/negative results;
- parity caveats;
- decision;
- evidence directory links;
- next step.

For an in-progress experiment, create/update the record before treating generated outputs as canonical evidence.

### `docs/experiments/README.md`

This is the chronological experiment index.

Every new numbered experiment must be added here.

Never rely on chat order as the experiment index.

## `docs/plans/` — pre-implementation proposals/specifications

```text
docs/plans/
├── README.md
├── V4_1_PROPOSAL.md
├── V4_4_RUN_SPEC.md
└── V4_5_RUN_SPEC.md
```

Purpose: preserve what was planned before implementation so later results can be compared against the original intent.

Use for substantial new version directions, run specifications, or architecture changes.

Do not rewrite a plan after results arrive to make the plan look prescient. Add status/supersession notes instead.

Plans are not evidence.

Experiment docs record what was actually tested.

## `docs/replay/` — replay semantics and contracts

Current canonical file:

`docs/replay/CANONICAL_REPLAY.md`

Purpose:

- sampling rules;
- feature-build rules;
- session/reset rules;
- accounting rules;
- dataset boundaries;
- regression-gate requirements;
- replay schema change control.

Replay semantics must not be duplicated differently in multiple new documents.

If replay v1 changes materially, create/version a new replay contract rather than silently altering the old baseline.

## `results/` — preserved machine-readable evidence

```text
results/
├── README.md
├── paper_trades*.csv
├── regression/
└── simulations/
```

### `results/README.md`

Owns the inventory/interpretation of recovered historical live-paper logs stored at results root.

### Historical root CSVs

Current root historical evidence:

- `paper_trades.csv` — V1;
- `paper_trades_v2.csv` — V2;
- `paper_trades_v3.csv` — V3;
- `paper_trades_v3_1.csv` — V3.1.

These exist for historical provenance.

Do not place new simulation bundles or arbitrary generated CSVs at results root.

New research evidence belongs under `results/simulations/`.

## `results/regression/` — frozen machine regression oracles

Current canonical oracle:

`results/regression/canonical_v4_4_reference.json`

Purpose: machine-readable values that must reproduce before candidate promotion evidence is valid.

Rules:

- treat golden files as immutable for their schema;
- do not edit expected values merely because code changed;
- if replay semantics change, version the schema and re-baseline explicitly;
- preserve previous oracle/history.

Do not store ordinary candidate outputs here.

## `results/simulations/` — canonical experiment evidence bundles

Each durable simulation/research experiment gets one directory.

Preferred naming:

`results/simulations/YYYY-MM-DD-<short-experiment-slug>/`

Existing examples:

- `2026-09-23-development-baseline/`
- `2026-09-23-v4_1-optimization/`
- `2026-09-24-v4_2-hourly-capture/`
- `2026-09-24-v4_3-capture-target/`
- `2026-09-24-v4_3-exit-harvest/`
- `2026-09-24-v4_4-more-trades/`
- `2026-09-24-v4_4-manager-optimization/`
- `2026-09-24-v4_4-lock/`
- `2026-09-24-v4_5-first-event-flow/`
- `2026-09-24-v4_5-burst-candidate-b/`

Expected current V4.5-C directory:

`results/simulations/2026-09-24-v4_5-c-profit-velocity/`

### Result-directory contents

Use only the files needed to make the run reproducible and reviewable.

Common patterns already used by the project:

- `README.md` — human-readable result interpretation;
- `*_config.json` — exact candidate/locked configuration;
- `locked_config.json` — exact configuration of a locked version;
- `run_metadata.json` — dataset/run/search metadata;
- `split_manifest.json` or `research_pool_split.json` — split identity/boundaries;
- `comparison.csv` — baseline/candidate metric comparison;
- `segment_results.csv` / `*_segments.csv` — chronological segment metrics;
- `stress_summary.csv` / `*_stress.csv` — execution stress;
- `sampling_robustness.csv` / `sampling_stress.csv` — sampling sensitivity;
- `locked_summary.csv` — locked aggregate metrics;
- `iteration_summary.csv` / `family_summary.csv` / `search_budget_summary.csv` — search history;
- `*_trades.csv` or `*_trades_instrumented.csv` — detailed trade ledger when needed;
- engine/exit/hourly diagnostic CSVs when they materially support a decision;
- canonical interval JSONs such as `canonical_500ms.json` and `canonical_1s.json`.

Do not invent a new file type when an existing convention fits.

### Result immutability

After an experiment is documented as completed:

- do not overwrite result files with a different run while keeping the same interpretation;
- if a rerun is a parity correction of the same experiment, document that correction explicitly;
- if methodology changes materially, create a new numbered experiment/result directory;
- preserve rejected/negative evidence when it informed decisions.

### Human + machine pair

For important durable evidence, prefer:

- human interpretation in experiment/result `README.md`;
- machine-readable metrics/config in CSV/JSON.

Do not make a chat transcript the only record of a result.

## `scripts/` — runnable project code

Current categories:

### Data/broker utilities

- `xau_probe.py` — MT5 XAUUSD contract/environment probe;
- `export_xau_ticks.py` — broker tick exporter;
- `archive_dataset.py` — hash/manifest/deterministic gzip archive helper.

### Historical/current paper strategy scripts

- `paper_challenge.py` — V1;
- `paper_challenge_v2.py` — V2;
- `paper_challenge_v3.py` — V3;
- `paper_challenge_v3_1.py` — V3.1;
- `paper_challenge_v4.py` — V4;
- `paper_challenge_v4_1.py` — V4.1;
- `paper_challenge_v4_2.py` — V4.2;
- `paper_challenge_v4_3.py` — V4.3;
- `paper_challenge_v4_4.py` — locked V4.4 current experimental paper version.

Naming rule:

`paper_challenge_v<major>_<minor>.py`

Do not create `paper_challenge_v4_5.py` until V4.5 is actually selected/locked for paper execution.

### Replay/research scripts

- `replay_lab.py` — older/general replay utility;
- `canonical_replay.py` — mandatory V4.x parity-gated replay source of truth;
- `v4_5_profit_velocity_search.py` — active V4.5-C search harness.

For new research harnesses, use a descriptive version-prefixed name under `scripts/`, for example:

`v4_5_<purpose>.py`

Do not put research scripts inside result directories.

### Script output placement

Research scripts should write durable generated evidence to their matching `results/simulations/<experiment>/` directory.

Temporary console-only diagnostics need not be committed.

Historical paper scripts currently write some log files relative to the working directory. When preserving those outputs as canonical evidence, place/archive the evidence under the appropriate `results/` location and document provenance.

Avoid writing new permanent artifacts into `scripts/`.

## Canonical cross-linking rules

Every accepted/current research line should be discoverable through links, not memory.

When adding a new experiment:

1. add the experiment doc to `docs/experiments/YYYY-MM-DD/`;
2. index it in `docs/experiments/README.md`;
3. write evidence to the matching `results/simulations/` directory;
4. link the experiment doc to the evidence directory;
5. if the algorithm meaningfully changes, update the version doc under `docs/algorithms/`;
6. if a new algorithm doc is added, index it in `docs/algorithms/README.md`;
7. update `xau-lab/README.md` if the current version/status changes materially.

## Naming conventions

### Versions

Use underscores in filenames:

- `v4_5.md`
- `paper_challenge_v4_5.py`

Use normal dotted notation in prose:

- V4.5

### Experiments

Document:

`docs/experiments/YYYY-MM-DD/NN-slug.md`

Evidence directory:

`results/simulations/YYYY-MM-DD-slug/`

The document number need not appear in the result-directory name if the descriptive slug already uniquely matches the experiment, but the experiment doc must link to it.

### Configs

Prefer explicit names:

- `candidate_b_config.json`;
- `locked_config.json`;
- `run_metadata.json`.

### Metrics

Prefer stable snake_case field/column names and explicit units:

- `pnl_inr`;
- `max_drawdown_inr`;
- `hold_sec`;
- `capture_ratio`;
- `spread_usd`.

Do not mix percentages and ratios under ambiguous field names.

## What not to do

Do not:

- create a separate branch for normal xau-lab research unless explicitly requested;
- create duplicate directory trees for a new chat;
- save canonical results only in chat;
- overwrite historical failures;
- put raw 220 MB CSV data into Git;
- store candidate simulation files at repository root;
- place experiment prose inside `scripts/`;
- place runnable source code inside `results/`;
- silently change replay semantics;
- silently replace the V4.4 regression oracle;
- call historical ad-hoc replay values the current parity baseline;
- open the 80-100% holdout during ordinary tuning;
- create a locked paper script before the corresponding research version is actually locked.

## New-chat structure recovery

A fresh assistant should be able to reconstruct the project by reading, in order:

```text
agents.md
structure.md
README.md
docs/replay/CANONICAL_REPLAY.md
results/regression/canonical_v4_4_reference.json
docs/algorithms/README.md
docs/algorithms/v4_5.md
docs/experiments/README.md
docs/experiments/2026-09-24/17-v4-5-c-profit-velocity.md
results/simulations/2026-09-24-v4_5-burst-candidate-b/
results/simulations/2026-09-24-v4_5-c-profit-velocity/   (when generated)
```

If the latest experiment number/version changes later, follow the indexes rather than assuming the paths above remain the newest.
