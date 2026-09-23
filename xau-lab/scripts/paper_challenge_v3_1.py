"""
XAUUSD LIVE PAPER CHALLENGE V3.1

Persistent armed-signal successor to V3.
Research only. NO REAL ORDERS.

Key differences from V3:
- armed signals survive temporary spread widening
- breakout level is frozen at arm time
- arm lifetime is bounded
- cancellation requires genuine directional invalidation
"""

import csv
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5

SYMBOL = "XAUUSD"
START_BALANCE_INR = 500.00
TARGET_BALANCE_INR = 550.00
INR_PER_USD = 95.7021
LEVERAGE = 100.0
CONTRACT_SIZE = 100.0
EXPOSURE_FRACTION = 1.0

SAMPLE_INTERVAL = 0.50
WARMUP_SECONDS = 45
COOLDOWN_SECONDS = 20
MAX_HOLD_SECONDS = 180

MAX_SPREAD_USD = 0.35
MIN_5S_MOMENTUM_USD = 0.30
MIN_15S_MOMENTUM_USD = 0.50
MOMENTUM_SPREAD_MULTIPLE = 2.0
BREAKOUT_BUFFER_USD = 0.05

BREAKOUT_CONFIRM_SECONDS = 2.0
ARM_MAX_SECONDS = 6.0
ARM_REVERSAL_TOLERANCE_USD = 0.10
ARM_BREAKOUT_TOLERANCE_USD = 0.15

MAX_LOSS_PER_TRADE_INR = 25.00
PROFIT_LOCK_TRIGGER_INR = 8.00
PROFIT_LOCK_MIN_INR = 2.00
PROFIT_LOCK_KEEP_FRACTION = 0.50
REVERSAL_CONFIRM_COUNT = 3
REVERSAL_MOMENTUM_USD = 0.30

LOG_FILE = Path("paper_trades_v3_1.csv")


def money(value):
    return f"₹{value:.2f}"


def calculate_ounces(balance_inr, price):
    capital_usd = max(balance_inr, 0.0) / INR_PER_USD
    notional_usd = capital_usd * LEVERAGE * EXPOSURE_FRACTION
    return 0.0 if price <= 0 else notional_usd / price


def calculate_lots(ounces):
    return ounces / CONTRACT_SIZE


def get_trade_pnl(position, bid, ask):
    if position is None:
        return 0.0
    move_usd = bid - position["entry"] if position["side"] == "BUY" else position["entry"] - ask
    return move_usd * position["ounces"] * INR_PER_USD


def quote_at_or_before(history, target_time):
    for q in reversed(history):
        if q["time"] <= target_time:
            return q
    return None


def write_log(event, side="", bid=0.0, ask=0.0, spread=0.0, ounces=0.0,
              equity=0.0, realized=0.0, pnl=0.0, momentum_5s=0.0,
              momentum_15s=0.0, reason=""):
    exists = LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow([
                "timestamp","event","side","bid","ask","spread_usd","ounces",
                "synthetic_lots","equity_inr","realized_inr","trade_pnl_inr",
                "momentum_5s","momentum_15s","reason",
            ])
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"), event, side,
            round(bid,4), round(ask,4), round(spread,4), round(ounces,6),
            round(calculate_lots(ounces),8), round(equity,2), round(realized,2),
            round(pnl,2), round(momentum_5s,4), round(momentum_15s,4), reason,
        ])


def close_position(reason, position, bid, ask, spread, realized_inr, pnl, m5, m15):
    new_realized = realized_inr + pnl
    final_balance = START_BALANCE_INR + new_realized
    print()
    print(f"EXIT {position['side']}")
    print(f"P&L:       {money(pnl)}")
    print(f"Reason:    {reason}")
    print(f"Peak P&L:  {money(position['peak_pnl'])}")
    print(f"Balance:   {money(final_balance)}")
    print()
    write_log("EXIT", position["side"], bid, ask, spread, position["ounces"],
              final_balance, new_realized, pnl, m5, m15, reason)
    return new_realized


