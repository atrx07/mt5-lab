# Provenance

This repository was assembled from the live-paper session, uploaded runtime output, saved CSV trade logs, and—after the first repo pass—the recovered contents of the original local `xau-lab` directory.

## Recovered original local source

On 2026-09-23 the original local files were recovered and promoted into the canonical repository:

- `tools/xau_probe.py`
- `scripts/paper_challenge.py`
- `scripts/paper_challenge_v2.py`
- `scripts/paper_challenge_v3.py`
- `scripts/paper_challenge_v3_1.py`

The earlier repository versions of V1/V2/V3 were behavior-preserving reconstructions created before the old local directory was available. Those reconstructions remain visible in Git history, but the files on `main` now use the recovered original source text. Text transport through Git/GitHub may normalize line endings from the Windows originals.

`paper_challenge_v4.py` is different: it is a new successor implementation created from the later research findings, not a recovered historical file.

## Recovered raw run logs

The old local directory also supplied the raw CSVs now archived under `results/`:

- `paper_trades.csv` — V1
- `paper_trades_v2.csv` — V2
- `paper_trades_v3.csv` — V3
- `paper_trades_v3_1.csv` — V3.1

These raw logs are the strongest historical evidence for the corresponding runs.

A useful correction came from this recovery: the V2 log did not actually end at the six-trade checkpoint previously discussed in chat. The recovered file contains **14 completed trades** and finishes at **₹439.40**. The earlier **₹475.48** figure is preserved as the balance after trade 6, not the final V2 run balance.

No historical or current script in this lab sends real MT5 orders.


## Repository layout note (2026-09-25)

The repository was reorganized so `scripts/` contains only final paper-challenge executors. Replay/research harnesses moved to `research/`, and broker/data helpers moved to `tools/`. This was a path/layout refactor only; historical strategy logic and preserved experiment evidence were not reinterpreted.
