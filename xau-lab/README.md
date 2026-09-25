# xau-lab

Experimental XAUUSD research and paper-trading lab built around MetaTrader 5.

> **Safety / scope:** every script in this lab is paper-only by default. None of the live-paper scripts call `mt5.order_send()`. The synthetic position sizes used in the ₹500 experiments are below the broker's observed minimum live size and are not directly executable on that account.

## Agent / new-chat continuation

For any new chat or coding-agent session, read these first:

1. [`agents.md`](agents.md) — canonical project instructions, research discipline, current state and continuation rules.
2. [`structure.md`](structure.md) — canonical file/directory placement and naming contract.

Repository evidence on `main` is the source of truth when chat memory disagrees.

## Environment observed during the experiments

- Instrument: `XAUUSD`
- MT5 account: MetaQuotes-Demo during testing
- Broker minimum volume observed: `0.01 lot`
- Contract size observed: `100 oz / lot`
- Minimum live position: `0.01 lot = 1 oz`
- INR/USD conversion used in the original scripts: `95.7021`
- Tick source: the locally running MT5 terminal
- BUY enters at ask and exits at bid; SELL enters at bid and exits at ask.

## Evolution

| Version | Main idea | Recorded outcome |
| --- | --- | --- |
| V1 | 1 oz fixed synthetic exposure on ₹100 | catastrophic sizing failure; ₹100 → -₹13.89 |
| V2 | dynamic fractional synthetic exposure | recovered full 14-trade run ₹500 → ₹439.40 |
| V3 | confirmed 5 s + 15 s breakouts | ₹500 → ₹482.53 |
| V3.1 | persistent armed breakouts | ₹500 → ₹463.46 |
| V4 | short-horizon pullback / resumption | seven-day development baseline remained strongly negative |
| V4.1 locked baseline | 30m trend → 5m context → 60s pullback/resumption + 3% risk sizing | development ₹500 → ₹627.52; validation ₹500 → ₹538.79 |
| V4.2 experimental | V4.1 primary + secondary breakout outside slow directional gate | first-80% continuous capture ~5.51% |
| **V4.3 locked** | **regime-adaptive V4.2 composite** | **canonical five-segment compounded result +₹603.60; ~8.07% capture** |
| **V4.4 locked** | **V4.3 + MICRO structural engine + Candidate K management** | **historical lock: 16.36% / 11.54%; reproducible replay oracle: 14.67% / 4.45%; final holdout unopened** |
| **V4.5 research** | **V4.4 + BURST with confirmed-failure exit under study** | **Provisional Candidate D: 19.1152% / 5.1487% capture; not locked; 50–60% and 1 s robustness remain weak** |

V4.4 is the current locked fractional experimental paper version. V4.5 is the active research line and is not locked.

Experiment 20 found that simple early PRIMARY/SECONDARY releases and SECONDARY sampled-flow vetoes fail joint 500 ms / 1 s seed selection. Candidate D remains provisional. The 50% profit-velocity / 20% exposure / 20% compounded-P&L improvements are a preferred strong-lock region; a narrower Pareto improvement may remain lock-eligible pending review, never automatically locked.

Experiment 21 tested a separate, bounded three-ticket trend/impulse/reversal research script. Its initial full first-80% result lost money on both grids; two seed revisions also failed joint-grid selection. No tested prototype reached ₹100 on an observed UTC quote day.

Experiment 22 froze a separate recent 24-hour MT5 quote snapshot and ran the historical V4.4 parity gate before synthetic replay. Candidate D lost heavily in realized-only recent diagnostics. A bounded impulse-only revision of the multi-ticket script improved its seed but lost on both later evaluation grids and under adverse-fill stress. Its continuous 24-hour synthetic P&L was only +₹1.89 at 500 ms / +₹6.08 at 1 s before stress. The terminal tick clock appeared about three hours ahead of host UTC. No candidate was promoted; Candidate D remains provisional, and V4.4 remains locked.

