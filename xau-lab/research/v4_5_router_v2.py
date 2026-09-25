"""Experiment 28: stronghold-aware Router v2 implementation for V4.5.

The routing mechanics and structural score are frozen before unseen validation.
Known data may be used for implementation/parity diagnostics only.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_state_v2_freeze as state_v2

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-09-25-v4_5-router-v2-implementation"

ENGINE_NAMES = {1: "PRIMARY", 2: "SECONDARY", 3: "MICRO", 4: "BURST"}
LEGACY_PRIORITY = (1, 2, 3, 4)
SCORE_FLOOR = 0.0
SQUASH_SCALE = 3.0

SCORE_COMPONENTS = {
    "PRIMARY": (
        "dir_m300_rel", "dir_m60_rel", "flow_align60", "pullback60_edge",
        "short_long_balance_stability", "market_heat_penalty", "execution_heat_penalty",
    ),
    "SECONDARY": (
        "dir_m30_rel", "dir_m60_rel", "flow_align10", "accel_10_60",
        "pullback60_edge", "range_expansion", "execution_heat_penalty",
    ),
    "MICRO": (
        "dir_m10_rel", "dir_m60_rel", "flow_align10", "flow_align60",
        "accel_10_60", "pullback60_edge", "execution_heat_penalty",
    ),
    "BURST": (
        "dir_m10_rel", "dir_m30_rel", "flow_align10", "accel_10_60",
        "activity_expansion", "range_expansion", "execution_heat_penalty",
    ),
}


def squash(value: float, scale: float = SQUASH_SCALE) -> float:
    if not math.isfinite(value):
        return 0.0
    return math.tanh(value / scale)


def positive_momentum(value: float) -> float:
    return squash(max(0.0, value))


def baseline_expansion(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return math.tanh(value - 1.0)


def penalty_above_baseline(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return -math.tanh(max(0.0, value - 1.0))


def pullback_edge(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    value = min(1.0, max(0.0, value))
    return 1.0 - 2.0 * value


def score_components(engine: str, state: Dict[str, float]) -> Dict[str, float]:
    common = {
        "dir_m10_rel": positive_momentum(state.get("dir_m10_rel", math.nan)),
        "dir_m30_rel": positive_momentum(state.get("dir_m30_rel", math.nan)),
        "dir_m60_rel": positive_momentum(state.get("dir_m60_rel", math.nan)),
        "dir_m300_rel": positive_momentum(state.get("dir_m300_rel", math.nan)),
        "flow_align10": float(np.clip(state.get("flow_align10", 0.0), -1.0, 1.0)),
        "flow_align60": float(np.clip(state.get("flow_align60", 0.0), -1.0, 1.0)),
        "accel_10_60": squash(state.get("accel_10_60", math.nan)),
        "pullback60_edge": pullback_edge(state.get("pullback60", math.nan)),
        "range_expansion": baseline_expansion(state.get("range60_rel", math.nan)),
        "activity_expansion": baseline_expansion(state.get("activity_rel", math.nan)),
        "market_heat_penalty": penalty_above_baseline(state.get("market_heat", math.nan)),
        "execution_heat_penalty": penalty_above_baseline(state.get("execution_heat", math.nan)),
        "short_long_balance_stability": -abs(squash(state.get("short_long_balance", math.nan))),
    }
    return {name: common[name] for name in SCORE_COMPONENTS[engine]}


def stronghold_score(engine: str, state: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    parts = score_components(engine, state)
    return float(sum(parts.values()) / len(parts)), parts


def signal_candidates(arr: Dict[str, np.ndarray], i: int, cont: float, last: Dict[int, float]) -> List[Tuple[int, int]]:
    t, mid, spread = arr["t"], arr["mid"], arr["spread"]
    m10, m30, m60, m120 = arr["m10"], arr["m30"], arr["m60"], arr["m120"]
    m300, m1800 = arr["m300"], arr["m1800"]
    r60, r300, er60 = arr["range60"], arr["range300"], arr["er60"]
    min10, max10 = arr["min_m10_30"], arr["max_m10_30"]
    min60, max60 = arr["min_m60_300"], arr["max_m60_300"]
    chh, chl = arr["ch_high120"], arr["ch_low120"]
    imb, qacc = arr["imb10"], arr["qacc"]
    ts = float(t[i])

    if spread[i] > 0.30:
        return []

    high = bool(np.isfinite(r300[i]) and np.isfinite(er60[i]) and r300[i] >= 5.0 and er60[i] >= 0.03)
    pcool = 450.0 if high else 900.0
    scool = 90.0 if high else 450.0
    out: List[Tuple[int, int]] = []

    if ts - cont >= 1800.0 and ts - last[1] >= pcool and all(np.isfinite(x) for x in (m60[i], m300[i], m1800[i], min60[i], max60[i])):
        if m1800[i] >= 8 and m300[i] >= 3 and min60[i] <= -0.8 and m60[i] >= 0.5:
            out.append((1, 1))
        elif m1800[i] <= -8 and m300[i] <= -3 and max60[i] >= 0.8 and m60[i] <= -0.5:
            out.append((1, -1))

    if ts - last[2] >= scool and all(np.isfinite(x) for x in (m30[i], chh[i], chl[i])):
        slowbuy = bool(np.isfinite(m300[i]) and np.isfinite(m1800[i]) and m1800[i] >= 8 and m300[i] >= 3)
        slowsell = bool(np.isfinite(m300[i]) and np.isfinite(m1800[i]) and m1800[i] <= -8 and m300[i] <= -3)
        if not ((slowbuy or slowsell) and not high):
            rng = chh[i] - chl[i]
            buf = max(0.5, 0.02 * rng)
            if rng >= 4:
                if mid[i] >= chh[i] + buf and m30[i] >= 1.5:
                    out.append((2, 1))
                elif mid[i] <= chl[i] - buf and m30[i] <= -1.5:
                    out.append((2, -1))

    if ts - last[3] >= 60.0 and all(np.isfinite(x) for x in (m10[i], m60[i], m120[i], er60[i], r60[i], min10[i], max10[i])):
        if r60[i] >= 2 and er60[i] >= 0.12 and qacc[i] >= 0.65 and spread[i] <= 0.25 * r60[i]:
            if m120[i] >= 6 and m60[i] >= 2 and min10[i] <= -0.5 and m10[i] >= 0.2 and imb[i] >= 0:
                out.append((3, 1))
            elif m120[i] <= -6 and m60[i] <= -2 and max10[i] >= 0.5 and m10[i] <= -0.2 and imb[i] <= 0:
                out.append((3, -1))

    cfg = canonical.burst_config("v4_5_b")
    if cfg[0] > 0.5 and ts - last[4] >= cfg[1]:
        if all(np.isfinite(x) for x in (m10[i], m30[i], m60[i], m120[i], er60[i], r60[i])):
            if r60[i] >= cfg[8] and spread[i] <= cfg[9] * r60[i] and spread[i] <= cfg[10] and qacc[i] >= cfg[6] and er60[i] >= cfg[5]:
                if m10[i] >= cfg[2] and m30[i] >= cfg[3] and m60[i] >= cfg[4] and m120[i] > 0 and imb[i] >= cfg[7]:
                    out.append((4, 1))
                elif m10[i] <= -cfg[2] and m30[i] <= -cfg[3] and m60[i] <= -cfg[4] and m120[i] < 0 and imb[i] <= -cfg[7]:
                    out.append((4, -1))
    return out


def candidate_state_rows(arr: Dict[str, np.ndarray]) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    prev_ss = None
    cont = 0.0
    fake_last = {1: -1e30, 2: -1e30, 3: -1e30, 4: -1e30}
    for i, ts in enumerate(arr["t"]):
        if prev_ss is None or arr["ss"][i] != prev_ss:
            cont = float(ts)
            prev_ss = arr["ss"][i]
        for engine, side in signal_candidates(arr, i, cont, fake_last):
            rows.append({
                "trade_id": f"cache-{i}-{engine}-{side}",
                "interval": "cache",
                "segment_id": 0,
                "engine": ENGINE_NAMES[engine],
                "side": "BUY" if side == 1 else "SELL",
                "side_sign": side,
                "entry_ts": float(ts),
                "exit_ts": float(ts),
                "pnl_inr": 0.0,
                "_sample_index": i,
            })
    return rows


def build_state_cache(raw_path: Path, arr: Dict[str, np.ndarray]) -> Dict[Tuple[int, int], Dict[str, float]]:
    enriched = state_v2.overlay(raw_path, candidate_state_rows(arr), "router-v2-cache")
    cache: Dict[Tuple[int, int], Dict[str, float]] = {}
    for row in enriched:
        key = (int(row["_sample_index"]), int(row["side_sign"]))
        cache[key] = {name: float(row.get(name, math.nan)) for name in state_v2.FEATURES}
    return cache


def choose_router(candidates: List[Tuple[int, int]], cache: Dict[Tuple[int, int], Dict[str, float]], i: int):
    priority = {engine: rank for rank, engine in enumerate(LEGACY_PRIORITY)}
    scored = []
    for engine, side in candidates:
        state = cache.get((i, side))
        if state is None:
            continue
        score, parts = stronghold_score(ENGINE_NAMES[engine], state)
        scored.append((score, -priority[engine], engine, side, parts))
    scored.sort(reverse=True)
    for score, _, engine, side, parts in scored:
        if score >= SCORE_FLOOR:
            return engine, side, score, parts
    return None


def simulate(arr: Dict[str, np.ndarray], start: int, end: int, cache=None, legacy=False):
    t, bid, ask = arr["t"], arr["bid"], arr["ask"]
    m30, m300 = arr["m30"], arr["m300"]
    r300, er60 = arr["range300"], arr["er60"]
    cfg = canonical.burst_config("v4_5_b")

    bal=500.0; gp=0.0; gl=0.0; ntr=0; wins=0; peakbal=500.0; maxdd=0.0
    pos=0; side=0; entry=0.0; oz=0.0; ptime=0.0; peak=0.0
    partial=0.0; partial_done=0; highopen=0; failure_since=-1e30
    last={1:-1e30,2:-1e30,3:-1e30,4:-1e30}
    prev_ss=None; cont=0.0; routed=0; holds=0

    for i in range(start,end):
        ts=float(t[i])
        if prev_ss is None or arr["ss"][i] != prev_ss:
            cont=ts
            prev_ss=arr["ss"][i]

        if pos:
            move=(bid[i]-entry) if side==1 else (entry-ask[i])
            held=ts-ptime
            if move>peak:
                peak=move
            if pos==3 and partial_done==0 and move>=5.5:
                closeoz=oz*0.75
                part=move*closeoz*canonical.INR_PER_USD
                bal+=part; partial+=part; oz-=closeoz; partial_done=1

            reason=0; rev=1; trig=-1.0; gb=0.0; tp=12.0; maxhold=900.0
            if pos==3:
                tp=10.0; trig=4.0; gb=2.0
            elif pos==4:
                tp=cfg[11]; maxhold=cfg[12]; trig=cfg[15]; gb=cfg[16]; rev=0
            elif pos==1 and highopen==1:
                tp=25.0; maxhold=900.0; rev=0
            elif pos==2 and highopen==1:
                tp=8.0; maxhold=1200.0; rev=0; trig=12.0; gb=3.0
            elif pos==1:
                tp=21.0; maxhold=1800.0

            if move<=-4.0:
                reason=1
            elif move>=tp:
                reason=2
            if reason==0 and trig>0 and peak>=trig and move<=peak-gb:
                reason=3
            if reason==0 and pos==3 and held>=45.0 and peak<0.75:
                reason=4
            if reason==0 and pos==4 and held>=cfg[13] and peak<cfg[14]:
                reason=4

            if pos==4 and not np.isfinite(m30[i]):
                failure_since=-1e30
            if reason==0 and pos==4 and np.isfinite(m30[i]):
                failure=(side==1 and m30[i]<=0) or (side==-1 and m30[i]>=0)
                if failure:
                    if failure_since<-1e20:
                        failure_since=ts
                    if ts-failure_since>=1.0:
                        reason=5
                else:
                    failure_since=-1e30

            if reason==0 and rev==1 and np.isfinite(m300[i]):
                if (side==1 and m300[i]<=0) or (side==-1 and m300[i]>=0):
                    reason=5
            if reason==0 and held>=maxhold:
                reason=7

            if reason:
                pnl=move*oz*canonical.INR_PER_USD
                total=pnl+partial
                bal+=pnl; ntr+=1
                if total>0:
                    gp+=total; wins+=1
                elif total<0:
                    gl-=total
                peakbal=max(peakbal,bal)
                maxdd=max(maxdd,peakbal-bal)
                last[pos]=ts
                pos=0
            continue

        candidates=signal_candidates(arr,i,cont,last)
        if not candidates:
            continue

        if legacy:
            engine,sside=candidates[0]
        else:
            choice=choose_router(candidates,cache or {},i)
            if choice is None:
                holds+=1
                continue
            engine,sside,_,_=choice
            routed+=1

        high=bool(np.isfinite(r300[i]) and np.isfinite(er60[i]) and r300[i]>=5.0 and er60[i]>=0.03)
        entry=ask[i] if sside==1 else bid[i]
        oz=min(bal*0.03/(4*canonical.INR_PER_USD),(bal/canonical.INR_PER_USD*100)/entry)
        pos=engine; side=sside; ptime=ts; peak=0.0; partial=0.0; partial_done=0
        highopen=1 if high else 0; failure_since=-1e30

    pf=gp/gl if gl>0 else 999.0
    terminal_unrealized=0.0
    if pos and end>start:
        j=end-1
        terminal_move=(bid[j]-entry) if side==1 else (entry-ask[j])
        terminal_unrealized=terminal_move*oz*canonical.INR_PER_USD
    return {
        "pnl_inr":bal-500.0,
        "terminal_unrealized_inr":terminal_unrealized,
        "terminal_equity_pnl_inr":bal-500.0+terminal_unrealized,
        "open_position_at_end":bool(pos),
        "profit_factor":pf,
        "trades":ntr,
        "wins":wins,
        "win_rate":wins/ntr if ntr else 0.0,
        "max_drawdown_inr":maxdd,
        "routed_entries":routed,
        "hold_decisions":holds,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("canonical_csv",type=Path)
    p.add_argument("--implementation-check",action="store_true",
                   help="Known-data lifecycle parity and Router-v2 diagnostic only; never promotion evidence.")
    p.add_argument("--output",type=Path,default=DEFAULT_OUT)
    a=p.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    a.output.mkdir(parents=True,exist_ok=True)
    config={
        "schema":"xau-router-v2-structural-v1",
        "state_schema":"xau-state-v2",
        "score_floor":SCORE_FLOOR,
        "squash_scale":SQUASH_SCALE,
        "legacy_tie_break_priority":[ENGINE_NAMES[x] for x in LEGACY_PRIORITY],
        "weights":"equal within engine; no P&L weight search",
        "components":SCORE_COMPONENTS,
        "fall_through":True,
        "hold_allowed":True,
        "trade_retention_target":0.95,
        "promotion_requires_new_unseen_snapshot":True
    }
    (a.output/"router_v2_config.json").write_text(json.dumps(config,indent=2)+"\n",encoding="utf-8")

    if not a.implementation_check:
        print(json.dumps({"status":"implementation frozen","config":config},indent=2))
        return

    diagnostics={}
    for interval in ("500ms","1s"):
        arr,bounds=canonical.build_features(a.canonical_csv,interval)
        canonical.assert_baseline(canonical.run_strategy(arr,bounds,"v4_4"),interval,canonical.DEFAULT_GOLDEN)
        cache=build_state_cache(a.canonical_csv,arr)
        rows=[]
        for sid,(start,end) in enumerate(autopsy.indices(arr,bounds)):
            legacy=simulate(arr,start,end,legacy=True)
            expected=autopsy.simulate_trace(
                *[arr[x] for x in canonical.FEATURE_NAMES],
                start,end,canonical.burst_config("v4_5_b"),1.0
            )
            for key,j in (("pnl_inr",0),("profit_factor",1),("trades",2),("wins",3),("max_drawdown_inr",4)):
                if abs(legacy[key]-float(expected[j]))>1e-9:
                    raise RuntimeError(f"legacy parity failure {interval} segment {sid} {key}")
            router=simulate(arr,start,end,cache=cache,legacy=False)
            rows.append({"segment_id":sid,"legacy":legacy,"router":router})
        diagnostics[interval]=rows

    (a.output/"known_data_implementation_diagnostic.json").write_text(
        json.dumps(diagnostics,indent=2)+"\n",encoding="utf-8"
    )
    print(json.dumps({"status":"implementation diagnostic complete","promotion_evidence":False},indent=2))


if __name__=="__main__":
    main()
