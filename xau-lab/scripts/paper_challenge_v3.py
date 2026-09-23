"""
XAUUSD LIVE PAPER CHALLENGE V3
Behavior-preserving reconstruction of the 2026-09-23 version.

V3 adds:
- 5s + 15s momentum agreement
- 2s breakout confirmation
- ₹25 hard stop
- profit lock after ₹8
- confirmed reversal exit
- 20s cooldown

Historical bug retained intentionally:
a temporary spread violation / invalid signal can erase an armed setup.

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

MAX_LOSS_PER_TRADE_INR = 25.0
PROFIT_LOCK_TRIGGER_INR = 8.0
PROFIT_LOCK_MIN_INR = 2.0
PROFIT_LOCK_KEEP_FRACTION = 0.50
REVERSAL_CONFIRM_COUNT = 3
REVERSAL_MOMENTUM_USD = 0.30

LOG_FILE = Path("paper_trades_v3.csv")


def at_or_before(history, target):
    for q in reversed(history):
        if q["time"] <= target:
            return q
    return None


def size_oz(balance_inr, price):
    return (max(balance_inr, 0.0) / INR_PER_USD) * LEVERAGE / price


def pnl(position, bid, ask):
    move = bid - position["entry"] if position["side"] == "BUY" else position["entry"] - ask
    return move * position["ounces"] * INR_PER_USD


def log(event, side, bid, ask, spread, ounces, equity, realized, trade_pnl, m5, m15, reason):
    exists = LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow([
                "timestamp","event","side","bid","ask","spread_usd","ounces",
                "synthetic_lots","equity_inr","realized_inr","trade_pnl_inr",
                "momentum_5s","momentum_15s","reason",
            ])
        w.writerow([
            datetime.now().isoformat(timespec="seconds"), event, side,
            round(bid,4), round(ask,4), round(spread,4), round(ounces,6),
            round(ounces/CONTRACT_SIZE,8), round(equity,2), round(realized,2),
            round(trade_pnl,2), round(m5,4), round(m15,4), reason,
        ])


if not mt5.initialize(timeout=10000):
    raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
if not mt5.symbol_select(SYMBOL, True):
    mt5.shutdown()
    raise RuntimeError(f"Could not select {SYMBOL}")

history = deque(maxlen=500)
realized = 0.0
position = None
armed = None
started = time.time()
last_exit = 0.0
trade_no = 0

log("START", "", 0,0,0,0, START_BALANCE_INR,0,0,0,0,"challenge_started")
print("=== XAUUSD LIVE PAPER CHALLENGE V3 ===")

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
        history.append({"time": now, "mid": mid, "bid": bid, "ask": ask})

        q5, q15 = at_or_before(history, now-5), at_or_before(history, now-15)
        m5 = 0.0 if q5 is None else mid - q5["mid"]
        m15 = 0.0 if q15 is None else mid - q15["mid"]

        u = 0.0 if position is None else pnl(position, bid, ask)
        equity = START_BALANCE_INR + realized + u

        state = position["side"] if position else f"ARMED-{armed['side']}" if armed else "NONE"
        print(f"{datetime.now():%H:%M:%S} | B {bid:.2f} | A {ask:.2f} | S {spread:.2f} | M5 {m5:+.2f} | M15 {m15:+.2f} | {state:11} | Eq ₹{equity:.2f}")

        if equity >= TARGET_BALANCE_INR:
            if position:
                realized += u
            break
        if equity <= 0:
            break

        if position:
            position["peak_pnl"] = max(position["peak_pnl"], u)
            reason = None
            if u <= -MAX_LOSS_PER_TRADE_INR:
                reason = "HARD_STOP"
            elif position["peak_pnl"] >= PROFIT_LOCK_TRIGGER_INR:
                floor = max(PROFIT_LOCK_MIN_INR, position["peak_pnl"] * PROFIT_LOCK_KEEP_FRACTION)
                if u <= floor:
                    reason = "PROFIT_LOCK"

            reverse_now = (
                position["side"] == "BUY" and m5 <= -REVERSAL_MOMENTUM_USD
            ) or (
                position["side"] == "SELL" and m5 >= REVERSAL_MOMENTUM_USD
            )
            position["reverse_count"] = position["reverse_count"] + 1 if reverse_now else 0
            if reason is None and position["reverse_count"] >= REVERSAL_CONFIRM_COUNT:
                reason = "CONFIRMED_REVERSAL"
            if reason is None and now - position["time"] >= MAX_HOLD_SECONDS:
                reason = "MAX_HOLD"

            if reason:
                realized += u
                print(f"EXIT {position['side']} | P&L ₹{u:.2f} | {reason} | peak ₹{position['peak_pnl']:.2f}")
                log("EXIT", position["side"], bid, ask, spread, position["ounces"], START_BALANCE_INR+realized, realized, u, m5, m15, reason)
                position = None
                last_exit = now
            time.sleep(SAMPLE_INTERVAL)
            continue

        if now-started < WARMUP_SECONDS or now-last_exit < COOLDOWN_SECONDS or q5 is None or q15 is None:
            armed = None
            time.sleep(SAMPLE_INTERVAL)
            continue

        base = [q for q in history if now-30 <= q["time"] <= now-5]
        if len(base) < 20:
            time.sleep(SAMPLE_INTERVAL)
            continue

        recent_high = max(q["mid"] for q in base)
        recent_low = min(q["mid"] for q in base)
        required_m5 = max(MIN_5S_MOMENTUM_USD, spread * MOMENTUM_SPREAD_MULTIPLE)

        buy = (
            spread <= MAX_SPREAD_USD and
            mid > recent_high + BREAKOUT_BUFFER_USD and
            m5 >= required_m5 and m15 >= MIN_15S_MOMENTUM_USD
        )
        sell = (
            spread <= MAX_SPREAD_USD and
            mid < recent_low - BREAKOUT_BUFFER_USD and
            m5 <= -required_m5 and m15 <= -MIN_15S_MOMENTUM_USD
        )
        desired = "BUY" if buy else "SELL" if sell else None

        # Historical V3 behavior: any invalid tick cancels the arm.
        if desired is None:
            armed = None
            time.sleep(SAMPLE_INTERVAL)
            continue

        if armed is None or armed["side"] != desired:
            armed = {"side": desired, "time": now}
            print(f"ARMED {desired} | waiting {BREAKOUT_CONFIRM_SECONDS:.1f}s")
            time.sleep(SAMPLE_INTERVAL)
            continue

        if now - armed["time"] < BREAKOUT_CONFIRM_SECONDS:
            time.sleep(SAMPLE_INTERVAL)
            continue

        entry = ask if desired == "BUY" else bid
        ounces = size_oz(START_BALANCE_INR + realized, entry)
        position = {
            "side": desired, "entry": entry, "ounces": ounces, "time": now,
            "peak_pnl": 0.0, "reverse_count": 0,
        }
        trade_no += 1
        initial = pnl(position, bid, ask)
        print(f"PAPER {desired} #{trade_no} | entry {entry:.2f} | spread cost ₹{initial:.2f}")
        log("ENTRY", desired, bid, ask, spread, ounces, START_BALANCE_INR+realized+initial, realized, initial, m5, m15, "confirmed_breakout")
        armed = None
        time.sleep(SAMPLE_INTERVAL)

except KeyboardInterrupt:
    print(f"Stopped. Final paper balance ₹{START_BALANCE_INR + realized:.2f}")
finally:
    mt5.shutdown()
