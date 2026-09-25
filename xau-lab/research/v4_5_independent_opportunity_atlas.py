"""Experiment 33: independent engine shadow-lane opportunity atlas.

No trading strategy is changed. Each existing Candidate-D engine is replayed in
its own independent one-position shadow lane using fixed ₹500 sizing. This
removes shared-slot competition, cross-engine cooldown cascades and compounding
from the outcome labels.

Purpose: determine whether the current four-engine family contains genuinely
complementary edge across changing windows before designing another router.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_regime_portability as portability
import v4_5_router_v2 as router
import v4_5_state_v2_freeze as state_v2

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OUT=ROOT/"results"/"simulations"/"2026-09-25-v4_5-independent-opportunity-atlas"
REASONS={1:"emergency_stop",2:"take_profit",3:"trail",4:"stagnation",5:"momentum_zero_cross",7:"max_hold"}
ENGINES=(1,2,3,4)
FIXED_BALANCE=500.0
BLOCK_SEC=4*3600.0


def fixed_oz(entry):
    return min(
        FIXED_BALANCE*0.03/(4*canonical.INR_PER_USD),
        (FIXED_BALANCE/canonical.INR_PER_USD*100)/entry,
    )


def simulate_lane(arr,start,end,engine,interval,window,segment_id):
    t,bid,ask=arr["t"],arr["bid"],arr["ask"]
    m30,m300=arr["m30"],arr["m300"]
    r300,er60=arr["range300"],arr["er60"]
    cfg=canonical.burst_config("v4_5_b")

    pos=0; side=0; entry=0.0; oz=0.0; ptime=0.0
    peak=0.0; trough=0.0; partial=0.0; partial_done=0
    highopen=0; failure_since=-1e30; entry_index=-1
    last={1:-1e30,2:-1e30,3:-1e30,4:-1e30}
    prev_ss=None; cont=0.0; rows=[]

    for i in range(start,end):
        ts=float(t[i])
        if prev_ss is None or arr["ss"][i]!=prev_ss:
            cont=ts; prev_ss=arr["ss"][i]

        if pos:
            move=(bid[i]-entry) if side==1 else (entry-ask[i])
            held=ts-ptime
            peak=max(peak,float(move)); trough=min(trough,float(move))

            if pos==3 and partial_done==0 and move>=5.5:
                closeoz=oz*0.75
                partial+=float(move)*closeoz*canonical.INR_PER_USD
                oz-=closeoz; partial_done=1

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
                pnl=float(move)*oz*canonical.INR_PER_USD+partial
                rows.append({
                    "window":window,"interval":interval,"segment_id":segment_id,
                    "engine":router.ENGINE_NAMES[engine],
                    "side":"BUY" if side==1 else "SELL","side_sign":side,
                    "entry_index":entry_index,"exit_index":i,
                    "entry_ts":ptime,"exit_ts":ts,"hold_sec":held,
                    "exit_reason":REASONS.get(reason,str(reason)),
                    "pnl_inr":pnl,"mfe_usd":peak,"mae_usd":trough,
                    "censored":False,"fixed_balance_inr":FIXED_BALANCE,
                })
                last[engine]=ts; pos=0
            continue

        candidates=router.signal_candidates(arr,i,cont,last)
        match=next(((e,s) for e,s in candidates if e==engine),None)
        if match is None:
            continue

        _,sside=match
        high=bool(np.isfinite(r300[i]) and np.isfinite(er60[i]) and r300[i]>=5.0 and er60[i]>=0.03)
        entry=float(ask[i] if sside==1 else bid[i])
        oz=fixed_oz(entry)
        pos=engine; side=sside; ptime=ts; entry_index=i
        peak=0.0; trough=0.0; partial=0.0; partial_done=0
        highopen=1 if high else 0; failure_since=-1e30

    if pos and end>start:
        j=end-1
        move=(bid[j]-entry) if side==1 else (entry-ask[j])
        peak=max(peak,float(move)); trough=min(trough,float(move))
        rows.append({
            "window":window,"interval":interval,"segment_id":segment_id,
            "engine":router.ENGINE_NAMES[engine],
            "side":"BUY" if side==1 else "SELL","side_sign":side,
            "entry_index":entry_index,"exit_index":j,
            "entry_ts":ptime,"exit_ts":float(t[j]),"hold_sec":float(t[j]-ptime),
            "exit_reason":"terminal_mark",
            "pnl_inr":float(move)*oz*canonical.INR_PER_USD+partial,
            "mfe_usd":peak,"mae_usd":trough,
            "censored":True,"fixed_balance_inr":FIXED_BALANCE,
        })
    return rows


def write_csv(path,rows):
    if not rows:
        path.write_text("",encoding="utf-8"); return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows(rows)


def engine_stats(rows):
    out=[]
    df=pd.DataFrame([r for r in rows if not bool(r.get("censored",False))])
    if df.empty:
        return out
    for (window,interval,engine),g in df.groupby(["window","interval","engine"],sort=True):
        pnl=pd.to_numeric(g.pnl_inr)
        gp=float(pnl[pnl>0].sum()); gl=float(-pnl[pnl<0].sum())
        ordered=g.sort_values("entry_ts")
        curve=pd.to_numeric(ordered.pnl_inr).cumsum()
        peak=curve.cummax().clip(lower=0.0)
        dd=float((peak-curve).max()) if len(curve) else 0.0
        out.append({
            "window":window,"interval":interval,"engine":engine,
            "trades":len(g),"wins":int((pnl>0).sum()),"win_rate":float((pnl>0).mean()),
            "pnl_inr":float(pnl.sum()),"mean_pnl_inr":float(pnl.mean()),
            "median_pnl_inr":float(pnl.median()),
            "profit_factor":gp/gl if gl>0 else 999.0,
            "fixed_size_max_drawdown_inr":dd,
            "emergency_stops":int((g.exit_reason=="emergency_stop").sum()),
            "max_holds":int((g.exit_reason=="max_hold").sum()),
        })
    return out


def block_stats(rows):
    df=pd.DataFrame([r for r in rows if not bool(r.get("censored",False))])
    if df.empty:return []
    df["block_id"]=(pd.to_numeric(df.entry_ts)//BLOCK_SEC).astype("int64")
    out=[]
    for (window,interval,engine,bid),g in df.groupby(["window","interval","engine","block_id"],sort=True):
        pnl=pd.to_numeric(g.pnl_inr)
        out.append({
            "window":window,"interval":interval,"engine":engine,"block_id":int(bid),
            "trades":len(g),"wins":int((pnl>0).sum()),"pnl_inr":float(pnl.sum()),
            "win_rate":float((pnl>0).mean()),
        })
    return out


def robustness_stats(blocks):
    df=pd.DataFrame(blocks)
    if df.empty:return []
    out=[]
    for (window,interval,engine),g in df.groupby(["window","interval","engine"],sort=True):
        p=pd.to_numeric(g.pnl_inr)
        out.append({
            "window":window,"interval":interval,"engine":engine,
            "blocks":len(g),"positive_block_fraction":float((p>0).mean()),
            "median_block_pnl_inr":float(p.median()),
            "mean_block_pnl_inr":float(p.mean()),
            "p10_block_pnl_inr":float(p.quantile(.10)),
            "p90_block_pnl_inr":float(p.quantile(.90)),
        })
    return out


def overlap_stats(rows):
    df=pd.DataFrame([r for r in rows if not bool(r.get("censored",False))])
    if df.empty:return []
    out=[]
    for (window,interval),g in df.groupby(["window","interval"],sort=True):
        clusters=g.groupby("entry_ts").engine.agg(lambda s:tuple(sorted(set(s))))
        multi=clusters[clusters.map(len)>1]
        combos={}
        for engines in multi:
            key="|".join(engines); combos[key]=combos.get(key,0)+1
        out.append({
            "window":window,"interval":interval,
            "entry_events":int(len(clusters)),
            "simultaneous_multi_engine_events":int(len(multi)),
            "simultaneous_fraction":float(len(multi)/len(clusters)) if len(clusters) else 0.0,
            "combinations":json.dumps(combos,sort_keys=True,separators=(",",":")),
        })
    return out


def cross_window(stats):
    df=pd.DataFrame(stats)
    if df.empty:return []
    out=[]
    for interval in sorted(df.interval.unique()):
        for engine in sorted(df.engine.unique()):
            a=df[(df.window=="historical7d")&(df.interval==interval)&(df.engine==engine)]
            b=df[(df.window=="recent24h")&(df.interval==interval)&(df.engine==engine)]
            if a.empty or b.empty:continue
            x=a.iloc[0]; y=b.iloc[0]
            out.append({
                "interval":interval,"engine":engine,
                "historical_pnl_inr":float(x.pnl_inr),"recent_pnl_inr":float(y.pnl_inr),
                "historical_win_rate":float(x.win_rate),"recent_win_rate":float(y.win_rate),
                "historical_trades":int(x.trades),"recent_trades":int(y.trades),
                "same_pnl_sign":bool(np.sign(x.pnl_inr)==np.sign(y.pnl_inr)),
            })
    return out


def outcome_profiles(rows):
    realized=[r for r in rows if not bool(r.get("censored",False))]
    df=pd.DataFrame(realized)
    if df.empty:return []
    out=[]
    for (window,interval,engine,outcome),g in df.assign(
        outcome=np.where(pd.to_numeric(df.pnl_inr)>0,"win","nonwin")
    ).groupby(["window","interval","engine","outcome"],sort=True):
        row={"window":window,"interval":interval,"engine":engine,"outcome":outcome,"trades":len(g),"pnl_inr":float(pd.to_numeric(g.pnl_inr).sum())}
        for feat in state_v2.FEATURES:
            row[feat]=float(pd.to_numeric(g[feat],errors="coerce").median())
        out.append(row)
    return out


def run_dataset(path,window,canonical_mode):
    rows=[]
    for interval in ("500ms","1s"):
        arr,bounds=canonical.build_features(path,interval)
        if canonical_mode:
            canonical.assert_baseline(canonical.run_strategy(arr,bounds,"v4_4"),interval,canonical.DEFAULT_GOLDEN)
            ranges=autopsy.indices(arr,bounds)
        else:
            ranges=[(0,len(arr["t"]))]
        for engine in ENGINES:
            for sid,(s,e) in enumerate(ranges):
                rows.extend(simulate_lane(arr,s,e,engine,interval,window,sid))
        del arr
    return state_v2.overlay(path,rows,window)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("canonical_csv",type=Path)
    ap.add_argument("recent_csv_or_gz",type=Path)
    ap.add_argument("--output",type=Path,default=DEFAULT_OUT)
    a=ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True,exist_ok=True)

    print("building independent historical shadow lanes",flush=True)
    historical=run_dataset(a.canonical_csv,"historical7d",True)
    print("building independent recent shadow lanes",flush=True)
    recent=run_dataset(a.recent_csv_or_gz,"recent24h",False)
    rows=historical+recent

    stats=engine_stats(rows)
    blocks=block_stats(rows)
    robust=robustness_stats(blocks)
    overlap=overlap_stats(rows)
    cross=cross_window(stats)
    profiles=outcome_profiles(rows)

    write_csv(a.output/"shadow_opportunities.csv",rows)
    write_csv(a.output/"engine_summary.csv",stats)
    write_csv(a.output/"four_hour_blocks.csv",blocks)
    write_csv(a.output/"engine_block_robustness.csv",robust)
    write_csv(a.output/"simultaneous_opportunities.csv",overlap)
    write_csv(a.output/"cross_window_engine_summary.csv",cross)
    write_csv(a.output/"state_outcome_profiles.csv",profiles)

    result={
        "schema":"xau-independent-opportunity-atlas-v1",
        "strategy_changed":False,
        "selection_performed":False,
        "fixed_balance_inr":FIXED_BALANCE,
        "shared_slot_removed_for_diagnostic":True,
        "cross_engine_cooldown_removed_for_diagnostic":True,
        "compounding_removed_for_labels":True,
        "final20_opened":False,
        "historical_rows":len(historical),
        "recent_rows":len(recent),
        "engine_summary":stats,
        "block_robustness":robust,
        "simultaneous_opportunities":overlap,
        "cross_window":cross,
        "decision":"Measure engine-family complementarity only. Do not select a new router or threshold from this known-data atlas.",
    }
    (a.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
