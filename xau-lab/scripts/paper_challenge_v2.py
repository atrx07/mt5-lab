import MetaTrader5 as mt5
import time
import csv

from collections import deque
from datetime import datetime
from pathlib import Path


# ============================================================
# XAUUSD LIVE PAPER CHALLENGE V2
#
# ₹500 -> ₹550
#
# LIVE MT5 PRICES
# SYNTHETIC FRACTIONAL GOLD EXPOSURE
# NO REAL ORDERS
# ============================================================


# ------------------------------------------------------------
# BASIC SETTINGS
# ------------------------------------------------------------

SYMBOL = "XAUUSD"

START_BALANCE_INR = 500.00
TARGET_BALANCE_INR = 550.00

# Approx conversion for our experiment.
INR_PER_USD = 95.7021

# Synthetic leverage.
# This does NOT change the MT5 demo account leverage.
# We are simulating fractional exposure ourselves.
LEVERAGE = 100.0

# Gold contract reference:
# 1 standard XAUUSD lot = 100 oz
CONTRACT_SIZE = 100.0

# 1.0 = use full synthetic 100x exposure
EXPOSURE_FRACTION = 1.0


# ------------------------------------------------------------
# STRATEGY SETTINGS
# ------------------------------------------------------------

SAMPLE_INTERVAL = 0.50

WARMUP_SECONDS = 30

# Ignore entries when spread gets ugly.
MAX_SPREAD_USD = 0.35

# Need at least this much movement over roughly 5 sec.
MIN_5S_MOMENTUM_USD = 0.30

# Need to break recent range by this much.
BREAKOUT_BUFFER_USD = 0.05

# Don't instantly reopen after closing.
COOLDOWN_SECONDS = 15

# Don't let one trade sit forever.
MAX_HOLD_SECONDS = 120

# Max synthetic INR loss for one trade.
MAX_LOSS_PER_TRADE_INR = 50.00


# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------

LOG_FILE = Path("paper_trades_v2.csv")


# ============================================================
# HELPERS
# ============================================================


def money(value):
    return f"₹{value:.2f}"


def calculate_ounces(balance_inr, price):
    """
    Calculate synthetic fractional XAU exposure.

    Example:
    ₹500 ~= $5.22
    100x leverage ~= $522 notional
    Gold ~= $4315
    Exposure ~= 0.121 oz

    This fractional position is NOT actually executable
    on our MT5 broker because its minimum is 0.01 lot = 1 oz.
    """

    if balance_inr <= 0 or price <= 0:
        return 0.0

    capital_usd = balance_inr / INR_PER_USD

    notional_usd = (
        capital_usd
        * LEVERAGE
        * EXPOSURE_FRACTION
    )

    ounces = notional_usd / price

    return ounces


def calculate_lots(ounces):
    return ounces / CONTRACT_SIZE


def get_trade_pnl(position, bid, ask):
    """
    BUY:
        enter at ASK
        exit at BID

    SELL:
        enter at BID
        exit at ASK

    Therefore spread is naturally included.
    """

    if position is None:
        return 0.0

    ounces = position["ounces"]

    if position["side"] == "BUY":

        move_usd = bid - position["entry"]

    else:

        move_usd = position["entry"] - ask

    pnl_usd = move_usd * ounces

    pnl_inr = pnl_usd * INR_PER_USD

    return pnl_inr


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
            reason
        ])


# ============================================================
# MT5 CONNECTION
# ============================================================


print()
print("================================================")
print("      XAUUSD LIVE PAPER CHALLENGE V2")
print("================================================")
print()
print("        ₹500 -> ₹550")
print()
print(" LIVE PRICE DATA")
print(" SYNTHETIC FRACTIONAL EXPOSURE")
print(" NO REAL ORDERS")
print()


if not mt5.initialize(timeout=10000):

    raise RuntimeError(
        f"MT5 initialization failed: "
        f"{mt5.last_error()}"
    )


if not mt5.symbol_select(SYMBOL, True):

    mt5.shutdown()

    raise RuntimeError(
        f"Could not select {SYMBOL}"
    )


info = mt5.symbol_info(SYMBOL)

if info is None:

    mt5.shutdown()

    raise RuntimeError(
        "Could not read symbol info."
    )


# Wait until a proper live tick exists.

print("Waiting for live XAUUSD tick...")

tick = None

for _ in range(20):

    tick = mt5.symbol_info_tick(SYMBOL)

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
        "No usable live XAUUSD tick."
    )


initial_price = (
    tick.bid + tick.ask
) / 2


initial_ounces = calculate_ounces(
    START_BALANCE_INR,
    initial_price
)

initial_lots = calculate_lots(
    initial_ounces
)


