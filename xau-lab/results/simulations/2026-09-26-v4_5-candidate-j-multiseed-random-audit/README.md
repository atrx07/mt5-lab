# Experiment 47R — Candidate J multi-seed random-window audit

Status: **completed; 500 ms positive mean replicated in all three new batches**

Three additional deterministic random batches are run without changing Candidate J:
- batch A
- batch B
- batch C

Each batch uses 40 real contiguous four-hour windows per grid with the same 50/50 historical-first80 vs recent24h source balance as Experiment 47.

Expected evidence:
- window_results.csv
- batch_summary.csv
- baseline_shadow_parity.csv
- summary.json

This is known-data robustness evidence only. Experiment 48 remains the fresh prospective gate. Final20 remains sealed.


## Main result

| Grid | A J mean | B J mean | C J mean | pooled J mean | pooled D mean | pooled H mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 500 ms | +₹0.97 | +₹8.13 | +₹3.92 | **+₹4.34** | -₹0.85 | -₹4.17 |
| 1 s | +₹0.54 | -₹2.85 | +₹1.83 | **-₹0.16** | -₹8.18 | -₹5.85 |

Candidate J beat D in 92.5% of pooled new 500 ms windows and 87.5% of pooled new 1 s windows.

Conclusion: the 500 ms positive mean replicated across all three additional seeds. The 1 s branch is near break-even, not confirmed profitable. Candidate J remains frozen for fresh Experiment 48 validation.
