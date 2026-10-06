# V4.5 Candidate O — acceptance-thesis invalidation exit

Date frozen: 2026-10-06

Status: **frozen before Candidate-O P&L evaluation**

## Why this is a new hypothesis

Candidate M's useful result is its entry mechanism: a counter-move must be fully reclaimed and price accepted beyond the pre-pullback level before capital enters. Candidate N showed that simply adding generic continuation breakouts destroys this selectivity and floods the strategy with poor trades.

Candidate O therefore does **not** add an entry family and does **not** loosen Candidate M. It asks a different question:

> once capital entered specifically because a pullback was reclaimed, should the trade remain alive after price has clearly lost that reclaimed pre-pullback level again?

Candidate M currently waits for the broad `m300` trend-failure exit or the fixed `$4` emergency stop when an accepted reclaim fails before reaching +1R. Candidate H's flow protection cannot help because it only arms after +1R MFE.

Candidate O keeps Candidate M's entry byte-for-byte in decision meaning and adds a causal **thesis invalidation exit** tied to the price level that justified the entry.

Known data may reject O, never promote it. Final20 remains sealed.

## Runtime information

MT5/broker-native only:

- canonical sampled bid/ask/mid state;
- raw MT5 microstate already used by M/H;
- no external feed;
- no fitted model;
- no outcome-trained threshold;
- no time-of-day/news/event exception table.

## Entry

Candidate M unchanged:

- >=1800 s uninterrupted session history;
- normalized structural trend: direction agreement on `m60`, `m300`, `m1800`; `abs(m60)/range60 >= 0.50`; `abs(m300)/range300 >= 0.50`;
- arm on current adverse `m10` of at least one current spread;
- freeze `arm_anchor = mid - m10`, `arm_spread`, side, and arm time;
- arm timeout 60 s;
- require price beyond `arm_anchor +/- arm_spread` continuously for 2.0 clock seconds;
- require `qacc >= 1`, direction-normalized raw `dir_mid_move2 > 0`, `dir_event_imb2 > 0`;
- require spread <= `$0.40` and <= `0.20 * range60`;
- BUY ask / SELL bid;
- 3% planned account risk, `$4` emergency stop, `$12` TP, 1800 s max hold.

At entry, Candidate O additionally retains the already-known frozen `arm_anchor` as `thesis_anchor`. This adds no new information and does not change admission.

## New exit — reclaimed-level invalidation

The pullback-reclaim thesis is invalid only after price loses the **pre-pullback anchor itself**, not merely the one-spread acceptance buffer.

For a BUY:

`mid < thesis_anchor`

For a SELL:

`mid > thesis_anchor`

The violation must remain continuous for **2.0 clock seconds**, reusing the same structural acceptance clock already frozen for Candidate M. If price restores the correct side of the anchor before 2 seconds elapse, the invalidation timer resets.

After 2 continuous seconds beyond the anchor in the adverse direction, exit immediately at the executable bid/ask and record `THESIS_INVALIDATION`.

This is evaluated after the emergency stop / take-profit checks but before slower structural `m300` failure. It is independent of P&L magnitude and does not require the trade to have reached any MFE threshold.

## Other lifecycle rules unchanged

- emergency stop `-$4`;
- take profit `+$12`;
- `m300` direction failure;
- max hold 1800 s;
- Candidate-H flow-confirmed profit protection unchanged: +1R MFE, >=1R giveback, 5-second checks, two adverse raw-flow confirmations.

No partial exits and no adaptive sizing.

## Why this should also avoid the "more trades" trap

O does not manufacture extra entry signals. If thesis invalidation closes a failed reclaim earlier, the shared slot becomes available for later **normal Candidate-M setups**. Any increase in trade count therefore comes only from reducing dead capital occupancy after a setup has invalidated, not from lowering entry standards.

## Abnormal / random situation discipline

No NFP/rollover clock table. O must survive with causal state only:

- >5 s continuity reset semantics remain canonical;
- new setup creation still requires 1800 s rebuilt history;
- spread/range entry guards remain unchanged;
- open trades are marked only on executable later quotes after gaps;
- thesis invalidation uses only observed mid and a frozen pre-entry anchor.

## Development evaluation

Run unchanged against every currently archived non-sealed source:

1. canonical historical first80 only, both grids;
2. frozen recent-24h archive, both grids;
3. current seven-day archive, both grids;
4. all six Experiment-48 Stage-1 blocks individually and pooled;
5. three newly predeclared deterministic real contiguous four-hour seeds **56011, 56012, 56013**, 80 windows/seed/grid alternating historical/current sources;
6. +`$0.10` adverse slippage per side on all three full raw archives.

Comparators: frozen M, H and D. Final20 stays sealed.

Current7d overlaps five Stage-1 blocks and is not summed with them as independent evidence.

## Predeclared development-survival screen

O earns a brand-new prospective validation only if all conditions hold on both grids:

- historical-first80 compounded P&L > 0;
- recent24h terminal-equity P&L >= 0;
- current7d terminal-equity P&L >= 0;
- >=20 completed trades on historical first80 and current7d;
- six-block pooled P&L >= 0;
- >=3/6 Stage-1 blocks positive;
- every random seed mean four-hour O P&L > 0;
- pooled random median O P&L >= 0;
- pooled random positive-window fraction >=50%;
- historical, recent24h and current7d P&L each remain >=0 under +`$0.10` adverse slippage per side;
- D/H/M comparator parity reproduces frozen references.

If O fails, do not tune the 2-second invalidation clock, anchor definition, M entry boundaries, stop/TP or flow exit against these outcomes. Diagnose the structural failure and define a different hypothesis.

Passing known data still does not authorize live money or a V4.5 lock; it only permits a new non-overlapping prospective validation.
