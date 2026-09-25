# Experiment 31 — Router v2 arbitration divergence audit

Status: **completed diagnostic; no strategy change; Candidate D remains leader**.

The instrumented replay reproduced Experiment 30 exactly before analysis.

Headline finding: the current Router-v2 failure is primarily **path-dependent arbitration damage**, not a simple shortage of trades and not mainly the immediate P&L of direct score substitutions.

On the historical 500 ms 0-40% segment, the -₹353.97 Router-minus-D gap decomposes into:

- -₹79.25 from smaller balance-based sizing on 90 otherwise identical trades;
- -₹51.06 from three same-engine timing shifts;
- -₹148.85 from four profitable-net Candidate-D trades that disappeared from the Router path;
- -₹74.81 from four Router-only losing trades;
- ₹0 immediate realized difference from the one simultaneous substitution in that segment.

Two Router HOLDs rejected PRIMARY entries whose fixed-₹500 exact-entry counterfactuals were +₹61.39 and +₹43.16, then re-entered later and changed the shared-slot/cooldown path.

At 1 s the main 0-40% damage was likewise dominated by timing/occupancy: one +₹28.33 Candidate-D MICRO trade was replaced 28 seconds later by a -₹22.46 Router SECONDARY trade.

The recent window shows the other side: 500 ms improved by ₹12.64 because two losing Candidate-D PRIMARY trades were omitted, while recent 1 s worsened because three Router-only follow-on trades lost -₹32.52.

Do not lower the score floor from these outcomes. Profitable and losing rejected PRIMARY entries overlap in the same narrow negative-score band.

Next: specify a **path-aware, priority-preserving** Router architecture before any new candidate is tested.

Machine-readable evidence includes `summary.json`, `arbitration_events.csv`, `trade_pairs.csv`, `trade_pair_summary.csv`, `segment_pair_damage.csv`, `decision_category_summary.csv`, `substitution_matrix.csv` and the instrumented trade ledgers.
