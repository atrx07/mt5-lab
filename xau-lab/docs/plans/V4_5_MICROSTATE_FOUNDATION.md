# V4.5 microstate-v1 foundation — frozen raw-event schema

Status: **frozen before outcome testing**

Date: 2026-09-25

## Why

Experiments 33–35 reject two tempting rescue paths without tuning them:

- the existing four momentum/trend-family engines broadly fail together in the hostile recent window;
- frozen SNAPBACK does not create the missing complement;
- the existing `xau-state-v2` representation does not show transferable trade-outcome predictability under the pre-registered ridge test.

The next step must add **new causal information**, not another threshold or model fitted to the same outcomes.

## New information source

`xau-microstate-v1` is computed directly from raw quote events immediately before an opportunity timestamp. It adds microstructure information that state-v2 does not contain explicitly:

- raw event inter-arrival timing;
- 2 s vs 10 s event-rate acceleration;
- event-path efficiency at 2 s and 10 s;
- raw signed event pressure at 2 s and 10 s;
- bid-vs-ask update sidedness;
- two-sided quote-update fraction;
- short-horizon spread shock/compression;
- direction-normalized 10 s range position.

No trade P&L, exit outcome, future quote or final20 observation is used to define a feature.

## Frozen feature schema

For each opportunity timestamp, using only raw events from the same continuity session:

1. `raw_count2`
2. `raw_count10`
3. `event_rate_accel_2_10` = (count2 / 2 s) / (count10 / 10 s)
4. `median_iat2_ms`
5. `median_iat10_ms`
6. `iat_ratio_2_10`
7. `mid_move2`
8. `mid_move10`
9. `dir_mid_move2`
10. `dir_mid_move10`
11. `event_eff2`
12. `event_eff10`
13. `event_imb2`
14. `event_imb10`
15. `dir_event_imb2`
16. `dir_event_imb10`
17. `dir_imbalance_delta_2_10`
18. `quote_sidedness2` = (bid-update count - ask-update count) / total one-or-both-side update count
19. `two_sided_update_frac2`
20. `spread_rel10` = current spread / median spread over raw events in prior 10 s
21. `spread_change_rel2` = (current spread - first spread in prior 2 s) / median spread10
22. `spread_compression10` = (max spread10 - current spread) / median spread10
23. `dir_range_position10` = side-normalized location inside prior 10 s raw mid range

All windows are strictly backward-looking and clipped at raw continuity gaps >5 s.

## Experiment 36

Experiment 36 is **representation-only**.

It overlays this frozen schema onto Experiment-33 independent opportunities but intentionally omits P&L from the output used for feature validation.

Allowed diagnostics:

- finite coverage;
- 500 ms / 1 s cross-grid stability for same-engine, same-side opportunities;
- historical-vs-recent distribution drift;
- session/warm-up behavior.

Not allowed:

- selecting feature thresholds from win/loss labels;
- fitting an outcome model;
- promoting a strategy;
- opening final20.

If the representation itself is unstable, reject it. If stable, preserve it for a future pre-registered opportunity/admission hypothesis and validate that hypothesis prospectively on genuinely new non-overlapping raw data.
