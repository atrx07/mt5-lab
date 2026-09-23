"""
Fast historical replay for xau-lab.

Input should be produced by export_xau_ticks.py and contain:
    timestamp_utc,bid,ask,...

Examples:
    python replay_lab.py xau_ticks_7d.csv
    python replay_lab.py xau_ticks_7d.csv --windows 100 --window-minutes 30 --seed 42

The replay implements the V4 pullback/resumption state machine using historical
bid/ask prices. It is intentionally deterministic and never touches MT5 orders.
"""

import argparse
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

START_BALANCE_INR = 500.0
INR_PER_USD = 95.7021
LEVERAGE = 100.0

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
IMPULSE_MAX_AGE_SECONDS = 45.0
RESET_M15_USD = 0.25

MAX_LOSS_INR = 8.0
PROFIT_LOCK_TRIGGER_INR = 4.0
PROFIT_LOCK_MIN_INR = 1.5
PROFIT_LOCK_KEEP_FRACTION = 0.65
REVERSAL_CONFIRM_COUNT = 2
REVERSAL_M2_USD = 0.25
MAX_HOLD_SECONDS = 60.0
COOLDOWN_SECONDS = 45.0


@dataclass
class Trade:
    side: str
    entry: float
    ounces: float
    opened_at: pd.Timestamp
    peak_pnl: float = 0.0
    reverse_count: int = 0


def size_oz(balance_inr, price):
    return (max(balance_inr, 0.0) / INR_PER_USD) * LEVERAGE / price


def pnl(trade, bid, ask):
    move = bid - trade.entry if trade.side == "BUY" else trade.entry - ask
    return move * trade.ounces * INR_PER_USD


