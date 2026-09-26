"""Experiment 45: external GC futures correlation bridge.

Fetches public Yahoo Finance 5-minute GC=F chart data and compares it with the
already-known MT5 XAUUSD quote history. This is an alignment/representation
experiment only: no P&L labels, no strategy changes, no final20 access.

GC=F is used as an aggregated COMEX Gold futures price proxy. It is NOT treated
as trade tape or full CME depth.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_regime_portability as portability

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-09-26-v4_5-external-gc-correlation"

YAHOO_SYMBOL = "GC=F"
YAHOO_INTERVAL = "5m"
LAGS_MIN = list(range(-240, 241, 5))
RECENT_MT5_MINUS_HOST_SEC = 10797.910989


def write_csv(path: Path, rows: List[Dict]):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: List[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def yahoo_url(host: str, start: pd.Timestamp, end: pd.Timestamp) -> str:
    p1 = int(start.timestamp())
    p2 = int(end.timestamp())
    symbol = urllib.parse.quote(YAHOO_SYMBOL, safe="")
    return (
        f"https://{host}/v8/finance/chart/{symbol}"
        f"?period1={p1}&period2={p2}&interval={YAHOO_INTERVAL}"
        "&includePrePost=true&events=div%2Csplits"
    )


def fetch_yahoo(start: pd.Timestamp, end: pd.Timestamp) -> Tuple[pd.DataFrame, Dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 xau-lab-research/1.0",
        "Accept": "application/json,text/plain,*/*",
    }
    last_error = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = yahoo_url(host, start, end)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = resp.read()
                status = getattr(resp, "status", 200)
            obj = json.loads(payload)
            chart = obj.get("chart", {})
            if chart.get("error"):
                raise RuntimeError(str(chart["error"]))
            result = (chart.get("result") or [None])[0]
            if not result:
                raise RuntimeError("Yahoo chart result is empty")
            ts = result.get("timestamp") or []
            quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
            if not ts:
                raise RuntimeError("Yahoo returned no timestamps")
            frame = pd.DataFrame({
                "timestamp_utc": pd.to_datetime(ts, unit="s", utc=True),
                "open": quote.get("open", [None] * len(ts)),
                "high": quote.get("high", [None] * len(ts)),
                "low": quote.get("low", [None] * len(ts)),
                "close": quote.get("close", [None] * len(ts)),
                "volume": quote.get("volume", [None] * len(ts)),
            })
            frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
            frame["volume"] = pd.to_numeric(frame["volume"], errors="coerce")
            frame = frame.dropna(subset=["close"]).drop_duplicates("timestamp_utc").sort_values("timestamp_utc")
            meta = {
                "provider": "Yahoo Finance chart endpoint",
                "symbol": YAHOO_SYMBOL,
                "interval": YAHOO_INTERVAL,
                "host": host,
                "requested_start_utc": start.isoformat(),
                "requested_end_utc": end.isoformat(),
                "http_status": int(status),
                "response_sha256": sha256_bytes(payload),
                "response_bytes": len(payload),
                "rows": int(len(frame)),
                "first_timestamp_utc": frame.timestamp_utc.iloc[0].isoformat() if len(frame) else None,
                "last_timestamp_utc": frame.timestamp_utc.iloc[-1].isoformat() if len(frame) else None,
                "source_note": "Aggregated continuous Gold futures proxy bars; not CME trade tape/depth.",
            }
            return frame, meta
        except Exception as exc:
            last_error = f"{host}: {type(exc).__name__}: {exc}"
            time.sleep(1.0)
    raise RuntimeError(f"Yahoo fetch failed: {last_error}")


def load_mt5(path: Path, *, nrows=None) -> pd.DataFrame:
    df = pd.read_csv(path, nrows=nrows, usecols=["timestamp_utc", "mid"])
    df["timestamp_utc"] = pd.to_datetime(df.timestamp_utc, utc=True, format="mixed")
    df["mid"] = pd.to_numeric(df.mid, errors="coerce")
    df = df.dropna(subset=["mid"]).sort_values("timestamp_utc")
    return df


def to_5m(frame: pd.DataFrame, price_col: str, *, timestamp_shift_sec: float = 0.0) -> pd.DataFrame:
    q = frame[["timestamp_utc", price_col]].copy()
    if timestamp_shift_sec:
        q["timestamp_utc"] = q["timestamp_utc"] + pd.to_timedelta(timestamp_shift_sec, unit="s")
    q = q.set_index("timestamp_utc").sort_index()
    q = q[price_col].resample("5min").last().dropna().to_frame("price")
    q["log_return"] = np.log(q.price).diff()
    return q


def correlation_stats(mt5: pd.DataFrame, gc: pd.DataFrame, *, gc_shift_min: int = 0) -> Dict:
    g = gc.copy()
    if gc_shift_min:
        g.index = g.index + pd.Timedelta(minutes=int(gc_shift_min))
    joined = mt5.rename(columns={"price": "mt5_price", "log_return": "mt5_return"}).join(
        g.rename(columns={"price": "gc_price", "log_return": "gc_return"}),
        how="inner",
    ).dropna(subset=["mt5_return", "gc_return"])
    if len(joined) < 5:
        return {
            "matched_returns": int(len(joined)),
            "pearson_return": math.nan,
            "spearman_return": math.nan,
            "direction_agreement": math.nan,
            "price_level_pearson": math.nan,
            "basis_median_usd": math.nan,
            "basis_std_usd": math.nan,
        }
    pr = float(joined.mt5_return.corr(joined.gc_return, method="pearson"))
    sr = float(joined.mt5_return.rank(method="average").corr(joined.gc_return.rank(method="average")))
    direction = float(np.mean(np.sign(joined.mt5_return) == np.sign(joined.gc_return)))
    level = float(joined.mt5_price.corr(joined.gc_price, method="pearson"))
    basis = joined.gc_price - joined.mt5_price
    return {
        "matched_returns": int(len(joined)),
        "pearson_return": pr,
        "spearman_return": sr,
        "direction_agreement": direction,
        "price_level_pearson": level,
        "basis_median_usd": float(basis.median()),
        "basis_std_usd": float(basis.std(ddof=0)),
    }


def lag_scan(mt5: pd.DataFrame, gc: pd.DataFrame, window: str) -> List[Dict]:
    rows = []
    for lag in LAGS_MIN:
        s = correlation_stats(mt5, gc, gc_shift_min=lag)
        rows.append({
            "window": window,
            "gc_shift_minutes_to_match_mt5": lag,
            **s,
        })
    return rows


def best_lag(rows: List[Dict]) -> Dict:
    valid = [r for r in rows if math.isfinite(float(r.get("pearson_return", math.nan)))]
    if not valid:
        return {}
    return max(valid, key=lambda r: (abs(float(r["pearson_return"])), int(r["matched_returns"])))


def slice_gc(gc: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return gc[(gc.timestamp_utc >= start) & (gc.timestamp_utc <= end)].copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("canonical_csv", type=Path)
    ap.add_argument("recent_csv_or_gz", type=Path)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    canonical.verify_dataset(args.canonical_csv)
    portability.verify_recent(args.recent_csv_or_gz)
    args.output.mkdir(parents=True, exist_ok=True)

    print("loading known MT5 windows", flush=True)
    hist = load_mt5(args.canonical_csv, nrows=canonical.RESEARCH_ROWS)
    recent = load_mt5(args.recent_csv_or_gz)

    hist_start = hist.timestamp_utc.iloc[0]
    hist_end = hist.timestamp_utc.iloc[-1]
    recent_start = recent.timestamp_utc.iloc[0]
    recent_end = recent.timestamp_utc.iloc[-1]

    request_start = min(hist_start, recent_start) - pd.Timedelta(hours=8)
    request_end = max(hist_end, recent_end) + pd.Timedelta(hours=8)

    print(f"fetching {YAHOO_SYMBOL} {YAHOO_INTERVAL} external proxy", flush=True)
    gc_raw, source_meta = fetch_yahoo(request_start, request_end)

    source_manifest = {
        "schema": "xau-external-gc-source-v1",
        **source_meta,
        "redistribution_policy": "Raw Yahoo response/bars are not committed; only source metadata and derived correlation evidence are stored.",
        "final20_opened": False,
    }
    (args.output / "external_source_manifest.json").write_text(
        json.dumps(source_manifest, indent=2) + "\n", encoding="utf-8"
    )

    windows = {
        "historical_first80": (hist, hist_start, hist_end),
        "recent24h": (recent, recent_start, recent_end),
    }

    lag_rows: List[Dict] = []
    summary_windows = {}
    alignment_rows = []

    for name, (mt5_raw, start, end) in windows.items():
        # Include lag-scan padding around the external slice.
        gslice = slice_gc(
            gc_raw,
            start - pd.Timedelta(hours=5),
            end + pd.Timedelta(hours=5),
        )
        gc5 = to_5m(gslice, "close")
        mt5_reported = to_5m(mt5_raw, "mid")

        raw_stats = correlation_stats(mt5_reported, gc5, gc_shift_min=0)
        scan = lag_scan(mt5_reported, gc5, name)
        lag_rows.extend(scan)
        best = best_lag(scan)

        # Mechanical derived check using the already-recorded recent MT5-host offset.
        mt5_clock_corrected = to_5m(
            mt5_raw, "mid", timestamp_shift_sec=-RECENT_MT5_MINUS_HOST_SEC
        )
        clock_stats = correlation_stats(mt5_clock_corrected, gc5, gc_shift_min=0)

        summary_windows[name] = {
            "mt5_reported_start_utc": start.isoformat(),
            "mt5_reported_end_utc": end.isoformat(),
            "mt5_raw_rows": int(len(mt5_raw)),
            "gc_5m_rows_near_window": int(len(gc5)),
            "raw_timestamp_alignment": raw_stats,
            "best_lag_alignment": best,
            "fixed_clock_correction_sec": -RECENT_MT5_MINUS_HOST_SEC,
            "fixed_clock_correction_alignment": clock_stats,
        }
        alignment_rows += [
            {"window": name, "alignment": "raw_reported", "shift_minutes": 0, **raw_stats},
            {
                "window": name,
                "alignment": "best_lag",
                "shift_minutes": best.get("gc_shift_minutes_to_match_mt5", math.nan),
                **{k: v for k, v in best.items() if k not in ("window", "gc_shift_minutes_to_match_mt5")},
            },
            {
                "window": name,
                "alignment": "mt5_minus_10797.91s",
                "shift_minutes": -RECENT_MT5_MINUS_HOST_SEC / 60.0,
                **clock_stats,
            },
        ]

    write_csv(args.output / "lag_scan.csv", lag_rows)
    write_csv(args.output / "alignment_summary.csv", alignment_rows)

    result = {
        "schema": "xau-external-gc-correlation-v1",
        "strategy_changed": False,
        "outcome_labels_used": False,
        "selection_performed": False,
        "external_symbol": YAHOO_SYMBOL,
        "external_interval": YAHOO_INTERVAL,
        "lag_scan_minutes": {"min": min(LAGS_MIN), "max": max(LAGS_MIN), "step": 5},
        "recent_recorded_mt5_minus_host_sec": RECENT_MT5_MINUS_HOST_SEC,
        "windows": summary_windows,
        "final20_opened": False,
        "decision": "Correlation/alignment evidence only. Do not promote a trading rule from this result.",
    }
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
