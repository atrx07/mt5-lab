"""Experiment 43: Candidate H flow-confirmed path-preserving PRIMARY exit.

Candidate H keeps Candidate D entries and Candidate G ghost occupancy. The real
PRIMARY may bank profit only after:
  * live MFE >= +1R ($4),
  * giveback from live MFE >= 1R,
  * two consecutive 5-second checks where both direction-normalized raw
    2-second mid movement and raw 2-second event imbalance oppose the trade.

No threshold search. SECONDARY/MICRO/BURST are unchanged. A capital-free ghost
preserves Candidate-D occupancy and PRIMARY cooldown timing after a real exit.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_candidate_g_ghost_ratchet as gbase
import v4_5_microstate_v1_freeze as microstate
import v4_5_regime_portability as portability
import v4_5_router_v2 as router
import v4_5_router_v2_full_eval as full_eval

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-09-26-v4_5-candidate-h-flow-confirmed-ghost-exit"

TRIGGER_MFE_USD = 4.0
MIN_GIVEBACK_USD = 4.0
CHECK_SEC = 5.0
NEGATIVE_CONFIRMATIONS = 2
RANDOM_SEED = gbase.RANDOM_SEED
RANDOM_WINDOWS = gbase.RANDOM_WINDOWS
RANDOM_HOURS = gbase.RANDOM_HOURS
SLIPPAGE_STRESS_USD_PER_SIDE = gbase.SLIPPAGE_STRESS_USD_PER_SIDE

CONFIG = {
    "schema": "xau-candidate-h-flow-confirmed-ghost-exit-v1",
    "base_strategy": "Candidate D from Experiment 19",
    "entry_changed": False,
    "changed_exit_engine": "PRIMARY only",
    "trigger_mfe_usd": TRIGGER_MFE_USD,
    "min_giveback_usd": MIN_GIVEBACK_USD,
    "check_sec": CHECK_SEC,
    "negative_confirmations": NEGATIVE_CONFIRMATIONS,
    "decay_condition": "dir_mid_move2 < 0 AND dir_event_imb2 < 0",
    "post_real_exit_slot_policy": "capital-free ghost preserves Candidate-D occupancy until legacy exit",
    "primary_cooldown_anchor": "ghost legacy-exit timestamp",
    "same_entry_path_required": True,
    "threshold_search": False,
    "known_data_promotion_allowed": False,
    "final20_opened": False,
}


def write_csv(path: Path, rows: List[Dict]):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: List[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def decay_state(raw, ts: float, side: int, cache: Dict[Tuple[float, int], Dict[str, float]]):
    key = (float(ts), int(side))
    feat = cache.get(key)
    if feat is None:
        feat = microstate.features_at(raw, float(ts), int(side))
        cache[key] = feat
    dm = float(feat.get("dir_mid_move2", math.nan))
    di = float(feat.get("dir_event_imb2", math.nan))
    bad = math.isfinite(dm) and math.isfinite(di) and dm < 0.0 and di < 0.0
    return bad, feat


def simulate(
    arr: Dict[str, np.ndarray],
    start: int,
    end: int,
    *,
    candidate_h: bool,
    raw: Dict[str, np.ndarray] | None = None,
    feature_cache: Dict[Tuple[float, int], Dict[str, float]] | None = None,
    extra_slippage_usd_per_side: float = 0.0,
    exit_events: List[Dict] | None = None,
    ghost_events: List[Dict] | None = None,
    context: str = "",
    capture_trace: bool = False,
):
    t, bid, ask = arr["t"], arr["bid"], arr["ask"]
    m30, m300 = arr["m30"], arr["m300"]
    r300, er60 = arr["range300"], arr["er60"]
    cfg = canonical.burst_config("v4_5_b")
    slip = float(extra_slippage_usd_per_side)

    bal = 500.0
    gp = gl = 0.0
    ntr = wins = 0
    peakbal = 500.0
    maxdd = 0.0

    pos = 0
    side = 0
    entry = oz = ptime = peak = 0.0
    partial = 0.0
    partial_done = 0
    highopen = 0
    failure_since = -1e30
    next_check = math.inf
    decay_confirm = 0

    ghost_active = False
    ghost_side = 0
    ghost_entry = ghost_ptime = 0.0
    ghost_highopen = 0
    ghost_origin_exit_ts = 0.0

    last = {1: -1e30, 2: -1e30, 3: -1e30, 4: -1e30}
    prev_ss = None
    cont = 0.0
    primary_entries = 0
    h_exits = 0
    ghost_releases = 0
    trace: List[Tuple[float, int, int]] = []

    if candidate_h and (raw is None or feature_cache is None):
        raise RuntimeError("Candidate H requires raw microstate source and cache")

    for i in range(start, end):
        ts = float(t[i])
        if prev_ss is None or arr["ss"][i] != prev_ss:
            cont = ts
            prev_ss = arr["ss"][i]

        if ghost_active:
            px = (bid[i] - slip) if ghost_side == 1 else (ask[i] + slip)
            move = float((px - ghost_entry) if ghost_side == 1 else (ghost_entry - px))
            held = ts - ghost_ptime
            reason = gbase.primary_legacy_reason(
                move=move,
                held=held,
                highopen=ghost_highopen,
                side=ghost_side,
                m300_value=float(m300[i]),
            )
            if reason:
                ghost_active = False
                ghost_releases += 1
                last[1] = ts
                if ghost_events is not None:
                    ghost_events.append({
                        "context": context,
                        "real_exit_ts": float(ghost_origin_exit_ts),
                        "legacy_release_ts": ts,
                        "ghost_duration_sec": float(ts - ghost_origin_exit_ts),
                        "side": "BUY" if ghost_side == 1 else "SELL",
                        "legacy_exit_reason": int(reason),
                        "legacy_exit_move_usd": move,
                    })
            continue

        if pos:
            exit_px = (bid[i] - slip) if side == 1 else (ask[i] + slip)
            move = float((exit_px - entry) if side == 1 else (entry - exit_px))
            held = ts - ptime
            peak = max(peak, move)

            if pos == 3 and partial_done == 0 and move >= 5.5:
                closeoz = oz * 0.75
                part = move * closeoz * canonical.INR_PER_USD
                bal += part
                partial += part
                oz -= closeoz
                partial_done = 1

            reason = 0
            rev = 1
            trig = -1.0
            gb = 0.0
            tp = 12.0
            maxhold = 900.0

            if pos == 3:
                tp = 10.0
                trig = 4.0
                gb = 2.0
            elif pos == 4:
                tp = cfg[11]
                maxhold = cfg[12]
                trig = cfg[15]
                gb = cfg[16]
                rev = 0
            elif pos == 1 and highopen == 1:
                tp = 25.0
                maxhold = 900.0
                rev = 0
            elif pos == 2 and highopen == 1:
                tp = 8.0
                maxhold = 1200.0
                rev = 0
                trig = 12.0
                gb = 3.0
            elif pos == 1:
                tp = 21.0
                maxhold = 1800.0

            if move <= -4.0:
                reason = 1
            elif move >= tp:
                reason = 2
            if reason == 0 and trig > 0 and peak >= trig and move <= peak - gb:
                reason = 3
            if reason == 0 and pos == 3 and held >= 45.0 and peak < 0.75:
                reason = 4
            if reason == 0 and pos == 4 and held >= cfg[13] and peak < cfg[14]:
                reason = 4

            if pos == 4 and not np.isfinite(m30[i]):
                failure_since = -1e30
            if reason == 0 and pos == 4 and np.isfinite(m30[i]):
                failure = (side == 1 and m30[i] <= 0) or (side == -1 and m30[i] >= 0)
                if failure:
                    if failure_since < -1e20:
                        failure_since = ts
                    if ts - failure_since >= 1.0:
                        reason = 5
                else:
                    failure_since = -1e30

            h_fired = False
            decay_feat = None
            if reason == 0 and candidate_h and pos == 1 and ts >= next_check:
                while next_check <= ts:
                    next_check += CHECK_SEC
                armed = peak >= TRIGGER_MFE_USD and (peak - move) >= MIN_GIVEBACK_USD
                if armed:
                    bad, decay_feat = decay_state(raw, ts, side, feature_cache)
                    decay_confirm = decay_confirm + 1 if bad else 0
                else:
                    decay_confirm = 0
                if decay_confirm >= NEGATIVE_CONFIRMATIONS:
                    reason = 8
                    h_fired = True

            legacy_same_tick = 0
            if h_fired:
                legacy_same_tick = gbase.primary_legacy_reason(
                    move=move,
                    held=held,
                    highopen=highopen,
                    side=side,
                    m300_value=float(m300[i]),
                )
            elif reason == 0 and rev == 1 and np.isfinite(m300[i]):
                if (side == 1 and m300[i] <= 0) or (side == -1 and m300[i] >= 0):
                    reason = 5
            if reason == 0 and held >= maxhold:
                reason = 7

            if reason:
                closing_pos = pos
                closing_side = side
                closing_entry = entry
                closing_ptime = ptime
                closing_highopen = highopen
                closing_peak = peak

                pnl = move * oz * canonical.INR_PER_USD
                total = pnl + partial
                bal += pnl
                ntr += 1
                if total > 0:
                    gp += total
                    wins += 1
                elif total < 0:
                    gl -= total
                peakbal = max(peakbal, bal)
                maxdd = max(maxdd, peakbal - bal)

                if reason == 8:
                    h_exits += 1
                    if exit_events is not None:
                        feat = decay_feat or {}
                        exit_events.append({
                            "context": context,
                            "entry_ts": float(closing_ptime),
                            "exit_ts": ts,
                            "side": "BUY" if closing_side == 1 else "SELL",
                            "held_sec": float(held),
                            "mfe_usd": float(closing_peak),
                            "exit_move_usd": float(move),
                            "giveback_usd": float(closing_peak - move),
                            "retained_fraction": float(move / closing_peak) if closing_peak > 0 else math.nan,
                            "dir_mid_move2": feat.get("dir_mid_move2", math.nan),
                            "dir_event_imb2": feat.get("dir_event_imb2", math.nan),
                            "dir_mid_move10": feat.get("dir_mid_move10", math.nan),
                            "dir_event_imb10": feat.get("dir_event_imb10", math.nan),
                            "decay_confirmations": int(decay_confirm),
                            "trade_pnl_inr": float(total),
                            "legacy_same_tick_exit": bool(legacy_same_tick),
                        })
                    if legacy_same_tick:
                        last[1] = ts
                    else:
                        ghost_active = True
                        ghost_side = closing_side
                        ghost_entry = closing_entry
                        ghost_ptime = closing_ptime
                        ghost_highopen = closing_highopen
                        ghost_origin_exit_ts = ts
                else:
                    last[closing_pos] = ts

                pos = 0
                decay_confirm = 0
            continue

        candidates = router.signal_candidates(arr, i, cont, last)
        if not candidates:
            continue
        engine, sside = candidates[0]
        high = bool(
            np.isfinite(r300[i]) and np.isfinite(er60[i])
            and r300[i] >= 5.0 and er60[i] >= 0.03
        )
        entry = float((ask[i] + slip) if sside == 1 else (bid[i] - slip))
        oz = min(
            bal * 0.03 / (4 * canonical.INR_PER_USD),
            (bal / canonical.INR_PER_USD * 100) / entry,
        )
        pos = engine
        side = sside
        ptime = ts
        peak = 0.0
        partial = 0.0
        partial_done = 0
        highopen = 1 if high else 0
        failure_since = -1e30
        decay_confirm = 0
        next_check = ts + CHECK_SEC if candidate_h and engine == 1 else math.inf
        if engine == 1:
            primary_entries += 1
        if capture_trace:
            trace.append((ts, int(engine), int(sside)))

    pf = gp / gl if gl > 0 else 999.0
    terminal_unrealized = 0.0
    if pos and end > start:
        j = end - 1
        px = (bid[j] - slip) if side == 1 else (ask[j] + slip)
        mv = float((px - entry) if side == 1 else (entry - px))
        terminal_unrealized = mv * oz * canonical.INR_PER_USD

    return {
        "pnl_inr": bal - 500.0,
        "terminal_unrealized_inr": terminal_unrealized,
        "terminal_equity_pnl_inr": bal - 500.0 + terminal_unrealized,
        "open_position_at_end": bool(pos),
        "ghost_active_at_end": bool(ghost_active),
        "profit_factor": pf,
        "trades": ntr,
        "wins": wins,
        "win_rate": wins / ntr if ntr else 0.0,
        "max_drawdown_inr": maxdd,
        "primary_entries": primary_entries,
        "primary_flow_exits": h_exits,
        "ghost_releases": ghost_releases,
        "entry_trace": trace if capture_trace else None,
    }


def compact(m: Dict) -> Dict:
    return {k: m[k] for k in (
        "pnl_inr", "terminal_unrealized_inr", "terminal_equity_pnl_inr",
        "open_position_at_end", "ghost_active_at_end", "profit_factor",
        "trades", "wins", "win_rate", "max_drawdown_inr",
        "primary_entries", "primary_flow_exits", "ghost_releases"
    )}


def summarize(rows: List[Dict]) -> Dict:
    factor = 1.0
    trades = wins = entries = exits = ghosts = 0
    dds = []
    for m in rows:
        factor *= 1.0 + m["pnl_inr"] / canonical.START_BALANCE_INR
        trades += int(m["trades"]); wins += int(m["wins"])
        entries += int(m["primary_entries"]); exits += int(m["primary_flow_exits"])
        ghosts += int(m["ghost_releases"]); dds.append(float(m["max_drawdown_inr"]))
    return {
        "compounded_pnl_inr": canonical.START_BALANCE_INR * (factor - 1.0),
        "trades": trades, "wins": wins,
        "win_rate": wins / trades if trades else 0.0,
        "max_segment_drawdown_inr": max(dds) if dds else 0.0,
        "primary_entries": entries, "primary_flow_exits": exits,
        "ghost_releases": ghosts,
    }


def random_summary(rows: List[Dict], prefix: str) -> Dict:
    pnl = np.asarray([r[f"{prefix}_pnl"] for r in rows], float)
    tr = np.asarray([r[f"{prefix}_trades"] for r in rows], float)
    wi = np.asarray([r[f"{prefix}_wins"] for r in rows], float)
    return {
        "windows": len(rows),
        "median_terminal_equity_pnl_inr": float(np.median(pnl)),
        "mean_terminal_equity_pnl_inr": float(np.mean(pnl)),
        "p05_terminal_equity_pnl_inr": float(np.quantile(pnl, 0.05)),
        "p95_terminal_equity_pnl_inr": float(np.quantile(pnl, 0.95)),
        "positive_window_fraction": float(np.mean(pnl > 0)),
        "total_trades": int(tr.sum()), "total_wins": int(wi.sum()),
        "aggregate_win_rate": float(wi.sum() / tr.sum()) if tr.sum() else 0.0,
    }


def assert_d(summary: Dict, interval: str):
    exp = gbase.fbase.EXPECTED_D[interval]
    if abs(summary["compounded_pnl_inr"] - exp["pnl"]) > 1e-6:
        raise RuntimeError(f"Candidate D parity drift {interval}: {summary}")
    if summary["trades"] != exp["trades"] or summary["wins"] != exp["wins"]:
        raise RuntimeError(f"Candidate D count drift {interval}: {summary}")


def assert_recent_d(m: Dict, interval: str):
    exp = gbase.fbase.EXPECTED_RECENT_D[interval]
    if abs(m["terminal_equity_pnl_inr"] - exp["pnl"]) > 1e-6:
        raise RuntimeError(f"Recent D parity drift {interval}: {m}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("canonical_csv", type=Path)
    ap.add_argument("recent_csv_or_gz", type=Path)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True, exist_ok=True)
    (a.output / "candidate_h_config.json").write_text(json.dumps(CONFIG, indent=2) + "\n", encoding="utf-8")

    hraw = microstate.load_raw(a.canonical_csv, nrows=canonical.RESEARCH_ROWS)
    rraw = microstate.load_raw(a.recent_csv_or_gz)
    hcache: Dict[Tuple[float, int], Dict[str, float]] = {}
    rcache: Dict[Tuple[float, int], Dict[str, float]] = {}

    result = {
        "schema": "xau-candidate-h-flow-confirmed-ghost-exit-eval-v1",
        "candidate_config": CONFIG,
        "known_data_promotion_allowed": False,
        "final20_opened": False,
        "random_window_method": "40 deterministic contiguous four-hour windows per grid alternating known historical-first80 and recent24h sources",
        "slippage_stress_usd_per_side": list(SLIPPAGE_STRESS_USD_PER_SIDE),
        "intervals": {},
    }
    segrows=[]; splitrows=[]; random_all=[]; stressrows=[]; exits=[]; ghosts=[]; pathrows=[]

    for interval in ("500ms","1s"):
        h_arr, h_bounds = canonical.build_features(a.canonical_csv, interval)
        canonical.assert_baseline(canonical.run_strategy(h_arr,h_bounds,"v4_4"),interval,canonical.DEFAULT_GOLDEN)
        h_inds = autopsy.indices(h_arr,h_bounds)
        dseg=[]; hseg=[]
        for sid,(s,e) in enumerate(h_inds):
            d=simulate(h_arr,s,e,candidate_h=False,capture_trace=True)
            legacy=router.simulate(h_arr,s,e,legacy=True)
            for key in ("pnl_inr","profit_factor","trades","wins","max_drawdown_inr"):
                if abs(float(d[key])-float(legacy[key]))>1e-9:
                    raise RuntimeError(f"D parity failure {interval} segment {sid} {key}")
            hh=simulate(h_arr,s,e,candidate_h=True,raw=hraw,feature_cache=hcache,
                        exit_events=exits,ghost_events=ghosts,
                        context=f"historical7d:{interval}:segment{sid}",capture_trace=True)
            parity=gbase.compare_trace(d,hh)
            if not parity["match"]:
                raise RuntimeError(f"H entry-path parity failure {interval} segment {sid}: {parity}")
            pathrows.append({"interval":interval,"segment_id":sid,**parity})
            dseg.append(d); hseg.append(hh)
            segrows.append({
                "interval":interval,"segment_id":sid,
                "candidate_d_pnl_inr":d["pnl_inr"],"candidate_h_pnl_inr":hh["pnl_inr"],
                "delta_h_vs_d_inr":hh["pnl_inr"]-d["pnl_inr"],
                "candidate_d_trades":d["trades"],"candidate_h_trades":hh["trades"],
                "candidate_d_wins":d["wins"],"candidate_h_wins":hh["wins"],
                "candidate_d_max_drawdown_inr":d["max_drawdown_inr"],
                "candidate_h_max_drawdown_inr":hh["max_drawdown_inr"],
                "candidate_h_primary_flow_exits":hh["primary_flow_exits"],
                "candidate_h_ghost_releases":hh["ghost_releases"],
            })
        ds=summarize(dseg); hs=summarize(hseg); assert_d(ds,interval)

        r_arr,_=canonical.build_features(a.recent_csv_or_gz,interval)
        rd=simulate(r_arr,0,len(r_arr["t"]),candidate_h=False,capture_trace=True)
        assert_recent_d(rd,interval)
        rh=simulate(r_arr,0,len(r_arr["t"]),candidate_h=True,raw=rraw,feature_cache=rcache,
                    exit_events=exits,ghost_events=ghosts,context=f"recent24h:{interval}:whole",
                    capture_trace=True)
        recent_path=gbase.compare_trace(rd,rh)
        if not recent_path["match"]:
            raise RuntimeError(f"H recent entry-path parity failure {interval}: {recent_path}")

        times=pd.read_csv(a.recent_csv_or_gz,usecols=["timestamp_utc"])["timestamp_utc"]
        cut_ts=pd.to_datetime(times.iloc[int(len(times)*0.6)],utc=True).timestamp()
        cut=int(np.searchsorted(r_arr["t"],cut_ts,"left"))
        splits=[]
        for name,s,e in (("seed",0,cut),("evaluation",cut,len(r_arr["t"]))):
            d=simulate(r_arr,s,e,candidate_h=False)
            hh=simulate(r_arr,s,e,candidate_h=True,raw=rraw,feature_cache=rcache)
            item={"split":name,"candidate_d":compact(d),"candidate_h":compact(hh),
                  "delta_h_vs_d_inr":hh["terminal_equity_pnl_inr"]-d["terminal_equity_pnl_inr"]}
            splits.append(item)
            splitrows.append({
                "interval":interval,"split":name,
                "candidate_d_terminal_equity_pnl_inr":d["terminal_equity_pnl_inr"],
                "candidate_h_terminal_equity_pnl_inr":hh["terminal_equity_pnl_inr"],
                "delta_h_vs_d_inr":item["delta_h_vs_d_inr"],
                "candidate_h_primary_flow_exits":hh["primary_flow_exits"],
            })

        rng=np.random.default_rng(RANDOM_SEED+(0 if interval=="500ms" else 1))
        hist_ranges=full_eval.continuous_ranges(h_arr,h_inds)
        recent_ranges=full_eval.continuous_ranges(r_arr,[(0,len(r_arr["t"]))])
        rrows=[]
        for wid in range(RANDOM_WINDOWS):
            source="historical7d" if wid%2==0 else "recent24h"
            arr,ranges,raw,cache=(h_arr,hist_ranges,hraw,hcache) if source=="historical7d" else (r_arr,recent_ranges,rraw,rcache)
            s,e,rid=full_eval.random_window_from_ranges(arr,ranges,rng,RANDOM_HOURS)
            d=simulate(arr,s,e,candidate_h=False)
            hh=simulate(arr,s,e,candidate_h=True,raw=raw,feature_cache=cache)
            row={"interval":interval,"window_id":wid,"source":source,"source_range_id":rid,
                 "start_ts":float(arr["t"][s]),"end_ts":float(arr["t"][e-1]),
                 "candidate_d_pnl":float(d["terminal_equity_pnl_inr"]),
                 "candidate_h_pnl":float(hh["terminal_equity_pnl_inr"]),
                 "candidate_d_trades":int(d["trades"]),"candidate_h_trades":int(hh["trades"]),
                 "candidate_d_wins":int(d["wins"]),"candidate_h_wins":int(hh["wins"]),
                 "candidate_h_flow_exits":int(hh["primary_flow_exits"])}
            rrows.append(row); random_all.append(row)
        dr=random_summary(rrows,"candidate_d"); hr=random_summary(rrows,"candidate_h")

        costs=[]
        for slip in SLIPPAGE_STRESS_USD_PER_SIDE:
            dss=[simulate(h_arr,s,e,candidate_h=False,extra_slippage_usd_per_side=slip) for s,e in h_inds]
            hss=[simulate(h_arr,s,e,candidate_h=True,raw=hraw,feature_cache=hcache,extra_slippage_usd_per_side=slip) for s,e in h_inds]
            hd=summarize(dss); hhx=summarize(hss)
            rds=simulate(r_arr,0,len(r_arr["t"]),candidate_h=False,extra_slippage_usd_per_side=slip)
            rhs=simulate(r_arr,0,len(r_arr["t"]),candidate_h=True,raw=rraw,feature_cache=rcache,extra_slippage_usd_per_side=slip)
            row={
                "extra_slippage_usd_per_side":slip,
                "historical_candidate_d_compounded_pnl_inr":hd["compounded_pnl_inr"],
                "historical_candidate_h_compounded_pnl_inr":hhx["compounded_pnl_inr"],
                "historical_delta_h_vs_d_inr":hhx["compounded_pnl_inr"]-hd["compounded_pnl_inr"],
                "recent_candidate_d_terminal_equity_pnl_inr":rds["terminal_equity_pnl_inr"],
                "recent_candidate_h_terminal_equity_pnl_inr":rhs["terminal_equity_pnl_inr"],
                "recent_delta_h_vs_d_inr":rhs["terminal_equity_pnl_inr"]-rds["terminal_equity_pnl_inr"],
                "historical_candidate_h_flow_exits":hhx["primary_flow_exits"],
                "recent_candidate_h_flow_exits":rhs["primary_flow_exits"],
            }
            costs.append(row); stressrows.append({"interval":interval,**row})

        result["intervals"][interval]={
            "canonical_first80":{
                "entry_path_parity":True,"candidate_d":ds,"candidate_h":hs,
                "delta_h_vs_d_inr":hs["compounded_pnl_inr"]-ds["compounded_pnl_inr"],
                "candidate_d_segments":[compact(x) for x in dseg],
                "candidate_h_segments":[compact(x) for x in hseg],
            },
            "recent24h_whole":{
                "entry_path_parity":recent_path,"candidate_d":compact(rd),"candidate_h":compact(rh),
                "delta_h_vs_d_inr":rh["terminal_equity_pnl_inr"]-rd["terminal_equity_pnl_inr"],
            },
            "recent24h_split":splits,
            "random_real_windows":{
                "candidate_d":dr,"candidate_h":hr,
                "candidate_h_better_than_d_fraction":float(np.mean([x["candidate_h_pnl"]>x["candidate_d_pnl"] for x in rrows])),
                "candidate_h_equal_to_d_fraction":float(np.mean([abs(x["candidate_h_pnl"]-x["candidate_d_pnl"])<=1e-9 for x in rrows])),
            },
            "cost_stress":costs,
        }

    write_csv(a.output/"entry_path_parity.csv",pathrows)
    write_csv(a.output/"canonical_segment_comparison.csv",segrows)
    write_csv(a.output/"recent_split_comparison.csv",splitrows)
    write_csv(a.output/"random_real_windows.csv",random_all)
    write_csv(a.output/"cost_stress.csv",stressrows)
    write_csv(a.output/"primary_flow_exit_events.csv",exits)
    write_csv(a.output/"ghost_release_events.csv",ghosts)
    (a.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
