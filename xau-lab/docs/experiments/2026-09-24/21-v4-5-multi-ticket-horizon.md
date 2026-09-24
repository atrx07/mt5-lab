# 21 — V4.5 autonomous multi-ticket horizon research

Date: 2026-09-24

Status: **completed negative experiment; no candidate promoted. Candidate D remains provisional.**

## Objective and hypothesis

Test a new, independent XAUUSD strategy that can hold up to three separate tickets concurrently. At each admission it chooses a trend (longer holding horizon) or impulse (shorter holding horizon) rule from past-only features. Each ticket has its own executable-price profit trigger and trailing confirmation. Test the requested ₹100 per UTC day against the existing ₹500 synthetic research account; this is a research target, not an entry/exit signal or promised income.

The broad idea of following an instrument's own past direction is motivated by [Moskowitz, Ooi and Pedersen (2012)](https://doi.org/10.1016/j.jfineco.2011.11.003). That paper studies much longer horizons and does not establish this intraday XAUUSD rule. Position-level profit confirmation is a hypothesis to test, not a reason to keep losers indefinitely. [FINRA explains](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets) that stop trigger prices may not be executable fill prices in volatile markets.

## Protocol and initial design

- Build the existing 500 ms and 1 s canonical feature arrays without changing their timestamps, sampling, features, or V4.4 oracle.
- Admit up to three same-direction tickets; no opposing hedge. Prototype 0 allows up to two trend and one impulse ticket. Prototypes 1–2 allow up to one trend and two short-horizon tickets. Each has an independent entry, size, horizon, peak, stop and exit reason.
- Trend admission uses aligned 30-minute, five-minute and one-minute momentum with a 10-second recovery after a recent pullback. Impulse admission uses aligned two-minute, 30-second and 10-second momentum plus raw tick imbalance, quote acceleration and efficiency. BUY/SELL rules are symmetric.
- Use ask to buy, bid to sell, and the opposite executable quote to close. Each ticket has a $4 emergency stop. Per-ticket planned entry risk is at most 1% of current marked equity and aggregate planned entry risk at most 3%; aggregate notional is capped at 100x equity. No size increase is allowed merely to reach ₹100/day.
- A winning ticket exits on its own profit confirmation/trail; a losing ticket may exit at the stop, maximum holding time, session gap or segment boundary. There is no profit-only guarantee.
- Force liquidation at the last available quote of each segment and on the first available quote after a session gap. Record both realized and marked-equity drawdown so open losses are visible.
- Verify the raw SHA-256 and V4.4 golden parity at both grids before interpreting this candidate. Use only the first 1,869,979 raw rows. Keep the final 20% sealed.
- Evaluate the frozen prototype 0 on the 0–40% seed and all four later chronological segments once. Any bounded revision must first pass joint 500 ms and 1 s seed selection before later-segment evaluation. Report first-80% compounded P&L where evaluated, daily realized P&L, PF, marked-equity drawdown, exposure, trade counts, duration, simultaneous-slot use, and an additional $0.20 adverse fill on each side. Compare against provisional Candidate D; do not automatically promote or lock.

## Evidence and decision

The raw SHA-256 matched the dataset contract, and the locked V4.4 replay reproduced the golden oracle at both 500 ms and 1 s before each prototype. Candidate D remains a separate, already parity-verified comparator; its canonical first-80% P&L is +₹1,430.31 / +₹385.25 and it is not locked. The final holdout was not read.

| Prototype and scope | 500 ms P&L | 1 s P&L | Peak open tickets | +₹100 UTC days | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| 0, full first-80% | -₹22.14 | -₹52.92 | 2 / 2 | 0 / 5 on both grids | reject; almost all trades were trend tickets |
| 1, seed 0–40% only | +₹29.15 | -₹23.13 | 3 / 3 | 0 / 3 on both grids | reject; short horizon opened, but 1 s losses remain |
| 2, seed 0–40% only | +₹13.72 | -₹37.90 | 1 / 1 | 0 / 3 on both grids | reject; reversal lane did not help |

Prototype 0's five chronological segment P&Ls were -₹8.35, +₹25.66, -₹4.52, -₹24.01, -₹10.00 at 500 ms and -₹59.33, +₹26.68, +₹0.71, -₹13.96, -₹5.29 at 1 s. Its median segment PF was 0.686 / 0.739 and maximum marked-equity segment drawdown ₹101.59 / ₹92.93. Its 20.26 / 17.74 ticket-exposure hours yielded negative compounded P&L per ticket-exposure hour. The observed UTC daily realized P&L never reached ₹100; the first and last research days are partial, and same-day segment resets make the daily sum a diagnostic rather than a continuous-account return.

With an extra $0.20 adverse fill per side, prototype 0 fell to -₹53.38 / -₹78.51. On the seed, prototype 1 fell to +₹14.72 / -₹62.81 and prototype 2 to +₹9.13 / -₹45.82. These cost tests were run in the same ticket engine; no live-size, financing, margin, or broker-order modeling was added.

The final distinct seed hypothesis tested short-horizon **reversal** after a large one-minute move and opposite 10-second flow, alongside the longer-horizon trend lane. It used the same three-ticket, 3% basket-risk, $4 emergency stop, spread, fill and cost rules. It failed the joint-grid seed criterion, so prototypes 1 and 2 were not run on segments 1–4. No configuration is promoted or lock-eligible. In this dataset, adding position slots and waiting for confirmed ticket profit did not create an edge; 1 s stop losses and costs dominated.

## Evidence and next step

- [Result bundle](../../../results/simulations/2026-09-24-v4_5-multi-ticket-horizon/)
- [Independent research script](../../../scripts/v4_5_multi_ticket_horizon.py)

The earlier focused raw-event admission direction remains the next V4.5 research step. This separate multi-ticket idea is archived as a negative result. Do not create a V4.5 paper/live executor or open the final holdout from this experiment.
