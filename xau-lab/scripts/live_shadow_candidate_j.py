"""Read-only live shadow for frozen Candidate D / H / J.

This runner NEVER sends broker orders. It captures MT5 XAUUSD ticks and
periodically replays a bounded recent window through the exact frozen research
implementations used by Experiments 43 and 47.

Modes
-----
--preflight <csv>
    Offline wiring/parity check. Does not import or connect to MetaTrader5.

--connect-check
    Read-only terminal/symbol connectivity check, then exit.

(default live mode)
    Capture raw MT5 ticks into data/live_shadow/<session>/ and write rolling
    shadow status/events. No trade execution API is called.

The rolling live replay is monitoring evidence, not a low-latency executor.
Experiment 48 later freezes a fresh raw snapshot and evaluates it offline.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import os
import sys
import tempfile
import time
from collections import Counter, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))

import canonical_replay as canonical
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_microstate_v1_freeze as microstate
import v4_5_quote_flow_phase_controller as qflow
import v4_5_tick_tape_field_audit as tape

SYMBOL = "XAUUSD"
EXPERIMENT_REF = "docs/experiments/2026-09-26/48-v4-5-candidate-j-fresh-validation.md"
RUNNER_REF = "docs/experiments/2026-09-26/48P-v4-5-candidate-j-live-shadow-preflight.md"

RAW_COLUMNS = [
    "timestamp_utc",
    "bid",
    "ask",
    "last",
    "volume",
    "flags",
    "volume_real",
    "spread",
    "mid",
]

ENGINE_NAMES = {1: "PRIMARY", 2: "SECONDARY", 3: "MICRO", 4: "BURST"}

PREFLIGHT_EXPECTED = {
    "500ms": {
        "D": {"pnl": -223.27329174700338, "trades": 39, "wins": 5},
        "H": {"pnl": -208.4689762103303, "trades": 39, "wins": 5},
        "J": {"pnl": -164.53993148659703, "trades": 31, "wins": 4},
    },
    "1s": {
        "D": {"pnl": -135.9095261798986, "trades": 34, "wins": 8},
        "H": {"pnl": -128.62645713776266, "trades": 34, "wins": 8},
        "J": {"pnl": -70.99924105736795, "trades": 28, "wins": 8},
    },
}


def atomic_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safety_scan_source() -> Dict:
    """AST-level guard: this paper runner must contain no MT5 trade call."""
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute):
            name = fn.attr.lower()
            if name == "order_send" or name.startswith("trade_"):
                forbidden.append({"line": getattr(node, "lineno", None), "call": fn.attr})
    if forbidden:
        raise RuntimeError(f"FORBIDDEN live-trading call found in shadow runner: {forbidden}")
    return {
        "status": "PASS",
        "forbidden_calls_found": 0,
        "policy": "read-only MT5 market-data access only; no order_send/trade_* calls",
    }


def compact(m: Dict) -> Dict:
    keys = (
        "pnl_inr",
        "terminal_unrealized_inr",
        "terminal_equity_pnl_inr",
        "open_position_at_end",
        "ghost_active_at_end",
        "profit_factor",
        "trades",
        "wins",
        "win_rate",
        "max_drawdown_inr",
        "primary_entries",
        "primary_flow_exits",
        "ghost_releases",
        "shadow_opportunities",
        "immediate_entries",
        "delayed_entries",
        "skipped_entries",
        "busy_skips",
        "phase_exits",
        "protected_pullbacks",
    )
    return {k: m[k] for k in keys if k in m}


def replay_window(path: Path, *, context: str = "live-shadow") -> Dict:
    """Replay one immutable/raw rolling window through frozen D/H/J."""
    traw = tape.load_raw(path)
    mraw = microstate.load_raw(path)
    result = {"source": str(path), "intervals": {}}

    for interval in ("500ms", "1s"):
        arr, _ = canonical.build_features(path, interval)
        qcache: Dict = {}
        mcache: Dict = {}

        d = hbase.simulate(
            arr,
            0,
            len(arr["t"]),
            candidate_h=False,
            capture_trace=True,
        )
        h_exits: List[Dict] = []
        h = hbase.simulate(
            arr,
            0,
            len(arr["t"]),
            candidate_h=True,
            raw=mraw,
            feature_cache=mcache,
            exit_events=h_exits,
            context=f"{context}:{interval}:H",
            capture_trace=True,
        )
        j_entries: List[Dict] = []
        j_exits: List[Dict] = []
        j = qflow.simulate_overlay(
            arr,
            0,
            len(arr["t"]),
            variant="Candidate-J",
            tape_raw=traw,
            micro_raw=mraw,
            quote_cache=qcache,
            micro_cache=mcache,
            entry_events=j_entries,
            exit_events=j_exits,
            context=f"{context}:{interval}:J",
            capture_shadow_trace=True,
        )

        shadow_parity = j.get("shadow_trace") == d.get("entry_trace")
        if not shadow_parity:
            raise RuntimeError(f"Candidate-J baseline shadow parity failed in {interval}")

        result["intervals"][interval] = {
            "D": compact(d),
            "H": compact(h),
            "J": compact(j),
            "shadow_parity": True,
            "d_entry_trace": d.get("entry_trace") or [],
            "h_entry_trace": h.get("entry_trace") or [],
            "h_extra_exit_events": h_exits,
            "j_entry_phase_events": j_entries,
            "j_phase_exit_events": j_exits,
        }
    return result


def run_preflight(csv_path: Path, out: Path | None) -> Dict:
    safety = safety_scan_source()
    r = replay_window(csv_path, context="preflight")
    checks = []
    for interval, expected in PREFLIGHT_EXPECTED.items():
        for candidate in ("D", "H", "J"):
            got = r["intervals"][interval][candidate]
            exp = expected[candidate]
            pnl = float(got["terminal_equity_pnl_inr"])
            ok = (
                abs(pnl - float(exp["pnl"])) <= 1e-6
                and int(got["trades"]) == int(exp["trades"])
                and int(got["wins"]) == int(exp["wins"])
            )
            checks.append(
                {
                    "interval": interval,
                    "candidate": candidate,
                    "pass": ok,
                    "expected_pnl_inr": exp["pnl"],
                    "actual_pnl_inr": pnl,
                    "expected_trades": exp["trades"],
                    "actual_trades": int(got["trades"]),
                    "expected_wins": exp["wins"],
                    "actual_wins": int(got["wins"]),
                }
            )
    if not all(x["pass"] for x in checks):
        raise RuntimeError("Live-shadow preflight parity failed:\n" + json.dumps(checks, indent=2))
    payload = {
        "schema": "xau-candidate-j-live-shadow-preflight-v1",
        "status": "PASS",
        "safety_scan": safety,
        "source": str(csv_path),
        "source_sha256": sha256_file(csv_path),
        "checks": checks,
        "final20_opened": False,
        "live_market_claimed": False,
    }
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(out, payload)
    return payload


def live_import_mt5():
    try:
        import MetaTrader5 as mt5
    except Exception as exc:
        raise RuntimeError(
            "MetaTrader5 Python package is required for live/connect-check mode. "
            "Offline --preflight mode does not require it."
        ) from exc
    return mt5


def mt5_connect(mt5, symbol: str) -> None:
    if not mt5.initialize(timeout=10000):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    terminal = mt5.terminal_info()
    if terminal is None or not terminal.connected:
        mt5.shutdown()
        raise RuntimeError("MT5 terminal is not connected")
    if not mt5.symbol_select(symbol, True):
        mt5.shutdown()
        raise RuntimeError(f"symbol_select({symbol}) failed: {mt5.last_error()}")


def connect_check(symbol: str) -> Dict:
    safety = safety_scan_source()
    mt5 = live_import_mt5()
    mt5_connect(mt5, symbol)
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None or tick.time_msc <= 0:
            raise RuntimeError(f"symbol_info_tick failed: {mt5.last_error()}")
        host = datetime.now(timezone.utc)
        broker = datetime.fromtimestamp(float(tick.time_msc) / 1000.0, timezone.utc)
        payload = {
            "status": "PASS",
            "symbol": symbol,
            "terminal_connected": True,
            "latest_tick_reported_utc": broker.isoformat(),
            "host_utc": host.isoformat(),
            "mt5_minus_host_clock_sec": (broker - host).total_seconds(),
            "bid": float(tick.bid),
            "ask": float(tick.ask),
            "flags": int(tick.flags),
            "safety_scan": safety,
            "note": "Connectivity only. A frozen weekend tick is acceptable here and is not live evidence.",
        }
        return payload
    finally:
        mt5.shutdown()


def append_rows(path: Path, rows: List[Dict]) -> None:
    if not rows:
        return
    exists = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RAW_COLUMNS)
        if not exists:
            w.writeheader()
        for row in rows:
            w.writerow({k: row[k] for k in RAW_COLUMNS})


def structured_ticks_to_rows(ticks) -> List[Dict]:
    out: List[Dict] = []
    if ticks is None or len(ticks) == 0:
        return out
    for rec in ticks:
        bid = float(rec["bid"])
        ask = float(rec["ask"])
        if not (bid > 0 and ask > bid):
            continue
        tmsc = int(rec["time_msc"])
        out.append(
            {
                "_time_msc": tmsc,
                "_signature": (
                    bid,
                    ask,
                    float(rec["last"]),
                    float(rec["volume"]),
                    int(rec["flags"]),
                    float(rec["volume_real"]),
                ),
                "timestamp_utc": pd.Timestamp(tmsc, unit="ms", tz="UTC").isoformat(),
                "bid": bid,
                "ask": ask,
                "last": float(rec["last"]),
                "volume": float(rec["volume"]),
                "flags": int(rec["flags"]),
                "volume_real": float(rec["volume_real"]),
                "spread": ask - bid,
                "mid": (ask + bid) / 2.0,
            }
        )
    out.sort(key=lambda x: x["_time_msc"])
    return out


def select_new_rows(
    fetched: List[Dict],
    last_time_msc: int,
    last_signature_counts: Counter,
) -> Tuple[List[Dict], int, Counter]:
    """Deduplicate overlapping MT5 history queries, including same-ms ticks."""
    if not fetched:
        return [], last_time_msc, last_signature_counts

    accepted: List[Dict] = []
    groups: Dict[int, List[Dict]] = {}
    for row in fetched:
        groups.setdefault(int(row["_time_msc"]), []).append(row)

    for tmsc in sorted(groups):
        rows = groups[tmsc]
        if tmsc < last_time_msc:
            continue
        if tmsc == last_time_msc:
            seen_now = Counter()
            for row in rows:
                sig = row["_signature"]
                seen_now[sig] += 1
                if seen_now[sig] > last_signature_counts.get(sig, 0):
                    accepted.append(row)
            continue
        accepted.extend(rows)

    if accepted:
        max_t = max(int(x["_time_msc"]) for x in accepted)
        final_group = groups.get(max_t, [x for x in fetched if int(x["_time_msc"]) == max_t])
        counts = Counter(x["_signature"] for x in final_group)
        return accepted, max_t, counts

    return [], last_time_msc, last_signature_counts


def public_row(row: Dict) -> Dict:
    return {k: row[k] for k in RAW_COLUMNS}


def event_timestamp(event: Dict) -> float:
    for k in ("decision_ts", "exit_ts", "baseline_entry_ts", "entry_ts"):
        v = event.get(k)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    return math.nan


def event_key(event: Dict) -> str:
    raw = json.dumps(event, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_seen_event_keys(path: Path) -> set[str]:
    seen: set[str] = set()
    if not path.exists():
        return seen
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            key = obj.get("_event_key")
            if key:
                seen.add(str(key))
    return seen


def emit_events(
    replay: Dict,
    path: Path,
    seen: set[str],
    *,
    trusted: bool,
    latest_ts: float,
    trusted_tail_sec: float,
) -> int:
    events: List[Dict] = []

    for interval, z in replay["intervals"].items():
        for ts, engine, side in z.get("d_entry_trace", []):
            events.append(
                {
                    "candidate": "D",
                    "event": "OPPORTUNITY_ENTRY",
                    "interval": interval,
                    "entry_ts": float(ts),
                    "engine": ENGINE_NAMES[int(engine)],
                    "side": "BUY" if int(side) == 1 else "SELL",
                }
            )
        for ev in z.get("h_extra_exit_events", []):
            events.append({"candidate": "H", "event": "EXTRA_EXIT", "interval": interval, **ev})
        for ev in z.get("j_entry_phase_events", []):
            events.append({"candidate": "J", "event": "ENTRY_PHASE", "interval": interval, **ev})
        for ev in z.get("j_phase_exit_events", []):
            events.append({"candidate": "J", "event": "PHASE_EXIT", "interval": interval, **ev})

    emitted = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for ev in events:
            ts = event_timestamp(ev)
            if math.isfinite(ts) and latest_ts - ts > trusted_tail_sec:
                continue
            ev["trusted_after_warmup"] = bool(trusted)
            ev["logged_host_utc"] = datetime.now(timezone.utc).isoformat()
            key = event_key(ev)
            if key in seen:
                continue
            ev["_event_key"] = key
            fh.write(json.dumps(ev, sort_keys=True, default=str) + "\n")
            seen.add(key)
            emitted += 1
    return emitted


def write_manifest(
    path: Path,
    *,
    session_id: str,
    symbol: str,
    rows: int,
    first_ts: str | None,
    last_ts: str | None,
    host_now: datetime,
    broker_now: datetime,
    market_state: str,
    session_start_host: datetime,
    ticks_path: Path,
) -> None:
    payload = {
        "schema": "xau-live-shadow-session-v1",
        "session_id": session_id,
        "symbol": symbol,
        "mode": "read-only-paper-shadow",
        "runner": "scripts/live_shadow_candidate_j.py",
        "used_by": [RUNNER_REF, EXPERIMENT_REF],
        "session_start_host_utc": session_start_host.isoformat(),
        "updated_host_utc": host_now.isoformat(),
        "latest_mt5_reported_utc": broker_now.isoformat(),
        "mt5_minus_host_clock_sec": (broker_now - host_now).total_seconds(),
        "market_state": market_state,
        "raw": {
            "path": str(ticks_path),
            "rows": rows,
            "first_timestamp_utc": first_ts,
            "last_timestamp_utc": last_ts,
            "columns": RAW_COLUMNS,
            "sha256": sha256_file(ticks_path) if ticks_path.exists() else None,
        },
        "safety": safety_scan_source(),
        "strategy": {
            "candidates": ["D", "H", "J"],
            "grids": ["500ms", "1s"],
            "candidate_j_frozen": True,
            "external_data_used": False,
        },
        "final20_opened": False,
    }
    atomic_json(path, payload)


def replay_rolling_rows(
    rows: Iterable[Dict],
    *,
    temp_dir: Path,
    context: str,
) -> Dict:
    public = [public_row(x) for x in rows]
    if len(public) < 2:
        raise RuntimeError("not enough captured ticks for shadow replay")
    temp_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        prefix="shadow_rolling_",
        dir=temp_dir,
        delete=False,
        newline="",
        encoding="utf-8",
    ) as fh:
        temp = Path(fh.name)
        w = csv.DictWriter(fh, fieldnames=RAW_COLUMNS)
        w.writeheader()
        w.writerows(public)
    try:
        return replay_window(temp, context=context)
    finally:
        try:
            temp.unlink()
        except OSError:
            pass


def live_main(args) -> None:
    safety_scan_source()
    mt5 = live_import_mt5()
    mt5_connect(mt5, args.symbol)

    session_start_host = datetime.now(timezone.utc)
    session_id = args.session_id or session_start_host.strftime("%Y%m%dT%H%M%SZ")
    session_dir = args.output_root / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    ticks_path = session_dir / "ticks.csv"
    manifest_path = session_dir / "session_manifest.json"
    status_path = session_dir / "shadow_status.json"
    events_path = session_dir / "shadow_events.jsonl"
    seen_events = load_seen_event_keys(events_path)

    latest = mt5.symbol_info_tick(args.symbol)
    if latest is None or latest.time_msc <= 0:
        mt5.shutdown()
        raise RuntimeError(f"symbol_info_tick failed: {mt5.last_error()}")

    last_time_msc = int(latest.time_msc) - 1
    last_signature_counts: Counter = Counter()
    rolling = deque()
    total_rows = 0
    first_ts: str | None = None
    last_ts: str | None = None

    last_tick_advance_host = time.monotonic()
    continuity_start_msc: int | None = None
    last_replay_host = 0.0
    last_manifest_host = 0.0
    last_print_host = 0.0

    print("==========================================================")
    print(" XAUUSD CANDIDATE D/H/J READ-ONLY LIVE SHADOW")
    print("==========================================================")
    print("NO REAL ORDERS. Raw tick capture + causal rolling replay.")
    print("Session:", session_id)
    print("Output:", session_dir.resolve())
    print("Press Ctrl+C to stop safely.")

    try:
        while True:
            host_now = datetime.now(timezone.utc)
            latest = mt5.symbol_info_tick(args.symbol)
            if latest is None or latest.time_msc <= 0:
                time.sleep(args.poll_sec)
                continue

            broker_now = datetime.fromtimestamp(float(latest.time_msc) / 1000.0, timezone.utc)
            end = broker_now + timedelta(milliseconds=1)
            if last_time_msc > 0:
                start = datetime.fromtimestamp(
                    max(0.0, last_time_msc / 1000.0 - args.fetch_lookback_sec),
                    timezone.utc,
                )
            else:
                start = broker_now - timedelta(seconds=args.fetch_lookback_sec)

            ticks = mt5.copy_ticks_range(args.symbol, start, end, mt5.COPY_TICKS_ALL)
            fetched = structured_ticks_to_rows(ticks)
            new_rows, new_last_msc, new_counts = select_new_rows(
                fetched, last_time_msc, last_signature_counts
            )

            if new_rows:
                cleaned = [public_row(x) for x in new_rows]
                append_rows(ticks_path, cleaned)

                prior_last_msc = last_time_msc
                for row in new_rows:
                    tmsc = int(row["_time_msc"])
                    if continuity_start_msc is None or (
                        prior_last_msc > 0 and tmsc - prior_last_msc > 5000
                    ):
                        continuity_start_msc = tmsc
                    rolling.append(row)
                    prior_last_msc = tmsc

                total_rows += len(new_rows)
                first_ts = first_ts or cleaned[0]["timestamp_utc"]
                last_ts = cleaned[-1]["timestamp_utc"]
                if new_last_msc > last_time_msc:
                    last_tick_advance_host = time.monotonic()
                last_time_msc = new_last_msc
                last_signature_counts = new_counts

            cutoff_msc = last_time_msc - int((args.replay_hours * 3600.0 + 120.0) * 1000.0)
            while rolling and int(rolling[0]["_time_msc"]) < cutoff_msc:
                rolling.popleft()

            idle_for = time.monotonic() - last_tick_advance_host
            market_state = "MARKET_IDLE" if idle_for >= args.idle_sec else "ACTIVE"
            capture_age_sec = (
                (last_time_msc - int(pd.Timestamp(first_ts).timestamp() * 1000)) / 1000.0
                if first_ts and last_time_msc > 0
                else 0.0
            )
            continuity_age_sec = (
                (last_time_msc - continuity_start_msc) / 1000.0
                if continuity_start_msc is not None and last_time_msc > 0
                else 0.0
            )
            warmup_complete = continuity_age_sec >= args.warmup_minutes * 60.0

            now_mono = time.monotonic()
            if (
                new_rows
                and len(rolling) >= 2
                and now_mono - last_replay_host >= args.refresh_sec
            ):
                replay = replay_rolling_rows(
                    rolling,
                    temp_dir=session_dir,
                    context=f"live-shadow:{session_id}",
                )
                latest_ts = last_time_msc / 1000.0
                emitted = emit_events(
                    replay,
                    events_path,
                    seen_events,
                    trusted=warmup_complete,
                    latest_ts=latest_ts,
                    trusted_tail_sec=args.trusted_tail_minutes * 60.0,
                )
                status = {
                    "schema": "xau-live-shadow-status-v1",
                    "session_id": session_id,
                    "host_utc": host_now.isoformat(),
                    "latest_mt5_reported_utc": broker_now.isoformat(),
                    "market_state": market_state,
                    "market_idle_host_seconds": idle_for,
                    "raw_rows_captured": total_rows,
                    "rolling_rows": len(rolling),
                    "capture_age_sec": capture_age_sec,
                    "current_continuity_age_sec": continuity_age_sec,
                    "warmup_complete": warmup_complete,
                    "replay_hours": args.replay_hours,
                    "refresh_sec": args.refresh_sec,
                    "new_events_emitted": emitted,
                    "intervals": {
                        interval: {
                            "D": replay["intervals"][interval]["D"],
                            "H": replay["intervals"][interval]["H"],
                            "J": replay["intervals"][interval]["J"],
                            "shadow_parity": replay["intervals"][interval]["shadow_parity"],
                        }
                        for interval in ("500ms", "1s")
                    },
                    "note": (
                        "Rolling causal paper replay only. Metrics are for the bounded replay "
                        "window, not official Experiment-48 prospective evidence."
                    ),
                }
                atomic_json(status_path, status)
                last_replay_host = now_mono

            if now_mono - last_manifest_host >= args.manifest_sec:
                write_manifest(
                    manifest_path,
                    session_id=session_id,
                    symbol=args.symbol,
                    rows=total_rows,
                    first_ts=first_ts,
                    last_ts=last_ts,
                    host_now=host_now,
                    broker_now=broker_now,
                    market_state=market_state,
                    session_start_host=session_start_host,
                    ticks_path=ticks_path,
                )
                last_manifest_host = now_mono

            if now_mono - last_print_host >= args.print_sec:
                print(
                    f"{host_now.strftime('%H:%M:%S')}Z | {market_state} | "
                    f"captured={total_rows:,} | rolling={len(rolling):,} | "
                    f"idle={idle_for:.1f}s | continuity={continuity_age_sec/60.0:.1f}m | "
                    f"warmup={'YES' if warmup_complete else 'NO'}"
                )
                last_print_host = now_mono

            time.sleep(args.poll_sec)

    except KeyboardInterrupt:
        print("\nStopping read-only shadow...")
    finally:
        try:
            latest = mt5.symbol_info_tick(args.symbol)
            if latest is not None and latest.time_msc > 0:
                broker_now = datetime.fromtimestamp(float(latest.time_msc) / 1000.0, timezone.utc)
            else:
                broker_now = datetime.now(timezone.utc)
            write_manifest(
                manifest_path,
                session_id=session_id,
                symbol=args.symbol,
                rows=total_rows,
                first_ts=first_ts,
                last_ts=last_ts,
                host_now=datetime.now(timezone.utc),
                broker_now=broker_now,
                market_state="STOPPED",
                session_start_host=session_start_host,
                ticks_path=ticks_path,
            )
        finally:
            mt5.shutdown()

    print("Raw ticks:", ticks_path.resolve())
    print("Manifest :", manifest_path.resolve())
    print("Status   :", status_path.resolve())
    print("Events   :", events_path.resolve())


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default=SYMBOL)
    ap.add_argument("--output-root", type=Path, default=ROOT / "data" / "live_shadow")
    ap.add_argument("--session-id")
    ap.add_argument("--poll-sec", type=float, default=0.25)
    ap.add_argument("--fetch-lookback-sec", type=float, default=120.0)
    ap.add_argument("--refresh-sec", type=float, default=15.0)
    ap.add_argument("--replay-hours", type=float, default=4.0)
    ap.add_argument("--warmup-minutes", type=float, default=90.0)
    ap.add_argument("--trusted-tail-minutes", type=float, default=30.0)
    ap.add_argument("--idle-sec", type=float, default=10.0)
    ap.add_argument("--manifest-sec", type=float, default=60.0)
    ap.add_argument("--print-sec", type=float, default=5.0)
    ap.add_argument("--connect-check", action="store_true")
    ap.add_argument("--preflight", type=Path)
    ap.add_argument("--preflight-out", type=Path)
    return ap.parse_args()


def main():
    args = parse_args()

    if args.poll_sec <= 0:
        raise SystemExit("--poll-sec must be > 0")
    if args.refresh_sec <= 0:
        raise SystemExit("--refresh-sec must be > 0")
    if args.replay_hours < 2.0:
        raise SystemExit("--replay-hours must be >= 2 hours")
    if args.preflight:
        payload = run_preflight(args.preflight, args.preflight_out)
        print(json.dumps(payload, indent=2))
        return
    if args.connect_check:
        payload = connect_check(args.symbol)
        print(json.dumps(payload, indent=2))
        return
    live_main(args)


if __name__ == "__main__":
    main()
