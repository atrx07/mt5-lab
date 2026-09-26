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

Experiment 27 froze `xau-state-v2`: 20 causal continuous raw-event features designed to distinguish whether an engine is entering inside its stronghold or after the opportunity is already exhausted. No threshold was fitted from either known dataset. The feature layer had full short-horizon coverage and strong 500 ms/1 s rank stability on both the seven-day benchmark and recent 24-hour window. It also pre-registered the stronghold-router goal: improve P&L and win rate while retaining at least 95% of Candidate D's system-level trade count through engine fall-through rather than simply deleting opportunities.

Experiment 28 froze the first Router v2 implementation. Instead of a fixed PRIMARY → SECONDARY → MICRO → BURST priority, the flat-state router gathers every simultaneously eligible engine, computes an engine-specific stronghold score from `xau-state-v2`, ranks qualifying opportunities, falls through when a candidate is rejected, and can HOLD when none clears neutral. The score was structurally specified with equal component weights and no P&L-fitted threshold.

Experiment 29 added a known-data **gate-proxy preflight**. It reproduced Candidate D's canonical trade ledger exactly, then applied the frozen stronghold score only to those realized entries. The proxy preserved about 97% of trades but damaged the seven-day benchmark while removing only one losing recent PRIMARY entry per grid. A seeded 10,000-scenario empirical regime-mixture bootstrap also failed to show a profitability advantage. Because that proxy could not model simultaneous-engine fall-through, it remained diagnostic and led directly to the full raw-tick replay in Experiment 30.

Experiment 30 then ran the **full raw-tick fall-through router** on a user-authorized GitHub worker. Candidate D parity passed exactly. Router v2 retained all canonical trades but cut 500 ms compounded P&L from **₹1,430.31 to ₹851.27** and 1 s from **₹385.25 to ₹297.67**, with lower win rates. On the whole recent 24-hour raw window it improved 500 ms only modestly (-₹223.27 → -₹210.63) and worsened 1 s (-₹135.91 → -₹144.22). Corrected contiguous-session four-hour stress windows also showed worse mean expectancy. **Candidate D therefore remains the V4.5 leader; the current Router-v2 score is not promoted.** Experiment 31 completed the decision-level arbitration audit. It reproduced Experiment 30 exactly and found that direct score substitutions explain only a small fraction of the loss. The dominant failure is **path dependence**: a HOLD or engine substitution changes cooldown history and shared-slot occupancy, causing delayed entries, missed Candidate-D winners, new losing follow-ons and then smaller 3%-of-balance sizing on otherwise identical later trades. In the historical 500 ms 0-40% segment, the -₹353.97 gap decomposes into -₹148.85 of missing D trades, -₹74.81 of Router-only losses, -₹51.06 of timing shifts and -₹79.25 of balance-sizing drag on identical trades. Candidate D remains leader; next architecture work must preserve path/priority rather than sweep the score floor.

Experiment 32 froze Router v3 before measuring its P&L. It recovered some Router-v2 canonical damage but remained below Candidate D: +₹1,162.46 / +₹214.06 at 500 ms / 1 s versus +₹1,430.31 / +₹385.25. Recent results improved slightly versus D but stayed negative (-₹210.63 / -₹128.87). Most importantly, **fallback entries were zero on canonical first80**; every veto was a PRIMARY-only opportunity. Router v3 is not promoted.

Experiment 33 stopped tuning routers around the same fixed data and measured each existing engine independently. Historical edge exists in all four lanes, but on recent 500 ms **PRIMARY, SECONDARY, MICRO and BURST all lose independently**; at recent 1 s only SECONDARY stays positive. Exact simultaneous entries occur on only ~2–4% of events. The engine family itself therefore lacks enough cross-regime complementarity.

Experiments 34-36 deliberately stop treating the known windows as a tuning scoreboard. Frozen SNAPBACK was rejected unchanged (-₹153.04 / -₹44.78 historical fixed-size P&L at 500 ms / 1 s and zero recent realized opportunities). The separately frozen state-v2 ridge transfer test was weak/anti-correlated historically and essentially uncorrelated on recent transfer. Experiment 36 then added outcome-blind `xau-microstate-v1`: 23 new raw-event features with 100% coverage and strict cross-grid median Spearman 0.869 historical / 0.935 recent. It is a representation foundation, not a candidate. Candidate D remains the V4.5 leader, and the next strategy-changing hypothesis must be frozen before genuinely new non-overlapping raw data is evaluated.

