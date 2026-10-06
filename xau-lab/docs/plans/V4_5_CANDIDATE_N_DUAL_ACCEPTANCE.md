# V4.5 Candidate N — dual price-acceptance continuation

Date frozen: 2026-10-06

Status: **frozen before Candidate-N P&L evaluation**

## Motivation

Candidate M is rejected unchanged, but Experiments 53–54 show that its price-acceptance mechanism is a large structural improvement over L/D/H in hostile later data. M also discards most of the old profitable first80 population. The next hypothesis must therefore add a genuinely different high-quality opportunity family without weakening M's pullback/reclaim standards.

Candidate N is **not** "M with looser thresholds". It keeps M's pullback path unchanged and adds a separate accepted-breakout continuation path for trends that never offer an M-style adverse 10-second pullback.

Known data may reject N, never promote it. Final20 remains sealed.

## Runtime information

MT5/broker-native only:

- canonical bid/ask/mid sampled state;
- exact MqlTick-derived raw microstate already frozen in microstate-v1;
- no external feed;
- no news/time-of-day exception table;
- no fitted model;
- no outcome-trained threshold.

## Shared structural trend and execution state

Reuse Candidate M exactly:

- >=1800 seconds uninterrupted sampled-session history;
- BUY requires `m60>0`, `m300>0`, `m1800>0`; SELL symmetric;
- `abs(m60)/range60 >= 0.50` and `abs(m300)/range300 >= 0.50`;
- `spread <= $0.40` and `spread <= 0.20*range60`;
- `qacc >= 1.0`;
- raw direction-normalized `dir_mid_move2 > 0` and `dir_event_imb2 > 0` at entry.

A canonical >5 s continuity break clears all setup state and requires the full 1800 s rebuild before any new setup can arm.

## Path A — Candidate M pullback acceptance, unchanged

Path A is byte-for-byte equivalent in decision meaning to Candidate M:

1. arm while current direction-normalized 10-second move is adverse by >= one current spread;
2. freeze `anchor = mid - m10`, arm spread, side and time;
3. expire after 60 seconds or cancel if structural trend disappears/flips;
4. require price to recover past `anchor +/- arm_spread` and remain accepted for 2.0 clock seconds;
5. require unchanged execution + raw-flow confirmation;
6. then enter.

Path A receives priority whenever a pullback arm exists.

## Path B — accepted 30-second breakout continuation

This is the new opportunity family.

### Causal breakout reference

For every sampled row, compute the highest and lowest **mid prices observed in the prior 30 clock seconds, excluding the current row and never crossing a canonical session boundary**.

No future values may enter this reference.

### Arm

Path B may arm only when:

- the shared normalized structural trend is valid;
- no Path-A pullback arm is active;
- the current 10-second move is **not** an M pullback;
- BUY: current mid first exceeds the causal prior-30-second high;
- SELL: current mid first falls below the causal prior-30-second low.

At arm time freeze:

- side;
- breakout reference level;
- current spread;
- arm time.

A continuous breakout episode cannot generate repeated arms. The breakout latch clears only after price returns to/through the frozen reference or the structural trend side disappears/flips.

### Acceptance

The breakout arm survives at most **30 clock seconds**, matching the causal breakout reference horizon.

Acceptance level:

- BUY: `mid >= breakout_reference + frozen_arm_spread`;
- SELL: `mid <= breakout_reference - frozen_arm_spread`.

Price must remain beyond that level continuously for **2.0 clock seconds**, identical to M's price-acceptance clock. If price returns inside, the timer resets while the arm remains alive.

If an M-style adverse pullback develops while a breakout arm is waiting, cancel Path B and allow the M family to own the next setup.

After acceptance, require the exact same execution and raw-flow confirmation as Path A before entry.

## Shared position / lifecycle

One shared N position maximum. First accepted path to enter owns the slot. Every trade records `entry_path = PULLBACK_ACCEPTANCE` or `BREAKOUT_ACCEPTANCE`.

Keep Candidate M's risk and lifecycle unchanged:

- BUY ask / SELL bid;
- 3% planned risk;
- $4 emergency stop (1R);
- $12 take profit (3R);
- 1800-second max hold;
- direction-normalized `m300 <= 0` structural-failure exit;
- Candidate-H flow-confirmed profit protection unchanged: arm at +1R MFE with >=1R giveback, 5-second checks, two consecutive adverse 2-second raw-flow confirmations.

## Random / abnormal situations

No hand-coded NFP, rollover or session-clock exclusions.

Candidate N must survive them causally through:

- canonical continuity resets;
- 1800-second post-gap rebuild;
- M's spread/range execution guard;
- frozen-price acceptance rather than one-tick breakout entry;
- arm expiry;
- raw quote-flow confirmation.

## Development evaluation

Run N unchanged against every currently archived non-sealed source:

1. canonical historical first80 only, both grids;
2. frozen recent-24h archive, both grids;
3. current seven-day archive, both grids;
4. all six Experiment-48 Stage-1 blocks individually and pooled;
5. deterministic real contiguous four-hour windows from historical/current sources using **three predeclared seeds: 55101, 55102, 55103; 80 windows per seed per grid**, alternating source by window id;
6. +$0.10 adverse slippage per side on all three full raw archives.

Comparators: frozen M, H and D where practical. Final20 stays sealed.

The current seven-day archive overlaps five Stage-1 blocks; never sum them as independent evidence.

## Predeclared development-survival screen

N earns a new prospective validation only if **all** of the following hold on both 500 ms and 1 s:

- historical-first80 compounded P&L > 0;
- recent-24h terminal-equity P&L >= 0;
- current-seven-day terminal-equity P&L >= 0;
- pooled six-block terminal-equity P&L >= 0;
- >=3/6 Stage-1 blocks positive;
- N completes more trades than M on historical first80 and current7d (the new path must actually add opportunity rather than merely rename M);
- every predeclared random seed has mean four-hour N P&L > 0;
- pooled random-window median N P&L >= 0;
- pooled random positive-window fraction >=50%;
- historical, recent24h and current7d remain >=0 under +$0.10 adverse slippage per side;
- D/H/M comparator values reproduce their frozen references within tolerance.

If N fails, do not tune the 30-second reference, 30-second expiry, 2-second acceptance, spread rules, structural dominance or flow confirmation against the observed outcomes. Diagnose whether the new breakout family itself is useful or harmful and define a new hypothesis if warranted.

Passing this known-data screen still does not authorize live money or V4.5 lock. It only permits a genuinely new non-overlapping prospective validation.
