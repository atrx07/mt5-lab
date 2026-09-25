# Experiment 25 — cross-window engine robustness

Status: **completed diagnostic; no trading change and no promotion**.

This bundle compares Candidate D engine attribution between the canonical seven-day history and the separate Experiment 22 recent split ledgers.

The recent ledgers are realized-only and boundary-sensitive. Their summed P&L is descriptive engine attribution, not a full-window terminal-equity result.

Main finding: no engine is robust enough to receive a global permission rule. PRIMARY shows the clearest cross-window failure; recent MICRO/BURST counts are too small for a global conclusion. The next router must combine engine identity with the frozen raw-event regime state and independent-window evidence.

Reproduce from committed result ledgers with:

```powershell
python scripts\v4_5_cross_window_engine_robustness.py
```
