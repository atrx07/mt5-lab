"""
XAUUSD LIVE PAPER CHALLENGE V1
Historical reconstruction from the 2026-09-23 experiment.

Research only. NO REAL ORDERS.
"""

import time
from collections import deque
from datetime import datetime

import MetaTrader5 as mt5

SYMBOL = "XAUUSD"
START_BALANCE_INR = 100.0
TARGET_BALANCE_INR = 150.0
INR_PER_USD = 95.7021

# Deliberately reckless historical V1 setting:
FIXED_OUNCES = 1.0

SAMPLE_INTERVAL = 0.50
WARMUP_SECONDS = 30
COOLDOWN_SECONDS = 15
MAX_HOLD_SECONDS = 120

MAX_SPREAD_USD = 0.35
MIN_5S_MOMENTUM_USD = 0.30
BREAKOUT_BUFFER_USD = 0.05


def quote_at_or_before(history, target):
    for q in reversed(history):
        if q["time"] <= target:
            return q
    return None


def pnl_inr(position, bid, ask):
    if position["side"] == "BUY":
        move = bid - position["entry"]
    else:
        move = position["entry"] - ask
    return move * position["ounces"] * INR_PER_USD


if not mt5.initialize(timeout=10000):
    raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
if not mt5.symbol_select(SYMBOL, True):
    mt5.shutdown()
    raise RuntimeError(f"Could not select {SYMBOL}")

history = deque(maxlen=500)
balance = START_BALANCE_INR
position = None
started = time.time()
last_exit = 0.0
trade_no = 0

print("=== XAUUSD LIVE PAPER CHALLENGE V1 ===")
print("₹100 -> ₹150 | fixed synthetic 1 oz | NO REAL ORDERS")

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
        history.append({"time": now, "bid": bid, "ask": ask, "mid": mid})

        q5 = quote_at_or_before(history, now - 5)
        m5 = 0.0 if q5 is None else mid - q5["mid"]

        unrealized = 0.0 if position is None else pnl_inr(position, bid, ask)
        equity = balance + unrealized

        print(
            f"{datetime.now():%H:%M:%S} | B {bid:.2f} | A {ask:.2f} | "
            f"S {spread:.2f} | M5 {m5:+.2f} | "
            f"{position['side'] if position else 'NONE':4} | Eq ₹{equity:.2f}"
        )

        if equity >= TARGET_BALANCE_INR:
            if position:
                balance += unrealized
            print(f"TARGET HIT: ₹{balance:.2f}")
            break

        if equity <= 0:
            if position:
                balance += unrealized
            print(f"ACCOUNT RUIN: ₹{balance:.2f}")
            break

        if position:
            held = now - position["time"]
            reverse = (
                position["side"] == "BUY" and m5 <= -MIN_5S_MOMENTUM_USD
            ) or (
                position["side"] == "SELL" and m5 >= MIN_5S_MOMENTUM_USD
            )
            if reverse or held >= MAX_HOLD_SECONDS:
                trade_pnl = pnl_inr(position, bid, ask)
                balance += trade_pnl
                print(f"EXIT {position['side']} | P&L ₹{trade_pnl:.2f} | Balance ₹{balance:.2f}")
                position = None
                last_exit = now
            time.sleep(SAMPLE_INTERVAL)
            continue

        if now - started < WARMUP_SECONDS or now - last_exit < COOLDOWN_SECONDS:
            time.sleep(SAMPLE_INTERVAL)
            continue
        if q5 is None or spread > MAX_SPREAD_USD:
            time.sleep(SAMPLE_INTERVAL)
            continue

        base = [q for q in history if now - 30 <= q["time"] <= now - 5]
        if len(base) < 20:
            time.sleep(SAMPLE_INTERVAL)
            continue

        high = max(q["mid"] for q in base)
        low = min(q["mid"] for q in base)

        side = None
        if mid > high + BREAKOUT_BUFFER_USD and m5 >= MIN_5S_MOMENTUM_USD:
            side = "BUY"
        elif mid < low - BREAKOUT_BUFFER_USD and m5 <= -MIN_5S_MOMENTUM_USD:
            side = "SELL"

        if side:
            entry = ask if side == "BUY" else bid
            position = {
                "side": side,
                "entry": entry,
                "time": now,
                "ounces": FIXED_OUNCES,
            }
            trade_no += 1
            cost = pnl_inr(position, bid, ask)
            print(
                f"PAPER {side} #{trade_no} | entry {entry:.2f} | "
                f"1.0000 oz | spread cost ₹{cost:.2f}"
            )

        time.sleep(SAMPLE_INTERVAL)

except KeyboardInterrupt:
    if position:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick and tick.bid > 0 and tick.ask > 0:
            balance += pnl_inr(position, tick.bid, tick.ask)
    print(f"Stopped. Final paper balance ₹{balance:.2f}")
finally:
    mt5.shutdown()
