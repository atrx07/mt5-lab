"""
Export recent XAUUSD MT5 ticks for offline replay.

Example:
    python export_xau_ticks.py --days 7
"""

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--days", type=float, default=7.0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    if args.days <= 0:
        raise SystemExit("--days must be > 0")

    if not mt5.initialize(timeout=10000):
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")

    try:
        if not mt5.symbol_select(args.symbol, True):
            raise RuntimeError(f"Could not select {args.symbol}")

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=args.days)

        ticks = mt5.copy_ticks_range(args.symbol, start, end, mt5.COPY_TICKS_ALL)

        if ticks is None:
            raise RuntimeError(f"copy_ticks_range failed: {mt5.last_error()}")
        if len(ticks) == 0:
            raise RuntimeError("MT5 returned zero ticks for the requested range.")

        df = pd.DataFrame(ticks)
        df["timestamp_utc"] = pd.to_datetime(df["time_msc"], unit="ms", utc=True)

        keep = ["timestamp_utc", "bid", "ask", "last", "volume", "flags", "volume_real"]
        keep = [c for c in keep if c in df.columns]
        df = df[keep]

        df = df[(df["bid"] > 0) & (df["ask"] > 0)].copy()
        df["spread"] = df["ask"] - df["bid"]
        df["mid"] = (df["bid"] + df["ask"]) / 2.0

        out = Path(args.out) if args.out else Path(f"xau_ticks_{args.days:g}d.csv")
        df.to_csv(out, index=False)

        print(f"Exported {len(df):,} usable ticks")
        print(f"From: {df['timestamp_utc'].iloc[0]}")
        print(f"To:   {df['timestamp_utc'].iloc[-1]}")
        print(f"Median spread: USD {df['spread'].median():.4f}")
        print(f"Saved: {out.resolve()}")

    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
