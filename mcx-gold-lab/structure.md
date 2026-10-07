# mcx-gold-lab canonical structure

Status: **file-placement and repository-layout contract**

All paths below are relative to `mcx-gold-lab/`. Mirrors `xau-lab/structure.md`
conventions; where the two labs differ, this file wins for this lab.

## Top-level contract

```text
mcx-gold-lab/
├── agents.md
├── structure.md
├── README.md
├── requirements.txt
├── .gitignore
├── data/
├── docs/
├── research/
├── results/
├── scripts/
└── tools/
```

`scripts/` is reserved for final paper-challenge executors. `research/` owns the
harness, baselines, and intermediate experiment code. `tools/` owns cost/data
utilities. Do not create parallel structures (`experiments-v2/`, `archive2/`, …)
unless the user explicitly changes the project structure.

Canonical work lives on `main`.

## Root files

### `agents.md`
Operational instructions for any assistant/agent. Update when the canonical
research state changes (leader, latest experiment, dataset status, workflow).
Not an experiment log.

### `structure.md`
This file-placement contract. Update when structure or the examples herein go
stale. Review before every push.

### `README.md`
Human-facing overview: what the lab is, why MCX, current status, run commands,
safety caveats. Update on material status changes.

### `requirements.txt`
Python runtime dependencies. Current: pandas, numpy. Add a dependency here when
a committed script requires it. No hidden undeclared packages.

### `.gitignore`
Raw tick captures (`data/raw/*` except curated `.csv.gz`), synthetic pickles,
`__pycache__`, `.env` (broker credentials must NEVER be committed).

## `data/` — canonical market-data storage

```text
data/
├── README.md            # archival policy + capture workflow
├── manifests/
│   └── <dataset-manifest>.json
└── raw/
    ├── .gitkeep
    └── <curated-lossless-dataset>.csv.gz
```

Manifest minimum fields: schema version, dataset ID, instrument, contract,
source/platform/exporter, capture window, row count, first/last timestamp,
column list, archive path, archive SHA-256, provenance/contamination notes.

Naming: `<instrument>_<contract>_<kind>_<range>.csv.gz`, e.g.
`gold_petal_ticks_2026-10-08.csv.gz`. Synthetic files are prefixed `SYNTHETIC_`.

## `docs/`

```text
docs/
├── README.md
├── PROVENANCE.md
├── plans/        # phased research plan, venue selection rationale
└── experiments/  # numbered experiment records (00-cost-model, 01-..., ...)
```

Small files with clear ownership. No giant append-only research file.

## `research/`

Harness (`harness.py`), baselines (`baselines.py`), smoke runner
(`run_baselines.py`), and intermediate experiment code. Nothing here places
orders.

## `results/`

Machine-readable outputs: `cost_model/exp0.json`, smoke-test logs. Synthetic
results are labeled and segregated; they are harness evidence, not strategy
evidence.

## `scripts/`

Paper-challenge executors. Paper-only by construction: no broker order-placement
imports allowed in this directory (enforced by review, not by tooling — yet).

## `tools/`

`mcx_cost_model.py` (Experiment 0), `synth_ticks.py` (harness validation only),
`capture_ticks.py` (broker websocket capture — specified, to be built against
real API credentials).
