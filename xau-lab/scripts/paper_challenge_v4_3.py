"""V4.2 XAUUSD live-paper strategy. Research only; sends no real orders.

V4.2 keeps V4.1 as the primary slow trend/pullback/resumption engine and adds
an experimental secondary breakout engine when the V4.1 slow directional gate
is inactive. The ₹50/hour objective is diagnostic only; it never forces a trade
or increases risk.
"""

import csv
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5

SYMBOL = "XAUUSD"
START_BALANCE_INR = 500.0
INR_PER_USD = 95.7021
LEVERAGE_CAP = 100.0
CONTRACT_SIZE = 100.0
HOURLY_TARGET_INR = 50.0

SAMPLE_INTERVAL = 0.50
MAX_QUOTE_GAP_SECONDS = 5.0
MAX_SPREAD_USD = 0.30
RISK_FRACTION = 0.03
STOP_DISTANCE_USD = 4.0

# V4.1 primary engine.
PRIMARY_WARMUP_SECONDS = 1800
PRIMARY_COOLDOWN_SECONDS = 900
PRIMARY_MAX_HOLD_SECONDS = 2400
PRIMARY_MIN_1800S_MOMENTUM_USD = 8.0
PRIMARY_MIN_300S_MOMENTUM_USD = 3.0
PRIMARY_PULLBACK_60S_MOMENTUM_USD = 0.80
PRIMARY_RESUME_60S_MOMENTUM_USD = 0.50
PRIMARY_PULLBACK_LOOKBACK_SECONDS = 300
PRIMARY_TAKE_PROFIT_DISTANCE_USD = 30.0
PRIMARY_TRAIL_TRIGGER_USD = 6.0
PRIMARY_TRAIL_GIVEBACK_USD = 8.0
PRIMARY_REVERSAL_HORIZON_SECONDS = 120

# V4.3 retains the V4.2 secondary breakout entry engine.
SECONDARY_LOOKBACK_SECONDS = 120
SECONDARY_BREAKOUT_BUFFER_USD = 0.50
SECONDARY_TREND_HORIZON_SECONDS = 30
SECONDARY_MIN_TREND_USD = 2.0
SECONDARY_MIN_RANGE_USD = 3.0
SECONDARY_COOLDOWN_SECONDS = 450
SECONDARY_PROFIT_COOLDOWN_SECONDS = 120
SECONDARY_TAKE_PROFIT_DISTANCE_USD = 21.0
SECONDARY_MAX_HOLD_SECONDS = 900
SECONDARY_REVERSAL_HORIZON_SECONDS = 300
BREAKEVEN_RECOVERY_TRIGGER_USD = 10.0

LOG_FILE = Path("paper_trades_v4_3.csv")
HOURLY_LOG_FILE = Path("paper_hourly_v4_3.csv")
history = deque(maxlen=10000)


def money(value):
    return "₹%.2f" % value


def quote_at_or_before(target_time):
    for q in reversed(history):
        if q["time"] <= target_time:
            return q
    return None


def momentum(now_mid, now, seconds):
    q = quote_at_or_before(now - seconds)
    if q is None:
        return None
    if now - q["time"] > seconds + MAX_QUOTE_GAP_SECONDS:
        return None
    return now_mid - q["mid"]


def calculate_ounces(balance_inr, price):
    if balance_inr <= 0 or price <= 0:
        return 0.0, 0.0
    risk_budget = balance_inr * RISK_FRACTION
    ounces_by_risk = risk_budget / (STOP_DISTANCE_USD * INR_PER_USD)
    capital_usd = balance_inr / INR_PER_USD
    ounces_by_leverage = (capital_usd * LEVERAGE_CAP) / price
    return min(ounces_by_risk, ounces_by_leverage), risk_budget


def pnl_inr(position, bid, ask):
    move = bid - position["entry"] if position["side"] == "BUY" else position["entry"] - ask
    return move * position["ounces"] * INR_PER_USD