def prepare(path, step_ms):
    df = pd.read_csv(path)
    required = {"timestamp_utc", "bid", "ask"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df = df.sort_values("timestamp_utc")
    df = df[(df["bid"] > 0) & (df["ask"] > 0)].copy()
    df["spread"] = df["ask"] - df["bid"]
    df["mid"] = (df["bid"] + df["ask"]) / 2.0

    if step_ms > 0:
        bucket = f"{step_ms}ms"
        df = (
            df.set_index("timestamp_utc")
              .resample(bucket)
              .last()
              .dropna(subset=["bid", "ask"])
              .reset_index()
        )
        df["spread"] = df["ask"] - df["bid"]
        df["mid"] = (df["bid"] + df["ask"]) / 2.0

    return df.reset_index(drop=True)


def replay_v4(df):
    if len(df) < 10:
        return {"final": START_BALANCE_INR, "pnl": 0.0, "trades": 0, "wins": 0, "max_dd": 0.0}

    ts = df["timestamp_utc"].astype("int64").to_numpy() / 1e9
    bid = df["bid"].to_numpy(float)
    ask = df["ask"].to_numpy(float)
    mid = (bid + ask) / 2.0
    spread = ask - bid

    def value_at(i, seconds):
        target = ts[i] - seconds
        j = np.searchsorted(ts, target, side="right") - 1
        return None if j < 0 else mid[j]

    realized = 0.0
    trade = None
    impulse = None
    consumed_side = None
    last_exit = -1e18
    trade_results = []
    peak_equity = START_BALANCE_INR
    max_dd = 0.0

    for i in range(len(df)):
        now = ts[i]
        q2 = value_at(i, 2)
        q5 = value_at(i, 5)
        q15 = value_at(i, 15)
        if q2 is None or q5 is None or q15 is None:
            continue

        m2 = mid[i] - q2
        m5 = mid[i] - q5
        m15 = mid[i] - q15

        u = 0.0 if trade is None else pnl(trade, bid[i], ask[i])
        equity = START_BALANCE_INR + realized + u
        peak_equity = max(peak_equity, equity)
        max_dd = max(max_dd, peak_equity - equity)

        if trade is not None:
            trade.peak_pnl = max(trade.peak_pnl, u)
            held = now - trade.opened_at.timestamp()
            reason = None

            if u <= -MAX_LOSS_INR:
                reason = "HARD_STOP"

            if reason is None and trade.peak_pnl >= PROFIT_LOCK_TRIGGER_INR:
                floor = max(PROFIT_LOCK_MIN_INR, trade.peak_pnl * PROFIT_LOCK_KEEP_FRACTION)
                if u <= floor:
                    reason = "PROFIT_LOCK"

            opposite = (
                trade.side == "BUY" and m2 <= -REVERSAL_M2_USD
            ) or (
                trade.side == "SELL" and m2 >= REVERSAL_M2_USD
            )
            trade.reverse_count = trade.reverse_count + 1 if opposite else 0

            if reason is None and trade.reverse_count >= REVERSAL_CONFIRM_COUNT:
                reason = "CONFIRMED_REVERSAL"
            if reason is None and held >= MAX_HOLD_SECONDS:
                reason = "MAX_HOLD"

            if reason:
                realized += u
                trade_results.append(u)
                consumed_side = trade.side
                trade = None
                impulse = None
                last_exit = now

            continue

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
            else:
                continue

        if impulse is None:
            if spread[i] > MAX_SPREAD_USD:
                continue

            buy = MIN_IMPULSE_M5_USD <= m5 <= MAX_IMPULSE_M5_USD and m15 >= MIN_IMPULSE_M15_USD
            sell = -MAX_IMPULSE_M5_USD <= m5 <= -MIN_IMPULSE_M5_USD and m15 <= -MIN_IMPULSE_M15_USD
            side = "BUY" if buy else "SELL" if sell else None

            if side:
                impulse = {
                    "side": side,
                    "time": now,
                    "extreme": mid[i],
                    "pullback_seen": False,
                    "pullback_extreme": mid[i],
                }
            continue

        side = impulse["side"]
        if now - impulse["time"] > IMPULSE_MAX_AGE_SECONDS:
            impulse = None
            continue

        context_alive = (
            side == "BUY" and m15 >= SLOW_CONTEXT_MIN_USD
        ) or (
            side == "SELL" and m15 <= -SLOW_CONTEXT_MIN_USD
        )
        if not context_alive:
            impulse = None
            continue

        if side == "BUY":
            impulse["extreme"] = max(impulse["extreme"], mid[i])
            retrace = impulse["extreme"] - mid[i]
        else:
            impulse["extreme"] = min(impulse["extreme"], mid[i])
            retrace = mid[i] - impulse["extreme"]

        if not impulse["pullback_seen"]:
            if PULLBACK_MIN_USD <= retrace <= PULLBACK_MAX_USD:
                impulse["pullback_seen"] = True
                impulse["pullback_extreme"] = mid[i]
            elif retrace > PULLBACK_MAX_USD:
                impulse = None
            continue

        if side == "BUY":
            impulse["pullback_extreme"] = min(impulse["pullback_extreme"], mid[i])
            resumed_distance = mid[i] - impulse["pullback_extreme"]
            resumed = m2 >= RESUME_M2_USD and m5 >= RESUME_M5_USD and resumed_distance >= RESUME_DISTANCE_USD
        else:
            impulse["pullback_extreme"] = max(impulse["pullback_extreme"], mid[i])
            resumed_distance = impulse["pullback_extreme"] - mid[i]
            resumed = m2 <= -RESUME_M2_USD and m5 <= -RESUME_M5_USD and resumed_distance >= RESUME_DISTANCE_USD

        if not resumed or spread[i] > MAX_SPREAD_USD:
            continue

        balance = START_BALANCE_INR + realized
        entry = ask[i] if side == "BUY" else bid[i]
        trade = Trade(
            side=side,
            entry=entry,
            ounces=size_oz(balance, entry),
            opened_at=df["timestamp_utc"].iloc[i],
        )
        impulse = None

    if trade is not None:
        final_u = pnl(trade, bid[-1], ask[-1])
        realized += final_u
        trade_results.append(final_u)

    final = START_BALANCE_INR + realized
    wins = sum(x > 0 for x in trade_results)

    return {
        "final": final,
        "pnl": realized,
        "trades": len(trade_results),
        "wins": wins,
        "win_rate": wins / len(trade_results) if trade_results else 0.0,
        "max_dd": max_dd,
    }


def random_windows(df, count, minutes, seed):
    rng = random.Random(seed)
    if df.empty:
        return []

    start = df["timestamp_utc"].iloc[0]
    end = df["timestamp_utc"].iloc[-1]
    length = pd.Timedelta(minutes=minutes)

    if end - start < length:
        return [df]

    max_start = end - length
    span_seconds = int((max_start - start).total_seconds())

    out = []
    for _ in range(count):
        offset = rng.randint(0, max(span_seconds, 0))
        a = start + pd.Timedelta(seconds=offset)
        b = a + length
        w = df[(df["timestamp_utc"] >= a) & (df["timestamp_utc"] < b)]
        if len(w) >= 10:
            out.append(w.reset_index(drop=True))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    p.add_argument("--step-ms", type=int, default=500)
    p.add_argument("--windows", type=int, default=0)
    p.add_argument("--window-minutes", type=int, default=30)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    df = prepare(args.csv, args.step_ms)

    if args.windows <= 0:
        r = replay_v4(df)
        print("=== V4 FULL REPLAY ===")
        print(f"Rows:          {len(df):,}")
        print(f"Trades:        {r['trades']}")
        print(f"Wins:          {r['wins']}")
        print(f"Win rate:      {r['win_rate']*100:.1f}%")
        print(f"Net P&L:       ₹{r['pnl']:.2f}")
        print(f"Final balance: ₹{r['final']:.2f}")
        print(f"Max drawdown:  ₹{r['max_dd']:.2f}")
        return

    windows = random_windows(df, args.windows, args.window_minutes, args.seed)
    rows = []
    for n, window in enumerate(windows, 1):
        r = replay_v4(window)
        rows.append({
            "window": n,
            "start": window["timestamp_utc"].iloc[0],
            "end": window["timestamp_utc"].iloc[-1],
            **r,
        })

    out = pd.DataFrame(rows)
    if out.empty:
        print("No usable replay windows.")
        return

    print("=== V4 RANDOM-WINDOW REPLAY ===")
    print(f"Windows:          {len(out)}")
    print(f"Window length:    {args.window_minutes} min")
    print(f"Mean P&L:         ₹{out['pnl'].mean():.2f}")
    print(f"Median P&L:       ₹{out['pnl'].median():.2f}")
    print(f"Positive windows: {(out['pnl'] > 0).mean()*100:.1f}%")
    print(f"Mean trades:      {out['trades'].mean():.2f}")
    print(f"Worst window:     ₹{out['pnl'].min():.2f}")
    print(f"Best window:      ₹{out['pnl'].max():.2f}")
    print(f"Worst drawdown:   ₹{out['max_dd'].max():.2f}")

    out.to_csv("replay_v4_windows.csv", index=False)
    print("Saved per-window results to replay_v4_windows.csv")


if __name__ == "__main__":
    main()
