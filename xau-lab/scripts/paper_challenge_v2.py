"""
XAUUSD LIVE PAPER CHALLENGE V2
Behavior-preserving reconstruction of the 2026-09-23 version.

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
EXPOSURE_FRACTION = 1.0
CONTRACT_SIZE = 100.0

SAMPLE_INTERVAL = 0.50
WARMUP_SECONDS = 30
COOLDOWN_SECONDS = 15
MAX_HOLD_SECONDS = 120

MAX_SPREAD_USD = 0.35
MIN_5S_MOMENTUM_USD = 0.30
BREAKOUT_BUFFER_USD = 0.05
MAX_LOSS_PER_TRADE_INR = 50.0

LOG_FILE = Path("paper_trades_v2.csv")


def quote_at_or_before(history, target):
    for q in reversed(history):
        if q["time"] <= target:
            return q
    return None


def ounces_for(balance_inr, price):
    capital_usd = max(balance_inr, 0.0) / INR_PER_USD
    return capital_usd * LEVERAGE * EXPOSURE_FRACTION / price


def pnl_inr(position, bid, ask):
    move = bid - position["entry"] if position["side"] == "BUY" else position["entry"] - ask
    return move * position["ounces"] * INR_PER_USD


def log_row(event, side, bid, ask, spread, ounces, balance, pnl, m5, reason):
    exists = LOG_FILE.exists()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow([
                "timestamp", "event", "side", "bid", "ask", "spread_usd",
                "ounces", "synthetic_lots", "balance_inr", "trade_pnl_inr",
                "momentum_5s", "reason",
            ])
        w.writerow([
            datetime.now().isoformat(timespec="seconds"), event, side,
            round(bid, 4), round(ask, 4), round(spread, 4),
            round(ounces, 6), round(ounces / CONTRACT_SIZE, 8),
            round(balance, 2), round(pnl, 2), round(m5, 4), reason,
        ])


if not mt5.initialize(timeout=10000):
    raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
if not mt5.symbol_select(SYMBOL, True):
    mt5.shutdown()
    raise RuntimeError(f"Could not select {SYMBOL}")

history = deque(maxlen=500)
realized = 0.0
position = None
started = time.time()
last_exit = 0.0
trade_no = 0

print("=== XAUUSD LIVE PAPER CHALLENGE V2 ===")
print("₹500 -> ₹550 | dynamic synthetic 100x exposure | NO REAL ORDERS")

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
        balance = START_BALANCE_INR + realized
        equity = balance + unrealized

        print(
            f"{datetime.now():%H:%M:%S} | Bid {bid:.2f} | Ask {ask:.2f} | "
            f"Spr {spread:.2f} | {position['side'] if position else 'NONE':4} | Eq ₹{equity:.2f}"
        )

        if equity >= TARGET_BALANCE_INR:
            if position:
                realized += unrealized
            print(f"TARGET HIT: ₹{START_BALANCE_INR + realized:.2f}")
            break
        if equity <= 0:
            print("ACCOUNT RUIN")
            break

        if position:
            held = now - position["time"]
            reverse = (
                position["side"] == "BUY" and m5 <= -MIN_5S_MOMENTUM_USD
            ) or (
                position["side"] == "SELL" and m5 >= MIN_5S_MOMENTUM_USD
            )
            stop = unrealized <= -MAX_LOSS_PER_TRADE_INR
            if reverse or stop or held >= MAX_HOLD_SECONDS:
                reason = "HARD_STOP" if stop else "MAX_HOLD" if held >= MAX_HOLD_SECONDS else "MOMENTUM_REVERSED"
                realized += unrealized
                print(f"EXIT {position['side']} | ₹{unrealized:.2f} | {reason} | Balance ₹{START_BALANCE_INR + realized:.2f}")
                log_row("EXIT", position["side"], bid, ask, spread, position["ounces"], START_BALANCE_INR + realized, unrealized, m5, reason)
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
            ounces = ounces_for(balance, entry)
            position = {"side": side, "entry": entry, "time": now, "ounces": ounces}
            trade_no += 1
            cost = pnl_inr(position, bid, ask)
            print(
                f"PAPER {side} #{trade_no} | entry {entry:.2f} | "
                f"{ounces:.4f} oz | lot {ounces / CONTRACT_SIZE:.6f} | "
                f"spread cost ₹{cost:.2f}"
            )
            log_row("ENTRY", side, bid, ask, spread, ounces, balance + cost, cost, m5, "breakout")

        time.sleep(SAMPLE_INTERVAL)

except KeyboardInterrupt:
    print(f"Stopped. Final paper balance ₹{START_BALANCE_INR + realized:.2f}")
finally:
    mt5.shutdown()