print("================================================")
print("      XAUUSD LIVE PAPER CHALLENGE V3.1")
print("================================================")
print("₹500 -> ₹550 | LIVE PRICE DATA | NO REAL ORDERS")

if not mt5.initialize(timeout=10000):
    raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
if not mt5.symbol_select(SYMBOL, True):
    mt5.shutdown()
    raise RuntimeError(f"Could not select {SYMBOL}")

info = mt5.symbol_info(SYMBOL)
if info is None:
    mt5.shutdown()
    raise RuntimeError("Could not read symbol information.")

tick = None
for _ in range(20):
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is not None and tick.bid > 0 and tick.ask > 0:
        break
    time.sleep(0.5)
if tick is None or tick.bid <= 0 or tick.ask <= 0:
    mt5.shutdown()
    raise RuntimeError("No usable XAUUSD tick.")

initial_price = (tick.bid + tick.ask) / 2
initial_ounces = calculate_ounces(START_BALANCE_INR, initial_price)

print(f"Initial exposure: {initial_ounces:.5f} oz")
print(f"Synthetic lots:   {calculate_lots(initial_ounces):.6f}")
print(f"Broker min lot:   {info.volume_min}")
print(f"Max spread:       USD {MAX_SPREAD_USD:.2f}")
print(f"Arm lifetime:     {ARM_MAX_SECONDS:.1f}s")
print(f"Hard stop:        {money(MAX_LOSS_PER_TRADE_INR)}")
print(f"Profit lock:      {money(PROFIT_LOCK_TRIGGER_INR)}")
print(f"Warming up {WARMUP_SECONDS}s...")

history = deque(maxlen=500)
realized_inr = 0.0
position = None
armed_signal = None
start_time = time.time()
last_status = 0.0
last_exit_time = 0.0
trade_number = 0

write_log("START", equity=START_BALANCE_INR, reason="challenge_started")

