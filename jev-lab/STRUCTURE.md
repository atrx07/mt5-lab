# jev-lab canonical structure

Status: **canonical file and documentation layout**. All paths below are relative to `jev-lab/`.

## Directory tree

```text
jev-lab/
├── AGENTS.md                 project rules and research discipline
├── STRUCTURE.md              this placement and naming contract
├── README.md                 human-facing status and entry points
├── .gitignore                local secrets and large generated data
├── configs/                  frozen, versioned experiment/policy settings
│   ├── .gitkeep
│   ├── 2026-09-24-00-btc-spot-baseline.json
│   └── 2026-09-24-01-jev-entry-shadow.json
├── data/
│   ├── README.md             acquisition, retention and manifest rules
│   ├── raw/                  immutable local source captures; ignored by Git
│   │   └── .gitkeep
│   ├── derived/              reproducible feature/cache files; ignored by Git
│   │   └── .gitkeep
│   └── manifests/            versioned source metadata and hashes
│       ├── .gitkeep
│       └── 2026-09-24-00-btc-spot-baseline.json
├── docs/
│   ├── README.md             documentation index
│   ├── algorithms/           versioned strategy and policy specifications
│   │   ├── README.md
│   │   └── baseline-v1.md
│   ├── experiments/          dated protocols, findings and decisions
│   │   ├── README.md
│   │   ├── 2026-09-24-00-btc-spot-baseline.md
│   │   └── 2026-09-24-01-jev-entry-shadow.md
│   ├── plans/                scoped implementation or milestone plans
│   │   └── README.md
│   └── sources/              dated research on external APIs/bots/venues
│       ├── README.md
│       ├── 2026-09-24-binance-spot-data.md
│       └── 2026-09-24-typesafe-api.md
├── results/
│   ├── README.md             evidence-bundle contract and index
│   ├── backtests/            historical replay outcomes
│   │   ├── .gitkeep
│   │   └── 2026-09-24-00-btc-spot-baseline/
│   │       ├── README.md
│   │       ├── config.json
│   │       ├── summary.json
│   │       └── trades.csv
│   ├── forward/              timestamped shadow and paper observations
│   │   └── .gitkeep
│   └── benchmarks/           latency, cost, data and execution diagnostics
│       └── .gitkeep
├── scripts/                  CLI entry points and one-off acquisition tools
│   ├── README.md
│   ├── capture_binance_klines.py
│   ├── probe_jev.py
│   └── replay_baseline.py
├── src/jev_lab/              reusable Python package
│   ├── README.md
│   ├── __init__.py
│   ├── binance_spot.py
│   ├── client.py
│   └── paper.py
└── tests/                    focused checks for meaningful invariants
    ├── README.md
    ├── test_client.py
    ├── test_paper.py
    └── fixtures/
        └── synthetic_choice.json
```

Create modules and dependencies only when an experiment needs them. The Jev client exists, but a strategy implementation, market connector, and order executor do not yet exist. Do not create parallel top-level `research/`, `archive/`, `runs/`, or `v2/` trees. If the structure genuinely needs to change, edit this file and move the affected indexes and links together.

## Ownership of root files

- `AGENTS.md`: objectives, current canonical state, research and execution rules, recovery steps. Update when lab-wide policy or status changes; do not use it as a run log.
- `STRUCTURE.md`: paths, naming, artifact contracts. Update with every structural change; keep the tree truthful.
- `README.md`: concise project overview, current stage, how to reproduce current work, and links to the latest evidence. Update when milestones change.
- `.gitignore`: excludes secrets, local raw data, derived caches and tool noise. Do not rely on it to make unsafe output safe; inspect files before committing.

## Configurations and code

`configs/<experiment-id>.json` stores the exact selected market, venue, model ID, prompt/policy version, risk limits, data IDs, fees, latency assumptions, and deterministic random seed when applicable. Once a run is cited, keep its config immutable. If a setting changes, create a new experiment ID.

`src/jev_lab/` owns reusable components as they are needed: data adapters, feature calculation, model client, policy, risk, replay, accounting, and audit logging. `scripts/` contains thin, documented command-line entry points; avoid duplicating strategy logic there. Declare dependencies at the lab root when executable code is first added, and pin enough versions to reproduce cited runs. `tests/` checks consequential contracts such as no look-ahead, fee accounting, limits, and fail-closed behavior; it is not a copy of implementation code.

## Data and provenance

`data/raw/` holds original market captures locally and remains Git-ignored. Never edit a raw capture in place. `data/derived/` holds regenerable features, resamples, and model-response caches locally. For durable large evidence, use a separately identified archive or artifact store and record its location and hash in a manifest; do not silently drop the only copy.

`data/manifests/<dataset-id>.json` is the versioned source of truth for every dataset. Record at minimum: dataset ID and schema, source and acquisition method, market/instrument and venue, time range and timezone, source and capture timestamps, fields and units, row/event counts, missing/duplicate/gap checks, raw and any archive SHA-256 hashes, storage location, licensing/redistribution limits, and known clock or quality caveats. If order-book data is used, record depth and snapshot/update semantics. If trades are used, record side convention. Do not claim a dataset is clean merely because it parsed.

## Documentation

- `docs/algorithms/README.md` indexes strategy versions. Create `baseline-v1.md`, `candidate-<slug>.md`, or `vN.md` as appropriate. Each document states status, market, input features, decision and skip logic, execution/risk rules, frozen config, evidence, and limitations. Locked versions are never edited to express a new strategy.
- `docs/experiments/README.md` is the chronological index. Name each record `YYYY-MM-DD-NN-slug.md`, with `NN` increasing within the date. The record states the predeclared question, baseline, allowed change, data/split, metrics and cost assumptions, then results, interpretation, and next decision. Keep unsuccessful experiments indexed.
- `docs/plans/` holds future work and implementation plans. A plan is not evidence that an experiment ran.
- `docs/sources/` holds dated notes on external Jev implementations, official API specifications, markets, and venues, with direct links and a clear line between verified facts and inference. Recheck changeable claims before relying on them.

## Results and evidence bundles

Use one result directory per experiment: `results/<mode>/<experiment-id>/`, where `<mode>` is `backtests`, `forward`, or `benchmarks` and `<experiment-id>` matches the experiment document stem. Each durable bundle should contain:

```text
README.md       what ran, source IDs, reproducibility command, caveats and decision
config.json     frozen effective settings, including model/prompt versions
summary.json    machine-readable net metrics and baseline comparison
```

Add trade, fill, decision, latency, cost, and period-level ledgers as CSV/JSONL only when relevant. Log model request hashes and timestamps; preserve full sanitized requests/responses in a controlled artifact when needed for exact replay. Never commit secrets, private account data, or unlicensed third-party market data. Label synthetic, paper, and live records explicitly. A result without a matching manifest and frozen config is diagnostic only, not promotion evidence.

## Change and review checklist

Before presenting a new result, check that: the source manifest exists; the baseline and candidate used the same conditions; train/evaluation boundaries are recorded; all costs and the fill model are disclosed; model version and prompts are frozen; negative outcomes are retained; indexes and status pages point to the new evidence; and `git diff --check` passes. Do not describe a candidate as profitable without specifying the measured period, execution mode, costs, and uncertainty.
