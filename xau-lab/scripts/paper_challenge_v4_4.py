"""V4.4 XAUUSD live-paper strategy. Research only; sends no real orders.

V4.4 keeps the parity-corrected V4.3 PRIMARY/SECONDARY architecture and adds a
MICRO structural pullback/resumption engine plus the locked Candidate K MICRO
management rules. The final 20% research holdout remained unopened at lock.
The ₹50/hour objective is diagnostic only and never forces a trade.
"""

import csv
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

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
PRIMARY_MAX_HOLD_SECONDS = 1800
PRIMARY_MIN_1800S_MOMENTUM_USD = 8.0
PRIMARY_MIN_300S_MOMENTUM_USD = 3.0
PRIMARY_PULLBACK_60S_MOMENTUM_USD = 0.80
PRIMARY_RESUME_60S_MOMENTUM_USD = 0.50
PRIMARY_PULLBACK_LOOKBACK_SECONDS = 300
PRIMARY_TAKE_PROFIT_DISTANCE_USD = 21.0

# V4.2 secondary breakout / normal-regime rules.
SECONDARY_LOOKBACK_SECONDS = 120
SECONDARY_BREAKOUT_BUFFER_USD = 0.50
SECONDARY_TREND_HORIZON_SECONDS = 30
SECONDARY_MIN_TREND_USD = 2.0
SECONDARY_MIN_RANGE_USD = 3.0
SECONDARY_COOLDOWN_SECONDS = 450
SECONDARY_TAKE_PROFIT_DISTANCE_USD = 12.0
SECONDARY_MAX_HOLD_SECONDS = 900

# V4.3 high-activity regime router.
HIGH_RANGE300_MIN_USD = 5.0
HIGH_ER60_MIN = 0.03
PRIMARY_COOLDOWN_HIGH_SECONDS = 450
SECONDARY_COOLDOWN_HIGH_SECONDS = 90
ALLOW_SECONDARY_INSIDE_SLOW_GATE_HIGH = True

SECONDARY_HIGH_LOOKBACK_SECONDS = 120
SECONDARY_HIGH_BUFFER_FLOOR_USD = 0.50
SECONDARY_HIGH_BUFFER_RANGE_FRACTION = 0.02
SECONDARY_HIGH_MIN_RANGE_USD = 4.0
SECONDARY_HIGH_MIN_TREND_USD = 1.5

# Locked high-activity position management.
PRIMARY_HIGH_TAKE_PROFIT_USD = 25.0
PRIMARY_HIGH_MAX_HOLD_SECONDS = 900
PRIMARY_HIGH_REVERSAL_EXIT = False

SECONDARY_HIGH_TRAIL_TRIGGER_USD = 12.0
SECONDARY_HIGH_TRAIL_GIVEBACK_USD = 3.0
SECONDARY_HIGH_TAKE_PROFIT_USD = 8.0
SECONDARY_HIGH_MAX_HOLD_SECONDS = 1200
SECONDARY_HIGH_REVERSAL_EXIT = False

# V4.4 MICRO engine: structural short-horizon pullback/resumption.
MICRO_COOLDOWN_SECONDS = 60
MICRO_MIN_120S_MOMENTUM_USD = 6.0
MICRO_MIN_60S_MOMENTUM_USD = 2.0
MICRO_PULLBACK_10S_USD = 0.50
MICRO_RESUME_10S_USD = 0.20
MICRO_PULLBACK_LOOKBACK_SECONDS = 30
MICRO_MIN_ER60 = 0.12
MICRO_MIN_RANGE60_USD = 2.0
MICRO_MAX_SPREAD_TO_RANGE60 = 0.25
MICRO_MIN_QUOTE_RATE_RATIO = 0.65
MICRO_MIN_TICK_IMBALANCE = 0.0

MICRO_TAKE_PROFIT_USD = 10.0
MICRO_MAX_HOLD_SECONDS = 900
MICRO_TRAIL_TRIGGER_USD = 4.0
MICRO_TRAIL_GIVEBACK_USD = 2.0
MICRO_STAGNATION_SECONDS = 45
MICRO_STAGNATION_PEAK_USD = 0.75
MICRO_PARTIAL_TRIGGER_USD = 5.50
MICRO_PARTIAL_FRACTION = 0.75

LOG_FILE = Path("paper_trades_v4_4.csv")
HOURLY_LOG_FILE = Path("paper_hourly_v4_4.csv")
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


def rolling_quotes(now, seconds):
    return [q for q in history if now - seconds <= q["time"] <= now]


