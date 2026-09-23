"""
XAUUSD LIVE PAPER CHALLENGE V4 — pullback/resumption research candidate

Philosophy:
    establish direction -> wait for pullback -> enter on resumption

V4 deliberately stops chasing the first obvious breakout.
It also enforces one trade per impulse.

Research only. NO REAL ORDERS.
"""

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
LEVERAGE = 100.0
CONTRACT_SIZE = 100.0
EXPOSURE_FRACTION = 1.0

SAMPLE_INTERVAL = 0.50
WARMUP_SECONDS = 45
COOLDOWN_SECONDS = 45
MAX_HOLD_SECONDS = 60

MAX_SPREAD_USD = 0.28

MIN_IMPULSE_M5_USD = 0.55
MIN_IMPULSE_M15_USD = 0.70
MAX_IMPULSE_M5_USD = 1.50

PULLBACK_MIN_USD = 0.20
PULLBACK_MAX_USD = 0.85
SLOW_CONTEXT_MIN_USD = 0.20

RESUME_M2_USD = 0.15
RESUME_M5_USD = 0.15
RESUME_DISTANCE_USD = 0.15

IMPULSE_MAX_AGE_SECONDS = 45
RESET_M15_USD = 0.25

MAX_LOSS_PER_TRADE_INR = 8.0
PROFIT_LOCK_TRIGGER_INR = 4.0
PROFIT_LOCK_MIN_INR = 1.5
PROFIT_LOCK_KEEP_FRACTION = 0.65

REVERSAL_CONFIRM_COUNT = 2
REVERSAL_M2_USD = 0.25

LOG_FILE = Path("paper_trades_v4.csv")


def money(value):
    return f"₹{value:.2f}"


def at_or_before(history, target):
    for q in reversed(history):
        if q["time"] <= target:
            return q
    return None


def exposure_oz(balance_inr, price):
    capital_usd = max(balance_inr, 0.0) / INR_PER_USD
    notional_usd = capital_usd * LEVERAGE * EXPOSURE_FRACTION
    return 0.0 if price <= 0 else notional_usd / price


def trade_pnl(position, bid, ask):
    if position is None:
        return 0.0
    move = bid - position["entry"] if position["side"] == "BUY" else position["entry"] - ask
    return move * position["ounces"] * INR_PER_USD


def write_log(event, side="", bid=0.0, ask=0.0, spread=0.0, ounces=0.0,
              equity=0.0, realized=0.0, pnl=0.0, m2=0.0, m5=0.0, m15=0.0,
              reason="", state=""):
    exists = LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow([
                "timestamp","event","side","bid","ask","spread_usd","ounces",
                "synthetic_lots","equity_inr","realized_inr","trade_pnl_inr",
                "momentum_2s","momentum_5s","momentum_15s","reason","state",
            ])
        w.writerow([
            datetime.now().isoformat(timespec="seconds"), event, side,
            round(bid,4), round(ask,4), round(spread,4), round(ounces,6),
            round(ounces/CONTRACT_SIZE,8), round(equity,2), round(realized,2),
            round(pnl,2), round(m2,4), round(m5,4), round(m15,4), reason, state,
        ])


def close_position(reason, position, bid, ask, spread, realized, u, m2, m5, m15):
    realized += u
    print()
    print(f"EXIT {position['side']} | P&L {money(u)} | {reason}")
    print(f"Peak P&L {money(position['peak_pnl'])}")
    print(f"Balance {money(START_BALANCE_INR + realized)}")
    print()
    write_log(
        "EXIT", position["side"], bid, ask, spread, position["ounces"],
        START_BALANCE_INR + realized, realized, u, m2, m5, m15,
        reason, "LOCKOUT"
    )
    return realized


if not mt5.initialize(timeout=10000):
    raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
if not mt5.symbol_select(SYMBOL, True):
    mt5.shutdown()
    raise RuntimeError(f"Could not select {SYMBOL}")

print("================================================")
print(" XAUUSD LIVE PAPER CHALLENGE V4")
print(" trend -> pullback -> resumption")
print(" NO REAL ORDERS")
print("================================================")
print(f"Start: {money(START_BALANCE_INR)}")
print(f"Target: {money(TARGET_BALANCE_INR)}")
print(f"Max spread: USD {MAX_SPREAD_USD:.2f}")
print(f"Hard stop: {money(MAX_LOSS_PER_TRADE_INR)}")
print(f"Profit lock trigger: {money(PROFIT_LOCK_TRIGGER_INR)}")
print(f"Cooldown: {COOLDOWN_SECONDS}s")
print()

history = deque(maxlen=800)
realized = 0.0
position = None
impulse = None
consumed_side = None
started = time.time()
last_exit = 0.0
last_status = 0.0
trade_no = 0

