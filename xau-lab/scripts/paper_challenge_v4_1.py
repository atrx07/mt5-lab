"""V4.1 XAUUSD live-paper strategy. Research only; sends no real orders."""

import csv
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5

SYMBOL = "XAUUSD"
START_BALANCE_INR = 500.0
TARGET_BALANCE_INR = 550.0
INR_PER_USD = 95.7021
LEVERAGE_CAP = 100.0
CONTRACT_SIZE = 100.0

SAMPLE_INTERVAL = 0.50
WARMUP_SECONDS = 1800
COOLDOWN_SECONDS = 900
MAX_HOLD_SECONDS = 1800
MAX_SPREAD_USD = 0.30

MIN_1800S_MOMENTUM_USD = 8.0
MIN_300S_MOMENTUM_USD = 3.0
PULLBACK_60S_MOMENTUM_USD = 0.80
RESUME_60S_MOMENTUM_USD = 0.50
PULLBACK_LOOKBACK_SECONDS = 300

RISK_FRACTION = 0.03
STOP_DISTANCE_USD = 4.0
TAKE_PROFIT_DISTANCE_USD = 21.0
TREND_REVERSAL_300S_USD = 0.0

LOG_FILE = Path("paper_trades_v4_1.csv")
history = deque(maxlen=5000)


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
    age = now - q["time"]
    if age > seconds + 5:
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
    if position["side"] == "BUY":
        move = bid - position["entry"]
    else:
        move = position["entry"] - ask
    return move * position["ounces"] * INR_PER_USD


def move_usd(position, bid, ask):
    if position["side"] == "BUY":
        return bid - position["entry"]
    return position["entry"] - ask


FIELDS = [
    "timestamp", "event", "side", "bid", "ask", "spread_usd",
    "entry_price", "ounces", "synthetic_lots", "risk_budget_inr",
    "equity_inr", "realized_inr", "trade_pnl_inr",
    "m60", "m300", "m1800", "mfe_inr", "mae_inr", "reason",
]


def write_log(row):
    exists = LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in FIELDS})


def close_position(reason, position, bid, ask, spread, realized, trade_pnl, m60, m300, m1800):
    realized += trade_pnl
    balance = START_BALANCE_INR + realized
    print()
    print("EXIT", position["side"], "|", reason)
    print("P&L:", money(trade_pnl), "| MFE:", money(position["mfe"]), "| MAE:", money(position["mae"]))
    print("Balance:", money(balance))
    print()

    write_log({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": "EXIT",
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
        "m60": "" if m60 is None else round(m60, 4),
        "m300": "" if m300 is None else round(m300, 4),
        "m1800": "" if m1800 is None else round(m1800, 4),
        "mfe_inr": round(position["mfe"], 2),
        "mae_inr": round(position["mae"], 2),
        "reason": reason,
    })
    return realized


print("================================================")
print("      XAUUSD LIVE PAPER CHALLENGE V4.1")
print("================================================")
print("30m trend -> 5m trend -> 60s pullback/resumption")
print("3% risk-sized synthetic exposure | NO REAL ORDERS")
print("Stop $%.2f | TP $%.2f | max spread $%.2f" % (
    STOP_DISTANCE_USD, TAKE_PROFIT_DISTANCE_USD, MAX_SPREAD_USD
))

if not mt5.initialize(timeout=10000):
    raise RuntimeError("MT5 initialization failed: %r" % (mt5.last_error(),))

if not mt5.symbol_select(SYMBOL, True):
    mt5.shutdown()
    raise RuntimeError("Could not select %s" % SYMBOL)

realized_inr = 0.0
position = None
last_exit_time = 0.0
start_time = time.time()
last_status = 0.0
trade_number = 0