Experiment 37 froze the first actual `xau-microstate-v1` strategy use before reading its outcomes: Candidate E preserved Candidate D and deferred a PRIMARY entry only when both immediate direction-normalized raw mid movement and raw event imbalance contradicted the trade. Candidate D parity passed. Candidate E reduced canonical first80 P&L to **₹1,163.47 / ₹374.58** versus D's **₹1,430.31 / ₹385.25** at 500 ms / 1 s. It improved the already-known recent 24-hour diagnostic to **-₹216.77 / -₹94.08** from **-₹223.27 / -₹135.91**, but both grids remained negative and deterministic four-hour stress-window mean expectancy was slightly worse than D on both grids. **Candidate E is rejected unchanged; Candidate D remains the V4.5 leader.** `xau-microstate-v1` remains a causal feature foundation; do not tune this two-feature veto on the same known windows.

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
python research\v4_5_router_v2.py xau_ticks_7d.csv
python research\v4_5_router_v2_full_eval.py xau_ticks_7d.csv xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_router_v2_arbitration_audit.py xau_ticks_7d.csv xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_router_v2_preflight.py
python research\v4_5_router_v3_priority_latched.py xau_ticks_7d.csv xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_independent_opportunity_atlas.py xau_ticks_7d.csv xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_snapback_foundation.py xau_ticks_7d.csv xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_state_v2_walkforward_predictability.py
python research\v4_5_microstate_v1_freeze.py xau_ticks_7d.csv xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_candidate_e_microstate_confirmation.py xau_ticks_7d.csv data/raw/xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_decision_policy_v1.py xau_ticks_7d.csv data/raw/xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_decision_policy_v2.py xau_ticks_7d.csv data/raw/xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_candidate_f_primary_ratchet.py xau_ticks_7d.csv data/raw/xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_candidate_g_ghost_ratchet.py xau_ticks_7d.csv data/raw/xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_signal_fingerprint_entry_quality.py xau_ticks_7d.csv data/raw/xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_candidate_h_flow_confirmed_ghost_exit.py xau_ticks_7d.csv data/raw/xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_tick_tape_field_audit.py xau_ticks_7d.csv data/raw/xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_external_gc_correlation.py xau_ticks_7d.csv data/raw/xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_external_gc_overlay_simulation.py xau_ticks_7d.csv data/raw/xau_ticks_recent_24h_2026-09-24.csv.gz
python research\v4_5_quote_flow_phase_controller.py xau_ticks_7d.csv data/raw/xau_ticks_recent_24h_2026-09-24.csv.gz
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
- [V4.5 Router v2 implementation freeze](docs/experiments/2026-09-25/28-v4-5-router-v2-implementation.md)
- [V4.5 Router v2 gate-proxy preflight](docs/experiments/2026-09-25/29-v4-5-router-v2-preflight.md)
- [V4.5 full raw-tick Router v2 replay](docs/experiments/2026-09-25/30-v4-5-router-v2-full-replay.md)
- [V4.5 Router v2 arbitration divergence audit](docs/experiments/2026-09-25/31-v4-5-router-v2-arbitration-audit.md)
- [V4.5 Router v3 priority-latched](docs/experiments/2026-09-25/32-v4-5-router-v3-priority-latched.md)
- [V4.5 independent engine opportunity atlas](docs/experiments/2026-09-25/33-v4-5-independent-opportunity-atlas.md)
- [V4.5 SNAPBACK complementary-engine foundation](docs/experiments/2026-09-25/34-v4-5-snapback-foundation.md)
- [V4.5 state-v2 walk-forward predictability](docs/experiments/2026-09-25/35-v4-5-state-v2-walkforward-predictability.md)
- [V4.5 microstate-v1 causal feature foundation](docs/experiments/2026-09-25/36-v4-5-microstate-v1-freeze.md)
- [V4.5 Candidate E microstate confirmation](docs/experiments/2026-09-25/37-v4-5-candidate-e-microstate-confirmation.md)
- [V4.5 Decision Policy v1](docs/experiments/2026-09-25/38-v4-5-decision-policy-v1.md)
- [V4.5 Decision Policy v2](docs/experiments/2026-09-25/39-v4-5-decision-policy-v2.md)
- [V4.5 Candidate F PRIMARY ratchet](docs/experiments/2026-09-25/40-v4-5-candidate-f-primary-ratchet.md)
- [V4.5 Candidate G ghost ratchet](docs/experiments/2026-09-25/41-v4-5-candidate-g-ghost-ratchet.md)
- [V4.5 signal-fingerprint entry quality](docs/experiments/2026-09-26/42-v4-5-signal-fingerprint-entry-quality.md)
- [V4.5 Candidate H flow-confirmed ghost exit](docs/experiments/2026-09-26/43-v4-5-candidate-h-flow-confirmed-ghost-exit.md)
- [V4.5 MT5 tick-tape field audit](docs/experiments/2026-09-26/44-v4-5-tick-tape-field-audit.md)
- [V4.5 external GC futures correlation bridge](docs/experiments/2026-09-26/45-v4-5-external-gc-correlation.md)
- [V4.5 same-timeline external GC overlay simulation](docs/experiments/2026-09-26/46-v4-5-external-gc-overlay-simulation.md)
- [V4.5 MT5-native quote-flow phase controller](docs/experiments/2026-09-26/47-v4-5-quote-flow-phase-controller.md)
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

