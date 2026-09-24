"""Read-only Binance spot kline capture for the first paper experiment."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PUBLIC_BASE_URL = "https://data-api.binance.vision"
INTERVAL_MS = {"30m": 30 * 60 * 1000}


class MarketDataError(Exception):
    """A public market-data request or quality check failed."""


def _get_json(path: str, query: dict[str, str | int] | None = None):
    url = PUBLIC_BASE_URL + path
    if query:
        url += "?" + urlencode(query)
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read(4_000_001)
    except HTTPError as exc:
        raise MarketDataError(f"Binance HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise MarketDataError(f"Binance request failed: {type(exc).__name__}") from None
    if len(raw) > 4_000_000:
        raise MarketDataError("Binance response exceeds size limit")
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise MarketDataError("Binance response is not JSON") from None


def capture_klines(*, symbol: str, interval: str, lookback_days: int) -> dict:
    """Fetch a contiguous, closed 30-minute kline window using public endpoints."""
    if symbol != "BTCUSDT" or interval not in INTERVAL_MS or not 1 <= lookback_days <= 365:
        raise MarketDataError("first paper source supports BTCUSDT, 30m, and 1–365 days only")
    host_before = datetime.now(timezone.utc)
    server_clock = _get_json("/api/v3/time")
    host_after = datetime.now(timezone.utc)
    if not isinstance(server_clock, dict) or not isinstance(server_clock.get("serverTime"), int):
        raise MarketDataError("Binance server clock is missing")
    server_ms = server_clock["serverTime"]
    host_mid_ms = int((host_before.timestamp() + host_after.timestamp()) * 500)
    interval_ms = INTERVAL_MS[interval]
    last_open_ms = (server_ms // interval_ms - 1) * interval_ms
    requested_rows = lookback_days * 24 * 60 * 60 * 1000 // interval_ms
    first_open_ms = last_open_ms - (requested_rows - 1) * interval_ms
    next_open_ms = first_open_ms
    rows: list[list] = []

    while next_open_ms <= last_open_ms:
        page = _get_json(
            "/api/v3/klines",
            {
                "symbol": symbol,
                "interval": interval,
                "startTime": next_open_ms,
                "endTime": last_open_ms + interval_ms - 1,
                "limit": 1000,
            },
        )
        if not isinstance(page, list) or not page:
            raise MarketDataError("Binance returned an empty or invalid kline page")
        for row in page:
            expected_open_ms = first_open_ms + len(rows) * interval_ms
            _validate_kline(row, expected_open_ms, interval_ms)
            rows.append(row)
        next_open_ms = first_open_ms + len(rows) * interval_ms
        if len(rows) > requested_rows:
            raise MarketDataError("Binance returned more candles than requested")

    if len(rows) != requested_rows or rows[-1][0] != last_open_ms:
        raise MarketDataError("Binance capture has missing or extra candles")
    return {
        "schema_version": "binance-spot-klines-v1",
        "source": PUBLIC_BASE_URL + "/api/v3/klines",
        "symbol": symbol,
        "interval": interval,
        "interval_ms": interval_ms,
        "lookback_days": lookback_days,
        "first_open_ms": first_open_ms,
        "last_open_ms": last_open_ms,
        "server_time_ms": server_ms,
        "host_capture_mid_ms": host_mid_ms,
        "clock_offset_ms": server_ms - host_mid_ms,
        "captured_at_utc": host_after.isoformat(),
        "rows": rows,
    }


def _validate_kline(row: object, expected_open_ms: int, interval_ms: int) -> None:
    if not isinstance(row, list) or len(row) != 12:
        raise MarketDataError("kline row must have 12 fields")
    if row[0] != expected_open_ms or row[6] != expected_open_ms + interval_ms - 1:
        raise MarketDataError("kline timestamps are missing, duplicated, or misaligned")
    try:
        open_, high, low, close, volume = (float(row[index]) for index in (1, 2, 3, 4, 5))
    except (TypeError, ValueError):
        raise MarketDataError("kline price or volume is invalid") from None
    if not all(math.isfinite(value) for value in (open_, high, low, close, volume)):
        raise MarketDataError("kline contains a non-finite value")
    if min(open_, high, low, close) <= 0 or volume < 0 or high < max(open_, close) or low > min(open_, close) or low > high:
        raise MarketDataError("kline OHLC or volume is inconsistent")
