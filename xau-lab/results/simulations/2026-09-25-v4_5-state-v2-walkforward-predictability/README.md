# Experiment 35 — state-v2 walk-forward predictability

Status: **execution pending**.

This is not a trading candidate.

A fixed ridge model with alpha 1.0 is trained only on past Experiment-33 shadow opportunities and predicts later fixed-size opportunity P&L. Features, preprocessing and the natural zero expected-P&L diagnostic threshold are frozen before execution.

Historical evaluation is expanding chronological walk-forward. The recent 24-hour window is predicted only after training on historical first80 opportunities.

A favorable result cannot promote a strategy; it can only justify freezing a future adaptive admission candidate for genuinely new data.
