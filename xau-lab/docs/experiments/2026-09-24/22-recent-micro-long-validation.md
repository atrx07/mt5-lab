# 22 — recent MT5 micro and long-horizon synthetic validation

Date: 2026-09-24

Status: **completed negative fresh-regime check; no V4.5 promotion**

## Objective

Freeze a bounded, recent XAUUSD tick snapshot from the connected MT5 terminal and compare the current provisional Candidate D with an independent micro/long-horizon alternative. Seek higher net profit and better trades after bid/ask costs, drawdown, exposure and 500 ms/1 s sensitivity; do not choose by gross profit or trade count alone. Any result from about one day of quotes is a fresh regime check, not lock or income evidence.

## Data and clock discipline

Use the last 24 hours ending at a frozen `symbol_info_tick` timestamp. Request `COPY_TICKS_ALL` with UTC-aware bounds as specified by the [official MT5 Python documentation](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py). Save raw CSV locally, its SHA-256 and acquisition metadata, then archive a deterministic lossless copy under `data/raw/` with a manifest. The terminal's tick clock currently appears about three hours ahead of host UTC; preserve both reported and acquisition clocks, measure the offset, and make no silent shift. Verify that the snapshot starts after the seven-day canonical source ended. Do not read the sealed final 20% of that source.

## Replay and selection protocol

1. Run the locked V4.4 golden parity gate on the original first-80% dataset at 500 ms and 1 s before using the recent snapshot. Use the unchanged canonical feature builder on the frozen snapshot; there is no golden P&L target for new data.
2. Replay V4.4, Candidate B, provisional Candidate D, and the independent Experiment 21 micro/long design with the same sampled features and executable bid/ask convention. Preserve position/engine trade ledgers when available. Distinguish short MICRO/BURST/impulse trades from longer PRIMARY/SECONDARY/trend trades.
3. Freeze a chronological seed/evaluation cut at 60% of the snapshot's raw ticks. Only use the seed for a bounded, interpretable improvement idea. Evaluate the frozen idea once on the later 40%, at both 500 ms and 1 s, with an additional $0.20 adverse fill on each side. Never promote from a tiny trade count or one favorable session.
4. Report net and cost-stressed P&L, PF, max marked or realized drawdown with its definition, trades/wins, median/mean holding time, exposure, micro/long attribution, and sampling degradation. Keep the ₹500 synthetic sizing and the existing 3% planned-risk/$4 emergency-stop discipline. No broker orders or unattended trading.

## Frozen source and boundary

The local MT5 snapshot contains 476,535 valid quotes from MT5-reported 2026-09-23 18:58:46.459 UTC through 2026-09-24 18:58:45.860 UTC. The host acquired it at 2026-09-24 15:58:48.152 UTC; the terminal-reported end was 10,797.91 s ahead of host UTC. Treat reported UTC dates as broker-clock labels, not verified civil UTC. The raw SHA-256 is `9243ac73c3d180417ff634fe9371a28939713a531c9ccfa63f919c94eb9a28b1`; the ignored raw CSV is preserved as deterministic gzip plus manifest under `data/`. The snapshot begins after the canonical seven-day dataset ends, so it does not overlap that dataset's sealed final 20%.

The 60% raw-row cut is 2026-09-24 12:35:33.013 on the reported clock. Canonical sampling produced 128,563 rows at 500 ms and 72,745 at 1 s. The median observed spread was $0.33, above Candidate D's $0.30 outer cap and the independent multi-ticket script's $0.25 cap. Both historical V4.4 golden gates passed before the recent-data comparisons.

## Seed attribution and one bounded revision

Candidate D lost ₹92.48 at 500 ms and ₹86.54 at 1 s on the seed. Its PRIMARY trades contributed -₹84.07 and -₹82.62 respectively. The independent Experiment 21 mode 1 lost ₹10.84 and ₹1.54; its impulse tickets contributed +₹3.60 and +₹7.78 while trend tickets contributed -₹14.44 and -₹9.32. This led to exactly one seed-derived change: mode 3 keeps mode 1's impulse admission, exit, sizing and risk rules, but disables trend ticket admission. It is an impulse-only research ablation, not a promoted all-horizon strategy.

| Model / recent segment | 500 ms P&L | 1 s P&L | 500 ms trades | 1 s trades |
| --- | ---: | ---: | ---: | ---: |
| V4.4 seed, realized only | -₹91.86 | -₹85.52 | 17 | 15 |
| Candidate B seed, realized only | -₹92.97 | -₹86.54 | 19 | 16 |
| Candidate D seed, realized only | -₹92.48 | -₹86.54 | 19 | 16 |
| Experiment 21 mode 1 seed, forced close | -₹10.84 | -₹1.54 | 17 | 12 |
| **Mode 3 seed, forced close** | **+₹3.73** | **+₹7.92** | **13** | **9** |
| V4.4 later evaluation, realized only | -₹143.18 | -₹45.21 | 17 | 15 |
| Candidate B later evaluation, realized only | -₹148.65 | -₹51.87 | 19 | 17 |
| Candidate D later evaluation, realized only | -₹149.92 | -₹52.31 | 19 | 17 |
| Experiment 21 mode 1 later evaluation, forced close | +₹4.24 | -₹3.99 | 12 | 10 |
| **Mode 3 later evaluation, forced close** | **-₹1.83** | **-₹1.81** | **10** | **7** |

Mode 3's later evaluation PF was 0.91 / 0.89, marked drawdown ₹10.86 / ₹11.13, and ticket exposure 0.413 / 0.279 hours at 500 ms / 1 s. An extra $0.20 adverse fill on **each side** worsened later P&L to -₹6.47 / -₹3.37. Its positive seed result therefore failed out-of-sample and cost stress. The same full rolling 24-hour quote window, replayed continuously with final forced liquidation, returned only +₹1.89 / +₹6.08 across 23 / 16 trades; cost stress made that -₹11.71 / -₹2.48. No reported UTC exit day approached ₹100. These are ₹500 synthetic results, not executable account returns.

## Accounting limits and decision

The independent multi-ticket simulator force-closes tickets on the last quote of each segment and after session gaps, and marks drawdown at executable bid/ask. The inherited V4.4/B/D diagnostic simulators report **realized trades only** and can leave an open position at segment end; their recent seed/evaluation P&L and realized-balance drawdown are therefore diagnostic, not directly rank-comparable to the forced-close multi-ticket results. No fresh-data promotion should be inferred from that comparison. The mode 3 versus mode 1 comparison uses the same forced-close simulator and split.

Mode 3 improves the exploratory full-window P&L relative to Experiment 21's modes 0/1, but it failed the frozen later segment on both grids and adverse-fill stress. It is **rejected for promotion**. Candidate D remains the provisional V4.5 leader on the first-80% canonical research record, but this fresh regime makes a lock less supportable. V4.4 remains the locked version. The final 20% seven-day holdout remains sealed; no order was sent.

Next: implement a fair forced-liquidation/terminal-equity diagnostic for the single-slot comparators without changing the canonical golden replay semantics. Collect additional non-overlapping recent snapshots to assess regime persistence before selecting a new micro/long admission rule. The existing raw-event admission idea remains a research direction, not an active tested candidate. Do not tune another threshold against this one later segment.

Evidence: `results/simulations/2026-09-24-recent-micro-long-validation/README.md`, `diagnostic_metadata.json`, and the preserved engine/ticket trade ledgers. Reproduce with `python research/v4_5_recent_validation.py` after restoring the two archived raw inputs as documented in `data/README.md`.
