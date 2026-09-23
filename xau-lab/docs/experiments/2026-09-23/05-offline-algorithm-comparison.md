# Offline algorithm comparison — 2026-09-23

Using the short broker quote clips captured during the live experiments, several strategy families were compared in fast replay.

These exploratory numbers are retained as research notes, not as proof of out-of-sample profitability.

The strongest recurring idea was not raw momentum chasing, but:

**established direction → pullback → directional resumption**

A second useful finding was to enforce **one trade per impulse**, so the bot cannot repeatedly re-enter the same move after a win or loss.

The successor became the V4 research candidate.