def rolling_range(now, seconds):
    qs = rolling_quotes(now, seconds)
    if len(qs) < 2:
        return None
    mids = [q["mid"] for q in qs]
    return max(mids) - min(mids)


def efficiency_ratio(now, seconds, current_momentum):
    if current_momentum is None:
        return None
    qs = rolling_quotes(now, seconds)
    if len(qs) < 2:
        return None
    path = 0.0
    prev = qs[0]["mid"]
    for q in qs[1:]:
        path += abs(q["mid"] - prev)
        prev = q["mid"]
    if path <= 0:
        return None
    return abs(current_momentum) / path


def raw_flow_features():
    """Return 10 s tick imbalance and 10 s/30 s quote-rate ratio."""
    start = datetime.now(timezone.utc) - timedelta(seconds=35)
    ticks = mt5.copy_ticks_from(SYMBOL, start, 50000, mt5.COPY_TICKS_ALL)
    if ticks is None or len(ticks) < 2:
        return None, None

    bids = np.asarray(ticks["bid"], dtype=float)
    asks = np.asarray(ticks["ask"], dtype=float)
    times = np.asarray(ticks["time_msc"], dtype=float) / 1000.0
    valid = (bids > 0) & (asks > 0)
    if valid.sum() < 2:
        return None, None

    mids = (bids[valid] + asks[valid]) / 2.0
    times = times[valid]
    end = times[-1]

    count10 = int(np.sum(times >= end - 10.0))
    count30 = int(np.sum(times >= end - 30.0))
    if count30 <= 0:
        return None, None

    rate10 = count10 / 10.0
    rate30 = count30 / 30.0
    qacc = rate10 / rate30 if rate30 > 0 else None

    diff = np.diff(mids)
    diff_times = times[1:]
    mask10 = diff_times >= end - 10.0
    d10 = diff[mask10]
    up = int(np.sum(d10 > 0))
    down = int(np.sum(d10 < 0))
    denom = up + down
    imbalance = (up - down) / denom if denom > 0 else 0.0
    return imbalance, qacc


def micro_signal(now, spread, m10, m60, m120, er60, range60, imb10, qacc):
    if (
        m10 is None or m60 is None or m120 is None or er60 is None
        or range60 is None or imb10 is None or qacc is None
    ):
        return None

    if range60 < MICRO_MIN_RANGE60_USD:
        return None
    if er60 < MICRO_MIN_ER60:
        return None
    if qacc < MICRO_MIN_QUOTE_RATE_RATIO:
        return None
    if spread > MICRO_MAX_SPREAD_TO_RANGE60 * range60:
        return None

    recent_m10 = []
    for q in history:
        if q["time"] < now - MICRO_PULLBACK_LOOKBACK_SECONDS:
            continue
        q10 = quote_at_or_before(q["time"] - 10)
        if q10 is None:
            continue
        if q["time"] - q10["time"] > 10 + MAX_QUOTE_GAP_SECONDS:
            continue
        recent_m10.append(q["mid"] - q10["mid"])

    if not recent_m10:
        return None

    buy = (
        m120 >= MICRO_MIN_120S_MOMENTUM_USD
        and m60 >= MICRO_MIN_60S_MOMENTUM_USD
        and min(recent_m10) <= -MICRO_PULLBACK_10S_USD
        and m10 >= MICRO_RESUME_10S_USD
        and imb10 >= MICRO_MIN_TICK_IMBALANCE
    )
    sell = (
        m120 <= -MICRO_MIN_120S_MOMENTUM_USD
        and m60 <= -MICRO_MIN_60S_MOMENTUM_USD
        and max(recent_m10) >= MICRO_PULLBACK_10S_USD
        and m10 <= -MICRO_RESUME_10S_USD
        and imb10 <= -MICRO_MIN_TICK_IMBALANCE
    )
    return "BUY" if buy else "SELL" if sell else None


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


