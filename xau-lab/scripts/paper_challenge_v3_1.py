import MetaTrader5 as mt5
import time
import csv

from collections import deque
from datetime import datetime
from pathlib import Path


# ============================================================
# XAUUSD LIVE PAPER CHALLENGE V3.1
#
# ₹500 -> ₹550
#
# LIVE MT5 PRICES
# SYNTHETIC FRACTIONAL GOLD EXPOSURE
# NO REAL ORDERS
#
# V3.1:
# - 5s + 15s momentum agreement
# - breakout confirmation
# - armed signals survive temporary spread widening
# - armed signals expire after 6s
# - fixed breakout level while armed
# - confirmed reversal exit
# - hard stop
# - profit trailing lock
# ============================================================


# ============================================================
# BASIC SETTINGS
# ============================================================

SYMBOL = "XAUUSD"

START_BALANCE_INR = 500.00
TARGET_BALANCE_INR = 550.00

INR_PER_USD = 95.7021

LEVERAGE = 100.0

CONTRACT_SIZE = 100.0

# 1.0 = full synthetic 100x exposure
EXPOSURE_FRACTION = 1.0


# ============================================================
# TIMING
# ============================================================

SAMPLE_INTERVAL = 0.50

WARMUP_SECONDS = 45

COOLDOWN_SECONDS = 20

MAX_HOLD_SECONDS = 180


# ============================================================
# ENTRY FILTERS
# ============================================================

MAX_SPREAD_USD = 0.35

MIN_5S_MOMENTUM_USD = 0.30

MIN_15S_MOMENTUM_USD = 0.50

MOMENTUM_SPREAD_MULTIPLE = 2.0

BREAKOUT_BUFFER_USD = 0.05


# ============================================================
# ARMED SIGNAL SETTINGS
# ============================================================

BREAKOUT_CONFIRM_SECONDS = 2.0

ARM_MAX_SECONDS = 6.0

# While armed, tolerate a little temporary opposite movement.
ARM_REVERSAL_TOLERANCE_USD = 0.10

# Price may briefly fall back inside the breakout zone.
ARM_BREAKOUT_TOLERANCE_USD = 0.15


# ============================================================
# EXIT / RISK SETTINGS
# ============================================================

MAX_LOSS_PER_TRADE_INR = 25.00


# Once trade reaches this profit,
# trailing protection activates.
PROFIT_LOCK_TRIGGER_INR = 8.00

# Minimum protected profit after lock activates.
PROFIT_LOCK_MIN_INR = 2.00

# Keep at least 50% of peak profit.
PROFIT_LOCK_KEEP_FRACTION = 0.50


# Reversal must persist for several samples.
REVERSAL_CONFIRM_COUNT = 3

REVERSAL_MOMENTUM_USD = 0.30


# ============================================================
# LOGGING
# ============================================================

LOG_FILE = Path("paper_trades_v3_1.csv")


# ============================================================
# HELPERS
# ============================================================


def money(value):
    return f"₹{value:.2f}"


def calculate_ounces(balance_inr, price):

    if balance_inr <= 0:
        return 0.0

    if price <= 0:
        return 0.0

    capital_usd = (
        balance_inr / INR_PER_USD
    )

    notional_usd = (
        capital_usd
        * LEVERAGE
        * EXPOSURE_FRACTION
    )

    ounces = (
        notional_usd / price
    )

    return ounces


def calculate_lots(ounces):

    return (
        ounces / CONTRACT_SIZE
    )


def get_trade_pnl(
    position,
    bid,
    ask
):

    if position is None:
        return 0.0

    ounces = position["ounces"]

    if position["side"] == "BUY":

        # BUY opens at ASK
        # BUY closes at BID

        move_usd = (
            bid - position["entry"]
        )

    else:

        # SELL opens at BID
        # SELL closes at ASK

        move_usd = (
            position["entry"] - ask
        )

    pnl_usd = (
        move_usd * ounces
    )

    pnl_inr = (
        pnl_usd * INR_PER_USD
    )

    return pnl_inr


def quote_at_or_before(
    history,
    target_time
):

    for q in reversed(history):

        if q["time"] <= target_time:

            return q

    return None