print()
print("=== EXPERIMENT SETTINGS ===")
print()
print(
    f"Starting balance:       "
    f"{money(START_BALANCE_INR)}"
)
print(
    f"Target balance:         "
    f"{money(TARGET_BALANCE_INR)}"
)
print(
    f"Synthetic leverage:     "
    f"{LEVERAGE:.0f}x"
)
print(
    f"Exposure fraction:      "
    f"{EXPOSURE_FRACTION:.2f}"
)
print(
    f"Initial XAU exposure:   "
    f"{initial_ounces:.5f} oz"
)
print(
    f"Synthetic lot size:     "
    f"{initial_lots:.6f}"
)
print(
    f"Broker minimum lot:     "
    f"{info.volume_min}"
)
print(
    f"Max loss / trade:       "
    f"{money(MAX_LOSS_PER_TRADE_INR)}"
)
print(
    f"Max allowed spread:     "
    f"${MAX_SPREAD_USD:.2f}"
)
print(
    f"USD/INR:                "
    f"{INR_PER_USD:.4f}"
)
print()
print(
    f"Warming up for "
    f"{WARMUP_SECONDS} seconds..."
)
print()


# ============================================================
# RUNTIME STATE
# ============================================================


history = deque(maxlen=300)

realized_inr = 0.0