write_log({
    "timestamp": datetime.now().isoformat(timespec="seconds"),
    "event": "START",
    "equity_inr": START_BALANCE_INR,
    "realized_inr": 0.0,
    "reason": "challenge_started",
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

        history.append({"time": now, "bid": bid, "ask": ask, "mid": mid})

        m60 = momentum(mid, now, 60)
        m300 = momentum(mid, now, 300)
        m1800 = momentum(mid, now, 1800)

        unrealized = 0.0 if position is None else pnl_inr(position, bid, ask)
        equity = START_BALANCE_INR + realized_inr + unrealized

        if now - last_status >= 2:
            state = "NONE" if position is None else "%s %.4foz" % (position["side"], position["ounces"])
            print("%s | B %.2f | A %.2f | S %.2f | %s | Eq %s" % (
                datetime.now().strftime("%H:%M:%S"), bid, ask, spread, state, money(equity)
            ))
            last_status = now

        if equity >= TARGET_BALANCE_INR:
            if position is not None:
                position["mfe"] = max(position["mfe"], unrealized)
                position["mae"] = min(position["mae"], unrealized)
                realized_inr = close_position(
                    "TARGET_REACHED", position, bid, ask, spread, realized_inr,
                    unrealized, m60, m300, m1800
                )
                position = None
            print("TARGET HIT:", money(START_BALANCE_INR + realized_inr))
            break

        if equity <= 0:
            print("ACCOUNT RUIN")
            break

        if position is not None:
            trade_pnl = unrealized
            position["mfe"] = max(position["mfe"], trade_pnl)
            position["mae"] = min(position["mae"], trade_pnl)
            held = now - position["time"]
            move = move_usd(position, bid, ask)
            reason = None

            if move <= -STOP_DISTANCE_USD:
                reason = "STOP"
            elif move >= TAKE_PROFIT_DISTANCE_USD:
                reason = "TAKE_PROFIT"
            elif m300 is not None:
                if position["side"] == "BUY" and m300 <= -TREND_REVERSAL_300S_USD:
                    reason = "TREND_REVERSAL"
                elif position["side"] == "SELL" and m300 >= TREND_REVERSAL_300S_USD:
                    reason = "TREND_REVERSAL"

            if reason is None and held >= MAX_HOLD_SECONDS:
                reason = "MAX_HOLD"

            if reason is not None:
                realized_inr = close_position(
                    reason, position, bid, ask, spread, realized_inr,
                    trade_pnl, m60, m300, m1800
                )
                position = None
                last_exit_time = now

            time.sleep(SAMPLE_INTERVAL)
            continue

        if now - start_time < WARMUP_SECONDS:
            time.sleep(SAMPLE_INTERVAL)
            continue

        if now - last_exit_time < COOLDOWN_SECONDS:
            time.sleep(SAMPLE_INTERVAL)
            continue

        if m60 is None or m300 is None or m1800 is None or spread > MAX_SPREAD_USD:
            time.sleep(SAMPLE_INTERVAL)
            continue

        recent_m60 = []
        for q in history:
            if q["time"] < now - PULLBACK_LOOKBACK_SECONDS:
                continue
            q60 = quote_at_or_before(q["time"] - 60)
            if q60 is None:
                continue
            if q["time"] - q60["time"] > 65:
                continue
            recent_m60.append(q["mid"] - q60["mid"])

        if not recent_m60:
            time.sleep(SAMPLE_INTERVAL)
            continue

        buy_signal = (
            m1800 >= MIN_1800S_MOMENTUM_USD
            and m300 >= MIN_300S_MOMENTUM_USD
            and min(recent_m60) <= -PULLBACK_60S_MOMENTUM_USD
            and m60 >= RESUME_60S_MOMENTUM_USD
        )
        sell_signal = (
            m1800 <= -MIN_1800S_MOMENTUM_USD
            and m300 <= -MIN_300S_MOMENTUM_USD
            and max(recent_m60) >= PULLBACK_60S_MOMENTUM_USD
            and m60 <= -RESUME_60S_MOMENTUM_USD
        )

        side = "BUY" if buy_signal else "SELL" if sell_signal else None
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
            "side": side,
            "entry": entry,
            "ounces": ounces,
            "risk_budget_inr": risk_budget,
            "time": now,
            "mfe": 0.0,
            "mae": 0.0,
        }
        trade_number += 1
        initial_pnl = pnl_inr(position, bid, ask)
        position["mae"] = min(0.0, initial_pnl)

        print()
        print("PAPER %s #%d | entry %.2f | %.5f oz | risk %s" % (
            side, trade_number, entry, ounces, money(risk_budget)
        ))
        print()

        write_log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event": "ENTRY",
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
            "m60": round(m60, 4),
            "m300": round(m300, 4),
            "m1800": round(m1800, 4),
            "mfe_inr": 0.0,
            "mae_inr": round(position["mae"], 2),
            "reason": "trend_pullback_resumption",
        })

        time.sleep(SAMPLE_INTERVAL)

except KeyboardInterrupt:
    print("Stopping V4.1...")
    if position is not None:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick and tick.bid > 0 and tick.ask > 0:
            final_pnl = pnl_inr(position, float(tick.bid), float(tick.ask))
            position["mfe"] = max(position["mfe"], final_pnl)
            position["mae"] = min(position["mae"], final_pnl)
            realized_inr = close_position(
                "MANUAL_STOP", position, float(tick.bid), float(tick.ask),
                float(tick.ask - tick.bid), realized_inr, final_pnl,
                None, None, None
            )
    print("Final paper balance:", money(START_BALANCE_INR + realized_inr))

finally:
    mt5.shutdown()

print("Trade log:", LOG_FILE.resolve())