try:
    while True:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None or tick.bid <= 0 or tick.ask <= 0:
            time.sleep(SAMPLE_INTERVAL)
            continue

        now = time.time()
        bid, ask = float(tick.bid), float(tick.ask)
        mid = (bid + ask) / 2
        spread = ask - bid
        history.append({"time": now, "bid": bid, "ask": ask, "mid": mid})

        quote_5s = quote_at_or_before(history, now - 5)
        quote_15s = quote_at_or_before(history, now - 15)
        momentum_5s = 0.0 if quote_5s is None else mid - quote_5s["mid"]
        momentum_15s = 0.0 if quote_15s is None else mid - quote_15s["mid"]

        unrealized = get_trade_pnl(position, bid, ask)
        equity = START_BALANCE_INR + realized_inr + unrealized

        if now - last_status >= 2:
            if position:
                state = f"{position['side']} {position['ounces']:.4f}oz"
            elif armed_signal:
                state = f"ARMED-{armed_signal['side']}"
            else:
                state = "NONE"
            print(
                f"{datetime.now():%H:%M:%S} | B {bid:.2f} | A {ask:.2f} | "
                f"S {spread:.2f} | M5 {momentum_5s:+.2f} | "
                f"M15 {momentum_15s:+.2f} | {state:15} | Eq {money(equity)}"
            )
            last_status = now

        if equity >= TARGET_BALANCE_INR:
            if position:
                realized_inr = close_position(
                    "TARGET_REACHED", position, bid, ask, spread, realized_inr,
                    unrealized, momentum_5s, momentum_15s
                )
                position = None
            print(f"TARGET HIT. Final balance {money(START_BALANCE_INR + realized_inr)}")
            break

        if equity <= 0:
            print("ACCOUNT SENT TO THE SHADOW REALM")
            break

        if position:
            held_for = now - position["time"]
            position["peak_pnl"] = max(position["peak_pnl"], unrealized)

            if unrealized <= -MAX_LOSS_PER_TRADE_INR:
                realized_inr = close_position(
                    "HARD_STOP", position, bid, ask, spread, realized_inr,
                    unrealized, momentum_5s, momentum_15s
                )
                position = None
                last_exit_time = now
                time.sleep(SAMPLE_INTERVAL)
                continue

            if position["peak_pnl"] >= PROFIT_LOCK_TRIGGER_INR:
                trailing_floor = max(PROFIT_LOCK_MIN_INR, position["peak_pnl"] * PROFIT_LOCK_KEEP_FRACTION)
                if unrealized <= trailing_floor:
                    realized_inr = close_position(
                        "PROFIT_LOCK", position, bid, ask, spread, realized_inr,
                        unrealized, momentum_5s, momentum_15s
                    )
                    position = None
                    last_exit_time = now
                    time.sleep(SAMPLE_INTERVAL)
                    continue

            reversal_now = (
                position["side"] == "BUY" and momentum_5s <= -REVERSAL_MOMENTUM_USD
            ) or (
                position["side"] == "SELL" and momentum_5s >= REVERSAL_MOMENTUM_USD
            )
            position["reverse_count"] = position["reverse_count"] + 1 if reversal_now else 0

            if position["reverse_count"] >= REVERSAL_CONFIRM_COUNT:
                realized_inr = close_position(
                    "CONFIRMED_REVERSAL", position, bid, ask, spread, realized_inr,
                    unrealized, momentum_5s, momentum_15s
                )
                position = None
                last_exit_time = now
                time.sleep(SAMPLE_INTERVAL)
                continue

            if held_for >= MAX_HOLD_SECONDS:
                realized_inr = close_position(
                    "MAX_HOLD", position, bid, ask, spread, realized_inr,
                    unrealized, momentum_5s, momentum_15s
                )
                position = None
                last_exit_time = now

            time.sleep(SAMPLE_INTERVAL)
            continue

        if now - start_time < WARMUP_SECONDS:
            time.sleep(SAMPLE_INTERVAL)
            continue

        if now - last_exit_time < COOLDOWN_SECONDS:
            armed_signal = None
            time.sleep(SAMPLE_INTERVAL)
            continue

        if quote_5s is None or quote_15s is None:
            time.sleep(SAMPLE_INTERVAL)
            continue

        previous_quotes = [q for q in history if now - 30 <= q["time"] <= now - 5]
        if len(previous_quotes) < 20:
            time.sleep(SAMPLE_INTERVAL)
            continue

        recent_high = max(q["mid"] for q in previous_quotes)
        recent_low = min(q["mid"] for q in previous_quotes)

        if armed_signal is not None:
            armed_side = armed_signal["side"]
            armed_for = now - armed_signal["time"]
            breakout_level = armed_signal["breakout_level"]

            if armed_side == "BUY":
                direction_alive = (
                    momentum_15s > 0
                    and momentum_5s > -ARM_REVERSAL_TOLERANCE_USD
                    and mid >= breakout_level - ARM_BREAKOUT_TOLERANCE_USD
                )
            else:
                direction_alive = (
                    momentum_15s < 0
                    and momentum_5s < ARM_REVERSAL_TOLERANCE_USD
                    and mid <= breakout_level + ARM_BREAKOUT_TOLERANCE_USD
                )

            if not direction_alive:
                print(f"CANCELLED {armed_side}: setup reversed")
                armed_signal = None
                time.sleep(SAMPLE_INTERVAL)
                continue

            if armed_for >= ARM_MAX_SECONDS:
                print(f"EXPIRED {armed_side} after {armed_for:.2f}s")
                armed_signal = None
                time.sleep(SAMPLE_INTERVAL)
                continue

            if armed_for < BREAKOUT_CONFIRM_SECONDS:
                time.sleep(SAMPLE_INTERVAL)
                continue

            if spread > MAX_SPREAD_USD:
                time.sleep(SAMPLE_INTERVAL)
                continue

            required_5s = max(MIN_5S_MOMENTUM_USD, spread * MOMENTUM_SPREAD_MULTIPLE)

            if armed_side == "BUY":
                confirmation_valid = (
                    mid >= breakout_level
                    and momentum_5s >= required_5s
                    and momentum_15s >= MIN_15S_MOMENTUM_USD
                )
            else:
                confirmation_valid = (
                    mid <= breakout_level
                    and momentum_5s <= -required_5s
                    and momentum_15s <= -MIN_15S_MOMENTUM_USD
                )

            if not confirmation_valid:
                time.sleep(SAMPLE_INTERVAL)
                continue

            desired_side = armed_side
            print(f"CONFIRMED {desired_side} after {armed_for:.2f}s")

        else:
            if spread > MAX_SPREAD_USD:
                time.sleep(SAMPLE_INTERVAL)
                continue

            required_5s = max(MIN_5S_MOMENTUM_USD, spread * MOMENTUM_SPREAD_MULTIPLE)

            buy_signal = (
                mid > recent_high + BREAKOUT_BUFFER_USD
                and momentum_5s >= required_5s
                and momentum_15s >= MIN_15S_MOMENTUM_USD
            )
            sell_signal = (
                mid < recent_low - BREAKOUT_BUFFER_USD
                and momentum_5s <= -required_5s
                and momentum_15s <= -MIN_15S_MOMENTUM_USD
            )

            desired_side = "BUY" if buy_signal else "SELL" if sell_signal else None
            if desired_side is None:
                time.sleep(SAMPLE_INTERVAL)
                continue

            breakout_level = recent_high + BREAKOUT_BUFFER_USD if desired_side == "BUY" else recent_low - BREAKOUT_BUFFER_USD

            armed_signal = {
                "side": desired_side,
                "time": now,
                "breakout_level": breakout_level,
                "arm_mid": mid,
                "arm_spread": spread,
            }
            print(
                f"ARMED {desired_side} | M5 {momentum_5s:+.2f} | "
                f"M15 {momentum_15s:+.2f} | spread {spread:.2f} | "
                f"breakout {breakout_level:.2f}"
            )
            time.sleep(SAMPLE_INTERVAL)
            continue

        current_balance = START_BALANCE_INR + realized_inr
        entry_price = ask if desired_side == "BUY" else bid
        ounces = calculate_ounces(current_balance, entry_price)

        position = {
            "side": desired_side,
            "entry": entry_price,
            "time": now,
            "ounces": ounces,
            "peak_pnl": 0.0,
            "reverse_count": 0,
        }
        trade_number += 1
        initial_pnl = get_trade_pnl(position, bid, ask)

        print("RACE STARTED")
        print(
            f"PAPER {desired_side} #{trade_number} | entry USD {entry_price:.2f} | "
            f"{ounces:.5f} oz | spread cost {money(initial_pnl)}"
        )

        write_log(
            "ENTRY", desired_side, bid, ask, spread, ounces,
            current_balance + initial_pnl, realized_inr, initial_pnl,
            momentum_5s, momentum_15s, "confirmed_breakout"
        )
        armed_signal = None
        time.sleep(SAMPLE_INTERVAL)

except KeyboardInterrupt:
    print("Stopping V3.1...")
    if position:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick and tick.bid > 0 and tick.ask > 0:
            final_pnl = get_trade_pnl(position, tick.bid, tick.ask)
            realized_inr = close_position(
                "MANUAL_STOP", position, tick.bid, tick.ask,
                tick.ask - tick.bid, realized_inr, final_pnl,
                momentum_5s, momentum_15s
            )
    print(f"Final paper balance: {money(START_BALANCE_INR + realized_inr)}")
finally:
    mt5.shutdown()

print(f"Trade log saved to: {LOG_FILE.resolve()}")
