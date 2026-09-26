# Architecture decision — MT5-only live decision path

Date: 2026-09-26
Status: **active owner decision**

Experiments 45-46 investigated external COMEX Gold futures proxy information.

The external bridge is now **archived research only** and is not part of the active V4.5 trading algorithm.

Reasons:

1. The five-minute external overlay failed to improve the path-dependent strategy and Candidate I was rejected.
2. The active live system should not require a second data-provider/network dependency unless it proves material portable value.
3. Cross-provider synchronization, availability, latency and licensing add operational failure modes.
4. Every active decision feature should be available causally from the same MT5/broker feed used for execution and should be replayable from archived MT5 fields.
5. The Experiment-45 ~3-hour discrepancy was a timestamp-label/clock-offset issue, not evidence of a three-hour market delay; nevertheless, the external dependency is not justified by the observed trading results.

Candidate D remains the V4.5 leader.
Candidate H remains the strongest retained exit-management branch.
External-GC scripts/results remain in the repository for reproducibility and provenance only.
Final20 remains sealed.

External-feed research may be reopened only by an explicit future owner decision.
