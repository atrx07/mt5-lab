# Research code

This directory contains XAUUSD canonical replay, diagnostics, feature/model experiments, candidate searches and intermediate research harnesses.

`../scripts/` is reserved for final paper-challenge executors only.

Rules:
- keep canonical replay and intermediate experiment code here;
- preserve research scripts that materially support experiment evidence;
- write durable outputs to `../results/simulations/<experiment>/`;
- do not move a research harness into `../scripts/` until the corresponding strategy version is selected and locked for paper execution.

Canonical replay entry point: `canonical_replay.py`.