def secondary_signal(now, mid, m30, m300, m1800, high_activity):
    if m30 is None:
        return None, None, None

    buy_gate, sell_gate = primary_slow_gate(m300, m1800)
    if (buy_gate or sell_gate) and not (
        high_activity and ALLOW_SECONDARY_INSIDE_SLOW_GATE_HIGH
    ):
        return None, None, None

    lookback = (
        SECONDARY_HIGH_LOOKBACK_SECONDS
        if high_activity else SECONDARY_LOOKBACK_SECONDS
    )
    prior = [q for q in history if now - lookback <= q["time"] < now]
    if len(prior) < 2:
        return None, None, None

    prior_high = max(q["mid"] for q in prior)
    prior_low = min(q["mid"] for q in prior)
    prior_range = prior_high - prior_low

    # Parity correction: the locked research row applied the V4.3 breakout
    # thresholds globally, not only while the high-activity flag was true.
    min_range = SECONDARY_HIGH_MIN_RANGE_USD
    min_trend = SECONDARY_HIGH_MIN_TREND_USD
    buffer = max(
        SECONDARY_HIGH_BUFFER_FLOOR_USD,
        SECONDARY_HIGH_BUFFER_RANGE_FRACTION * prior_range,
    )

    if prior_range < min_range:
        return None, prior_high, prior_low

    buy = mid >= prior_high + buffer and m30 >= min_trend
    sell = mid <= prior_low - buffer and m30 <= -min_trend
    return ("BUY" if buy else "SELL" if sell else None), prior_high, prior_low


FIELDS = [
    "timestamp", "event", "engine", "side", "high_activity_entry",
    "bid", "ask", "spread_usd", "entry_price", "ounces", "synthetic_lots",
    "risk_budget_inr", "equity_inr", "realized_inr", "trade_pnl_inr",
    "m10", "m30", "m60", "m120", "m300", "m1800",
    "range60", "range300", "er60", "imb10", "quote_rate_ratio",
    "channel_high", "channel_low", "mfe_inr", "mae_inr",
    "peak_move_usd", "partial_realized_inr", "reason",
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
                   m30, m60, m300, m1800, range300, er60):
    realized += trade_pnl
    total_trade_pnl = trade_pnl + position.get("partial_realized_inr", 0.0)
    balance = START_BALANCE_INR + realized
    print()
    print("EXIT", position["engine"], position["side"], "|", reason)
    print("P&L:", money(total_trade_pnl), "| MFE:", money(position["mfe"]), "| MAE:", money(position["mae"]))
    print("Balance:", money(balance))
    print()

    write_log({
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": "EXIT",
        "engine": position["engine"],
        "side": position["side"],
        "high_activity_entry": position["high_activity_entry"],
        "bid": round(bid, 4),
        "ask": round(ask, 4),
        "spread_usd": round(spread, 4),
        "entry_price": round(position["entry"], 4),
        "ounces": round(position["ounces"], 6),
        "synthetic_lots": round(position["ounces"] / CONTRACT_SIZE, 8),
        "risk_budget_inr": round(position["risk_budget_inr"], 2),
        "equity_inr": round(balance, 2),
        "realized_inr": round(realized, 2),
        "trade_pnl_inr": round(total_trade_pnl, 2),
        "m10": position.get("last_m10", ""),
        "m30": "" if m30 is None else round(m30, 4),
        "m60": "" if m60 is None else round(m60, 4),
        "m120": position.get("last_m120", ""),
        "m300": "" if m300 is None else round(m300, 4),
        "m1800": "" if m1800 is None else round(m1800, 4),
        "range60": position.get("last_range60", ""),
        "range300": "" if range300 is None else round(range300, 4),
        "er60": "" if er60 is None else round(er60, 6),
        "imb10": position.get("last_imb10", ""),
        "quote_rate_ratio": position.get("last_qacc", ""),
        "channel_high": position.get("channel_high", ""),
        "channel_low": position.get("channel_low", ""),
        "mfe_inr": round(position["mfe"], 2),
        "mae_inr": round(position["mae"], 2),
        "peak_move_usd": round(position["peak_move_usd"], 4),
        "partial_realized_inr": round(position.get("partial_realized_inr", 0.0), 2),
        "reason": reason,
    })
    return realized


print("================================================")
print("      XAUUSD LIVE PAPER CHALLENGE V4.4")
print("================================================")
print("V4.3 + MICRO structural engine + Candidate K management")
print("₹50/hour is DIAGNOSTIC ONLY; it never forces a trade")
print("3% risk-sized synthetic exposure | NO REAL ORDERS")
print("Research lock: >10% capture at 1s robustness under canonical segment accounting")

if not mt5.initialize(timeout=10000):
    raise RuntimeError("MT5 initialization failed: %r" % (mt5.last_error(),))

if not mt5.symbol_select(SYMBOL, True):
    mt5.shutdown()
    raise RuntimeError("Could not select %s" % SYMBOL)

