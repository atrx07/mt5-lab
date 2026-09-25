"""Experiment 31: Router-v2 arbitration divergence audit.

This is a diagnostic-only replay. It does not change Candidate D, xau-state-v2,
Router-v2 scores, risk, lifecycle, or the final20 holdout.

The script runs Candidate D and the frozen Router v2 side-by-side on the same
sampled ticks, records every decision divergence, and evaluates normalized
counterfactual tickets at direct arbitration points.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_regime_portability as portability
import v4_5_router_v2 as router

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OUT=ROOT/"results"/"simulations"/"2026-09-25-v4_5-router-v2-arbitration-audit"
REASONS={1:"emergency_stop",2:"take_profit",3:"trail",4:"stagnation",5:"momentum_zero_cross",7:"max_hold"}
EXPECTED={
    "500ms":{
        "candidate_d":1430.311133793068,
        "router_v2":851.2651000196032,
        "candidate_trades":163,
        "router_trades":163,
    },
    "1s":{
        "candidate_d":385.2544619534224,
        "router_v2":297.6666981590078,
        "candidate_trades":156,
        "router_trades":156,
    },
}


def action_name(action):
    if action is None:
        return "HOLD"
    engine,side=action
    return f"{router.ENGINE_NAMES[int(engine)]}:{'BUY' if int(side)==1 else 'SELL'}"


def candidates_text(candidates):
    return "|".join(action_name(x) for x in candidates) if candidates else ""


def json_compact(value):
    return json.dumps(value,separators=(",",":"),sort_keys=True)


def score_candidates(candidates,cache,i):
    priority={engine:rank for rank,engine in enumerate(router.LEGACY_PRIORITY)}
    rows=[]
    for engine,side in candidates:
        state=cache.get((i,side))
        if state is None:
            continue
        score,parts=router.stronghold_score(router.ENGINE_NAMES[engine],state)
        rows.append({
            "engine":router.ENGINE_NAMES[engine],
            "side":"BUY" if side==1 else "SELL",
            "score":float(score),
            "qualifies":bool(score>=router.SCORE_FLOOR),
            "priority":priority[engine],
            "parts":{k:float(v) for k,v in parts.items()},
        })
    rows.sort(key=lambda x:(x["score"],-x["priority"]),reverse=True)
    return rows


def fresh_state(name):
    return {
        "name":name,
        "bal":500.0,"gp":0.0,"gl":0.0,"ntr":0,"wins":0,
        "peakbal":500.0,"maxdd":0.0,
        "pos":0,"side":0,"entry":0.0,"entry_oz":0.0,"oz":0.0,
        "ptime":0.0,"peak":0.0,"trough":0.0,"partial":0.0,
        "partial_done":0,"highopen":0,"failure_since":-1e30,
        "last":{1:-1e30,2:-1e30,3:-1e30,4:-1e30},
        "entry_balance":500.0,"entry_index":-1,
        "trades":[],"routed_entries":0,"hold_decisions":0,
    }


def lifecycle_params(pos,highopen,cfg):
    reason_rev=1; trig=-1.0; gb=0.0; tp=12.0; maxhold=900.0
    if pos==3:
        tp=10.0; trig=4.0; gb=2.0
    elif pos==4:
        tp=cfg[11]; maxhold=cfg[12]; trig=cfg[15]; gb=cfg[16]; reason_rev=0
    elif pos==1 and highopen==1:
        tp=25.0; maxhold=900.0; reason_rev=0
    elif pos==2 and highopen==1:
        tp=8.0; maxhold=1200.0; reason_rev=0; trig=12.0; gb=3.0
    elif pos==1:
        tp=21.0; maxhold=1800.0
    return tp,maxhold,trig,gb,reason_rev


def process_open_position(state,arr,i,segment_id,interval,window):
    """Process one tick for an already-open position.

    Returns True whenever the strategy started this tick in-position. The caller
    must skip entry logic on that tick, matching router.simulate exactly even if
    the position closes here.
    """
    if not state["pos"]:
        return False

    t,bid,ask=arr["t"],arr["bid"],arr["ask"]
    m30,m300=arr["m30"],arr["m300"]
    cfg=canonical.burst_config("v4_5_b")
    ts=float(t[i]); pos=int(state["pos"]); side=int(state["side"])
    move=(bid[i]-state["entry"]) if side==1 else (state["entry"]-ask[i])
    held=ts-state["ptime"]
    state["peak"]=max(state["peak"],float(move))
    state["trough"]=min(state["trough"],float(move))

    if pos==3 and state["partial_done"]==0 and move>=5.5:
        closeoz=state["oz"]*0.75
        part=float(move)*closeoz*canonical.INR_PER_USD
        state["bal"]+=part
        state["partial"]+=part
        state["oz"]-=closeoz
        state["partial_done"]=1

    tp,maxhold,trig,gb,rev=lifecycle_params(pos,state["highopen"],cfg)
    reason=0
    if move<=-4.0:
        reason=1
    elif move>=tp:
        reason=2
    if reason==0 and trig>0 and state["peak"]>=trig and move<=state["peak"]-gb:
        reason=3
    if reason==0 and pos==3 and held>=45.0 and state["peak"]<0.75:
        reason=4
    if reason==0 and pos==4 and held>=cfg[13] and state["peak"]<cfg[14]:
        reason=4

    if pos==4 and not np.isfinite(m30[i]):
        state["failure_since"]=-1e30
    if reason==0 and pos==4 and np.isfinite(m30[i]):
        failure=(side==1 and m30[i]<=0) or (side==-1 and m30[i]>=0)
        if failure:
            if state["failure_since"]<-1e20:
                state["failure_since"]=ts
            if ts-state["failure_since"]>=1.0:
                reason=5
        else:
            state["failure_since"]=-1e30

    if reason==0 and rev==1 and np.isfinite(m300[i]):
        if (side==1 and m300[i]<=0) or (side==-1 and m300[i]>=0):
            reason=5
    if reason==0 and held>=maxhold:
        reason=7

    if reason:
        remaining=float(move)*state["oz"]*canonical.INR_PER_USD
        total=remaining+state["partial"]
        state["bal"]+=remaining
        state["ntr"]+=1
        if total>0:
            state["gp"]+=total; state["wins"]+=1
        elif total<0:
            state["gl"]-=total
        state["peakbal"]=max(state["peakbal"],state["bal"])
        state["maxdd"]=max(state["maxdd"],state["peakbal"]-state["bal"])
        state["last"][pos]=ts
        state["trades"].append({
            "window":window,"interval":interval,"segment_id":segment_id,
            "strategy":state["name"],"trade_index":len(state["trades"]),
            "entry_index":state["entry_index"],"exit_index":i,
            "engine":router.ENGINE_NAMES[pos],"side":"BUY" if side==1 else "SELL",
            "entry_ts":state["ptime"],"exit_ts":ts,
            "hold_sec":held,"exit_reason":REASONS.get(reason,str(reason)),
            "entry_balance_inr":state["entry_balance"],"entry_oz":state["entry_oz"],
            "pnl_inr":total,"mfe_usd":state["peak"],"mae_usd":state["trough"],
            "exit_move_usd":float(move),"partial_pnl_inr":state["partial"],
        })
        state["pos"]=0
    return True


def open_trade(state,arr,i,engine,side):
    r300,er60=arr["range300"],arr["er60"]
    high=bool(np.isfinite(r300[i]) and np.isfinite(er60[i]) and r300[i]>=5.0 and er60[i]>=0.03)
    entry=float(arr["ask"][i] if side==1 else arr["bid"][i])
    bal=float(state["bal"])
    oz=min(bal*0.03/(4*canonical.INR_PER_USD),(bal/canonical.INR_PER_USD*100)/entry)
    state.update({
        "pos":int(engine),"side":int(side),"entry":entry,
        "entry_oz":float(oz),"oz":float(oz),"ptime":float(arr["t"][i]),
        "peak":0.0,"trough":0.0,"partial":0.0,"partial_done":0,
        "highopen":1 if high else 0,"failure_since":-1e30,
        "entry_balance":bal,"entry_index":int(i),
    })


def flat_decision(state,arr,i,cont,cache,mode):
    candidates=router.signal_candidates(arr,i,cont,state["last"])
    scores=score_candidates(candidates,cache,i)
    action=None
    if candidates:
        if mode=="candidate_d":
            action=candidates[0]
        else:
            choice=router.choose_router(candidates,cache,i)
            if choice is None:
                state["hold_decisions"]+=1
            else:
                action=(int(choice[0]),int(choice[1]))
                state["routed_entries"]+=1
        if action is not None:
            open_trade(state,arr,i,*action)
    return candidates,action,scores


def terminal_metrics(state,arr,end):
    unreal=0.0
    if state["pos"] and end>0:
        j=end-1
        move=(arr["bid"][j]-state["entry"]) if state["side"]==1 else (state["entry"]-arr["ask"][j])
        # Partial MICRO profit is already in balance; terminal unrealized is only the remaining open quantity.
        unreal=float(move)*state["oz"]*canonical.INR_PER_USD
    gl=state["gl"]
    return {
        "pnl_inr":float(state["bal"]-500.0),
        "terminal_unrealized_inr":float(unreal),
        "terminal_equity_pnl_inr":float(state["bal"]-500.0+unreal),
        "open_position_at_end":bool(state["pos"]),
        "profit_factor":float(state["gp"]/gl) if gl>0 else 999.0,
        "trades":int(state["ntr"]),"wins":int(state["wins"]),
        "win_rate":float(state["wins"]/state["ntr"]) if state["ntr"] else 0.0,
        "max_drawdown_inr":float(state["maxdd"]),
        "routed_entries":int(state["routed_entries"]),
        "hold_decisions":int(state["hold_decisions"]),
    }


def counterfactual_ticket(arr,i,end,engine,side,balance=500.0):
    """Run one isolated engine ticket from this exact sampled entry point."""
    state=fresh_state("counterfactual")
    state["bal"]=float(balance); state["peakbal"]=float(balance); state["entry_balance"]=float(balance)
    open_trade(state,arr,i,engine,side)
    for j in range(i+1,end):
        process_open_position(state,arr,j,-1,"cf","counterfactual")
        if not state["pos"]:
            tr=state["trades"][-1]
            return {
                "pnl_inr":float(tr["pnl_inr"]),"mfe_usd":float(tr["mfe_usd"]),
                "mae_usd":float(tr["mae_usd"]),"hold_sec":float(tr["hold_sec"]),
                "exit_reason":tr["exit_reason"],"open_at_end":False,
            }
    if state["pos"] and end>i+1:
        j=end-1
        move=(arr["bid"][j]-state["entry"]) if side==1 else (state["entry"]-arr["ask"][j])
        mtm=state["partial"]+float(move)*state["oz"]*canonical.INR_PER_USD
        return {
            "pnl_inr":float(mtm),"mfe_usd":float(state["peak"]),
            "mae_usd":float(state["trough"]),"hold_sec":float(arr["t"][j]-state["ptime"]),
            "exit_reason":"terminal_mark","open_at_end":True,
        }
    return {"pnl_inr":0.0,"mfe_usd":0.0,"mae_usd":0.0,"hold_sec":0.0,"exit_reason":"no_future_tick","open_at_end":True}


def classify_tick(d_was_pos,r_was_pos,d_candidates,r_candidates,d_action,r_action):
    if d_was_pos!=r_was_pos:
        if (not d_was_pos and d_action is not None) or (not r_was_pos and r_action is not None):
            return "slot_occupancy_cascade"
        return None
    if d_was_pos and r_was_pos:
        return None
    if d_action==r_action:
        return None
    if d_candidates!=r_candidates:
        return "cooldown_history_divergence"
    if d_action is not None and r_action is None:
        return "router_hold"
    if d_action is None and r_action is not None:
        return "router_extra_entry"
    if d_action is not None and r_action is not None:
        return "direct_score_substitution"
    return None


def run_dual(arr,start,end,cache,window,interval,segment_id):
    d=fresh_state("candidate_d"); rv=fresh_state("router_v2")
    prev_ss=None; cont=0.0; events=[]

    for i in range(start,end):
        ts=float(arr["t"][i])
        if prev_ss is None or arr["ss"][i]!=prev_ss:
            cont=ts; prev_ss=arr["ss"][i]

        d_was_pos=bool(d["pos"]); r_was_pos=bool(rv["pos"])
        d_pos_before=action_name((d["pos"],d["side"])) if d_was_pos else "FLAT"
        r_pos_before=action_name((rv["pos"],rv["side"])) if r_was_pos else "FLAT"

        process_open_position(d,arr,i,segment_id,interval,window)
        process_open_position(rv,arr,i,segment_id,interval,window)

        d_candidates=[]; r_candidates=[]; d_action=None; r_action=None; d_scores=[]; r_scores=[]
        if not d_was_pos:
            d_candidates,d_action,d_scores=flat_decision(d,arr,i,cont,cache,"candidate_d")
        if not r_was_pos:
            r_candidates,r_action,r_scores=flat_decision(rv,arr,i,cont,cache,"router_v2")

        cls=classify_tick(d_was_pos,r_was_pos,d_candidates,r_candidates,d_action,r_action)
        if cls is None:
            continue

        row={
            "window":window,"interval":interval,"segment_id":segment_id,
            "sample_index":i,"timestamp":ts,"classification":cls,
            "candidate_d_position_before":d_pos_before,
            "router_position_before":r_pos_before,
            "candidate_d_candidates":candidates_text(d_candidates),
            "router_candidates":candidates_text(r_candidates),
            "candidate_d_action":action_name(d_action),
            "router_action":action_name(r_action),
            "candidate_d_last":json_compact({router.ENGINE_NAMES[k]:float(v) for k,v in d["last"].items()}),
            "router_last":json_compact({router.ENGINE_NAMES[k]:float(v) for k,v in rv["last"].items()}),
            "candidate_d_scores":json_compact(d_scores),
            "router_scores":json_compact(r_scores),
            "d_cf_pnl_500":math.nan,"router_cf_pnl_500":math.nan,"cf_delta_router_minus_d":math.nan,
            "d_cf_mfe_usd":math.nan,"d_cf_mae_usd":math.nan,
            "router_cf_mfe_usd":math.nan,"router_cf_mae_usd":math.nan,
        }
        # Only compare normalized isolated tickets when both systems were flat:
        # this measures arbitration quality without contamination from existing slot occupancy.
        if not d_was_pos and not r_was_pos:
            if d_action is not None:
                cf=counterfactual_ticket(arr,i,end,*d_action,balance=500.0)
                row["d_cf_pnl_500"]=cf["pnl_inr"]; row["d_cf_mfe_usd"]=cf["mfe_usd"]; row["d_cf_mae_usd"]=cf["mae_usd"]
            if r_action is not None:
                cf=counterfactual_ticket(arr,i,end,*r_action,balance=500.0)
                row["router_cf_pnl_500"]=cf["pnl_inr"]; row["router_cf_mfe_usd"]=cf["mfe_usd"]; row["router_cf_mae_usd"]=cf["mae_usd"]
            if np.isfinite(row["d_cf_pnl_500"]) and np.isfinite(row["router_cf_pnl_500"]):
                row["cf_delta_router_minus_d"]=row["router_cf_pnl_500"]-row["d_cf_pnl_500"]
        events.append(row)

    return d,rv,events,terminal_metrics(d,arr,end),terminal_metrics(rv,arr,end)


def assert_same(a,b,label,tol=1e-8):
    for k in ("pnl_inr","profit_factor","trades","wins","max_drawdown_inr"):
        av=float(a[k]); bv=float(b[k])
        if abs(av-bv)>tol:
            raise RuntimeError(f"{label} parity failed {k}: {av} != {bv}")


def match_trades(dtrades,rtrades):
    used=set(); rows=[]
    for d in dtrades:
        best=None
        for j,r in enumerate(rtrades):
            if j in used: continue
            dt=abs(float(r["entry_ts"])-float(d["entry_ts"]))
            if dt<=0.01:
                rank=0 if (r["engine"]==d["engine"] and r["side"]==d["side"]) else 1
                key=(rank,dt,j)
            elif r["engine"]==d["engine"] and r["side"]==d["side"] and dt<=120.0:
                key=(2,dt,j)
            elif dt<=120.0:
                key=(3,dt,j)
            else:
                continue
            if best is None or key<best[0]:
                best=(key,j,r)
        if best is None:
            rows.append({
                "window":d["window"],"interval":d["interval"],"segment_id":d["segment_id"],
                "pair_type":"candidate_d_unmatched","entry_delta_sec":math.nan,
                "candidate_d_engine":d["engine"],"candidate_d_side":d["side"],
                "candidate_d_entry_ts":d["entry_ts"],"candidate_d_exit_ts":d["exit_ts"],
                "candidate_d_exit_reason":d["exit_reason"],"candidate_d_pnl_inr":d["pnl_inr"],
                "candidate_d_mfe_usd":d["mfe_usd"],"candidate_d_mae_usd":d["mae_usd"],
                "router_engine":"","router_side":"","router_entry_ts":math.nan,"router_exit_ts":math.nan,
                "router_exit_reason":"","router_pnl_inr":math.nan,"router_mfe_usd":math.nan,"router_mae_usd":math.nan,
                "paired_pnl_delta_router_minus_d":math.nan,
            })
            continue
        _,j,r=best; used.add(j)
        dt=float(r["entry_ts"])-float(d["entry_ts"])
        if abs(dt)<=0.01:
            typ="exact_same_action" if (r["engine"]==d["engine"] and r["side"]==d["side"]) else "simultaneous_substitution"
        elif r["engine"]==d["engine"] and r["side"]==d["side"]:
            typ="same_engine_timing_shift"
        else:
            typ="nearby_replacement"
        rows.append({
            "window":d["window"],"interval":d["interval"],"segment_id":d["segment_id"],
            "pair_type":typ,"entry_delta_sec":dt,
            "candidate_d_engine":d["engine"],"candidate_d_side":d["side"],
            "candidate_d_entry_ts":d["entry_ts"],"candidate_d_exit_ts":d["exit_ts"],
            "candidate_d_exit_reason":d["exit_reason"],"candidate_d_pnl_inr":d["pnl_inr"],
            "candidate_d_mfe_usd":d["mfe_usd"],"candidate_d_mae_usd":d["mae_usd"],
            "router_engine":r["engine"],"router_side":r["side"],
            "router_entry_ts":r["entry_ts"],"router_exit_ts":r["exit_ts"],
            "router_exit_reason":r["exit_reason"],"router_pnl_inr":r["pnl_inr"],
            "router_mfe_usd":r["mfe_usd"],"router_mae_usd":r["mae_usd"],
            "paired_pnl_delta_router_minus_d":float(r["pnl_inr"])-float(d["pnl_inr"]),
        })
    for j,r in enumerate(rtrades):
        if j in used: continue
        rows.append({
            "window":r["window"],"interval":r["interval"],"segment_id":r["segment_id"],
            "pair_type":"router_unmatched","entry_delta_sec":math.nan,
            "candidate_d_engine":"","candidate_d_side":"","candidate_d_entry_ts":math.nan,"candidate_d_exit_ts":math.nan,
            "candidate_d_exit_reason":"","candidate_d_pnl_inr":math.nan,"candidate_d_mfe_usd":math.nan,"candidate_d_mae_usd":math.nan,
            "router_engine":r["engine"],"router_side":r["side"],
            "router_entry_ts":r["entry_ts"],"router_exit_ts":r["exit_ts"],
            "router_exit_reason":r["exit_reason"],"router_pnl_inr":r["pnl_inr"],
            "router_mfe_usd":r["mfe_usd"],"router_mae_usd":r["mae_usd"],
            "paired_pnl_delta_router_minus_d":math.nan,
        })
    return rows


def summarize_segments(metrics):
    factor=1.0; trades=wins=0; dd=0.0
    for x in metrics:
        factor*=1.0+x["pnl_inr"]/500.0
        trades+=x["trades"]; wins+=x["wins"]; dd=max(dd,x["max_drawdown_inr"])
    return {
        "compounded_pnl_inr":500.0*(factor-1.0),"trades":trades,"wins":wins,
        "win_rate":wins/trades if trades else 0.0,"max_segment_drawdown_inr":dd,
    }


def write_csv(path,rows):
    if not rows:
        path.write_text("",encoding="utf-8"); return
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


def aggregate_events(events):
    groups={}
    for e in events:
        key=(e["window"],e["interval"],e["classification"])
        g=groups.setdefault(key,{"count":0,"cf_count":0,"cf_delta_sum":0.0,"d_cf_sum":0.0,"router_cf_sum":0.0})
        g["count"]+=1
        if np.isfinite(e["cf_delta_router_minus_d"]):
            g["cf_count"]+=1
            g["cf_delta_sum"]+=float(e["cf_delta_router_minus_d"])
            g["d_cf_sum"]+=float(e["d_cf_pnl_500"])
            g["router_cf_sum"]+=float(e["router_cf_pnl_500"])
    out=[]
    for (window,interval,cls),g in sorted(groups.items()):
        out.append({"window":window,"interval":interval,"classification":cls,**g,
                    "cf_delta_mean":g["cf_delta_sum"]/g["cf_count"] if g["cf_count"] else math.nan})
    return out


def substitution_matrix(events):
    groups={}
    for e in events:
        if e["classification"]!="direct_score_substitution": continue
        key=(e["window"],e["interval"],e["candidate_d_action"],e["router_action"])
        g=groups.setdefault(key,{"count":0,"cf_count":0,"cf_delta_sum":0.0})
        g["count"]+=1
        if np.isfinite(e["cf_delta_router_minus_d"]):
            g["cf_count"]+=1; g["cf_delta_sum"]+=float(e["cf_delta_router_minus_d"])
    return [
        {"window":k[0],"interval":k[1],"candidate_d_action":k[2],"router_action":k[3],
         **v,"cf_delta_mean":v["cf_delta_sum"]/v["cf_count"] if v["cf_count"] else math.nan}
        for k,v in sorted(groups.items())
    ]


def aggregate_trade_pairs(rows,by_segment=False):
    groups={}
    for r in rows:
        key=(r["window"],r["interval"],r["segment_id"],r["pair_type"]) if by_segment else (r["window"],r["interval"],r["pair_type"])
        g=groups.setdefault(key,{"count":0,"candidate_d_pnl_sum":0.0,"router_pnl_sum":0.0,"paired_delta_sum":0.0,"paired_delta_count":0})
        g["count"]+=1
        for field,out in (("candidate_d_pnl_inr","candidate_d_pnl_sum"),("router_pnl_inr","router_pnl_sum")):
            try:
                v=float(r[field])
            except (TypeError,ValueError):
                v=math.nan
            if np.isfinite(v):
                g[out]+=v
        try:
            d=float(r["paired_pnl_delta_router_minus_d"])
        except (TypeError,ValueError):
            d=math.nan
        if np.isfinite(d):
            g["paired_delta_sum"]+=d; g["paired_delta_count"]+=1
    out=[]
    for key,g in sorted(groups.items()):
        if by_segment:
            window,interval,segment_id,pair_type=key
            out.append({"window":window,"interval":interval,"segment_id":segment_id,"pair_type":pair_type,**g})
        else:
            window,interval,pair_type=key
            out.append({"window":window,"interval":interval,"pair_type":pair_type,**g})
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("canonical_csv",type=Path)
    ap.add_argument("recent_csv_or_gz",type=Path)
    ap.add_argument("--output",type=Path,default=DEFAULT_OUT)
    a=ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True,exist_ok=True)

    all_events=[]; all_pairs=[]; all_dtrades=[]; all_rtrades=[]; segment_rows=[]
    summary={
        "schema":"xau-router-v2-arbitration-audit-v1",
        "strategy_changed":False,"score_changed":False,"holdout_opened":False,
        "known_data_only":True,"intervals":{}
    }

    for interval in ("500ms","1s"):
        print(f"{interval}: canonical feature build",flush=True)
        arr,bounds=canonical.build_features(a.canonical_csv,interval)
        canonical.assert_baseline(canonical.run_strategy(arr,bounds,"v4_4"),interval,canonical.DEFAULT_GOLDEN)
        print(f"{interval}: canonical state cache",flush=True)
        cache=router.build_state_cache(a.canonical_csv,arr)
        d_metrics=[]; r_metrics=[]

        for sid,(start,end) in enumerate(autopsy.indices(arr,bounds)):
            d,rv,events,dm,rm=run_dual(arr,start,end,cache,"historical7d",interval,sid)
            # Instrumented simulator must be identical to the Experiment-30 engine.
            assert_same(dm,router.simulate(arr,start,end,legacy=True),f"{interval} historical s{sid} candidate D")
            assert_same(rm,router.simulate(arr,start,end,cache=cache,legacy=False),f"{interval} historical s{sid} router")
            d_metrics.append(dm); r_metrics.append(rm)
            all_events.extend(events); all_dtrades.extend(d["trades"]); all_rtrades.extend(rv["trades"])
            pairs=match_trades(d["trades"],rv["trades"]); all_pairs.extend(pairs)
            segment_rows.append({
                "window":"historical7d","interval":interval,"segment_id":sid,
                "candidate_d_pnl_inr":dm["pnl_inr"],"router_v2_pnl_inr":rm["pnl_inr"],
                "pnl_delta_router_minus_d":rm["pnl_inr"]-dm["pnl_inr"],
                "candidate_d_trades":dm["trades"],"router_v2_trades":rm["trades"],
                "candidate_d_wins":dm["wins"],"router_v2_wins":rm["wins"],
                "decision_divergences":len(events),
            })

        ds=summarize_segments(d_metrics); rs=summarize_segments(r_metrics)
        exp=EXPECTED[interval]
        if abs(ds["compounded_pnl_inr"]-exp["candidate_d"])>1e-6 or ds["trades"]!=exp["candidate_trades"]:
            raise RuntimeError(f"{interval} Candidate D canonical parity failed: {ds}")
        if abs(rs["compounded_pnl_inr"]-exp["router_v2"])>1e-6 or rs["trades"]!=exp["router_trades"]:
            raise RuntimeError(f"{interval} Router v2 canonical parity failed: {rs}")

        del arr,cache
        print(f"{interval}: recent feature build",flush=True)
        arr,_=canonical.build_features(a.recent_csv_or_gz,interval)
        print(f"{interval}: recent state cache",flush=True)
        cache=router.build_state_cache(a.recent_csv_or_gz,arr)
        d,rv,events,dm,rm=run_dual(arr,0,len(arr["t"]),cache,"recent24h",interval,0)
        assert_same(dm,router.simulate(arr,0,len(arr["t"]),legacy=True),f"{interval} recent candidate D")
        assert_same(rm,router.simulate(arr,0,len(arr["t"]),cache=cache,legacy=False),f"{interval} recent router")
        all_events.extend(events); all_dtrades.extend(d["trades"]); all_rtrades.extend(rv["trades"])
        all_pairs.extend(match_trades(d["trades"],rv["trades"]))
        segment_rows.append({
            "window":"recent24h","interval":interval,"segment_id":0,
            "candidate_d_pnl_inr":dm["pnl_inr"],"router_v2_pnl_inr":rm["pnl_inr"],
            "pnl_delta_router_minus_d":rm["pnl_inr"]-dm["pnl_inr"],
            "candidate_d_trades":dm["trades"],"router_v2_trades":rm["trades"],
            "candidate_d_wins":dm["wins"],"router_v2_wins":rm["wins"],
            "decision_divergences":len(events),
        })

        summary["intervals"][interval]={
            "canonical_first80":{"candidate_d":ds,"router_v2":rs,"pnl_delta_inr":rs["compounded_pnl_inr"]-ds["compounded_pnl_inr"]},
            "recent24h":{"candidate_d":dm,"router_v2":rm,"pnl_delta_inr":rm["pnl_inr"]-dm["pnl_inr"]},
        }
        del arr,cache

    event_summary=aggregate_events(all_events)
    subs=substitution_matrix(all_events)
    top_damage=sorted(
        [e for e in all_events if np.isfinite(e["cf_delta_router_minus_d"])],
        key=lambda e:e["cf_delta_router_minus_d"]
    )[:50]

    summary["event_class_summary"]=event_summary
    summary["direct_substitution_matrix"]=subs
    summary["total_divergence_events"]=len(all_events)
    summary["top_counterfactual_damage_events"]=[
        {k:e[k] for k in ("window","interval","segment_id","timestamp","classification",
                           "candidate_d_action","router_action","d_cf_pnl_500","router_cf_pnl_500",
                           "cf_delta_router_minus_d")}
        for e in top_damage[:20]
    ]

    write_csv(a.output/"segment_damage.csv",segment_rows)
    write_csv(a.output/"arbitration_events.csv",all_events)
    write_csv(a.output/"trade_pairs.csv",all_pairs)
    write_csv(a.output/"candidate_d_trades.csv",all_dtrades)
    write_csv(a.output/"router_v2_trades.csv",all_rtrades)
    write_csv(a.output/"decision_category_summary.csv",event_summary)
    write_csv(a.output/"substitution_matrix.csv",subs)
    write_csv(a.output/"top_damage_events.csv",top_damage)
    write_csv(a.output/"trade_pair_summary.csv",aggregate_trade_pairs(all_pairs,False))
    write_csv(a.output/"segment_pair_damage.csv",aggregate_trade_pairs(all_pairs,True))
    (a.output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