write_log("START", equity=START_BALANCE_INR, reason="challenge_started", state="RESET")

try:
    while True:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None or tick.bid <= 0 or tick.ask <= 0:
            time.sleep(SAMPLE_INTERVAL)
            continue

        now = time.time()
        bid, ask = float(tick.bid), float(tick.ask)
        mid = (bid + ask) / 2.0
        spread = ask - bid
        history.append({"time": now, "mid": mid, "bid": bid, "ask": ask})

        q2 = at_or_before(history, now - 2)
        q5 = at_or_before(history, now - 5)
        q15 = at_or_before(history, now - 15)
        m2 = 0.0 if q2 is None else mid - q2["mid"]
        m5 = 0.0 if q5 is None else mid - q5["mid"]
        m15 = 0.0 if q15 is None else mid - q15["mid"]

        u = 0.0 if position is None else trade_pnl(position, bid, ask)
        equity = START_BALANCE_INR + realized + u

        if position:
            state = f"IN-{position['side']}"
        elif consumed_side:
            state = f"LOCKOUT-{consumed_side}"
        elif impulse:
            state = f"{'PULLBACK' if impulse['pullback_seen'] else 'IMPULSE'}-{impulse['side']}"
        else:
            state = "RESET"

        if now - last_status >= 2:
            print(
                f"{datetime.now():%H:%M:%S} | B {bid:.2f} | A {ask:.2f} | "
                f"S {spread:.2f} | M2 {m2:+.2f} | M5 {m5:+.2f} | "
                f"M15 {m15:+.2f} | {state:16} | Eq {money(equity)}"
            )
            last_status = now

        if equity >= TARGET_BALANCE_INR:
            if position:
                realized = close_position(
                    "TARGET_REACHED", position, bid, ask, spread, realized, u, m2, m5, m15
                )
                position = None
            print(f"TARGET HIT: {money(START_BALANCE_INR + realized)}")
            break

        if equity <= 0:
            print("ACCOUNT RUIN")
            break

        # -------------------------------------------------
        # Manage open position
        # -------------------------------------------------
        if position:
            position["peak_pnl"] = max(position["peak_pnl"], u)
            held = now - position["time"]
            reason = None

            if u <= -MAX_LOSS_PER_TRADE_INR:
                reason = "HARD_STOP"

            if reason is None and position["peak_pnl"] >= PROFIT_LOCK_TRIGGER_INR:
                floor = max(
                    PROFIT_LOCK_MIN_INR,
                    position["peak_pnl"] * PROFIT_LOCK_KEEP_FRACTION,
                )
                if u <= floor:
                    reason = "PROFIT_LOCK"

            opposite = (
                position["side"] == "BUY" and m2 <= -REVERSAL_M2_USD
            ) or (
                position["side"] == "SELL" and m2 >= REVERSAL_M2_USD
            )
            position["reverse_count"] = position["reverse_count"] + 1 if opposite else 0

            if reason is None and position["reverse_count"] >= REVERSAL_CONFIRM_COUNT:
                reason = "CONFIRMED_REVERSAL"

            if reason is None and held >= MAX_HOLD_SECONDS:
                reason = "MAX_HOLD"

            if reason:
                side = position["side"]
                realized = close_position(
                    reason, position, bid, ask, spread, realized, u, m2, m5, m15
                )
                position = None
                consumed_side = side
                impulse = None
                last_exit = now

            time.sleep(SAMPLE_INTERVAL)
            continue

        # -------------------------------------------------
        # Warmup
        # -------------------------------------------------
        if now - started < WARMUP_SECONDS or q2 is None or q5 is None or q15 is None:
            time.sleep(SAMPLE_INTERVAL)
            continue

        # -------------------------------------------------
        # Lockout: one trade per impulse
        # -------------------------------------------------
        if consumed_side is not None:
            cooled = now - last_exit >= COOLDOWN_SECONDS
            reset = abs(m15) <= RESET_M15_USD
            opposite_regime = (
                consumed_side == "BUY" and m15 <= -MIN_IMPULSE_M15_USD
            ) or (
                consumed_side == "SELL" and m15 >= MIN_IMPULSE_M15_USD
            )

            if cooled and (reset or opposite_regime):
                consumed_side = None
                impulse = None
                print("RESET complete: new impulse may be traded.")
            else:
                time.sleep(SAMPLE_INTERVAL)
                continue

        # -------------------------------------------------
        # Create a fresh impulse
        # -------------------------------------------------
        if impulse is None:
            if spread > MAX_SPREAD_USD:
                time.sleep(SAMPLE_INTERVAL)
                continue

            buy_impulse = (
                MIN_IMPULSE_M5_USD <= m5 <= MAX_IMPULSE_M5_USD
                and m15 >= MIN_IMPULSE_M15_USD
            )
            sell_impulse = (
                -MAX_IMPULSE_M5_USD <= m5 <= -MIN_IMPULSE_M5_USD
                and m15 <= -MIN_IMPULSE_M15_USD
            )

            side = "BUY" if buy_impulse else "SELL" if sell_impulse else None

            if side:
                impulse = {
                    "side": side,
                    "time": now,
                    "origin": mid,
                    "extreme": mid,
                    "pullback_seen": False,
                    "pullback_extreme": mid,
                }
                print(
                    f"IMPULSE {side} | origin {mid:.2f} | "
                    f"M5 {m5:+.2f} | M15 {m15:+.2f}"
                )

            time.sleep(SAMPLE_INTERVAL)
            continue

        # -------------------------------------------------
        # Maintain / invalidate impulse
        # -------------------------------------------------
        side = impulse["side"]

        if now - impulse["time"] > IMPULSE_MAX_AGE_SECONDS:
            print(f"IMPULSE {side} expired.")
            impulse = None
            time.sleep(SAMPLE_INTERVAL)
            continue

        context_alive = (
            side == "BUY" and m15 >= SLOW_CONTEXT_MIN_USD
        ) or (
            side == "SELL" and m15 <= -SLOW_CONTEXT_MIN_USD
        )

        if not context_alive:
            print(f"IMPULSE {side} invalidated by slow context.")
            impulse = None
            time.sleep(SAMPLE_INTERVAL)
            continue

        if side == "BUY":
            impulse["extreme"] = max(impulse["extreme"], mid)
            retrace = impulse["extreme"] - mid
        else:
            impulse["extreme"] = min(impulse["extreme"], mid)
            retrace = mid - impulse["extreme"]

        if not impulse["pullback_seen"]:
            if PULLBACK_MIN_USD <= retrace <= PULLBACK_MAX_USD:
                impulse["pullback_seen"] = True
                impulse["pullback_extreme"] = mid
                print(f"PULLBACK {side} detected | retrace USD {retrace:.2f}")
            elif retrace > PULLBACK_MAX_USD:
                impulse = None

            time.sleep(SAMPLE_INTERVAL)
            continue

        # Continue tracking the deepest pullback.
        if side == "BUY":
            impulse["pullback_extreme"] = min(impulse["pullback_extreme"], mid)
            resumed_distance = mid - impulse["pullback_extreme"]
            resumed = (
                m2 >= RESUME_M2_USD
                and m5 >= RESUME_M5_USD
                and resumed_distance >= RESUME_DISTANCE_USD
            )
        else:
            impulse["pullback_extreme"] = max(impulse["pullback_extreme"], mid)
            resumed_distance = impulse["pullback_extreme"] - mid
            resumed = (
                m2 <= -RESUME_M2_USD
                and m5 <= -RESUME_M5_USD
                and resumed_distance >= RESUME_DISTANCE_USD
            )

        if not resumed or spread > MAX_SPREAD_USD:
            time.sleep(SAMPLE_INTERVAL)
            continue

        # -------------------------------------------------
        # Entry on resumption
        # -------------------------------------------------
        balance = START_BALANCE_INR + realized
        entry = ask if side == "BUY" else bid
        ounces = exposure_oz(balance, entry)

        position = {
            "side": side,
            "entry": entry,
            "ounces": ounces,
            "time": now,
            "peak_pnl": 0.0,
            "reverse_count": 0,
        }
        trade_no += 1
        initial = trade_pnl(position, bid, ask)

        print()
        print(f"PAPER {side} #{trade_no}")
        print(f"Entry: USD {entry:.2f}")
        print(f"Exposure: {ounces:.5f} oz")
        print(f"Spread: USD {spread:.2f}")
        print(f"Initial spread P&L: {money(initial)}")
        print()

        write_log(
            "ENTRY", side, bid, ask, spread, ounces, balance + initial,
            realized, initial, m2, m5, m15, "pullback_resumption", "IN_TRADE"
        )

        # The impulse is consumed immediately. Another entry requires reset after exit.
        impulse = None
        time.sleep(SAMPLE_INTERVAL)

except KeyboardInterrupt:
    print("Stopping V4...")
    if position:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick and tick.bid > 0 and tick.ask > 0:
            u = trade_pnl(position, tick.bid, tick.ask)
            realized = close_position(
                "MANUAL_STOP", position, tick.bid, tick.ask,
                tick.ask - tick.bid, realized, u, m2, m5, m15
            )
    print(f"Final paper balance: {money(START_BALANCE_INR + realized)}")
finally:
    mt5.shutdown()

print(f"Trade log saved to: {LOG_FILE.resolve()}")
