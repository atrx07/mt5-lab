# Results

Raw run artifacts preserved from the original local XAUUSD lab.

| File | Strategy | Completed trades | Final recorded balance |
| --- | --- | ---: | ---: |
| [`paper_trades.csv`](paper_trades.csv) | V1 | 2 | -₹13.89 |
| [`paper_trades_v2.csv`](paper_trades_v2.csv) | V2 | 14 | ₹439.40 |
| [`paper_trades_v3.csv`](paper_trades_v3.csv) | V3 | 3 | ₹482.53 |
| [`paper_trades_v3_1.csv`](paper_trades_v3_1.csv) | V3.1 | 18 | ₹463.46 |

These are evidence files, not performance claims. They preserve the actual experiment outputs so later analysis can be reproduced and corrected when necessary.

The V2 file is particularly important because it revealed that the live session continued beyond the earlier six-trade checkpoint: ₹475.48 was an intermediate balance, while the recovered full run ended at ₹439.40.


## Research simulation evidence

Versioned offline research evidence lives under [`simulations/`](simulations/). Each important completed experiment keeps a human-readable `README.md` beside machine-readable CSV/JSON output.

Current V4.5 evidence chain:

- [Experiment 32 — Router v3 priority-latched](simulations/2026-09-25-v4_5-router-v3-priority-latched/) — not promoted;
- [Experiment 33 — independent engine opportunity atlas](simulations/2026-09-25-v4_5-independent-opportunity-atlas/) — existing engines broadly fail together on the recent hostile regime;
- [Experiment 34 — SNAPBACK foundation](simulations/2026-09-25-v4_5-snapback-foundation/) — rejected unchanged;
- [Experiment 35 — state-v2 walk-forward predictability](simulations/2026-09-25-v4_5-state-v2-walkforward-predictability/) — transferable predictability not demonstrated;
- [Experiment 36 — microstate-v1 foundation](simulations/2026-09-25-v4_5-microstate-v1-freeze/) — retained as outcome-blind representation evidence only.

Candidate D remains the provisional V4.5 research leader. The canonical final20 holdout remains sealed. For the authoritative current state and next step, read [`../agents.md`](../agents.md) and [`../structure.md`](../structure.md).
