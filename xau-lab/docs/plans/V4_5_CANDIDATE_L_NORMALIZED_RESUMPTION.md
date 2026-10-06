# V4.5 Candidate L — normalized structural resumption

Date frozen: 2026-10-06

Status: **frozen before Candidate-L P&L evaluation**

## Hypothesis

The old D/H/J family relies on several fixed-dollar market-regime gates that are brittle when ordinary XAUUSD spread/range scale moves. Experiment 50 showed that normalized price-shape ratios transferred much more closely between the old and current seven-day regimes than the hard `$0.30` execution cap.

Candidate L therefore stops trying to classify individual D opportunities with a fitted score. It creates a new, conservative **trend -> pullback -> resumption** opportunity directly from causal, scale-normalized geometry and MT5-native raw flow.

This is not a threshold search. Every rule below is frozen before Candidate-L P&L is inspected.

## Name

`Candidate K` is already the locked V4.4 MICRO management configuration. The new V4.5 candidate is **Candidate L**.

## Data / information allowed live

MT5 broker-native tick data only:

- bid / ask;
- canonical sampled mid-price features;
- raw quote-event microstate from `xau-microstate-v1`;
- no external feed;
- no outcome-trained model;
- no future labels;
- no time-of-day/news calendar exception table.

## Session / continuity safety

A new entry requires at least **1800 seconds of uninterrupted sampled-session history**. Any canonical continuity reset (`>5 s` raw/sampled gap) resets eligibility until a new 1800-second history is available.

This is not a fitted warmup: the candidate explicitly consumes an 1800-second trend horizon and therefore requires that horizon to exist causally.

An existing position is never synthetically filled through a quote gap. It is evaluated at the first later executable bid/ask quote.

## Structural trend state

For sample `i`, define BUY trend only when all are finite and:

- `m60 > 0`, `m300 > 0`, `m1800 > 0`;
- `range60 > 0`, `range300 > 0`;
- `abs(m60) / range60 >= 0.50`;
- `abs(m300) / range300 >= 0.50`.

SELL is symmetric with all three momentum horizons negative.

The `0.50` boundary has a geometric interpretation: net directional displacement must account for at least half of the observed range on both the 60-second and 300-second horizons. It was not selected from trade outcomes.

If no side satisfies this state, Candidate L is explicitly **HOLD / no trade**.

## Pullback requirement

A BUY trend is eligible only if an actual adverse 10-second move occurred within the previous 30 seconds and its magnitude was at least one current spread:

`min_m10_30 <= -spread`

SELL:

`max_m10_30 >= +spread`

Using one spread as the minimum counter-move gives the pullback economic meaning without introducing another fixed-dollar market threshold.

A pullback episode can be consumed only once. After an entry, Candidate L cannot reuse the same still-active pullback window; the pullback condition must clear or the structural trend side must change before a new entry can be armed.

## Resumption trigger

With a valid trend + unconsumed pullback, BUY requires:

- `m10 >= spread`;
- `m30 >= 2 * spread`;
- `qacc >= 1.0`;
- raw `dir_mid_move2 > 0`;
- raw `dir_event_imb2 > 0`.

SELL is direction-normalized symmetrically.

The spread multiples are execution-economic boundaries, not P&L-selected price thresholds. `qacc >= 1.0` means the most recent 10-second quote rate is not below its 30-second baseline.

## Execution-quality guard

A new entry is forbidden unless both hold:

- `spread <= $0.40`;
- `spread <= 0.20 * range60`.

The `$0.40` ceiling is explicitly a risk-budget rule: one spread may consume at most **10% of the unchanged $4 emergency-stop distance**. The relative gate additionally prevents a nominally acceptable spread from consuming too much of a quiet local move.

These constants are frozen from risk/geometry semantics, not selected by Candidate-L P&L.

## Entry / risk

- one shared Candidate-L position maximum;
- BUY fills at ask; SELL fills at bid;
- planned account risk: **3%**;
- emergency-stop distance: **$4**;
- synthetic leverage cap: **100x**;
- same sizing formula as the current V4.5 line.

Candidate L deliberately does **not** introduce adaptive leverage or a fitted stop in its first test. This keeps the first structural experiment attributable to admission/geometry rather than changing every part of the strategy simultaneously.

## Lifecycle

Candidate L uses a simple R-based PRIMARY-style lifecycle:

- emergency stop: `-1R = -$4`;
- take profit: `+3R = +$12`;
- maximum hold: 1800 seconds;
- structural failure exit when direction-normalized `m300 <= 0`;
- no partial realization.

### Flow-confirmed profit protection

Retain Candidate H's strongest mechanism in R units:

- arm after live MFE >= `+1R`;
- require giveback from live MFE >= `1R`;
- evaluate every 5 seconds;
- require two consecutive confirmations where raw direction-normalized 2-second mid movement **and** raw 2-second event imbalance are both adverse;
- then exit at executable bid/ask.

There is no ghost occupancy because Candidate L is an independent opportunity architecture rather than an overlay that must preserve Candidate-D downstream timing.

## No-news-table / random-situation rule

Candidate L gets no hand-written clock exclusions for known rollover or macro-event timestamps. Random/shock conditions are handled only through causal continuity, structure and execution-quality guards that are available live.

## Development evaluation

Candidate L may be **rejected** using already-known development data, but cannot be promoted by them.

Run unchanged on:

1. canonical historical first80, both grids;
2. current seven-day dataset, both grids;
3. all six Experiment-48 Stage-1 blocks, both grids;
4. deterministic real contiguous four-hour windows alternating old/current seven-day continuity ranges;
5. extra adverse slippage per side: `$0.05`, `$0.10`, `$0.20`.

Compare to D and H where the harness permits like-for-like comparison.

## Predeclared development-survival screen

Candidate L is eligible to be frozen for a new prospective test only if **all** hold:

- historical first80 compounded P&L > 0 on 500 ms and 1 s;
- current-seven-day terminal-equity P&L > 0 on 500 ms and 1 s;
- deterministic four-hour random-window mean terminal-equity P&L > 0 on both grids;
- at least 20 completed trades on each seven-day source/grid so a sparse lucky path cannot pass;
- current-seven-day terminal-equity P&L remains > 0 with an extra `$0.10` adverse slippage per side on both grids;
- no baseline/parity regression in the comparator harness.

The six Stage-1 blocks are reported individually and pooled as hostile-condition diagnostics, but are not an additional tuning target and are not double-counted as a separate promotion dataset because much of their time lies inside the current seven-day capture.

If this frozen first Candidate-L hypothesis fails the survival screen, do not tune the numeric boundaries against the same outcomes. Diagnose the structural failure and either reject the family or define a meaningfully different causal hypothesis.

## Promotion rule

Passing development only earns a **new prospective validation**, not a V4.5 lock and not real-money authorization.

Final20 remains sealed.