The seven-day and recent-24h windows are now heavily observed. Their role is parity, diagnostics and rejection of already-frozen ideas—not repeated strategy selection. Candidate D remains the V4.5 research leader. Experiments 38-42 rejected two learned exit controllers and three increasingly informed entry-selection formulations, including the full signal-fingerprint "encyclopedia"; the known causal state still does not rank individual trades portably enough. Experiment 43's Candidate H is the strongest exit-management branch so far: path-preserving ghost occupancy plus confirmed raw-flow deterioration retained +₹1,287.09 / +₹360.79 canonical first80 P&L, improved recent losses on both grids, reduced 500 ms max segment drawdown to ₹148.66, and improved random four-hour mean P&L to -₹3.36 / -₹7.21, but variable-window mean expectancy remains negative and Candidate D still owns the canonical P&L lead. Final20 remains sealed; promotion still requires genuinely new non-overlapping raw data. Experiment 44 audited the archived MT5 tick tape and found a hard data limitation: `last`, `volume`, `volume_real`, and LAST/VOLUME/BUY/SELL flags are empty on this broker's XAUUSD history. Exact BID/ASK change flags are populated and highly cross-grid stable, so they are retained as quote-microstructure inputs, but true aggressor-side trade flow is not available from the current feed.
Experiment 45 confirmed that external COMEX Gold futures proxy data is tightly aligned with MT5 XAUUSD once the broker's ~3-hour timestamp offset is corrected: 5-minute return Pearson correlation was 0.9921 historical-first80 and 0.9915 recent24h, with 95.05% / 95.83% directional agreement. This validates external GC as a price-discovery sensor, but aggregated Yahoo bars are not trade tape; richer CME trades/depth remain the next data-acquisition step.
Experiment 46 tested that bridge inside the full path-dependent simulator using only same-timeline historical GC data. A conservative PRIMARY/SECONDARY guard based on opposite GC 5m+15m direction skipped 18/22 canonical trades and worsened P&L; requiring the same coarse external reversal before Candidate-H exits suppressed almost all useful H exits. Candidate I fell to +₹1,044.62/+₹345.91 canonical and -₹233.16/-₹137.53 recent, with random 4h means -₹14.73/-₹15.09. Conclusion: the GC relationship is real, but five-minute direction is too coarse for individual 500 ms/1 s decisions. Candidate D remains leader; Candidate H remains the best retained exit branch; next external work should use finer GC trades/depth or sub-five-minute data.

### Live-practicality gate after Experiment 46

External GC data is **not part of the active V4.5 algorithm or live dependency set**. Experiments 45-46 are retained as research evidence only. The ~3-hour discrepancy observed in Experiment 45 was a timestamp-label/clock-offset issue rather than evidence that futures information itself arrives three hours late, but the practical decision is unchanged: the active strategy must not depend on a secondary market-data feed that is unavailable from the execution terminal, adds synchronization/latency/availability risk, or has not demonstrated portable live value.

From this point, a feature is eligible for the active candidate only if it is available causally from the same MT5/broker feed at decision time and can be reconstructed from the archived MT5 fields used in replay. Candidate D remains the leader; Candidate H remains the strongest retained exit branch. External-GC scripts/evidence stay archived for provenance and are not a planned runtime component. Final20 remains sealed.

Experiment 47 returned to MT5-native data only and introduced a frozen quote-flow phase controller using exact bid/ask update flags plus raw quote-path state. Candidate J materially improved hostile recent performance and random-window robustness: random four-hour mean moved from D -₹6.26/-₹8.25 to J **+₹3.75/-₹2.82** at 500 ms/1 s, and J beat D in 100%/87.5% of the deterministic random windows. It also reduced max segment drawdown to ₹139.87/₹109.26. The cost was lower known canonical first80 P&L (+₹1,048.86/+₹273.18 versus D +₹1,430.31/+₹385.25), so J is **not promoted**. Freeze J unchanged for genuinely fresh MT5-only validation; do not tune the phase rules on known windows.
