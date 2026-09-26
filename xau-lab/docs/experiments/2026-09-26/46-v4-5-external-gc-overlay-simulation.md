# 46 — V4.5 same-timeline external GC overlay simulation

Date: 2026-09-26
Status: **completed full simulation; Candidate I rejected; external 5-minute overlay too coarse**

Experiment 46 integrates the Experiment-45 GC bridge into the path-dependent MT5 simulator while guaranteeing that every external observation comes from the **same historical timeline** as the replayed MT5 tick data.

It compares Candidate D, Candidate H, an external-entry-only branch, an external-exit-only branch, and combined Candidate I.

Frozen plan:
`docs/plans/V4_5_EXTERNAL_GC_OVERLAY_SIMULATION.md`

Implementation:
`research/v4_5_external_gc_overlay_simulation.py`

Evidence:
`results/simulations/2026-09-26-v4_5-external-gc-overlay-simulation/`

No current external market data may be mixed into historical replays. Final20 remains sealed.


## Result

The final run used only external GC bars from the archived MT5 dates. The source request was derived from the MT5 archive and covered 2026-09-16 09:56 UTC through 2026-09-24 17:58 UTC, with 1,751 derived five-minute GC feature rows committed. No current-market GC observation entered the replay.

A first implementation pass exposed a pandas timestamp-unit mismatch in the external sensor. That pass was discarded before interpretation. The sensor was corrected to explicit Unix-second conversion and the entire simulation was rerun; the evidence below is from the corrected run.

All ghost-preserving variants retained exact downstream Candidate-D entry-path timing.

### Canonical first80

| Grid | Candidate D | Candidate H | GC-entry | GC-exit | Candidate I |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | **+₹1,430.31** | +₹1,287.09 | +₹1,044.62 | **+₹1,430.31** | +₹1,044.62 |
| 1 s | +₹385.25 | +₹360.79 | +₹344.61 | **+₹386.61** | +₹345.91 |

External admission skipped 18 canonical 500 ms trades and 22 canonical 1 s trades. The simple five-minute/fifteen-minute directional disagreement guard removed too much useful edge.

The external exit confirmation was the opposite extreme. At 500 ms it blocked every Candidate-H extra exit, collapsing GC-exit back to Candidate D. At 1 s it allowed only one extra PRIMARY exit and improved canonical P&L by about ₹1.35 versus D.

### Recent24h

| Grid | Candidate D | Candidate H | GC-entry | GC-exit | Candidate I |
| --- | ---: | ---: | ---: | ---: | ---: |
| 500 ms | -₹223.27 | **-₹208.47** | -₹233.16 | -₹223.27 | -₹233.16 |
| 1 s | -₹135.91 | **-₹128.63** | -₹137.53 | -₹135.91 | -₹137.53 |

The external admission guard skipped four recent 500 ms and five recent 1 s entries, but the removed set was not selectively bad enough to improve the result.

Requiring five-minute/fifteen-minute GC disagreement before Candidate-H decay exits suppressed all recent H exits, so GC-exit reverted to Candidate D on both grids.

### Random real four-hour windows

| Grid | Candidate D mean | Candidate H mean | Candidate I mean | D positive | H positive | I positive |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 500 ms | -₹6.26 | **-₹3.36** | -₹14.73 | 30.0% | 35.0% | 37.5% |
| 1 s | -₹8.25 | **-₹7.21** | -₹15.09 | 27.5% | 30.0% | 30.0% |

Candidate I increased 500 ms positive-window frequency but badly worsened mean expectancy and lower-tail behavior. At 1 s it was also materially worse than D/H.

### Interpretation

Experiment 45 proved that GC and MT5 XAUUSD are tightly linked at five-minute resolution after clock correction. Experiment 46 shows that this does **not** mean a coarse five-minute directional overlay can decide individual 500 ms / 1 s trades.

The simple external guard is too slow and redundant:

1. broad GC direction often agrees with Candidate-D entries even when the individual trade later fails;
2. when GC does disagree, skipping the MT5 trade frequently removes profitable opportunities too;
3. Candidate-H local decay can occur while five-minute GC direction is still aligned, so requiring five-minute/fifteen-minute reversal suppresses useful profit-protection exits;
4. external correlation is therefore relevant, but the useful information must be **finer-grained than aggregated five-minute direction**.

The volume field was preserved in the aligned external evidence, but no volume threshold or post-hoc selection was introduced.

## Decision

**Reject Candidate I and the frozen five-minute directional overlay unchanged.**

Candidate D remains the V4.5 leader. Candidate H remains the strongest retained exit-management branch.

Do not tune the GC return horizons or disagreement thresholds on these known windows.

The next justified external-data step is higher-resolution GC information from the same dates—preferably actual trades/order-book depth, or at minimum sub-five-minute futures data—then test whether cross-market impulse/tape state contains information that broad five-minute direction does not.

Final20 remains sealed.
