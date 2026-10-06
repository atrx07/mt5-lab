# V4.5 Candidate M — pullback price-acceptance state machine

Date frozen: 2026-10-06

Status: **frozen before Candidate-M P&L evaluation**

## Why this is a new hypothesis

Candidate L is rejected and must not be retuned. Experiment 52 showed that its failure was not mainly exit management or rapid re-entry churn: roughly 78-86% of losing trades across the development sources never achieved even +0.5R MFE, while Candidate-H-style flow exits were profitable when they armed.

Candidate M therefore does **not** tighten L's dominance ratio, spread multiples, qacc boundary, stop or m300 exit. It changes the entry mechanism itself.

The hypothesis is:

> after a genuine counter-move inside a normalized multi-horizon trend, capital should not be committed when short-term flow merely turns favorable; price must first **reclaim the pre-pullback level and remain accepted beyond it for clock time**.

This is a state-machine / market-acceptance hypothesis, not a fitted score.

## Runtime information

MT5 broker-native data only:

- bid / ask and canonical sampled mid-price state;
- raw MT5 microstate (`dir_mid_move2`, `dir_event_imb2`);
- no external feed;
- no outcome-trained model;
- no future labels;
- no news/time-of-day exception table.

Final20 remains sealed.

## Continuity

A new arm or entry requires at least **1800 seconds of uninterrupted sampled-session history**. A canonical continuity reset (`>5 s` gap) clears all arm/acceptance state and blocks new setup creation until 1800 seconds of causal history is rebuilt.

An open trade is never forward-filled through missing quotes; it is evaluated at the first later executable bid/ask quote.

## Macro trend state

Use the exact normalized trend definition frozen for Candidate L; it is not being tuned:

BUY:

- `m60 > 0`, `m300 > 0`, `m1800 > 0`;
- `range60 > 0`, `range300 > 0`;
- `abs(m60)/range60 >= 0.50`;
- `abs(m300)/range300 >= 0.50`.

SELL is symmetric.

No valid side means explicit HOLD.

## Step 1 — arm on an actual current pullback

Unlike Candidate L's previous-30-second pullback memory, Candidate M arms only while the **current 10-second displacement is adverse** by at least one current spread:

BUY:

`m10 <= -spread`

SELL:

`m10 >= +spread`

At the first qualifying sample, freeze:

- `arm_side`;
- `arm_time`;
- `arm_spread = current spread`;
- `anchor = mid - m10`.

`anchor` is therefore the causally observed approximate mid-price from ten seconds earlier, before the detected 10-second counter-move.

The same still-active pullback cannot create multiple arms. It must clear, or the macro trend side must change, before another setup can arm.

## Step 2 — require price acceptance beyond the pre-pullback level

The arm survives for at most **60 seconds**. This is six times the 10-second pullback observation horizon and is frozen as a structural clock, not selected from P&L.

Cancel the arm immediately if the normalized macro-trend side disappears or flips.

Acceptance level:

BUY:

`mid >= anchor + arm_spread`

SELL:

`mid <= anchor - arm_spread`

Price must remain beyond that frozen level continuously for **2.0 clock seconds**. If price falls back inside the level before 2 seconds elapse, the acceptance timer resets while the original arm remains alive.

This is the key difference from L: a favorable two-second flow print is not enough; actual price must recover the whole detected pullback and establish itself beyond the pre-pullback level.

## Step 3 — live execution confirmation

After two seconds of price acceptance, entry still requires:

- `qacc >= 1.0`;
- raw direction-normalized `dir_mid_move2 > 0`;
- raw direction-normalized `dir_event_imb2 > 0`;
- `spread <= $0.40`;
- `spread <= 0.20 * range60`.

The `$0.40` cap remains the same frozen risk-budget interpretation as L: current spread may consume at most 10% of the unchanged `$4` emergency-stop distance. The range-relative guard prevents that nominal ceiling from accepting economically poor execution in a quiet local market.

If execution confirmation is not yet available, the arm may continue waiting until its 60-second expiry as long as price/trend state remains valid.

## Entry / risk

- one shared Candidate-M position maximum;
- BUY at ask / SELL at bid;
- planned account risk 3%;
- emergency stop `$4 = 1R`;
- 100x synthetic leverage cap;
- no adaptive sizing model.

## Lifecycle

Keep Candidate L's lifecycle unchanged so this experiment isolates the new acceptance mechanism:

- stop `-1R = -$4`;
- take profit `+3R = +$12`;
- maximum hold 1800 s;
- direction-normalized `m300 <= 0` structural failure exit;
- no partial realization.

Retain Candidate H's useful flow-confirmed profit protection unchanged:

- arm at MFE >= +1R and giveback >=1R;
- check every 5 seconds;
- require two consecutive adverse raw 2-second mid-move + event-imbalance confirmations;
- then exit at executable bid/ask.

No ghost occupancy is used because M is an independent opportunity architecture.

## Random / abnormal situation discipline

No special clock table will exclude known rollover, NFP, or other event timestamps. Candidate M must fail safe from causal information alone:

- continuity reset removes setup state;
- 1800-second rebuild prevents post-gap instant entry;
- spread/range execution checks reject shock-quality quotes;
- a pullback setup expires mechanically after 60 seconds;
- price acceptance resets if the breakout is not maintained.

## Development evaluation

Candidate M may be rejected, never promoted, by known development evidence.

Run unchanged on:

1. canonical historical first80, both grids;
2. current seven-day dataset, both grids;
3. all six Experiment-48 Stage-1 blocks, both grids;
4. the same deterministic 80 real contiguous four-hour windows per grid used for Candidate L (`seed 51051`, alternating old/current sources);
5. adverse execution stress `$0.05`, `$0.10`, `$0.20` per side.

D and H comparator parity must reproduce the frozen references.

## Predeclared development-survival screen

Candidate M earns only a brand-new prospective validation if **all** conditions hold on both 500 ms and 1 s:

- historical-first80 compounded P&L > 0;
- current-seven-day terminal-equity P&L > 0;
- >=20 completed trades on each seven-day source/grid;
- deterministic four-hour random-window **mean P&L > 0**;
- deterministic four-hour random-window **median P&L >= 0**;
- deterministic four-hour positive-window fraction >=45%;
- historical-first80 P&L remains >0 under +`$0.10` adverse slippage per side;
- current-seven-day P&L remains >0 under +`$0.10` adverse slippage per side;
- D/H comparator parity passes.

The six Stage-1 blocks are reported separately as hostile-condition diagnostics but not double-counted as another independent promotion dataset because substantial portions overlap the current seven-day capture.

If M fails, do not tune these numeric rules to the observed P&L. Diagnose the structural failure and define a genuinely different hypothesis if warranted.

Passing known development data still does **not** authorize live money or a V4.5 lock; it only permits a new non-overlapping prospective test.

Final20 remains sealed.