position = None

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
# MAIN LOOP
# ============================================================


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

        bid = float(tick.bid)
        ask = float(tick.ask)

        mid = (bid + ask) / 2

        spread = ask - bid


        history.append({
            "time": now,
            "bid": bid,
            "ask": ask,
            "mid": mid
        })


        # ----------------------------------------------------
        # ACCOUNT EQUITY
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
        # STATUS
        # ----------------------------------------------------

        if now - last_status >= 2:

            if position:

                position_text = (
                    f"{position['side']} "
                    f"{position['ounces']:.4f}oz"
                )

            else:

                position_text = "NONE"


            print(
                f"{datetime.now().strftime('%H:%M:%S')} | "
                f"Bid {bid:.2f} | "
                f"Ask {ask:.2f} | "
                f"Spr {spread:.2f} | "
                f"{position_text:14} | "
                f"Eq {money(equity)}"
            )


            last_status = now


        # ====================================================
        # TARGET HIT
        # ====================================================

        if equity >= TARGET_BALANCE_INR:

            if position:

                realized_inr += unrealized

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
                    equity=equity,
                    realized=realized_inr,
                    pnl=unrealized,
                    reason="TARGET_REACHED"
                )

                position = None


            print()
            print("🔥🔥🔥 TARGET HIT 🔥🔥🔥")
            print()
            print(
                f"Final balance: "
                f"{money(equity)}"
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

            if position:

                realized_inr += unrealized

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
                    equity=equity,
                    realized=realized_inr,
                    pnl=unrealized,
                    reason="ACCOUNT_RUIN"
                )

                position = None


            print()
            print(
                "💀 ACCOUNT GOT SENT "
                "TO THE SHADOW REALM"
            )
            print()
            print(
                f"Final balance: "
                f"{money(equity)}"
            )
            print()

            break


        # ====================================================
        # MANAGE OPEN POSITION
        # ====================================================

        if position:

            held_for = (
                now - position["time"]
            )


            # ------------------------------------------------
            # HARD STOP LOSS
            # ------------------------------------------------

            if (
                unrealized
                <= -MAX_LOSS_PER_TRADE_INR
            ):

                realized_inr += unrealized

                print()
                print(
                    f"🛑 STOP LOSS "
                    f"{position['side']}"
                )
                print(
                    f"Trade P&L: "
                    f"{money(unrealized)}"
                )
                print(
                    f"Balance: "
                    f"{money(
                        START_BALANCE_INR
                        + realized_inr
                    )}"
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
                    equity=(
                        START_BALANCE_INR
                        + realized_inr
                    ),
                    realized=realized_inr,
                    pnl=unrealized,
                    reason="hard_stop_loss"
                )


                position = None

                last_exit_time = now

                time.sleep(
                    SAMPLE_INTERVAL
                )

                continue


            # ------------------------------------------------
            # MOMENTUM REVERSAL
            # ------------------------------------------------

            five_sec_quotes = [
                q
                for q in history
                if q["time"] <= now - 5
            ]


            if five_sec_quotes:

                five_sec_mid = (
                    five_sec_quotes[-1]["mid"]
                )

                momentum = (
                    mid - five_sec_mid
                )

                reverse_signal = False


                if (
                    position["side"] == "BUY"
                    and
                    momentum
                    < -MIN_5S_MOMENTUM_USD
                ):

                    reverse_signal = True


                elif (
                    position["side"] == "SELL"
                    and
                    momentum
                    > MIN_5S_MOMENTUM_USD
                ):

                    reverse_signal = True


                if reverse_signal:

                    realized_inr += unrealized

                    print()
                    print(
                        f"↩ EXIT "
                        f"{position['side']}"
                    )
                    print(
                        f"P&L: "
                        f"{money(unrealized)}"
                    )
                    print(
                        "Reason: momentum reversed"
                    )
                    print(
                        f"Balance: "
                        f"{money(
                            START_BALANCE_INR
                            + realized_inr
                        )}"
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
                        equity=(
                            START_BALANCE_INR
                            + realized_inr
                        ),
                        realized=realized_inr,
                        pnl=unrealized,
                        reason="momentum_reversal"
                    )


                    position = None

                    last_exit_time = now

                    time.sleep(
                        SAMPLE_INTERVAL
                    )

                    continue


            # ------------------------------------------------
            # MAX HOLD
            # ------------------------------------------------

            if held_for >= MAX_HOLD_SECONDS:

                realized_inr += unrealized

                print()
                print(
                    f"⌛ EXIT "
                    f"{position['side']}"
                )
                print(
                    f"P&L: "
                    f"{money(unrealized)}"
                )
                print(
                    "Reason: max hold time"
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
                    equity=(
                        START_BALANCE_INR
                        + realized_inr
                    ),
                    realized=realized_inr,
                    pnl=unrealized,
                    reason="max_hold"
                )


                position = None

                last_exit_time = now


            time.sleep(
                SAMPLE_INTERVAL
            )

            continue


        # ====================================================
        # NO POSITION: LOOK FOR ENTRY
        # ====================================================


        # ----------------------------------------------------
        # Warmup
        # ----------------------------------------------------

        if (
            now - start_time
            < WARMUP_SECONDS
        ):

            time.sleep(
                SAMPLE_INTERVAL
            )

            continue


        # ----------------------------------------------------
        # Cooldown
        # ----------------------------------------------------

        if (
            now - last_exit_time
            < COOLDOWN_SECONDS
        ):

            time.sleep(
                SAMPLE_INTERVAL
            )

            continue


        # ----------------------------------------------------
        # Spread filter
        # ----------------------------------------------------

        if spread > MAX_SPREAD_USD:

            time.sleep(
                SAMPLE_INTERVAL
            )

            continue


        # ----------------------------------------------------
        # Recent history
        # ----------------------------------------------------

        previous_quotes = [
            q
            for q in history
            if (
                now - 30
                <= q["time"]
                <= now - 5
            )
        ]


        five_sec_quotes = [
            q
            for q in history
            if q["time"] <= now - 5
        ]


        if (
            len(previous_quotes) < 20
            or
            not five_sec_quotes
        ):

            time.sleep(
                SAMPLE_INTERVAL
            )

            continue


        recent_high = max(
            q["mid"]
            for q in previous_quotes
        )

        recent_low = min(
            q["mid"]
            for q in previous_quotes
        )


        five_sec_mid = (
            five_sec_quotes[-1]["mid"]
        )


        momentum = (
            mid - five_sec_mid
        )


        # Current balance available
        # before opening another trade.

        current_balance = (
            START_BALANCE_INR
            + realized_inr
        )


        # ====================================================
        # BUY BREAKOUT
        # ====================================================

        if (
            mid
            > recent_high
            + BREAKOUT_BUFFER_USD

            and

            momentum
            >= MIN_5S_MOMENTUM_USD
        ):

            ounces = calculate_ounces(
                current_balance,
                ask
            )

            lots = calculate_lots(
                ounces
            )


            position = {
                "side": "BUY",
                "entry": ask,
                "time": now,
                "ounces": ounces
            }


            trade_number += 1


            initial_pnl = get_trade_pnl(
                position,
                bid,
                ask
            )


            print()
            print(
                f"🟢 PAPER BUY #{trade_number}"
            )
            print(
                f"Entry ask:    "
                f"${ask:.2f}"
            )
            print(
                f"Exposure:     "
                f"{ounces:.5f} oz"
            )
            print(
                f"Synthetic lot:"
                f" {lots:.6f}"
            )
            print(
                f"Spread:       "
                f"${spread:.2f}"
            )
            print(
                f"Momentum:     "
                f"+${momentum:.2f}/5s"
            )
            print(
                f"Spread cost:  "
                f"{money(initial_pnl)}"
            )
            print()


            write_log(
                event="ENTRY",
                side="BUY",
                bid=bid,
                ask=ask,
                spread=spread,
                ounces=ounces,
                lots=lots,
                equity=(
                    current_balance
                    + initial_pnl
                ),
                realized=realized_inr,
                pnl=initial_pnl,
                reason="upside_breakout"
            )


        # ====================================================
        # SELL BREAKOUT