def move_usd(position, bid, ask):
    return bid - position["entry"] if position["side"] == "BUY" else position["entry"] - ask


def primary_slow_gate(m300, m1800):
    if m300 is None or m1800 is None:
        return False, False
    buy_gate = (
        m1800 >= PRIMARY_MIN_1800S_MOMENTUM_USD
        and m300 >= PRIMARY_MIN_300S_MOMENTUM_USD
    )
    sell_gate = (
        m1800 <= -PRIMARY_MIN_1800S_MOMENTUM_USD
        and m300 <= -PRIMARY_MIN_300S_MOMENTUM_USD
    )
    return buy_gate, sell_gate


def primary_signal(now, m60, m300, m1800):
    if m60 is None or m300 is None or m1800 is None:
        return None

    recent_m60 = []
    for q in history:
        if q["time"] < now - PRIMARY_PULLBACK_LOOKBACK_SECONDS:
            continue
        q60 = quote_at_or_before(q["time"] - 60)
        if q60 is None:
            continue
        if q["time"] - q60["time"] > 60 + MAX_QUOTE_GAP_SECONDS:
            continue
        recent_m60.append(q["mid"] - q60["mid"])

    if not recent_m60:
        return None

    buy_signal = (
        m1800 >= PRIMARY_MIN_1800S_MOMENTUM_USD
        and m300 >= PRIMARY_MIN_300S_MOMENTUM_USD
        and min(recent_m60) <= -PRIMARY_PULLBACK_60S_MOMENTUM_USD
        and m60 >= PRIMARY_RESUME_60S_MOMENTUM_USD
    )
    sell_signal = (
        m1800 <= -PRIMARY_MIN_1800S_MOMENTUM_USD
        and m300 <= -PRIMARY_MIN_300S_MOMENTUM_USD
        and max(recent_m60) >= PRIMARY_PULLBACK_60S_MOMENTUM_USD
        and m60 <= -PRIMARY_RESUME_60S_MOMENTUM_USD
    )
    return "BUY" if buy_signal else "SELL" if sell_signal else None


def secondary_signal(now, mid, m30, m300, m1800):
    buy_gate, sell_gate = primary_slow_gate(m300, m1800)
    if buy_gate or sell_gate or m30 is None:
        return None, None, None

    prior = [
        q for q in history
        if now - SECONDARY_LOOKBACK_SECONDS <= q["time"] < now
    ]
    if len(prior) < 2:
        return None, None, None

    prior_high = max(q["mid"] for q in prior)
    prior_low = min(q["mid"] for q in prior)
    prior_range = prior_high - prior_low
    if prior_range < SECONDARY_MIN_RANGE_USD:
        return None, prior_high, prior_low

    buy = (
        mid >= prior_high + SECONDARY_BREAKOUT_BUFFER_USD
        and m30 >= SECONDARY_MIN_TREND_USD
    )
    sell = (
        mid <= prior_low - SECONDARY_BREAKOUT_BUFFER_USD
        and m30 <= -SECONDARY_MIN_TREND_USD
    )
    return ("BUY" if buy else "SELL" if sell else None), prior_high, prior_low


FIELDS = [
    "timestamp", "event", "engine", "side", "bid", "ask", "spread_usd",
    "entry_price", "ounces", "synthetic_lots", "risk_budget_inr",
    "equity_inr", "realized_inr", "trade_pnl_inr", "m30", "m60",
    "m300", "m1800", "channel_high", "channel_low", "mfe_inr", "mae_inr",
    "reason",
]

HOURLY_FIELDS = [
    "hour_start_local", "hour_end_local", "start_realized_inr",
    "end_realized_inr", "hour_realized_pnl_inr", "target_inr", "target_met",
    "trades_closed",
]


def write_log(row):
    exists = LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in FIELDS})


def write_hourly_log(row):
    exists = HOURLY_LOG_FILE.exists()
    with HOURLY_LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HOURLY_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in HOURLY_FIELDS})