Experiment 23 changes the research method rather than the strategy. It derives normalized regime state directly from raw tick events before the 500 ms / 1 s execution grids, using only past completed windows. V4.4 golden parity, Candidate B trace parity and Candidate D parity all passed. Across 119 matched Candidate D entries, the raw-event regime labels agreed between grids on volatility 92.44%, spread 89.92%, efficiency 92.44%, activity 95.80%, and the complete four-part regime key 76.47%. No engine gate or strategy rule was promoted from this diagnostic.

Experiment 24 then tested 48 simple one-category engine vetoes using only the 0-40% seed. Two met the predeclared joint-grid seed criteria; the stronger seed pick blocked MICRO when raw relative 60-second range was below 0.75. It improved both seed grids, but chronological evaluation reduced full first-80% 500 ms compounded P&L to ₹1,407.86 versus Candidate D's ₹1,430.31, while 1 s improved to ₹398.05 versus ₹385.25. Trade count stayed near baseline, but joint-grid performance did not improve, so the router probe is rejected. The frozen regime schema still needs independent-window validation before another router family is selected.

Experiment 25 compared Candidate D engine attribution across the canonical historical window and Experiment 22's non-overlapping recent split ledgers without changing any rule. PRIMARY moved from +₹586.30 / +₹156.00 historical engine P&L at 500 ms / 1 s to -₹184.37 / -₹118.65 in the recent realized split attribution. MICRO and BURST also lost in the fresh split but on only 3–5 trades per grid; SECONDARY remained unstable. The eventual router therefore has to condition on market state rather than simply declaring an engine globally good or bad.

Experiment 26 applied the frozen `xau-raw-event-regime-v1` schema unchanged to the separate recent 24-hour raw snapshot. The representation remained highly consistent between 500 ms and 1 s, but historical four-part regime keys did **not** preserve profitability: historically positive engine/grid/regime keys lost ₹90.74 on 23 recent 500 ms trades and ₹123.88 on 21 recent 1 s trades. The bins are therefore retained as descriptive state, not a router permission table. PRIMARY's recent failure was dominated by emergency-stop and momentum-zero-cross exits while its max-hold exits remained profitable, pointing to an admission/exhaustion problem rather than a complete loss of the underlying trend opportunity class.

Experiment 27 now freezes `xau-state-v2`: 20 causal continuous raw-event features designed to distinguish whether an engine is entering inside its stronghold or after the opportunity is already exhausted. No threshold was fitted from either known dataset. The feature layer had full short-horizon coverage and strong 500 ms/1 s rank stability on both the seven-day benchmark and recent 24-hour window. The next profit-seeking router must be evaluated on a **new** snapshot, with a pre-registered goal of improving P&L and win rate while retaining at least 95% of Candidate D's system-level trade count through engine fall-through rather than simply deleting opportunities.

Starting with V4.5 research, all candidate simulations must use the parity-gated canonical replay harness. V4.4's strategy parameters are unchanged; the 14.67% / 4.45% regression values are a reproducible measurement re-baseline used only as the future comparison oracle. The earlier 16.36% / 11.54% lock outputs remain preserved as historical research evidence.

V4.3 replay-parity documentation was corrected during the V4.4 lock: its canonical +₹603.60 figure is the compounded result of five independently reset research segments, not a literal one-pass continuous replay.

Any change to the locked V4.4 configuration belongs to V4.5 research.

The final 20% research holdout remains unopened by the canonical replay workflow.

## Current experimental paper version

```powershell
python scripts\paper_challenge_v4_4.py
```

Previous versions remain available:

```powershell
python scripts\paper_challenge_v4_3.py
python scripts\paper_challenge_v4_2.py
python scripts\paper_challenge_v4_1.py
```

Completed V4.5-C Phase C1 research harness:

```powershell
python research\v4_5_profit_velocity_search.py xau_ticks_7d.csv
```

Latest V4.5 diagnostics and candidate replay:

```powershell
python research\v4_5_burst_path_autopsy.py xau_ticks_7d.csv
python research\v4_5_confirmed_failure.py xau_ticks_7d.csv --confirm-sec 1
python research\v4_5_exposure_velocity.py xau_ticks_7d.csv
python research\v4_5_multi_ticket_horizon.py xau_ticks_7d.csv --mode 0
python research\v4_5_recent_validation.py
python research\v4_5_regime_normalization.py xau_ticks_7d.csv
python research\v4_5_regime_router_probe.py xau_ticks_7d.csv
python research\v4_5_cross_window_engine_robustness.py
python research\v4_5_regime_portability.py xau_ticks_7d.csv xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_state_v2_freeze.py xau_ticks_7d.csv xau_ticks_recent_24h_2026-09-24.csv.gz
```