def write_log(
    event,
    side="",
    bid=0.0,
    ask=0.0,
    spread=0.0,
    ounces=0.0,
    lots=0.0,
    equity=0.0,
    realized=0.0,
    pnl=0.0,
    momentum_5s=0.0,
    momentum_15s=0.0,
    reason=""
):

    exists = LOG_FILE.exists()

    with LOG_FILE.open(
        "a",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        if not exists:

            writer.writerow([
                "timestamp",
                "event",
                "side",
                "bid",
                "ask",
                "spread_usd",
                "ounces",
                "synthetic_lots",
                "equity_inr",
                "realized_inr",
                "trade_pnl_inr",
                "momentum_5s",
                "momentum_15s",
                "reason"
            ])

        writer.writerow([
            datetime.now().isoformat(
                timespec="seconds"
            ),
            event,
            side,
            round(bid, 4),
            round(ask, 4),
            round(spread, 4),
            round(ounces, 6),
            round(lots, 8),
            round(equity, 2),
            round(realized, 2),
            round(pnl, 2),
            round(momentum_5s, 4),
            round(momentum_15s, 4),
            reason
        ])


# ============================================================
# CONNECT TO MT5
# ============================================================


print()

print(
    "================================================"
)

print(
    "      XAUUSD LIVE PAPER CHALLENGE V3.1"
)

print(
    "================================================"
)

print()

print(
    "             ₹500 -> ₹550"
)

print()

print(
    " LIVE PRICE DATA"
)

print(
    " SYNTHETIC FRACTIONAL EXPOSURE"
)

print(
    " NO REAL ORDERS"
)

print()


if not mt5.initialize(
    timeout=10000
):

    raise RuntimeError(
        f"MT5 initialization failed: "
        f"{mt5.last_error()}"
    )


if not mt5.symbol_select(
    SYMBOL,
    True
):

    mt5.shutdown()

    raise RuntimeError(
        f"Could not select {SYMBOL}"
    )


info = mt5.symbol_info(
    SYMBOL
)


if info is None:

    mt5.shutdown()

    raise RuntimeError(
        "Could not read symbol information."
    )


print(
    "Waiting for live XAUUSD tick..."
)


tick = None


for _ in range(20):

    tick = mt5.symbol_info_tick(
        SYMBOL
    )

    if (
        tick is not None
        and tick.bid > 0
        and tick.ask > 0
    ):

        break

    time.sleep(0.5)


if (
    tick is None
    or tick.bid <= 0
    or tick.ask <= 0
):

    mt5.shutdown()

    raise RuntimeError(
        "No usable XAUUSD tick."
    )


initial_price = (
    tick.bid + tick.ask
) / 2


initial_ounces = calculate_ounces(
    START_BALANCE_INR,
    initial_price
)


print()

print(
    "=== V3.1 SETTINGS ==="
)

print()


print(
    f"Starting balance:        "
    f"{money(START_BALANCE_INR)}"
)

print(
    f"Target balance:          "
    f"{money(TARGET_BALANCE_INR)}"
)

print(
    f"Synthetic leverage:      "
    f"{LEVERAGE:.0f}x"
)

print(
    f"Initial exposure:        "
    f"{initial_ounces:.5f} oz"
)

print(
    f"Synthetic lots:          "
    f"{calculate_lots(initial_ounces):.6f}"
)

print(
    f"Broker minimum lot:      "
    f"{info.volume_min}"
)

print(
    f"Maximum spread:          "
    f"${MAX_SPREAD_USD:.2f}"
)

print(
    f"5s momentum minimum:     "
    f"${MIN_5S_MOMENTUM_USD:.2f}"
)

print(
    f"15s momentum minimum:    "
    f"${MIN_15S_MOMENTUM_USD:.2f}"
)

print(
    f"Momentum/spread ratio:   "
    f"{MOMENTUM_SPREAD_MULTIPLE:.1f}x"
)

print(
    f"Breakout confirmation:   "
    f"{BREAKOUT_CONFIRM_SECONDS:.1f}s"
)

print(
    f"Max armed duration:      "
    f"{ARM_MAX_SECONDS:.1f}s"
)

print(
    f"Max loss / trade:        "
    f"{money(MAX_LOSS_PER_TRADE_INR)}"
)

print(
    f"Profit lock trigger:     "
    f"{money(PROFIT_LOCK_TRIGGER_INR)}"
)

print(
    f"Cooldown:                "
    f"{COOLDOWN_SECONDS}s"
)

print()

print(
    f"Warming up for "
    f"{WARMUP_SECONDS}s..."
)

print()


# ============================================================
# STATE
# ============================================================


history = deque(
    maxlen=500
)


realized_inr = 0.0

position = None

armed_signal = None

start_time = time.time()

last_status = 0.0

last_exit_time = 0.0

trade_number = 0


write_log(
    event="START",
    equity=START_BALANCE_INR,
    realized=0.0,
    reason="challenge_started"
)


# ============================================================
# POSITION CLOSE FUNCTION
# ============================================================


def close_position(
    reason,
    position,
    bid,
    ask,
    spread,
    realized_inr,
    pnl,
    momentum_5s,
    momentum_15s
):

    new_realized = (
        realized_inr + pnl
    )


    final_balance = (
        START_BALANCE_INR
        + new_realized
    )


    print()

    print(
        f"EXIT {position['side']}"
    )

    print(
        f"P&L:       "
        f"{money(pnl)}"
    )

    print(
        f"Reason:    "
        f"{reason}"
    )

    print(
        f"Peak P&L:  "
        f"{money(position['peak_pnl'])}"
    )

    print(
        f"Balance:   "
        f"{money(final_balance)}"
    )

    print()


    write_log(
        event="EXIT",
        side=position["side"],
        bid=bid,
        ask=ask,
        spread=spread,
        ounces=position["ounces"],
        lots=calculate_lots(
            position["ounces"]
        ),
        equity=final_balance,
        realized=new_realized,
        pnl=pnl,
        momentum_5s=momentum_5s,
        momentum_15s=momentum_15s,
        reason=reason
    )


    return new_realized


# ============================================================
# MAIN LOOP
# ============================================================


try:

    while True:

        tick = mt5.symbol_info_tick(
            SYMBOL
        )


        if (
            tick is None
            or tick.bid <= 0
            or tick.ask <= 0
        ):

            time.sleep(
                SAMPLE_INTERVAL
            )

            continue


        now = time.time()


        bid = float(
            tick.bid
        )

        ask = float(
            tick.ask
        )


        mid = (
            bid + ask
        ) / 2


        spread = (
            ask - bid
        )


        history.append({
            "time": now,
            "bid": bid,
            "ask": ask,
            "mid": mid
        })


        # ====================================================
        # MOMENTUM
        # ====================================================


        quote_5s = quote_at_or_before(
            history,
            now - 5
        )


        quote_15s = quote_at_or_before(
            history,
            now - 15
        )


        momentum_5s = 0.0

        momentum_15s = 0.0


        if quote_5s:

            momentum_5s = (
                mid
                - quote_5s["mid"]
            )


        if quote_15s:

            momentum_15s = (
                mid
                - quote_15s["mid"]
            )


        # ====================================================
        # ACCOUNT
        # ====================================================


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


        # ====================================================
        # STATUS
        # ====================================================


        if (
            now - last_status
            >= 2
        ):

            if position:

                state = (
                    f"{position['side']} "
                    f"{position['ounces']:.4f}oz"
                )


            elif armed_signal:

                state = (
                    f"ARMED-"
                    f"{armed_signal['side']}"
                )


            else:

                state = "NONE"


            print(
                f"{datetime.now().strftime('%H:%M:%S')} | "
                f"B {bid:.2f} | "
                f"A {ask:.2f} | "
                f"S {spread:.2f} | "
                f"M5 {momentum_5s:+.2f} | "
                f"M15 {momentum_15s:+.2f} | "
                f"{state:15} | "
                f"Eq {money(equity)}"
            )


            last_status = now


        # ====================================================
        # TARGET HIT
        # ====================================================


        if (
            equity
            >= TARGET_BALANCE_INR
        ):

            if position:

                realized_inr = close_position(
                    "TARGET_REACHED",
                    position,
                    bid,
                    ask,
                    spread,
                    realized_inr,
                    unrealized,
                    momentum_5s,
                    momentum_15s
                )


                position = None


            print()

            print(
                "🔥🔥🔥 TARGET HIT 🔥🔥🔥"
            )

            print()

            print(
                f"Final balance: "
                f"{money(
                    START_BALANCE_INR
                    + realized_inr
                )}"
            )

            print(
                f"Trades taken: "
                f"{trade_number}"
            )

            print()

            break


        # ====================================================
        # ACCOUNT RUIN
        # ====================================================


        if equity <= 0:

            print()

            print(
                "💀 ACCOUNT SENT TO "
                "THE SHADOW REALM"
            )

            print()

            break


        # ====================================================
        # MANAGE OPEN POSITION
        # ====================================================


        if position:


            held_for = (
                now
                - position["time"]
            )


            # ------------------------------------------------
            # TRACK PEAK PROFIT
            # ------------------------------------------------


            if (
                unrealized
                > position["peak_pnl"]
            ):

                position["peak_pnl"] = (
                    unrealized
                )


            # ------------------------------------------------
            # HARD STOP LOSS
            # ------------------------------------------------


            if (
                unrealized
                <= -MAX_LOSS_PER_TRADE_INR
            ):

                realized_inr = close_position(
                    "HARD_STOP",
                    position,
                    bid,
                    ask,
                    spread,
                    realized_inr,
                    unrealized,
                    momentum_5s,
                    momentum_15s
                )


                position = None

                last_exit_time = now


                time.sleep(
                    SAMPLE_INTERVAL
                )

                continue


            # ------------------------------------------------
            # PROFIT LOCK
            # ------------------------------------------------


            if (
                position["peak_pnl"]
                >= PROFIT_LOCK_TRIGGER_INR
            ):


                trailing_floor = max(
                    PROFIT_LOCK_MIN_INR,

                    position["peak_pnl"]
                    * PROFIT_LOCK_KEEP_FRACTION
                )


                if (
                    unrealized
                    <= trailing_floor
                ):

                    realized_inr = close_position(
                        "PROFIT_LOCK",
                        position,
                        bid,
                        ask,
                        spread,
                        realized_inr,
                        unrealized,
                        momentum_5s,
                        momentum_15s
                    )


                    position = None

                    last_exit_time = now


                    time.sleep(
                        SAMPLE_INTERVAL
                    )

                    continue


            # ------------------------------------------------
            # CONFIRMED REVERSAL
            # ------------------------------------------------


            reversal_now = False


            if (
                position["side"] == "BUY"
                and
                momentum_5s
                <= -REVERSAL_MOMENTUM_USD
            ):

                reversal_now = True


            elif (
                position["side"] == "SELL"
                and
                momentum_5s
                >= REVERSAL_MOMENTUM_USD
            ):

                reversal_now = True


            if reversal_now:

                position["reverse_count"] += 1


            else:

                position["reverse_count"] = 0

