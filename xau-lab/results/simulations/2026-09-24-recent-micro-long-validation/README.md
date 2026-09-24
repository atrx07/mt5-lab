# Experiment 22 — recent MT5 synthetic replay

Status: **completed; no candidate promoted**. This directory is synthetic research evidence, not broker executions or a live profit log.

Source: `data/manifests/xau_ticks_recent_24h_2026-09-24.json` and its deterministic gzip archive. The frozen 24-hour raw source has 476,535 valid quotes and SHA-256 `9243ac73c3d180417ff634fe9371a28939713a531c9ccfa63f919c94eb9a28b1`. MT5's reported tick clock was about three hours ahead of host UTC during capture. No timestamp correction was applied. The canonical seven-day final 20% was not inspected.

Method: `scripts/v4_5_recent_validation.py` verifies both dataset hashes, runs historical V4.4 golden parity on 500 ms and 1 s, applies the unchanged canonical feature builder to the recent snapshot, and compares V4.4/B/D with the independent multi-ticket modes 0/1. A 60% raw-row chronological cut defined the seed. Seed horizon attribution selected one bounded ablation, multi-ticket mode 3, which disables trend ticket admission while retaining mode 1 impulse rules. The later 40% was evaluated once. Ticket results include forced liquidation at segment end and $0.20 adverse fill per side stress. `diagnostic_metadata.json` records exact metrics and split indices; `*_trades.csv` files preserve ledgers.

| Mode 3 metric | 500 ms | 1 s |
| --- | ---: | ---: |
| Seed P&L | +₹3.73 | +₹7.92 |
| Later evaluation P&L | -₹1.83 | -₹1.81 |
| Later evaluation with adverse fills | -₹6.47 | -₹3.37 |
| Continuous full-window P&L | +₹1.89 | +₹6.08 |
| Continuous full-window with adverse fills | -₹11.71 | -₹2.48 |
| Full-window trades / wins | 23 / 11 | 16 / 8 |
| Full-window PF | 1.05 | 1.23 |
| Full-window marked drawdown | ₹14.04 | ₹11.31 |
| Full-window ticket exposure | 0.982 h | 0.649 h |

No reported UTC exit day approached ₹100. The recent seed gain did not survive chronological evaluation or cost stress, and the trade counts are small. Mode 3 is rejected for promotion. Mode 1 and mode 0 also lost on the continuous full window. Candidate D remains provisional on canonical first-80% history; V4.4 remains locked.

V4.4/B/D segment outputs are realized-only diagnostics from inherited simulators, which may leave a position open at the segment boundary. Their recent P&L and realized-balance drawdown must not be ranked directly against forced-close ticket P&L. A fair terminal-equity diagnostic is a next step; do not change the V4.4 golden semantics silently.

The complete experiment interpretation, data-clock caveat, selection discipline and next step are in `docs/experiments/2026-09-24/22-recent-micro-long-validation.md`. Restore the ignored raw CSVs with `scripts/restore_dataset.py` before reproducing the evidence. No broker order was sent.
