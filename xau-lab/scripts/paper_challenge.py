import MetaTrader5 as mt5
import time
import csv
from collections import deque
from datetime import datetime
from pathlib import Path

# ============================================================
# XAUUSD ₹100 -> ₹150 PAPER CHALLENGE
# ABSOLUTELY NO REAL ORDERS ARE SENT
# ============================================================

SYMBOL = "XAUUSD"

START_BALANCE_INR = 100.00
TARGET_BALANCE_INR = 150.00

# Current USD/INR approximation for this experiment
INR_PER_USD = 95.7021

# Your MT5 contract:
# 1 lot = 100 oz
# 0.01 lot = 1 oz
VOLUME_LOTS = 0.01
CONTRACT_SIZE = 100.0
OUNCES = VOLUME_LOTS * CONTRACT_SIZE

# Strategy settings
SAMPLE_INTERVAL = 0.50
WARMUP_SECONDS = 30

# Do not enter during ugly spread widening
MAX_SPREAD_USD = 0.35

# Require a meaningful short-term push
MIN_5S_MOMENTUM_USD = 0.30

# Must break recent range by at least this much
BREAKOUT_BUFFER_USD = 0.05

# Avoid machine-gunning entries
COOLDOWN_SECONDS = 15

# Exit stale trades rather than sit forever
MAX_HOLD_SECONDS = 120

LOG_FILE = Path("paper_trades.csv")


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def inr(value):
    return f"₹{value:.2f}"


def write_log(
    event,
    side="",
    bid=0.0,
    ask=0.0,
    spread=0.0,
    equity=0.0,
    realized=0.0,
    pnl=0.0,
    reason=""
):
    exists = LOG_FILE.exists()

    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not exists:
            writer.writerow([
                "timestamp",
                "event",
                "side",
                "bid",
                "ask",
                "spread_usd",
                "equity_inr",
                "realized_inr",
                "trade_pnl_inr",
                "reason",
            ])

        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            event,
            side,
            round(bid, 3),
            round(ask, 3),
            round(spread, 3),
            round(equity, 2),
            round(realized, 2),
            round(pnl, 2),
            reason,
        ])


def get_trade_pnl(position, bid, ask):
    """
    BUY enters at ASK and exits at BID.
    SELL enters at BID and exits at ASK.

    This automatically includes the spread.
    """

    if position is None:
        return 0.0

    if position["side"] == "BUY":
        pnl_usd = (bid - position["entry"]) * OUNCES

    else:
        pnl_usd = (position["entry"] - ask) * OUNCES

    return pnl_usd * INR_PER_USD


# ------------------------------------------------------------
# Connect
# ------------------------------------------------------------

print()
print("============================================")
print(" XAUUSD ₹100 -> ₹150 PAPER CHALLENGE")
print("============================================")
print()
print("NO REAL ORDERS WILL BE SENT.")
print()

if not mt5.initialize(timeout=10000):
    raise RuntimeError(
        f"MT5 initialization failed: {mt5.last_error()}"
    )

if not mt5.symbol_select(SYMBOL, True):
    mt5.shutdown()
    raise RuntimeError(f"Could not select {SYMBOL}")

info = mt5.symbol_info(SYMBOL)

if info is None:
    mt5.shutdown()
    raise RuntimeError("Could not read symbol information.")

print(f"Symbol:             {SYMBOL}")
print(f"Contract exposure:  {OUNCES:.2f} oz")
print(f"Starting balance:   {inr(START_BALANCE_INR)}")
print(f"Target balance:     {inr(TARGET_BALANCE_INR)}")
print(f"USD/INR used:       {INR_PER_USD:.4f}")
print(f"Max spread:         ${MAX_SPREAD_USD:.2f}")
print()
print(f"Warming up for {WARMUP_SECONDS}s...")
print()


# ------------------------------------------------------------
# Runtime state
# ------------------------------------------------------------

history = deque(maxlen=240)

realized_inr = 0.0
position = None

start_time = time.time()
last_status = 0
last_exit_time = 0

write_log(
    event="START",
    equity=START_BALANCE_INR,
    realized=0.0,
    reason="challenge_started"
)