def close_position(reason, position, bid, ask, spread, realized, trade_pnl,
                   m30, m60, m300, m1800):
    realized += trade_pnl
    balance = START_BALANCE_INR + realized
    print()
    print("EXIT", position["engine"], position["side"], "|", reason)
    print("P&L:", money(trade_pnl), "| MFE:", money(position["mfe"]), "| MAE:", money(position["mae"]))
    print("Balance:", money(balance))
    print()

    write_log({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": "EXIT",
        "engine": position["engine"],
        "side": position["side"],
        "bid": round(bid, 4),
        "ask": round(ask, 4),
        "spread_usd": round(spread, 4),
        "entry_price": round(position["entry"], 4),
        "ounces": round(position["ounces"], 6),
        "synthetic_lots": round(position["ounces"] / CONTRACT_SIZE, 8),
        "risk_budget_inr": round(position["risk_budget_inr"], 2),
        "equity_inr": round(balance, 2),
        "realized_inr": round(realized, 2),
        "trade_pnl_inr": round(trade_pnl, 2),
        "m30": "" if m30 is None else round(m30, 4),
        "m60": "" if m60 is None else round(m60, 4),
        "m300": "" if m300 is None else round(m300, 4),
        "m1800": "" if m1800 is None else round(m1800, 4),
        "channel_high": position.get("channel_high", ""),
        "channel_low": position.get("channel_low", ""),
        "mfe_inr": round(position["mfe"], 2),
        "mae_inr": round(position["mae"], 2),
        "reason": reason,
    })
    return realized


print("================================================")
print("      XAUUSD LIVE PAPER CHALLENGE V4.3")
print("================================================")
print("V4.2 entries + V4.3 exit harvesting / continuation re-entry")
print("₹50/hour is DIAGNOSTIC ONLY; it never forces a trade")
print("3% risk-sized synthetic exposure | NO REAL ORDERS")
print("Primary TP $%.2f | Secondary TP $%.2f | Stop $%.2f | max spread $%.2f" % (
    PRIMARY_TAKE_PROFIT_DISTANCE_USD,
    SECONDARY_TAKE_PROFIT_DISTANCE_USD,
    STOP_DISTANCE_USD,
    MAX_SPREAD_USD,
))

if not mt5.initialize(timeout=10000):
    raise RuntimeError("MT5 initialization failed: %r" % (mt5.last_error(),))

if not mt5.symbol_select(SYMBOL, True):
    mt5.shutdown()
    raise RuntimeError("Could not select %s" % SYMBOL)

realized_inr = 0.0
position = None
last_primary_exit_time = -1e18
last_secondary_exit_time = -1e18
continuity_start_time = time.time()
last_sample_time = None
last_status = 0.0
trade_number = 0
hour_start_time = time.time()
hour_start_realized = 0.0
hour_closed_trades = 0

write_log({
    "timestamp": datetime.now().isoformat(timespec="seconds"),
    "event": "START",
    "engine": "V4.3",
    "equity_inr": START_BALANCE_INR,
    "realized_inr": 0.0,
    "reason": "paper_started",
})