realized_inr = 0.0
position = None
last_primary_exit_time = -1e18
last_secondary_exit_time = -1e18
last_micro_exit_time = -1e18
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
    "engine": "V4.4",
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

        m10 = momentum(mid, now, 10)
        m30 = momentum(mid, now, SECONDARY_TREND_HORIZON_SECONDS)
        m60 = momentum(mid, now, 60)
        m120 = momentum(mid, now, 120)
        m300 = momentum(mid, now, 300)
        m1800 = momentum(mid, now, 1800)
        range60 = rolling_range(now, 60)
        range300 = rolling_range(now, 300)
        er60 = efficiency_ratio(now, 60, m60)
        imb10, qacc = raw_flow_features()
        high_activity = (
            range300 is not None
            and er60 is not None
            and range300 >= HIGH_RANGE300_MIN_USD
            and er60 >= HIGH_ER60_MIN
        )

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
            regime = "HIGH" if high_activity else "NORMAL"
            print("%s | B %.2f | A %.2f | S %.2f | %s | %s | Eq %s" % (
                datetime.now().strftime("%H:%M:%S"),
                bid, ask, spread, regime, state, money(equity)
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

            high_open = position["high_activity_entry"]
            engine = position["engine"]

            if engine == "MICRO":
                if (
                    not position["partial_done"]
                    and move >= MICRO_PARTIAL_TRIGGER_USD
                ):
                    close_ounces = position["ounces"] * MICRO_PARTIAL_FRACTION
                    partial_pnl = move * close_ounces * INR_PER_USD
                    realized_inr += partial_pnl
                    position["ounces"] -= close_ounces
                    position["partial_done"] = True
                    position["partial_realized_inr"] += partial_pnl
                    print(
                        "PARTIAL MICRO | realized",
                        money(partial_pnl),
                        "| remaining %.5f oz" % position["ounces"],
                    )

                tp = MICRO_TAKE_PROFIT_USD
                max_hold = MICRO_MAX_HOLD_SECONDS
                reversal_exit = True
                trail_trigger = MICRO_TRAIL_TRIGGER_USD
                trail_giveback = MICRO_TRAIL_GIVEBACK_USD
            elif high_open and engine == "PRIMARY":
                tp = PRIMARY_HIGH_TAKE_PROFIT_USD
                max_hold = PRIMARY_HIGH_MAX_HOLD_SECONDS
                reversal_exit = PRIMARY_HIGH_REVERSAL_EXIT
                trail_trigger = None
                trail_giveback = None
            elif high_open and engine == "SECONDARY":
                tp = SECONDARY_HIGH_TAKE_PROFIT_USD
                max_hold = SECONDARY_HIGH_MAX_HOLD_SECONDS
                reversal_exit = SECONDARY_HIGH_REVERSAL_EXIT
                trail_trigger = SECONDARY_HIGH_TRAIL_TRIGGER_USD
                trail_giveback = SECONDARY_HIGH_TRAIL_GIVEBACK_USD
            elif engine == "PRIMARY":
                tp = PRIMARY_TAKE_PROFIT_DISTANCE_USD
                max_hold = PRIMARY_MAX_HOLD_SECONDS
                reversal_exit = True
                trail_trigger = None
                trail_giveback = None
            else:
                tp = SECONDARY_TAKE_PROFIT_DISTANCE_USD
                max_hold = SECONDARY_MAX_HOLD_SECONDS
                reversal_exit = True
                trail_trigger = None
                trail_giveback = None

            if move <= -STOP_DISTANCE_USD:
                reason = "STOP"
            elif move >= tp:
                reason = "TAKE_PROFIT"

            if (
                reason is None
                and trail_trigger is not None
                and position["peak_move_usd"] >= trail_trigger
                and move <= position["peak_move_usd"] - trail_giveback
            ):
                reason = "TRAIL"

            if (
                reason is None
                and engine == "MICRO"
                and held >= MICRO_STAGNATION_SECONDS
                and position["peak_move_usd"] < MICRO_STAGNATION_PEAK_USD
            ):
                reason = "STAGNATION"

            if reason is None and reversal_exit and m300 is not None:
                if position["side"] == "BUY" and m300 <= 0.0:
                    reason = "TREND_REVERSAL"
                elif position["side"] == "SELL" and m300 >= 0.0:
                    reason = "TREND_REVERSAL"

            if reason is None and held >= max_hold:
                reason = "MAX_HOLD"

            if reason is not None:
                realized_inr = close_position(
                    reason, position, bid, ask, spread, realized_inr,
                    trade_pnl, m30, m60, m300, m1800, range300, er60
                )
                if engine == "PRIMARY":
                    last_primary_exit_time = now
                elif engine == "SECONDARY":
                    last_secondary_exit_time = now
                else:
                    last_micro_exit_time = now
                position = None
                hour_closed_trades += 1

            time.sleep(SAMPLE_INTERVAL)
            continue

        if spread > MAX_SPREAD_USD:
            time.sleep(SAMPLE_INTERVAL)
            continue

        primary_cooldown = (
            PRIMARY_COOLDOWN_HIGH_SECONDS
            if high_activity else PRIMARY_COOLDOWN_SECONDS
        )
        secondary_cooldown = (
            SECONDARY_COOLDOWN_HIGH_SECONDS
            if high_activity else SECONDARY_COOLDOWN_SECONDS
        )

        side = None
        engine = None
        channel_high = None
        channel_low = None

        if (
            now - continuity_start_time >= PRIMARY_WARMUP_SECONDS
            and now - last_primary_exit_time >= primary_cooldown
        ):
            side = primary_signal(now, m60, m300, m1800)
            if side is not None:
                engine = "PRIMARY"

        if side is None and now - last_secondary_exit_time >= secondary_cooldown:
            side, channel_high, channel_low = secondary_signal(
                now, mid, m30, m300, m1800, high_activity
            )
            if side is not None:
                engine = "SECONDARY"

        if side is None and now - last_micro_exit_time >= MICRO_COOLDOWN_SECONDS:
            side = micro_signal(
                now, spread, m10, m60, m120, er60, range60, imb10, qacc
            )
            if side is not None:
                engine = "MICRO"

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
            "partial_done": False,
            "partial_realized_inr": 0.0,
            "last_m10": "" if m10 is None else round(m10, 4),
            "last_m120": "" if m120 is None else round(m120, 4),
            "last_range60": "" if range60 is None else round(range60, 4),
            "last_imb10": "" if imb10 is None else round(imb10, 6),
            "last_qacc": "" if qacc is None else round(qacc, 6),
            "high_activity_entry": high_activity,
            "channel_high": "" if channel_high is None else round(channel_high, 4),
            "channel_low": "" if channel_low is None else round(channel_low, 4),
        }
        trade_number += 1
        initial_pnl = pnl_inr(position, bid, ask)
        position["mae"] = min(0.0, initial_pnl)

        print()
        print("PAPER %s %s #%d | %s | entry %.2f | %.5f oz | risk %s" % (
            engine,
            side,
            trade_number,
            "HIGH" if high_activity else "NORMAL",
            entry,
            ounces,
            money(risk_budget),
        ))
        print()

        write_log({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event": "ENTRY",
            "engine": engine,
            "side": side,
            "high_activity_entry": high_activity,
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
            "m10": "" if m10 is None else round(m10, 4),
            "m30": "" if m30 is None else round(m30, 4),
            "m60": "" if m60 is None else round(m60, 4),
            "m120": "" if m120 is None else round(m120, 4),
            "m300": "" if m300 is None else round(m300, 4),
            "m1800": "" if m1800 is None else round(m1800, 4),
            "range60": "" if range60 is None else round(range60, 4),
            "range300": "" if range300 is None else round(range300, 4),
            "er60": "" if er60 is None else round(er60, 6),
            "imb10": "" if imb10 is None else round(imb10, 6),
            "quote_rate_ratio": "" if qacc is None else round(qacc, 6),
            "channel_high": position["channel_high"],
            "channel_low": position["channel_low"],
            "mfe_inr": 0.0,
            "mae_inr": round(position["mae"], 2),
            "peak_move_usd": 0.0,
            "partial_realized_inr": 0.0,
            "reason": (
                "v4_1_trend_pullback_resumption"
                if engine == "PRIMARY"
                else "regime_adaptive_range_breakout"
                if engine == "SECONDARY"
                else "micro_structural_pullback_resumption"
            ),
        })

        time.sleep(SAMPLE_INTERVAL)

except KeyboardInterrupt:
    print("Stopping V4.4...")
    if position is not None:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick and tick.bid > 0 and tick.ask > 0:
            final_pnl = pnl_inr(position, float(tick.bid), float(tick.ask))
            position["mfe"] = max(position["mfe"], final_pnl)
            position["mae"] = min(position["mae"], final_pnl)
            realized_inr = close_position(
                "MANUAL_STOP", position, float(tick.bid), float(tick.ask),
                float(tick.ask - tick.bid), realized_inr, final_pnl,
                None, None, None, None, None, None
            )
    print("Final paper balance:", money(START_BALANCE_INR + realized_inr))

finally:
    mt5.shutdown()

print("Trade log:", LOG_FILE.resolve())
print("Hourly log:", HOURLY_LOG_FILE.resolve())
