# Provenance

This repository was assembled after the first live-paper session from the chat transcript, uploaded runtime logs and saved CSV trade logs.

- `paper_challenge.py`, `paper_challenge_v2.py` and `paper_challenge_v3.py` are **behavior-preserving reconstructions** from the settings and run behavior recorded during the session. They are not claimed to be byte-identical to the original chat snippets.
- `paper_challenge_v3_1.py` preserves the V3.1 logic that was explicitly written in the session: persistent armed signals, fixed breakout level, bounded arm lifetime, multi-horizon momentum, hard stop, profit lock and confirmed reversal.
- `paper_challenge_v4.py` is a new successor implementation created from the later research findings.
- `results/paper_trades_v3.csv` and `results/paper_trades_v3_1.csv` are copied from the actual uploaded run logs and are the strongest historical evidence in this archive.

No script in this repository sends real MT5 orders.
