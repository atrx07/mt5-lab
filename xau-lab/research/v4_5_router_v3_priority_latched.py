"""Experiment 32: path-aware, priority-preserving Router v3.

This candidate is structurally specified from Experiment-31 mechanism evidence
before performance evaluation. It deliberately does not search score floors,
weights, cooldowns, or engine thresholds on known P&L.

Core rules:
  * preserve Candidate D engine priority;
  * use the frozen Router-v2 stronghold score only as a veto, never to re-rank;
  * when an engine is vetoed, latch that rejection for the engine's already
    existing Candidate-D cooldown horizon so the same setup cannot re-enter
    moments later as a fresh decision;
  * after a veto, fall through to the next lower-priority candidate on that
    same tick;
  * HOLD only when no priority-ordered candidate clears the frozen 0.0 score.

Known-data runs are diagnostic only. Promotion still requires a genuinely new
non-overlapping raw snapshot.
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
import v4_5_regime_portability as portability
import v4_5_router_v2 as v2
import v4_5_router_v2_full_eval as full_eval

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OUT=ROOT/"results"/"simulations"/"2026-09-25-v4_5-router-v3-priority-latched"

EXPECTED_D={
    "500ms":{"pnl":1430.311133793068,"trades":163,"wins":81},
    "1s":{"pnl":385.2544619534224,"trades":156,"wins":71},
}
RANDOM_SEED=20260925
RANDOM_WINDOWS=40
RANDOM_HOURS=4.0


def cooldown_seconds(engine:int,arr:Dict[str,np.ndarray],i:int)->float:
    r300=float(arr["range300"][i]); er60=float(arr["er60"][i])
    high=bool(np.isfinite(r300) and np.isfinite(er60) and r300>=5.0 and er60>=0.03)
    if engine==1:
        return 450.0 if high else 900.0
    if engine==2:
        return 90.0 if high else 450.0
    if engine==3:
        return 60.0
    if engine==4:
        return float(canonical.burst_config("v4_5_b")[1])
    raise ValueError(engine)


def available_candidates(arr,i,cont,last,blocked_until):
    ts=float(arr["t"][i])
    raw=v2.signal_candidates(arr,i,cont,last)
    return [(engine,side) for engine,side in raw if ts>=blocked_until[engine]]


def choose_priority_latched(candidates,cache,i,arr,blocked_until):
    """Return the first priority-ordered candidate that clears frozen score 0.

    Rejected engines receive a virtual cooldown using their pre-existing
    Candidate-D cooldown duration. No candidate is globally re-ranked.
    """
    ts=float(arr["t"][i])
    rejected=[]
    for rank,(engine,side) in enumerate(candidates):
        state=cache.get((i,side))
        if state is None:
            score=math.nan
            parts={}
            qualifies=False
        else:
            score,parts=v2.stronghold_score(v2.ENGINE_NAMES[engine],state)
            qualifies=bool(score>=v2.SCORE_FLOOR)

        if qualifies:
            return {
                "choice":(engine,side),
                "score":float(score),
                "parts":parts,
                "rank":rank,
                "rejected":rejected,
            }

        until=ts+cooldown_seconds(engine,arr,i)
        blocked_until[engine]=max(blocked_until[engine],until)
        rejected.append({
            "engine":engine,
            "side":side,
            "score":float(score) if math.isfinite(score) else None,
            "blocked_until":float(blocked_until[engine]),
        })

    return {"choice":None,"score":None,"parts":{},"rank":None,"rejected":rejected}


def simulate(arr,start,end,cache):
    t,bid,ask=arr["t"],arr["bid"],arr["ask"]
    m30,m300=arr["m30"],arr["m300"]
    r300,er60=arr["range300"],arr["er60"]
    cfg=canonical.burst_config("v4_5_b")

    bal=500.0; gp=0.0; gl=0.0; ntr=0; wins=0; peakbal=500.0; maxdd=0.0
    pos=0; side=0; entry=0.0; oz=0.0; ptime=0.0; peak=0.0
    partial=0.0; partial_done=0; highopen=0; failure_since=-1e30
    last={1:-1e30,2:-1e30,3:-1e30,4:-1e30}
    blocked_until={1:-1e30,2:-1e30,3:-1e30,4:-1e30}
    prev_ss=None; cont=0.0

    routed=0; holds=0; rejected_count=0; latch_events=0
    fallback_entries=0; first_priority_entries=0
    rejection_by_engine={1:0,2:0,3:0,4:0}

    for i in range(start,end):
        ts=float(t[i])
        if prev_ss is None or arr["ss"][i]!=prev_ss:
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

        candidates=available_candidates(arr,i,cont,last,blocked_until)
        if not candidates:
            continue

        decision=choose_priority_latched(candidates,cache,i,arr,blocked_until)
        for r in decision["rejected"]:
            rejected_count+=1; latch_events+=1; rejection_by_engine[int(r["engine"])]+=1

        choice=decision["choice"]
        if choice is None:
            holds+=1
            continue

        engine,sside=choice
        routed+=1
        if int(decision["rank"])==0:
            first_priority_entries+=1
        else:
            fallback_entries+=1

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
        "rejected_candidates":rejected_count,
        "rejection_latch_events":latch_events,
        "fallback_entries":fallback_entries,
        "first_priority_entries":first_priority_entries,
        "rejections_primary":rejection_by_engine[1],
        "rejections_secondary":rejection_by_engine[2],
        "rejections_micro":rejection_by_engine[3],
        "rejections_burst":rejection_by_engine[4],
    }


def compact(m):
    return {k:m[k] for k in (
        "pnl_inr","terminal_unrealized_inr","terminal_equity_pnl_inr",
        "open_position_at_end","profit_factor","trades","wins","win_rate",
        "max_drawdown_inr","routed_entries","hold_decisions","rejected_candidates",
        "rejection_latch_events","fallback_entries","first_priority_entries",
        "rejections_primary","rejections_secondary","rejections_micro","rejections_burst"
    ) if k in m}


def summarize_segments(rows):
    factor=1.0; trades=wins=0; dds=[]; counters={}
    for m in rows:
        factor*=1.0+m["pnl_inr"]/canonical.START_BALANCE_INR
        trades+=m["trades"]; wins+=m["wins"]; dds.append(m["max_drawdown_inr"])
        for k in ("routed_entries","hold_decisions","rejected_candidates","rejection_latch_events",
                  "fallback_entries","first_priority_entries","rejections_primary","rejections_secondary",
                  "rejections_micro","rejections_burst"):
            counters[k]=counters.get(k,0)+int(m.get(k,0))
    return {
        "compounded_pnl_inr":canonical.START_BALANCE_INR*(factor-1.0),
        "trades":trades,"wins":wins,"win_rate":wins/trades if trades else 0.0,
        "max_segment_drawdown_inr":max(dds) if dds else 0.0,
        **counters,
    }


def assert_candidate_d(summary,interval):
    exp=EXPECTED_D[interval]
    if abs(summary["compounded_pnl_inr"]-exp["pnl"])>1e-6:
        raise RuntimeError(f"Candidate D P&L parity drift {interval}: {summary}")
    if summary["trades"]!=exp["trades"] or summary["wins"]!=exp["wins"]:
        raise RuntimeError(f"Candidate D count parity drift {interval}: {summary}")


def random_summary(rows,prefix):
    pnl=np.asarray([r[f"{prefix}_pnl"] for r in rows],dtype=float)
    tr=np.asarray([r[f"{prefix}_trades"] for r in rows],dtype=float)
    wi=np.asarray([r[f"{prefix}_wins"] for r in rows],dtype=float)
    return {
        "windows":len(rows),
        "median_terminal_equity_pnl_inr":float(np.median(pnl)) if len(pnl) else 0.0,
        "mean_terminal_equity_pnl_inr":float(np.mean(pnl)) if len(pnl) else 0.0,
        "p05_terminal_equity_pnl_inr":float(np.quantile(pnl,.05)) if len(pnl) else 0.0,
        "p95_terminal_equity_pnl_inr":float(np.quantile(pnl,.95)) if len(pnl) else 0.0,
        "positive_window_fraction":float(np.mean(pnl>0)) if len(pnl) else 0.0,
        "total_trades":int(tr.sum()),"total_wins":int(wi.sum()),
        "aggregate_win_rate":float(wi.sum()/tr.sum()) if tr.sum() else 0.0,
    }


def write_csv(path,rows):
    if not rows:
        path.write_text("",encoding="utf-8"); return
    with path.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("canonical_csv",type=Path)
    ap.add_argument("recent_csv_or_gz",type=Path)
    ap.add_argument("--random-windows",type=int,default=RANDOM_WINDOWS)
    ap.add_argument("--random-hours",type=float,default=RANDOM_HOURS)
    ap.add_argument("--seed",type=int,default=RANDOM_SEED)
    ap.add_argument("--output",type=Path,default=DEFAULT_OUT)
    a=ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True,exist_ok=True)

    result={
        "schema":"xau-router-v3-priority-latched-v1",
        "strategy_changed":True,
        "structurally_preregistered":True,
        "score_tuned":False,
        "cooldown_tuned":False,
        "known_data_promotion_allowed":False,
        "final20_opened":False,
        "architecture":{
            "priority":"Candidate D legacy PRIMARY > SECONDARY > MICRO > BURST",
            "score_role":"frozen Router-v2 score is veto only; never re-ranks",
            "score_floor":v2.SCORE_FLOOR,
            "rejection_latch":"existing Candidate-D engine cooldown horizon",
            "fall_through":"lower-priority candidate may be evaluated after veto",
            "hold":"only when no priority-ordered candidate clears score",
        },
        "random_window_method":"real contiguous four-hour windows from known canonical first80/recent24h; stress only, never promotion evidence",
        "intervals":{},
    }
    all_random=[]

    for interval in ("500ms","1s"):
        print(f"{interval}: canonical features",flush=True)
        h_arr,h_bounds=canonical.build_features(a.canonical_csv,interval)
        canonical.assert_baseline(canonical.run_strategy(h_arr,h_bounds,"v4_4"),interval,canonical.DEFAULT_GOLDEN)
        print(f"{interval}: canonical state cache",flush=True)
        h_cache=v2.build_state_cache(a.canonical_csv,h_arr)
        h_inds=autopsy.indices(h_arr,h_bounds)

        dseg=[]; v2seg=[]; v3seg=[]
        for sid,(s,e) in enumerate(h_inds):
            d=v2.simulate(h_arr,s,e,legacy=True)
            old=v2.simulate(h_arr,s,e,cache=h_cache,legacy=False)
            new=simulate(h_arr,s,e,h_cache)
            dseg.append(d); v2seg.append(old); v3seg.append(new)
        ds=full_eval.summarize_segments(dseg)
        oldsum=full_eval.summarize_segments(v2seg)
        newsum=summarize_segments(v3seg)
        assert_candidate_d(ds,interval)

        print(f"{interval}: recent features",flush=True)
        r_arr,_=canonical.build_features(a.recent_csv_or_gz,interval)
        print(f"{interval}: recent state cache",flush=True)
        r_cache=v2.build_state_cache(a.recent_csv_or_gz,r_arr)
        rd=v2.simulate(r_arr,0,len(r_arr["t"]),legacy=True)
        rold=v2.simulate(r_arr,0,len(r_arr["t"]),cache=r_cache,legacy=False)
        rnew=simulate(r_arr,0,len(r_arr["t"]),r_cache)

        times=pd.read_csv(a.recent_csv_or_gz,usecols=["timestamp_utc"])["timestamp_utc"]
        cut_ts=pd.to_datetime(times.iloc[int(len(times)*.6)],utc=True).timestamp()
        cut=int(np.searchsorted(r_arr["t"],cut_ts,"left"))
        recent_split=[]
        for name,s,e in (("seed",0,cut),("evaluation",cut,len(r_arr["t"]))):
            d=v2.simulate(r_arr,s,e,legacy=True)
            old=v2.simulate(r_arr,s,e,cache=r_cache,legacy=False)
            new=simulate(r_arr,s,e,r_cache)
            recent_split.append({"split":name,"candidate_d":full_eval.compact(d),"router_v2":full_eval.compact(old),"router_v3":compact(new)})

        rng=np.random.default_rng(a.seed+(0 if interval=="500ms" else 1))
        hist_ranges=full_eval.continuous_ranges(h_arr,h_inds)
        recent_ranges=full_eval.continuous_ranges(r_arr,[(0,len(r_arr["t"]))])
        rows=[]
        for wid in range(a.random_windows):
            source="historical7d" if wid%2==0 else "recent24h"
            if source=="historical7d":
                arr,cache,ranges=h_arr,h_cache,hist_ranges
            else:
                arr,cache,ranges=r_arr,r_cache,recent_ranges
            s,e,range_id=full_eval.random_window_from_ranges(arr,ranges,rng,a.random_hours)
            d=v2.simulate(arr,s,e,legacy=True)
            old=v2.simulate(arr,s,e,cache=cache,legacy=False)
            new=simulate(arr,s,e,cache)
            rows.append({
                "interval":interval,"window_id":wid,"source":source,"source_range_id":range_id,
                "start_ts":float(arr["t"][s]),"end_ts":float(arr["t"][e-1]),
                "candidate_d_pnl":float(d["terminal_equity_pnl_inr"]),
                "router_v2_pnl":float(old["terminal_equity_pnl_inr"]),
                "router_v3_pnl":float(new["terminal_equity_pnl_inr"]),
                "candidate_d_trades":int(d["trades"]),"router_v2_trades":int(old["trades"]),"router_v3_trades":int(new["trades"]),
                "candidate_d_wins":int(d["wins"]),"router_v2_wins":int(old["wins"]),"router_v3_wins":int(new["wins"]),
                "router_v3_holds":int(new["hold_decisions"]),"router_v3_fallback_entries":int(new["fallback_entries"]),
                "router_v3_rejected_candidates":int(new["rejected_candidates"]),
            })
        all_random.extend(rows)
        dr=random_summary(rows,"candidate_d"); oldr=random_summary(rows,"router_v2"); newr=random_summary(rows,"router_v3")

        result["intervals"][interval]={
            "canonical_first80":{
                "candidate_d":ds,"router_v2":oldsum,"router_v3":newsum,
                "router_v3_delta_vs_d":newsum["compounded_pnl_inr"]-ds["compounded_pnl_inr"],
                "router_v3_trade_retention":newsum["trades"]/ds["trades"] if ds["trades"] else 0.0,
                "router_v3_win_rate_delta":newsum["win_rate"]-ds["win_rate"],
                "candidate_d_segments":[full_eval.compact(x) for x in dseg],
                "router_v2_segments":[full_eval.compact(x) for x in v2seg],
                "router_v3_segments":[compact(x) for x in v3seg],
            },
            "recent24h_whole":{
                "candidate_d":full_eval.compact(rd),"router_v2":full_eval.compact(rold),"router_v3":compact(rnew),
                "router_v3_delta_vs_d":rnew["terminal_equity_pnl_inr"]-rd["terminal_equity_pnl_inr"],
                "router_v3_trade_retention":rnew["trades"]/rd["trades"] if rd["trades"] else 0.0,
                "router_v3_win_rate_delta":rnew["win_rate"]-rd["win_rate"],
            },
            "recent24h_split":recent_split,
            "random_real_windows":{
                "candidate_d":dr,"router_v2":oldr,"router_v3":newr,
                "router_v3_better_than_d_fraction":float(np.mean([x["router_v3_pnl"]>x["candidate_d_pnl"] for x in rows])) if rows else 0.0,
                "router_v3_trade_retention":newr["total_trades"]/dr["total_trades"] if dr["total_trades"] else 0.0,
            },
        }

        del h_arr,h_cache,r_arr,r_cache

    write_csv(a.output/"random_real_windows.csv",all_random)
    (a.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
