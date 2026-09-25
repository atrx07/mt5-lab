# Experiment 35 — state-v2 walk-forward predictability

Status: **completed; transferable predictability not demonstrated**.

This was a fixed no-search diagnostic, not a trading candidate.

Historical expanding walk-forward prediction was weak or anti-correlated with future fixed-size P&L. On later recent data, Spearman correlation was only +0.018 at 500 ms and -0.008 at 1 s; predicted-positive subsets remained deeply negative.

The result does **not** justify changing alpha, selecting features, changing the zero threshold or escalating to a more flexible model on these same windows.

Conclusion: do not build a state-v2 adaptive admission candidate from this evidence. A future candidate must add genuinely new causal information or a structurally new opportunity family and be frozen before new unseen validation.