try:
    while True:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None or tick.bid <= 0 or tick.ask <= 0:
            time.sleep(SAMPLE_INTERVAL)
            continue

        now = time.time()
        bid = float(tick.bid)
        ask = float(tick.ask)
        mid = (bid + ask) / 2.0
        spread = ask - bid

        if last_sample_time is not None and now - last_sample_time > MAX_QUOTE_GAP_SECONDS:
            history.clear()
            continuity_start_time = now
            print("Quote gap %.1fs -> continuity reset" % (now - last_sample_time))
        last_sample_time = now

        history.append({"time": now, "bid": bid, "ask": ask, "mid": mid})

        m30 = momentum(mid, now, SECONDARY_TREND_HORIZON_SECONDS)
        m60 = momentum(mid, now, 60)
        m300 = momentum(mid, now, 300)
        m1800 = momentum(mid, now, 1800)

        unrealized = 0.0 if position is None else pnl_inr(position, bid, ask)
        equity = START_BALANCE_INR + realized_inr + unrealized

        if now - hour_start_time >= 3600:
            hour_end = datetime.now()
            hour_pnl = realized_inr - hour_start_realized
            met = hour_pnl >= HOURLY_TARGET_INR
            print()
            print("HOURLY REVIEW | realized", money(hour_pnl), "| target", money(HOURLY_TARGET_INR), "|", "MET" if met else "MISSED")
            print("No forced trading response; review offline if opportunity capture was poor.")
            print()
            write_hourly_log({
                "hour_start_local": datetime.fromtimestamp(hour_start_time).isoformat(timespec="seconds"),
                "hour_end_local": hour_end.isoformat(timespec="seconds"),
                "start_realized_inr": round(hour_start_realized, 2),
                "end_realized_inr": round(realized_inr, 2),
                "hour_realized_pnl_inr": round(hour_pnl, 2),
                "target_inr": HOURLY_TARGET_INR,
                "target_met": met,
                "trades_closed": hour_closed_trades,
            })
            hour_start_time = now
            hour_start_realized = realized_inr
            hour_closed_trades = 0

        if now - last_status >= 2:
            state = "NONE" if position is None else "%s:%s %.4foz" % (
                position["engine"], position["side"], position["ounces"]
            )
            print("%s | B %.2f | A %.2f | S %.2f | %s | Eq %s" % (
                datetime.now().strftime("%H:%M:%S"), bid, ask, spread, state, money(equity)
            ))
            last_status = now

        if equity <= 0:
            print("ACCOUNT RUIN")
            break

        if position is not None:
            trade_pnl = unrealized
            position["mfe"] = max(position["mfe"], trade_pnl)
            position["mae"] = min(position["mae"], trade_pnl)
            held = now - position["time"]
            move = move_usd(position, bid, ask)
            position["peak_move_usd"] = max(position["peak_move_usd"], move)
            reason = None

            if move <= -STOP_DISTANCE_USD:
                reason = "STOP"
            elif position["engine"] == "PRIMARY" and move >= PRIMARY_TAKE_PROFIT_DISTANCE_USD:
                reason = "TAKE_PROFIT"
            elif position["engine"] == "SECONDARY" and move >= SECONDARY_TAKE_PROFIT_DISTANCE_USD:
                reason = "TAKE_PROFIT"

            if (
                reason is None
                and position["engine"] == "PRIMARY"
                and position["peak_move_usd"] >= PRIMARY_TRAIL_TRIGGER_USD
                and move <= position["peak_move_usd"] - PRIMARY_TRAIL_GIVEBACK_USD
            ):
                reason = "TRAIL"

            if (
                reason is None
                and position["peak_move_usd"] >= BREAKEVEN_RECOVERY_TRIGGER_USD
                and move <= 0.0
            ):
                reason = "BREAKEVEN_RECOVERY"

            reversal = m120 if position["engine"] == "PRIMARY" else m300
            if reason is None and reversal is not None:
                if position["side"] == "BUY" and reversal <= 0.0:
                    reason = "TREND_REVERSAL"
                elif position["side"] == "SELL" and reversal >= 0.0:
                    reason = "TREND_REVERSAL"

            max_hold = (
                PRIMARY_MAX_HOLD_SECONDS
                if position["engine"] == "PRIMARY"
                else SECONDARY_MAX_HOLD_SECONDS
            )
            if reason is None and held >= max_hold:
                reason = "MAX_HOLD"

            if reason is not None:
                engine = position["engine"]
                realized_inr = close_position(
                    reason, position, bid, ask, spread, realized_inr,
                    trade_pnl, m30, m60, m300, m1800
                )
                position = None
                hour_closed_trades += 1
                if engine == "PRIMARY":
                    last_primary_exit_time = now
                else:
                    last_secondary_exit_time = now
                    last_secondary_exit_was_profit = trade_pnl > 0.0

            time.sleep(SAMPLE_INTERVAL)
            continue

        if spread > MAX_SPREAD_USD:
            time.sleep(SAMPLE_INTERVAL)
            continue

        side = None
        engine = None
        channel_high = None
        channel_low = None

        if (
            now - continuity_start_time >= PRIMARY_WARMUP_SECONDS
            and now - last_primary_exit_time >= PRIMARY_COOLDOWN_SECONDS
        ):
            side = primary_signal(now, m60, m300, m1800)
            if side is not None:
                engine = "PRIMARY"

        secondary_cooldown = (
            SECONDARY_PROFIT_COOLDOWN_SECONDS
            if last_secondary_exit_was_profit
            else SECONDARY_COOLDOWN_SECONDS
        )
        if side is None and now - last_secondary_exit_time >= secondary_cooldown:
            side, channel_high, channel_low = secondary_signal(now, mid, m30, m300, m1800)
            if side is not None:
                engine = "SECONDARY"

        if side is None:
            time.sleep(SAMPLE_INTERVAL)
            continue

        balance = START_BALANCE_INR + realized_inr
        entry = ask if side == "BUY" else bid
        ounces, risk_budget = calculate_ounces(balance, entry)
        if ounces <= 0:
            time.sleep(SAMPLE_INTERVAL)
            continue

        position = {
            "engine": engine,
            "side": side,
            "entry": entry,
            "ounces": ounces,
            "risk_budget_inr": risk_budget,
            "time": now,
            "mfe": 0.0,
            "mae": 0.0,
            "peak_move_usd": 0.0,
            "channel_high": "" if channel_high is None else round(channel_high, 4),
            "channel_low": "" if channel_low is None else round(channel_low, 4),
        }
        trade_number += 1
        initial_pnl = pnl_inr(position, bid, ask)
        position["mae"] = min(0.0, initial_pnl)

        print()
        print("PAPER %s %s #%d | entry %.2f | %.5f oz | risk %s" % (
            engine, side, trade_number, entry, ounces, money(risk_budget)
        ))
        print()

        write_log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event": "ENTRY",
            "engine": engine,
            "side": side,
            "bid": round(bid, 4),
            "ask": round(ask, 4),
            "spread_usd": round(spread, 4),
            "entry_price": round(entry, 4),
            "ounces": round(ounces, 6),
            "synthetic_lots": round(ounces / CONTRACT_SIZE, 8),
            "risk_budget_inr": round(risk_budget, 2),
            "equity_inr": round(balance + initial_pnl, 2),
            "realized_inr": round(realized_inr, 2),
            "trade_pnl_inr": round(initial_pnl, 2),
            "m30": "" if m30 is None else round(m30, 4),
            "m60": "" if m60 is None else round(m60, 4),
            "m300": "" if m300 is None else round(m300, 4),
            "m1800": "" if m1800 is None else round(m1800, 4),
            "channel_high": position["channel_high"],
            "channel_low": position["channel_low"],
            "mfe_inr": 0.0,
            "mae_inr": round(position["mae"], 2),
            "reason": (
                "v4_1_trend_pullback_resumption"
                if engine == "PRIMARY"
                else "secondary_range_breakout"
            ),
        })

        time.sleep(SAMPLE_INTERVAL)

except KeyboardInterrupt:
    print("Stopping V4.3...")
    if position is not None:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick and tick.bid > 0 and tick.ask > 0:
            final_pnl = pnl_inr(position, float(tick.bid), float(tick.ask))
            position["mfe"] = max(position["mfe"], final_pnl)
            position["mae"] = min(position["mae"], final_pnl)
            realized_inr = close_position(
                "MANUAL_STOP", position, float(tick.bid), float(tick.ask),
                float(tick.ask - tick.bid), realized_inr, final_pnl,
                None, None, None, None
            )
    print("Final paper balance:", money(START_BALANCE_INR + realized_inr))

finally:
    mt5.shutdown()

print("Trade log:", LOG_FILE.resolve())
print("Hourly log:", HOURLY_LOG_FILE.resolve())
