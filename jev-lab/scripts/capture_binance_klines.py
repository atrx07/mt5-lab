"""Capture the frozen public BTC/USDT dataset; writes no orders or keys."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jev_lab.binance_spot import MarketDataError, capture_klines  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/2026-09-24-00-btc-spot-baseline.json")
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        experiment_id = config["experiment_id"]
        market = config["market_data"]
        document = capture_klines(
            symbol=market["symbol"],
            interval=market["interval"],
            lookback_days=market["lookback_days"],
        )
        output_path = ROOT / "data/raw" / f"{experiment_id}.json"
        manifest_path = ROOT / "data/manifests" / f"{experiment_id}.json"
        raw_bytes = (json.dumps(document, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
        digest = sha256(raw_bytes).hexdigest()
        manifest = {
            "schema_version": "jev-lab-dataset-manifest-v1",
            "dataset_id": experiment_id,
            "experiment_id": experiment_id,
            "source": document["source"],
            "acquisition_method": "public REST GET, paginated klines, no authentication",
            "venue": "Binance Spot public market data",
            "symbol": document["symbol"],
            "interval": document["interval"],
            "timezone": "UTC, source timestamps are Unix milliseconds",
            "first_open_ms": document["first_open_ms"],
            "last_open_ms": document["last_open_ms"],
            "server_time_ms": document["server_time_ms"],
            "host_capture_mid_ms": document["host_capture_mid_ms"],
            "clock_offset_ms": document["clock_offset_ms"],
            "captured_at_utc": document["captured_at_utc"],
            "row_count": len(document["rows"]),
            "fields": ["open_time_ms", "open", "high", "low", "close", "base_volume", "close_time_ms", "quote_volume", "trade_count", "taker_buy_base_volume", "taker_buy_quote_volume", "unused"],
            "quality": {"contiguous": True, "duplicate_open_times": 0, "missing_intervals": 0, "incomplete_last_candle": False},
            "raw_path": output_path.relative_to(ROOT).as_posix(),
            "raw_sha256": digest,
            "raw_bytes": len(raw_bytes),
            "licensing_note": "Local research capture; do not redistribute source rows without reviewing Binance terms.",
            "caveat": "OHLCV does not contain historical bid/ask or execution fills.",
        }
        if output_path.exists() or manifest_path.exists():
            raise FileExistsError("dataset or manifest already exists; captures are immutable")
        output_path.write_bytes(raw_bytes)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"dataset_id": experiment_id, "rows": len(document["rows"]), "raw_sha256": digest, "manifest": str(manifest_path)}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, MarketDataError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
