"""Experiment 51: Candidate L normalized structural-resumption architecture.

Candidate L is frozen by docs/plans/V4_5_CANDIDATE_L_NORMALIZED_RESUMPTION.md
before this P&L evaluation. It is intentionally NOT a fitted D/J admission score.
It creates an independent trend -> pullback -> resumption opportunity from
scale-normalized canonical geometry and MT5-native raw microstate.

Known datasets are development/rejection evidence only. Final20 remains sealed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_microstate_v1_freeze as microstate
import v4_5_router_v2_full_eval as full_eval
from v4_5_candidate_j_stage1_staged_validation import (
    build_features_all_rows,
    inspect_block,
    make_combined_csv,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OLD = ROOT / "xau_ticks_7d.csv"
DEFAULT_NEW = ROOT / "data" / "raw" / "xau_ticks_7d_current_2026-10-06.csv.gz"
DEFAULT_NEW_MANIFEST = ROOT / "data" / "manifests" / "xau_ticks_7d_2026-09-29_to_2026-10-06.json"
DEFAULT_BLOCKS = ROOT / "data" / "prospective_restored"
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-10-06-v4_5-candidate-l-normalized-resumption"

STOP_USD = 4.0
TP_USD = 12.0
MAX_HOLD_SEC = 1800.0
CONTINUITY_SEC = 1800.0
TREND_DOMINANCE = 0.50
MAX_SPREAD_USD = 0.40
MAX_SPREAD_RANGE60 = 0.20
QACC_MIN = 1.0
M10_SPREAD_MULT = 1.0
M30_SPREAD_MULT = 2.0
FLOW_CHECK_SEC = 5.0
FLOW_CONFIRMATIONS = 2
FLOW_ARM_MFE_USD = 4.0
FLOW_MIN_GIVEBACK_USD = 4.0
RANDOM_SEED = 51051
RANDOM_WINDOWS = 80
RANDOM_HOURS = 4.0
STRESS = (0.0, 0.05, 0.10, 0.20)

CONFIG = {
    "schema": "xau-candidate-l-normalized-resumption-v1",
    "external_data_used": False,
    "model_search": False,
    "threshold_search": False,
    "final20_opened": False,
    "continuity_sec": CONTINUITY_SEC,
    "trend_horizons_sec": [60, 300, 1800],
    "trend_dominance_ratio": TREND_DOMINANCE,
    "pullback_min_magnitude": "one current spread via min/max m10 over prior 30s",
    "resumption_m10_spread_multiple": M10_SPREAD_MULT,
    "resumption_m30_spread_multiple": M30_SPREAD_MULT,
    "qacc_min": QACC_MIN,
    "raw_entry_confirmation": "dir_mid_move2 > 0 AND dir_event_imb2 > 0",
    "max_spread_usd": MAX_SPREAD_USD,
    "max_spread_fraction_range60": MAX_SPREAD_RANGE60,
    "risk_fraction": 0.03,
    "stop_usd": STOP_USD,
    "take_profit_usd": TP_USD,
    "max_hold_sec": MAX_HOLD_SEC,
    "flow_exit": {
        "arm_mfe_usd": FLOW_ARM_MFE_USD,
        "min_giveback_usd": FLOW_MIN_GIVEBACK_USD,
        "check_sec": FLOW_CHECK_SEC,
        "negative_confirmations": FLOW_CONFIRMATIONS,
        "condition": "dir_mid_move2 < 0 AND dir_event_imb2 < 0",
    },
    "reentry_policy": "same still-active pullback window cannot be consumed twice",
}

EXPECTED_HIST_D = {"500ms": 1430.311133793068, "1s": 385.2544619534224}
EXPECTED_HIST_H = {"500ms": 1287.0891, "1s": 360.7936}
EXPECTED_CURRENT = {
    "500ms": {"D": -216.15801063833612, "H": -180.9269930375778},
    "1s": {"D": -229.1744592962699, "H": -194.96479018295344},
}
EXPECTED_BLOCK_POOLED = {
    "500ms": {"D": -165.31701569566403, "H": -97.90961515037145},
    "1s": {"D": -130.26711793884755, "H": -74.45786116462},
}


def write_csv(path: Path, rows: List[Dict]) -> None:
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
        w.writeheader(); w.writerows(rows)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_current(path: Path, manifest_path: Path) -> Dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = str(manifest["archive"]["sha256"]).lower()
    actual = sha256_file(path).lower()
    if actual != expected:
        raise RuntimeError(f"current7d archive SHA mismatch: {actual} != {expected}")
    return manifest


def session_start_times(arr: Dict[str, np.ndarray]) -> np.ndarray:
    t = np.asarray(arr["t"], float)
    ss = np.asarray(arr["ss"])
    idx = np.arange(len(t), dtype=np.int64)
    change = np.r_[True, ss[1:] != ss[:-1]]
    first = np.maximum.accumulate(np.where(change, idx, 0))
    return t[first]


def finite_ratio(a: float, b: float) -> float:
    return float(a / b) if math.isfinite(a) and math.isfinite(b) and abs(b) > 1e-12 else math.nan


def structural_side(arr: Dict[str, np.ndarray], i: int, session_starts: np.ndarray) -> int:
    ts = float(arr["t"][i])
    if ts - float(session_starts[i]) < CONTINUITY_SEC:
        return 0
    m60 = float(arr["m60"][i]); m300 = float(arr["m300"][i]); m1800 = float(arr["m1800"][i])
    r60 = float(arr["range60"][i]); r300 = float(arr["range300"][i])
    if not all(math.isfinite(x) for x in (m60, m300, m1800, r60, r300)) or r60 <= 0 or r300 <= 0:
        return 0
    if m60 > 0 and m300 > 0 and m1800 > 0:
        side = 1
    elif m60 < 0 and m300 < 0 and m1800 < 0:
        side = -1
    else:
        return 0
    if abs(m60) / r60 < TREND_DOMINANCE or abs(m300) / r300 < TREND_DOMINANCE:
        return 0
    return side


def pullback_active(arr: Dict[str, np.ndarray], i: int, side: int) -> bool:
    spread = float(arr["spread"][i])
    if not math.isfinite(spread) or spread <= 0:
        return False
    if side == 1:
        v = float(arr["min_m10_30"][i])
        return math.isfinite(v) and v <= -spread
    v = float(arr["max_m10_30"][i])
    return math.isfinite(v) and v >= spread


def execution_ok(arr: Dict[str, np.ndarray], i: int) -> bool:
    spread = float(arr["spread"][i]); r60 = float(arr["range60"][i])
    return (
        math.isfinite(spread) and math.isfinite(r60) and spread > 0 and r60 > 0
        and spread <= MAX_SPREAD_USD
        and spread <= MAX_SPREAD_RANGE60 * r60
    )


def resumption_ok(
    arr: Dict[str, np.ndarray], i: int, side: int,
    raw: Dict[str, np.ndarray], cache: Dict[Tuple[float, int], Dict[str, float]],
) -> Tuple[bool, Dict[str, float]]:
    spread = float(arr["spread"][i]); m10 = float(arr["m10"][i]); m30 = float(arr["m30"][i]); qacc = float(arr["qacc"][i])
    if not all(math.isfinite(x) for x in (spread, m10, m30, qacc)):
        return False, {}
    if side * m10 < M10_SPREAD_MULT * spread or side * m30 < M30_SPREAD_MULT * spread or qacc < QACC_MIN:
        return False, {}
    ts = float(arr["t"][i]); key = (ts, int(side))
    feat = cache.get(key)
    if feat is None:
        feat = microstate.features_at(raw, ts, int(side)); cache[key] = feat
    dm = float(feat.get("dir_mid_move2", math.nan)); di = float(feat.get("dir_event_imb2", math.nan))
    ok = math.isfinite(dm) and math.isfinite(di) and dm > 0.0 and di > 0.0
    return ok, feat


def compact(m: Dict) -> Dict:
    keys = (
        "pnl_inr", "terminal_unrealized_inr", "terminal_equity_pnl_inr",
        "open_position_at_end", "profit_factor", "trades", "wins", "win_rate",
        "max_drawdown_inr", "entries", "flow_exits", "trend_failure_exits",
        "stop_exits", "tp_exits", "time_exits", "trend_state_samples",
        "pullback_samples", "execution_pass_samples", "resumption_pass_samples",
    )
    return {k: m[k] for k in keys if k in m}


def simulate_l(
    arr: Dict[str, np.ndarray], start: int, end: int, *,
    raw: Dict[str, np.ndarray], cache: Dict[Tuple[float, int], Dict[str, float]],
    extra_slippage_usd_per_side: float = 0.0,
    capture_trades: bool = False,
    context: str = "",
) -> Dict:
    t = np.asarray(arr["t"], float); bid = np.asarray(arr["bid"], float); ask = np.asarray(arr["ask"], float)
    session_starts = session_start_times(arr)
    slip = float(extra_slippage_usd_per_side)

    bal = canonical.START_BALANCE_INR
    gp = gl = 0.0
    peakbal = bal; maxdd = 0.0
    ntr = wins = 0
    pos = 0; side = 0
    entry = oz = ptime = peak = 0.0
    next_check = math.inf; neg_conf = 0
    consumed_pullback = False
    previous_structural_side = 0

    entries = flow_exits = trend_failure_exits = stop_exits = tp_exits = time_exits = 0
    trend_state_samples = pullback_samples = execution_pass_samples = resumption_pass_samples = 0
    trade_rows: List[Dict] = []

    for i in range(start, end):
        ts = float(t[i])

        if pos:
            exit_px = (bid[i] - slip) if side == 1 else (ask[i] + slip)
            move = float((exit_px - entry) if side == 1 else (entry - exit_px))
            held = ts - ptime
            peak = max(peak, move)
            reason = 0
            if move <= -STOP_USD:
                reason = 1; stop_exits += 1
            elif move >= TP_USD:
                reason = 2; tp_exits += 1

            if reason == 0 and ts >= next_check:
                while next_check <= ts:
                    next_check += FLOW_CHECK_SEC
                armed = peak >= FLOW_ARM_MFE_USD and (peak - move) >= FLOW_MIN_GIVEBACK_USD
                if armed:
                    bad, _ = hbase.decay_state(raw, ts, side, cache)
                    neg_conf = neg_conf + 1 if bad else 0
                else:
                    neg_conf = 0
                if neg_conf >= FLOW_CONFIRMATIONS:
                    reason = 8; flow_exits += 1

            if reason == 0:
                m300 = float(arr["m300"][i])
                if math.isfinite(m300) and side * m300 <= 0:
                    reason = 5; trend_failure_exits += 1
            if reason == 0 and held >= MAX_HOLD_SEC:
                reason = 7; time_exits += 1

            if reason:
                pnl = move * oz * canonical.INR_PER_USD
                bal += pnl; ntr += 1
                if pnl > 0:
                    gp += pnl; wins += 1
                elif pnl < 0:
                    gl -= pnl
                peakbal = max(peakbal, bal); maxdd = max(maxdd, peakbal - bal)
                if capture_trades:
                    trade_rows.append({
                        "context": context, "entry_ts": ptime, "exit_ts": ts,
                        "side": "BUY" if side == 1 else "SELL",
                        "entry_price": entry, "exit_move_usd": move, "mfe_usd": peak,
                        "held_sec": held, "pnl_inr": pnl, "exit_reason": reason,
                    })
                pos = 0; side = 0; neg_conf = 0; next_check = math.inf
            continue

        s = structural_side(arr, i, session_starts)
        if s != previous_structural_side:
            consumed_pullback = False
            previous_structural_side = s
        if s == 0:
            continue
        trend_state_samples += 1

        pb = pullback_active(arr, i, s)
        if not pb:
            consumed_pullback = False
            continue
        pullback_samples += 1
        if consumed_pullback:
            continue

        if not execution_ok(arr, i):
            continue
        execution_pass_samples += 1

        ok, _ = resumption_ok(arr, i, s, raw, cache)
        if not ok:
            continue
        resumption_pass_samples += 1

        px = float((ask[i] + slip) if s == 1 else (bid[i] - slip))
        oz_new = min(
            bal * 0.03 / (STOP_USD * canonical.INR_PER_USD),
            (bal / canonical.INR_PER_USD * 100.0) / px,
        )
        if not math.isfinite(oz_new) or oz_new <= 0:
            continue
        pos = 1; side = s; entry = px; oz = oz_new; ptime = ts; peak = 0.0
        next_check = ts + FLOW_CHECK_SEC; neg_conf = 0
        consumed_pullback = True; entries += 1

    pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
    terminal_unrealized = 0.0
    if pos and end > start:
        j = end - 1
        px = float((bid[j] - slip) if side == 1 else (ask[j] + slip))
        move = float((px - entry) if side == 1 else (entry - px))
        terminal_unrealized = move * oz * canonical.INR_PER_USD

    return {
        "pnl_inr": float(bal - canonical.START_BALANCE_INR),
        "terminal_unrealized_inr": float(terminal_unrealized),
        "terminal_equity_pnl_inr": float(bal - canonical.START_BALANCE_INR + terminal_unrealized),
        "open_position_at_end": bool(pos),
        "profit_factor": float(pf),
        "trades": int(ntr), "wins": int(wins), "win_rate": float(wins / ntr) if ntr else 0.0,
        "max_drawdown_inr": float(maxdd),
        "entries": int(entries), "flow_exits": int(flow_exits), "trend_failure_exits": int(trend_failure_exits),
        "stop_exits": int(stop_exits), "tp_exits": int(tp_exits), "time_exits": int(time_exits),
        "trend_state_samples": int(trend_state_samples), "pullback_samples": int(pullback_samples),
        "execution_pass_samples": int(execution_pass_samples), "resumption_pass_samples": int(resumption_pass_samples),
        "trade_rows": trade_rows if capture_trades else None,
    }


def compounded(rows: List[Dict]) -> Dict:
    factor = 1.0; trades = wins = 0; dds: List[float] = []
    counters = {k: 0 for k in ("entries","flow_exits","trend_failure_exits","stop_exits","tp_exits","time_exits")}
    for m in rows:
        factor *= 1.0 + float(m["pnl_inr"]) / canonical.START_BALANCE_INR
        trades += int(m["trades"]); wins += int(m["wins"]); dds.append(float(m["max_drawdown_inr"]))
        for k in counters: counters[k] += int(m.get(k, 0))
    return {
        "compounded_pnl_inr": float(canonical.START_BALANCE_INR * (factor - 1.0)),
        "trades": trades, "wins": wins, "win_rate": wins / trades if trades else 0.0,
        "max_segment_drawdown_inr": max(dds) if dds else 0.0,
        **counters,
    }


def random_summary(rows: List[Dict], key: str) -> Dict:
    x = np.asarray([float(r[key]) for r in rows], float)
    return {
        "windows": int(len(x)), "mean_pnl_inr": float(np.mean(x)), "median_pnl_inr": float(np.median(x)),
        "p05_pnl_inr": float(np.quantile(x, 0.05)), "p95_pnl_inr": float(np.quantile(x, 0.95)),
        "positive_fraction": float(np.mean(x > 0)),
    }


def assert_close(actual: float, expected: float, label: str, tol: float = 1e-3) -> None:
    if abs(float(actual) - float(expected)) > tol:
        raise RuntimeError(f"{label} parity drift: {actual} != {expected}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--historical", type=Path, default=DEFAULT_OLD)
    ap.add_argument("--current", type=Path, default=DEFAULT_NEW)
    ap.add_argument("--current-manifest", type=Path, default=DEFAULT_NEW_MANIFEST)
    ap.add_argument("--prospective-root", type=Path, default=DEFAULT_BLOCKS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)

    canonical.verify_dataset(a.historical)
    new_manifest = verify_current(a.current, a.current_manifest)
    (a.output / "candidate_l_config.json").write_text(json.dumps(CONFIG, indent=2) + "\n", encoding="utf-8")

    result = {
        "schema": "xau-v4-5-candidate-l-eval-v1",
        "config": CONFIG,
        "status": "known-data development/rejection evaluation",
        "current_dataset_id": new_manifest["dataset_id"],
        "final20_opened": False,
        "external_data_used": False,
        "intervals": {},
    }
    block_rows: List[Dict] = []; random_rows: List[Dict] = []; stress_rows: List[Dict] = []; trade_rows: List[Dict] = []

    for interval in ("500ms", "1s"):
        print(f"{interval}: build historical", flush=True)
        h_arr, h_bounds = canonical.build_features(a.historical, interval)
        v44 = canonical.run_strategy(h_arr, h_bounds, "v4_4")
        canonical.assert_baseline(v44, interval, canonical.DEFAULT_GOLDEN)
        h_ranges = autopsy.indices(h_arr, h_bounds)
        h_raw = microstate.load_raw(a.historical, nrows=canonical.RESEARCH_ROWS)
        h_cache: Dict[Tuple[float, int], Dict[str, float]] = {}

        dseg = [hbase.simulate(h_arr,s,e,candidate_h=False) for s,e in h_ranges]
        hseg = [hbase.simulate(h_arr,s,e,candidate_h=True,raw=h_raw,feature_cache=h_cache) for s,e in h_ranges]
        lseg = [simulate_l(h_arr,s,e,raw=h_raw,cache=h_cache,capture_trades=True,context=f"historical:{interval}:seg{sid}") for sid,(s,e) in enumerate(h_ranges)]
        for m in lseg: trade_rows.extend(m.get("trade_rows") or [])
        ds = hbase.summarize(dseg); hs = hbase.summarize(hseg); ls = compounded(lseg)
        assert_close(ds["compounded_pnl_inr"], EXPECTED_HIST_D[interval], f"historical D {interval}", 1e-6)
        assert_close(hs["compounded_pnl_inr"], EXPECTED_HIST_H[interval], f"historical H {interval}", 0.02)

        print(f"{interval}: build current7d", flush=True)
        c_arr = build_features_all_rows(a.current, interval)
        c_raw = microstate.load_raw(a.current)
        c_cache: Dict[Tuple[float, int], Dict[str, float]] = {}
        cd = hbase.simulate(c_arr,0,len(c_arr["t"]),candidate_h=False)
        ch = hbase.simulate(c_arr,0,len(c_arr["t"]),candidate_h=True,raw=c_raw,feature_cache=c_cache)
        cl = simulate_l(c_arr,0,len(c_arr["t"]),raw=c_raw,cache=c_cache,capture_trades=True,context=f"current7d:{interval}")
        trade_rows.extend(cl.get("trade_rows") or [])
        assert_close(cd["terminal_equity_pnl_inr"], EXPECTED_CURRENT[interval]["D"], f"current D {interval}", 1e-6)
        assert_close(ch["terminal_equity_pnl_inr"], EXPECTED_CURRENT[interval]["H"], f"current H {interval}", 1e-6)

        print(f"{interval}: six Stage-1 development blocks", flush=True)
        br: List[Dict] = []
        with tempfile.TemporaryDirectory(prefix="candidate-l-") as td:
            temp = Path(td)
            for session_dir in sorted(p for p in a.prospective_root.iterdir() if p.is_dir() and (p/"block_manifest.json").exists()):
                block = inspect_block(session_dir)
                combined = make_combined_csv(block, temp)
                arr = build_features_all_rows(combined, interval)
                raw = microstate.load_raw(combined); cache: Dict[Tuple[float, int], Dict[str, float]] = {}
                s = int(np.searchsorted(arr["t"], block["start"].timestamp(), side="left"))
                e = int(np.searchsorted(arr["t"], block["end"].timestamp(), side="right"))
                dm = hbase.simulate(arr,s,e,candidate_h=False)
                hm = hbase.simulate(arr,s,e,candidate_h=True,raw=raw,feature_cache=cache)
                lm = simulate_l(arr,s,e,raw=raw,cache=cache,capture_trades=True,context=f"block:{session_dir.name}:{interval}")
                trade_rows.extend(lm.get("trade_rows") or [])
                row = {"session": session_dir.name, "interval": interval}
                for label,m in (("D",dm),("H",hm),("L",lm)):
                    row[f"{label}_pnl"] = float(m["terminal_equity_pnl_inr"]); row[f"{label}_trades"] = int(m["trades"]); row[f"{label}_wins"] = int(m["wins"])
                br.append(row); block_rows.append(row)
        pooled = {label: float(sum(r[f"{label}_pnl"] for r in br)) for label in ("D","H","L")}
        assert_close(pooled["D"], EXPECTED_BLOCK_POOLED[interval]["D"], f"blocks D {interval}", 1e-6)
        assert_close(pooled["H"], EXPECTED_BLOCK_POOLED[interval]["H"], f"blocks H {interval}", 1e-6)

        print(f"{interval}: deterministic real 4h windows", flush=True)
        rng = np.random.default_rng(RANDOM_SEED + (0 if interval == "500ms" else 1))
        hranges = full_eval.continuous_ranges(h_arr, h_ranges)
        cranges = full_eval.continuous_ranges(c_arr, [(0,len(c_arr["t"]))])
        rr: List[Dict] = []
        for wid in range(RANDOM_WINDOWS):
            if wid % 2 == 0:
                source="historical"; arr=h_arr; ranges=hranges; raw=h_raw; cache=h_cache
            else:
                source="current7d"; arr=c_arr; ranges=cranges; raw=c_raw; cache=c_cache
            s,e,rid = full_eval.random_window_from_ranges(arr,ranges,rng,RANDOM_HOURS)
            dm = hbase.simulate(arr,s,e,candidate_h=False)
            hm = hbase.simulate(arr,s,e,candidate_h=True,raw=raw,feature_cache=cache)
            lm = simulate_l(arr,s,e,raw=raw,cache=cache)
            row = {
                "interval": interval, "window_id": wid, "source": source, "range_id": rid,
                "start_ts": float(arr["t"][s]), "end_ts": float(arr["t"][e-1]),
                "D_pnl": float(dm["terminal_equity_pnl_inr"]), "H_pnl": float(hm["terminal_equity_pnl_inr"]), "L_pnl": float(lm["terminal_equity_pnl_inr"]),
                "D_trades": int(dm["trades"]), "H_trades": int(hm["trades"]), "L_trades": int(lm["trades"]),
            }
            rr.append(row); random_rows.append(row)
        random_stats = {label: random_summary(rr,f"{label}_pnl") for label in ("D","H","L")}

        print(f"{interval}: cost stress", flush=True)
        stresses = {}
        for slip in STRESS:
            dcur = hbase.simulate(c_arr,0,len(c_arr["t"]),candidate_h=False,extra_slippage_usd_per_side=slip)
            hcur = hbase.simulate(c_arr,0,len(c_arr["t"]),candidate_h=True,raw=c_raw,feature_cache=c_cache,extra_slippage_usd_per_side=slip)
            lcur = simulate_l(c_arr,0,len(c_arr["t"]),raw=c_raw,cache=c_cache,extra_slippage_usd_per_side=slip)
            lhist = [simulate_l(h_arr,s,e,raw=h_raw,cache=h_cache,extra_slippage_usd_per_side=slip) for s,e in h_ranges]
            lhs = compounded(lhist)
            sr = {
                "interval": interval, "slip": slip,
                "D_current_pnl": float(dcur["terminal_equity_pnl_inr"]), "H_current_pnl": float(hcur["terminal_equity_pnl_inr"]), "L_current_pnl": float(lcur["terminal_equity_pnl_inr"]),
                "L_historical_compounded_pnl": float(lhs["compounded_pnl_inr"]),
                "L_current_trades": int(lcur["trades"]), "L_historical_trades": int(lhs["trades"]),
            }
            stress_rows.append(sr); stresses[str(slip)] = sr

        gates = {
            "historical_positive": ls["compounded_pnl_inr"] > 0,
            "current_positive": cl["terminal_equity_pnl_inr"] > 0,
            "random_mean_positive": random_stats["L"]["mean_pnl_inr"] > 0,
            "historical_trades_ge_20": ls["trades"] >= 20,
            "current_trades_ge_20": cl["trades"] >= 20,
            "current_plus_0_10_slip_positive": stresses["0.1"]["L_current_pnl"] > 0,
            "comparator_parity": True,
        }
        result["intervals"][interval] = {
            "historical_first80": {"D": ds, "H": hs, "L": ls},
            "current7d": {"D": hbase.compact(cd), "H": hbase.compact(ch), "L": compact(cl)},
            "stage1_blocks": {"pooled_pnl": pooled, "positive_L_blocks": int(sum(r["L_pnl"] > 0 for r in br)), "blocks": len(br)},
            "random_real_4h": random_stats,
            "cost_stress": stresses,
            "development_survival_gates": gates,
        }

    all_gates = [v for item in result["intervals"].values() for v in item["development_survival_gates"].values()]
    result["development_survival_pass"] = bool(all(all_gates))
    result["decision"] = (
        "PASS development-survival screen; Candidate L may be frozen unchanged for a brand-new prospective validation."
        if result["development_survival_pass"] else
        "FAIL development-survival screen; reject frozen Candidate L unchanged. Do not tune its numeric boundaries against these known outcomes."
    )

    write_csv(a.output / "stage1_block_comparison.csv", block_rows)
    write_csv(a.output / "random_real_4h_windows.csv", random_rows)
    write_csv(a.output / "cost_stress.csv", stress_rows)
    write_csv(a.output / "candidate_l_trades.csv", trade_rows)
    (a.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