Historical tick export:

```powershell
python tools\export_xau_ticks.py --days 7
```

## Dataset preservation

The seven-day broker-tick dataset and Experiment 22's frozen recent snapshot are tracked under [`data/`](data/).

The raw ~220 MB CSV remains ignored. A lossless gzip archive plus a SHA-256 manifest is the canonical repository copy.

See [`data/README.md`](data/README.md) for the exact archive/push workflow.

## Documentation

- [Canonical agent instructions](agents.md)
- [Canonical repository structure](structure.md)
- [Algorithm index](docs/algorithms/README.md)
- [Experiment index](docs/experiments/README.md)
- [V4.5 research line](docs/algorithms/v4_5.md)
- [V4.5-C profit-velocity experiment](docs/experiments/2026-09-24/17-v4-5-c-profit-velocity.md)
- [V4.5 BURST-path autopsy](docs/experiments/2026-09-24/18-v4-5-burst-path-autopsy.md)
- [V4.5 confirmed-failure experiment](docs/experiments/2026-09-24/19-v4-5-confirmed-failure.md)
- [V4.5 exposure-velocity experiment](docs/experiments/2026-09-24/20-v4-5-exposure-velocity.md)
- [V4.5 independent multi-ticket experiment](docs/experiments/2026-09-24/21-v4-5-multi-ticket-horizon.md)
- [Recent MT5 micro/long synthetic validation](docs/experiments/2026-09-24/22-recent-micro-long-validation.md)
- [V4.5 raw-event regime-normalization foundation](docs/experiments/2026-09-25/23-v4-5-regime-normalization.md)
- [V4.5 bounded regime-router probe](docs/experiments/2026-09-25/24-v4-5-regime-router-probe.md)
- [V4.5 cross-window engine robustness](docs/experiments/2026-09-25/25-v4-5-cross-window-engine-robustness.md)
- [V4.5 frozen regime portability](docs/experiments/2026-09-25/26-v4-5-regime-portability.md)
- [V4.5 state-v2 feature freeze](docs/experiments/2026-09-25/27-v4-5-state-v2-freeze.md)
- [V4.1 optimization evidence](docs/experiments/2026-09-23/08-v4-1-optimization.md)
- [V4.2 algorithm](docs/algorithms/v4_2.md)
- [V4.3 algorithm](docs/algorithms/v4_3.md)
- [V4.4 algorithm](docs/algorithms/v4_4.md)
- [V4.3 capture-target research and lock](docs/experiments/2026-09-24/10-v4-3-capture-target-research.md)
- [V4.4 parity fix and lock](docs/experiments/2026-09-24/13-v4-4-parity-and-lock.md)
- [Canonical replay contract](docs/replay/CANONICAL_REPLAY.md)
- [Canonical replay freeze](docs/experiments/2026-09-24/16-canonical-replay-freeze.md)
- [Dataset archive policy](data/README.md)
- [Provenance](docs/PROVENANCE.md)

## Code layout

- `scripts/` — final paper-challenge executors only;
- `research/` — canonical replay and intermediate strategy/feature/model experiments;
- `tools/` — MT5/data capture, archive, restore and probe utilities.

## Canonical replay gate

Every new V4.x candidate must pass the locked V4.4 regression assertion inside `research/canonical_replay.py` before its result is considered valid. If preprocessing, sampling, features, boundaries or accounting drift, the run fails instead of silently producing a new baseline.

## Research discipline

Major-version graduation requires realistic bid/ask execution, holdout evidence with its provenance caveat, multiple regimes, drawdown checks, stress tests and live-paper validation. Fractional versions may be locked as experimental iterations when they show a distinct measurable improvement while preserving fixed risk discipline. Hourly earning/capture targets are evaluation benchmarks, not instructions to force trades or increase risk.