try:

    while True:

        tick = mt5.symbol_info_tick(SYMBOL)

        if (
            tick is None
            or tick.bid <= 0
            or tick.ask <= 0
        ):
            time.sleep(SAMPLE_INTERVAL)
            continue

        now = time.time()

        bid = tick.bid
        ask = tick.ask
        mid = (bid + ask) / 2
        spread = ask - bid

        history.append({
            "time": now,
            "bid": bid,
            "ask": ask,
            "mid": mid,
        })

        # ----------------------------------------------------
        # Current equity
        # ----------------------------------------------------

        unrealized = get_trade_pnl(
            position,
            bid,
            ask
        )

        equity = (
            START_BALANCE_INR
            + realized_inr
            + unrealized
        )

        # ----------------------------------------------------
        # Status display
        # ----------------------------------------------------

        if now - last_status >= 2:

            position_text = (
                position["side"]
                if position
                else "NONE"
            )

            print(
                f"{datetime.now().strftime('%H:%M:%S')} | "
                f"Bid {bid:.2f} | "
                f"Ask {ask:.2f} | "
                f"Spr {spread:.2f} | "
                f"{position_text:4} | "
                f"Equity {inr(equity)}"
            )

            last_status = now

        # ----------------------------------------------------
        # Challenge target
        # ----------------------------------------------------

        if equity >= TARGET_BALANCE_INR:

            if position:

                realized_inr += unrealized

                write_log(
                    event="EXIT",
                    side=position["side"],
                    bid=bid,
                    ask=ask,
                    spread=spread,
                    equity=equity,
                    realized=realized_inr,
                    pnl=unrealized,
                    reason="TARGET_REACHED"
                )

            print()
            print("🔥🔥🔥 TARGET HIT 🔥🔥🔥")
            print(f"Final balance: {inr(equity)}")
            print()

            break

        # ----------------------------------------------------
        # Ruin condition
        # ----------------------------------------------------

        if equity <= 0:

            if position:

                realized_inr += unrealized

                write_log(
                    event="EXIT",
                    side=position["side"],
                    bid=bid,
                    ask=ask,
                    spread=spread,
                    equity=equity,
                    realized=realized_inr,
                    pnl=unrealized,
                    reason="ACCOUNT_RUINED"
                )

            print()
            print("💀 ACCOUNT GOT SENT TO THE SHADOW REALM")
            print(f"Final balance: {inr(equity)}")
            print()

            break

        # ----------------------------------------------------
        # Manage existing position
        # ----------------------------------------------------

        if position:

            held_for = now - position["time"]

            # Find price roughly five seconds ago
            five_sec_quotes = [
                q for q in history
                if q["time"] <= now - 5
            ]

            if five_sec_quotes:

                five_sec_mid = five_sec_quotes[-1]["mid"]

                momentum = mid - five_sec_mid

                reverse_signal = False

                if (
                    position["side"] == "BUY"
                    and momentum < -MIN_5S_MOMENTUM_USD
                ):
                    reverse_signal = True

                if (
                    position["side"] == "SELL"
                    and momentum > MIN_5S_MOMENTUM_USD
                ):
                    reverse_signal = True

                if reverse_signal:

                    realized_inr += unrealized

                    print()
                    print(
                        f"EXIT {position['side']} | "
                        f"P&L {inr(unrealized)} | "
                        f"momentum reversed"
                    )
                    print()

                    write_log(
                        event="EXIT",
                        side=position["side"],
                        bid=bid,
                        ask=ask,
                        spread=spread,
                        equity=equity,
                        realized=realized_inr,
                        pnl=unrealized,
                        reason="momentum_reversal"
                    )

                    position = None
                    last_exit_time = now

                    time.sleep(SAMPLE_INTERVAL)
                    continue

            if held_for >= MAX_HOLD_SECONDS:

                realized_inr += unrealized

                print()
                print(
                    f"EXIT {position['side']} | "
                    f"P&L {inr(unrealized)} | "
                    f"max hold reached"
                )
                print()

                write_log(
                    event="EXIT",
                    side=position["side"],
                    bid=bid,
                    ask=ask,
                    spread=spread,
                    equity=equity,
                    realized=realized_inr,
                    pnl=unrealized,
                    reason="max_hold"
                )

                position = None
                last_exit_time = now

            time.sleep(SAMPLE_INTERVAL)
            continue

        # ----------------------------------------------------
        # Warm-up before strategy may enter
        # ----------------------------------------------------

        if now - start_time < WARMUP_SECONDS:
            time.sleep(SAMPLE_INTERVAL)
            continue

        if now - last_exit_time < COOLDOWN_SECONDS:
            time.sleep(SAMPLE_INTERVAL)
            continue

        # ----------------------------------------------------
        # Reject bad spread
        # ----------------------------------------------------

        if spread > MAX_SPREAD_USD:
            time.sleep(SAMPLE_INTERVAL)
            continue

        # ----------------------------------------------------
        # Build breakout signal
        # ----------------------------------------------------

        previous_quotes = [
            q for q in history
            if now - 30 <= q["time"] <= now - 5
        ]

        five_sec_quotes = [
            q for q in history
            if q["time"] <= now - 5
        ]

        if (
            len(previous_quotes) < 20
            or not five_sec_quotes
        ):
            time.sleep(SAMPLE_INTERVAL)
            continue

        recent_high = max(
            q["mid"] for q in previous_quotes
        )

        recent_low = min(
            q["mid"] for q in previous_quotes
        )

        five_sec_mid = five_sec_quotes[-1]["mid"]

        momentum = mid - five_sec_mid

        # ----------------------------------------------------
        # BUY breakout
        # ----------------------------------------------------

        if (
            mid > recent_high + BREAKOUT_BUFFER_USD
            and momentum >= MIN_5S_MOMENTUM_USD
        ):

            # A real BUY fills at ASK
            position = {
                "side": "BUY",
                "entry": ask,
                "time": now,
            }

            initial_pnl = get_trade_pnl(
                position,
                bid,
                ask
            )

            print()
            print("🟢 PAPER BUY")
            print(f"Entry ask: ${ask:.2f}")
            print(f"Spread:    ${spread:.2f}")
            print(f"Momentum:  +${momentum:.2f}/5s")
            print(
                f"Immediate spread cost: "
                f"{inr(initial_pnl)}"
            )
            print()

            write_log(
                event="ENTRY",
                side="BUY",
                bid=bid,
                ask=ask,
                spread=spread,
                equity=START_BALANCE_INR
                + realized_inr
                + initial_pnl,
                realized=realized_inr,
                pnl=initial_pnl,
                reason="upside_breakout"
            )

        # ----------------------------------------------------
        # SELL breakout
        # ----------------------------------------------------

        elif (
            mid < recent_low - BREAKOUT_BUFFER_USD
            and momentum <= -MIN_5S_MOMENTUM_USD
        ):

            # A real SELL fills at BID
            position = {
                "side": "SELL",
                "entry": bid,
                "time": now,
            }

            initial_pnl = get_trade_pnl(
                position,
                bid,
                ask
            )

            print()
            print("🔴 PAPER SELL")
            print(f"Entry bid: ${bid:.2f}")
            print(f"Spread:    ${spread:.2f}")
            print(f"Momentum:  ${momentum:.2f}/5s")
            print(
                f"Immediate spread cost: "
                f"{inr(initial_pnl)}"
            )
            print()

            write_log(
                event="ENTRY",
                side="SELL",
                bid=bid,
                ask=ask,
                spread=spread,
                equity=START_BALANCE_INR
                + realized_inr
                + initial_pnl,
                realized=realized_inr,
                pnl=initial_pnl,
                reason="downside_breakout"
            )

        time.sleep(SAMPLE_INTERVAL)


except KeyboardInterrupt:

    print()
    print("Stopped manually.")

    if position:

        tick = mt5.symbol_info_tick(SYMBOL)

        if tick:
            pnl = get_trade_pnl(
                position,
                tick.bid,
                tick.ask
            )

            realized_inr += pnl

            equity = (
                START_BALANCE_INR
                + realized_inr
            )

            print(
                f"Paper position closed at "
                f"{inr(pnl)} P&L"
            )

    print(
        f"Final paper balance: "
        f"{inr(START_BALANCE_INR + realized_inr)}"
    )


finally:
    mt5.shutdown()

print()
print(f"Log saved to: {LOG_FILE.resolve()}")