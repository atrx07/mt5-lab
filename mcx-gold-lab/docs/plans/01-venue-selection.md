# Venue selection — why MCX gold futures

## The decision

**Primary: GOLDPETAL (1 g) futures. Secondary: GOLDGUINEA (8 g).**
Exchange: MCX. Access: SEBI-registered Indian broker + API.

## Why not the alternatives

| Venue | Verdict | Reason |
|---|---|---|
| MT5 XAUUSD (offshore broker) | REJECTED for real money | FEMA breach for Indian residents; min ticket 1 oz ≈ Rs 3.9L notional makes small-capital research non-executable. Kept as xau-lab research sandbox only. |
| Crypto spot (Binance/CoinDCX) | FALLBACK | Lawful via FIU-registered venues, but 31.2% tax on winners-only + 1% TDS structurally kills small-edge strategies. See spot-trading-bot plan. |
| NSE equity intraday | DEFERRED | Lawful, liquid, good APIs — but our edge research is in gold microstructure. Different beast; no transfer assumed. |
| Currency derivatives | REJECTED | Lawful but USDINR is too slow for tick-level engines; they would starve. |

## Contract economics (gold Rs 15,125/g, MCX bhavcopy 2026-10-06; model: `tools/mcx_cost_model.py`)

| Contract | Notional/lot | Margin/lot | RT cost | Breakeven |
|---|---|---|---|---|
| GOLDPETAL (1 g) | Rs 15,125 | ~Rs 1,059 | Rs 13.31 | 13.3 ticks |
| GOLDGUINEA (8 g) | Rs 1,21,000 | ~Rs 8,470 | Rs 68.00 | 8.5 ticks |
| GOLDM (100 g) | Rs 12,00,000 | ~Rs 84,000 | Rs 253.50 | 25.4 ticks |

Petal: tradable from ~Rs 5-10k accounts. Guinea: efficiency sweet spot above
~Rs 25k. Costs are NOT the binding constraint here — spread (Rs 2-3 at Rs 1
ticks) and edge existence are.

## Contract specifications (MCX circulars, verified 2026-10-08)

- Trading unit: 1 g (Petal) / 8 g (Guinea). Tick: Rs 1 per lot (Petal; Guinea
  tick marked VERIFY against live feed).
- Session: Monday-Friday, 9:00 am to 11:30/11:55 pm IST. No weekend session.
- Daily price limits: 3% base -> 6% -> 9% (15-min cooling before 9%). Breakout
  logic MUST be circuit-aware; limit-lock days don't exist in MT5 gold.
- Margins: 6% initial (or SPAN, whichever higher) + 1% extreme loss margin.
- Monthly expiry with rollover. Never hold into delivery; roll rules are part
  of every candidate's specification.

## Broker / API selection

- **Default: Zerodha Kite Connect.** Most mature Python client, largest
  community, MCX supported. Execution + account APIs free since Mar 2025;
  real-time websocket + historical data Rs 500/month. Rate limits:
  10 orders/sec, 200/min, 3000/day.
- **Free alternatives:** Upstox API (free incl. data, MCX, sandbox), Angel One
  SmartAPI (free, MCX). Smaller communities for tick-level MCX work.
- **SEBI retail algo framework (Feb 2025 circular, in force 2026):** self-coded
  strategies up to 10 orders/second run on static IP + API key with NO prior
  exchange registration; above that, or via vendors, registration is required.
  Confirm order-rate headroom with the broker before building execution.
- Data note: broker historical APIs serve candles, not raw ticks. Tick research
  requires websocket capture into our own store (`tools/capture_ticks.py`) or a
  tick vendor (TrueData / Global DataFeeds — evaluate when needed).

## Tax note (not advice; verify with a CA)

Commodity futures profits for an individual are typically treated as business
income (or capital gains if delivery-based investment — not our case). No
31.2%-style VDA regime applies. Maintain a trade ledger from day one regardless.
