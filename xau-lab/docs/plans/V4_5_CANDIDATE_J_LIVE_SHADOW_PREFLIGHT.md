# Experiment 48P — Candidate J live-shadow harness preflight

Date: 2026-09-26
Status: **frozen before implementation preflight**

## Objective

Prepare the read-only live-shadow infrastructure needed before Experiment 48 starts on fresh post-reopen MT5 data.

This milestone does **not** claim live-market validation while XAUUSD is closed. It prepares and validates the tooling only.

## Safety contract

The live-shadow runner:

- sends no broker orders;
- never calls MT5 trade execution APIs;
- does not modify positions, pending orders or account settings;
- reads XAUUSD ticks only;
- writes local raw-tick capture and paper-shadow evidence only.

Any future real execution is a separate milestone.

## Candidate set

Run the already-frozen implementations side-by-side:

1. Candidate D;
2. Candidate H;
3. Candidate J.

Both 500 ms and 1 s grids are observed.

Candidate J remains frozen exactly as Experiment 47/47R. No rule or threshold changes are permitted.

## Live architecture

The runner has two independent responsibilities:

### Raw capture

- poll MT5 for all XAUUSD ticks;
- preserve `timestamp_utc,bid,ask,last,volume,flags,volume_real,spread,mid`;
- append to a session-local CSV;
- preserve broker-reported timestamp and host acquisition timestamp in the session manifest;
- tolerate inactive-market periods without manufacturing ticks.

### Shadow replay

At a fixed refresh cadence, replay a bounded recent raw window through the **same frozen research implementations** used by Experiments 43/47:

- Candidate D via the Candidate-H baseline implementation;
- Candidate H via its frozen flow-confirmed ghost exit;
- Candidate J via the frozen quote-flow phase controller.

The replay is paper/shadow monitoring only. It reconstructs decisions causally from data already received; it is not a low-latency execution engine.

Log:

- Candidate-D opportunity entries;
- Candidate-H extra exit events;
- Candidate-J TAKE / WAIT / SKIP entry-phase events;
- Candidate-J quote-phase exits;
- latest D/H/J paper metrics per grid;
- host-vs-broker clock offset;
- raw-tick count and last tick age.

## Weekend behavior

When the market is inactive:

- no synthetic tick is created;
- no strategy decision is advanced;
- the runner reports `MARKET_IDLE`;
- raw capture remains unchanged.

## Preflight

Before use on fresh data, run the harness in offline preflight mode against the existing recent24h archive and assert that the wrapper reproduces the already-recorded Experiment-47 D/H/J whole-window metrics on both grids.

This checks wiring only and is not new strategy evidence.

## Live session output

Default local folder:

`data/live_shadow/<session-id>/`

Files:

- `ticks.csv`;
- `session_manifest.json`;
- `shadow_status.json`;
- `shadow_events.jsonl`.

The live-shadow folder remains gitignored. A later explicit freeze step may archive a qualifying fresh snapshot for Experiment 48.

## Evidence contract

Record:
`docs/experiments/2026-09-26/48P-v4-5-candidate-j-live-shadow-preflight.md`

Runner:
`scripts/live_shadow_candidate_j.py`

Preflight evidence:
`results/simulations/2026-09-26-v4_5-candidate-j-live-shadow-preflight/`

Final20 remains sealed.
