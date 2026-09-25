"""Freeze a bounded, read-only MT5 tick snapshot for offline XAUUSD research."""

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=24.0)
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if not 0 < args.hours <= 48:
        parser.error("--hours must be in (0, 48]")
    if args.out.exists() or args.manifest.exists():
        parser.error("snapshot output already exists; use new paths for a new freeze")
    if not mt5.initialize(timeout=10000):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        if terminal is None or not terminal.connected:
            raise RuntimeError("MT5 terminal is not connected")
        if not mt5.symbol_select(args.symbol, True):
            raise RuntimeError(f"symbol_select failed: {mt5.last_error()}")
        latest = mt5.symbol_info_tick(args.symbol)
        host_now = datetime.now(timezone.utc)
        if latest is None or latest.time_msc <= 0:
            raise RuntimeError(f"symbol_info_tick failed: {mt5.last_error()}")
        end = datetime.fromtimestamp(latest.time_msc / 1000, timezone.utc)
        start = end - timedelta(hours=args.hours)
        ticks = mt5.copy_ticks_range(args.symbol, start, end, mt5.COPY_TICKS_ALL)
        if ticks is None:
            raise RuntimeError(f"copy_ticks_range failed: {mt5.last_error()}")
        if len(ticks) == 0:
            raise RuntimeError("no ticks in requested MT5-reported time window")
        frame = pd.DataFrame(ticks)
        frame = frame[(frame.bid > 0) & (frame.ask > frame.bid)].copy()
        if frame.empty:
            raise RuntimeError("no positive bid/ask quotes")
        frame["timestamp_utc"] = pd.to_datetime(frame.time_msc, unit="ms", utc=True)
        if not frame.timestamp_utc.is_monotonic_increasing:
            frame = frame.sort_values("timestamp_utc", kind="stable")
        frame["spread"] = frame.ask - frame.bid
        frame["mid"] = (frame.ask + frame.bid) / 2
        columns = ["timestamp_utc", "bid", "ask", "last", "volume", "flags", "volume_real", "spread", "mid"]
        frame = frame[columns]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(args.out, index=False)
        offset_sec = (end - host_now).total_seconds()
        manifest = {
            "schema_version": 1,
            "dataset_id": f"{args.symbol.lower()}-mt5-recent-{args.hours:g}h-{end.strftime('%Y-%m-%d')}",
            "instrument": args.symbol,
            "source": {
                "platform": "MetaTrader 5",
                "exporter": "scripts/capture_recent_xau_ticks.py",
                "tick_filter": "COPY_TICKS_ALL; bid>0 and ask>bid",
                "reported_timestamp_basis": "MT5 time_msc interpreted as UTC, per MQL5 Python API documentation",
                "host_acquisition_utc": host_now.isoformat(),
                "latest_mt5_reported_utc": end.isoformat(),
                "mt5_minus_host_clock_sec": offset_sec,
                "requested_window_hours": args.hours,
            },
            "raw": {
                "filename": args.out.name,
                "sha256": sha256_file(args.out),
                "bytes": args.out.stat().st_size,
                "data_rows": len(frame),
                "first_timestamp_utc": frame.timestamp_utc.iloc[0].isoformat(),
                "last_timestamp_utc": frame.timestamp_utc.iloc[-1].isoformat(),
                "columns": columns,
            },
            "archive": {
                "format": "gzip",
                "relative_path": f"data/raw/{args.out.name}.gz",
                "compression_level": 9,
                "deterministic_header": {"mtime": 0, "filename": ""},
                "status": "pending",
            },
            "used_by": ["docs/experiments/2026-09-24/22-recent-micro-long-validation.md"],
            "notes": [
                "This frozen snapshot is an offline replay input, not an order or live trading log.",
                "MT5 tick time appears about three hours ahead of host UTC; no silent clock shift was applied.",
                "The canonical seven-day final 20% holdout was not read.",
            ],
        }
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "rows": len(frame), "first": manifest["raw"]["first_timestamp_utc"],
            "last": manifest["raw"]["last_timestamp_utc"],
            "host_utc": host_now.isoformat(), "mt5_minus_host_sec": offset_sec,
            "median_spread_usd": float(frame.spread.median()),
            "raw_sha256": manifest["raw"]["sha256"],
            "raw_path": str(args.out), "manifest_path": str(args.manifest),
        }, indent=2))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
