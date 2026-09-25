"""Experiment 34: frozen SNAPBACK complementary-engine foundation.

No threshold search is allowed. Signal constants are inherited from Candidate-D
MICRO/global gates and the ER60 complement; lifecycle constants are inherited
from the short BURST lane, excluding BURST's trend-following m30 failure exit.

Known data may reject SNAPBACK but cannot promote or tune it.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_regime_portability as portability
import v4_5_state_v2_freeze as state_v2

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OUT=ROOT/"results"/"simulations"/"2026-09-25-v4_5-snapback-foundation"
FIXED_BALANCE=500.0
COOLDOWN_SEC=60.0
STOP_USD=4.0
TP_USD=12.0
MAX_HOLD_SEC=120.0
STAGNATION_AFTER_SEC=60.0
STAGNATION_PEAK_USD=0.80
TRAIL_TRIGGER_USD=5.50
TRAIL_GIVEBACK_USD=2.0
SLIPPAGE_PER_SIDE_USD=0.20
BLOCK_SEC=4*3600.0


def fixed_oz(entry):
    return min(
        FIXED_BALANCE*0.03/(STOP_USD*canonical.INR_PER_USD),
        (FIXED_BALANCE/canonical.INR_PER_USD*100)/entry,
    )


def signal(arr,i,last_exit):
    t,spread=arr["t"],arr["spread"]
    m10,m60,m120=arr["m10"],arr["m60"],arr["m120"]
    r60,er60,qacc,imb=arr["range60"],arr["er60"],arr["qacc"],arr["imb10"]
    min10,max10=arr["min_m10_30"],arr["max_m10_30"]
    ts=float(t[i])
    if ts-last_exit<COOLDOWN_SEC:
        return 0
    vals=(m10[i],m60[i],m120[i],r60[i],er60[i],min10[i],max10[i])
    if not all(np.isfinite(x) for x in vals):
        return 0
    if spread[i]>0.30 or r60[i]<2.0 or er60[i]>=0.12 or qacc[i]<0.65 or spread[i]>0.25*r60[i]:
        return 0
    # Background uptrend failing into countertrend SELL.
    if m120[i]>=6.0 and m60[i]>=2.0 and max10[i]>=0.50 and m10[i]<=-0.20 and imb[i]<=0:
        return -1
    # Background downtrend failing into countertrend BUY.
    if m120[i]<=-6.0 and m60[i]<=-2.0 and min10[i]<=-0.50 and m10[i]>=0.20 and imb[i]>=0:
        return 1
    return 0


def simulate_lane(arr,start,end,interval,window,segment_id):
    t,bid,ask=arr["t"],arr["bid"],arr["ask"]
    pos=0; side=0; entry=0.0; oz=0.0; ptime=0.0; entry_index=-1
    peak=0.0; trough=0.0; last_exit=-1e30; rows=[]
    prev_ss=None

    for i in range(start,end):
        ts=float(t[i])
        if prev_ss is None or arr["ss"][i]!=prev_ss:
            # Session discontinuity invalidates any open path; mark terminal/censored
            # rather than pretending the gap was tradable.
            if pos:
                j=max(start,i-1)
                move=(bid[j]-entry) if side==1 else (entry-ask[j])
                rows.append({
                    "window":window,"interval":interval,"segment_id":segment_id,
                    "engine":"SNAPBACK","side":"BUY" if side==1 else "SELL","side_sign":side,
                    "entry_index":entry_index,"exit_index":j,"entry_ts":ptime,"exit_ts":float(t[j]),
                    "hold_sec":float(t[j]-ptime),"exit_reason":"session_boundary_mark",
                    "entry_usd":entry,"entry_oz":oz,
                    "pnl_inr":float(move)*oz*canonical.INR_PER_USD,
                    "mfe_usd":peak,"mae_usd":trough,"censored":True,
                    "fixed_balance_inr":FIXED_BALANCE,
                })
                pos=0
            prev_ss=arr["ss"][i]

        if pos:
            move=(bid[i]-entry) if side==1 else (entry-ask[i])
            held=ts-ptime
            peak=max(peak,float(move)); trough=min(trough,float(move))
            reason=None
            if move<=-STOP_USD:
                reason="emergency_stop"
            elif move>=TP_USD:
                reason="take_profit"
            elif peak>=TRAIL_TRIGGER_USD and move<=peak-TRAIL_GIVEBACK_USD:
                reason="trail"
            elif held>=STAGNATION_AFTER_SEC and peak<STAGNATION_PEAK_USD:
                reason="stagnation"
            elif held>=MAX_HOLD_SEC:
                reason="max_hold"
            if reason is not None:
                pnl=float(move)*oz*canonical.INR_PER_USD
                rows.append({
                    "window":window,"interval":interval,"segment_id":segment_id,
                    "engine":"SNAPBACK","side":"BUY" if side==1 else "SELL","side_sign":side,
                    "entry_index":entry_index,"exit_index":i,"entry_ts":ptime,"exit_ts":ts,
                    "hold_sec":held,"exit_reason":reason,
                    "entry_usd":entry,"entry_oz":oz,
                    "pnl_inr":pnl,"mfe_usd":peak,"mae_usd":trough,
                    "censored":False,"fixed_balance_inr":FIXED_BALANCE,
                })
                last_exit=ts; pos=0
            continue

        s=signal(arr,i,last_exit)
        if not s:
            continue
        entry=float(ask[i] if s==1 else bid[i])
        oz=fixed_oz(entry)
        pos=1; side=s; ptime=ts; entry_index=i
        peak=0.0; trough=0.0

    if pos and end>start:
        j=end-1
        move=(bid[j]-entry) if side==1 else (entry-ask[j])
        peak=max(peak,float(move)); trough=min(trough,float(move))
        rows.append({
            "window":window,"interval":interval,"segment_id":segment_id,
            "engine":"SNAPBACK","side":"BUY" if side==1 else "SELL","side_sign":side,
            "entry_index":entry_index,"exit_index":j,"entry_ts":ptime,"exit_ts":float(t[j]),
            "hold_sec":float(t[j]-ptime),"exit_reason":"terminal_mark",
            "entry_usd":entry,"entry_oz":oz,
            "pnl_inr":float(move)*oz*canonical.INR_PER_USD,
            "mfe_usd":peak,"mae_usd":trough,"censored":True,
            "fixed_balance_inr":FIXED_BALANCE,
        })
    return rows


def write_csv(path,rows):
    if not rows:
        path.write_text("",encoding="utf-8"); return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=fields);w.writeheader();w.writerows(rows)


def realized(rows):
    return [r for r in rows if not bool(r.get("censored",False))]


def stats(rows):
    out=[]
    df=pd.DataFrame(realized(rows))
    if df.empty:return out
    for (window,interval),g in df.groupby(["window","interval"],sort=True):
        p=pd.to_numeric(g.pnl_inr)
        gp=float(p[p>0].sum()); gl=float(-p[p<0].sum())
        curve=p.cumsum(); peak=curve.cummax().clip(lower=0.0)
        slip=2.0*SLIPPAGE_PER_SIDE_USD*pd.to_numeric(g.entry_oz)*canonical.INR_PER_USD
        stressed=p-slip
        out.append({
            "window":window,"interval":interval,"trades":len(g),"wins":int((p>0).sum()),
            "win_rate":float((p>0).mean()),"pnl_inr":float(p.sum()),
            "mean_pnl_inr":float(p.mean()),"median_pnl_inr":float(p.median()),
            "profit_factor":gp/gl if gl>0 else 999.0,
            "fixed_size_max_drawdown_inr":float((peak-curve).max()) if len(curve) else 0.0,
            "stressed_20c_each_side_pnl_inr":float(stressed.sum()),
            "stressed_20c_each_side_win_rate":float((stressed>0).mean()),
            "emergency_stops":int((g.exit_reason=="emergency_stop").sum()),
            "max_holds":int((g.exit_reason=="max_hold").sum()),
        })
    return out


def block_rows(rows):
    df=pd.DataFrame(realized(rows))
    if df.empty:return []
    df["block_id"]=(pd.to_numeric(df.entry_ts)//BLOCK_SEC).astype("int64")
    out=[]
    for (window,interval,bid),g in df.groupby(["window","interval","block_id"],sort=True):
        p=pd.to_numeric(g.pnl_inr)
        out.append({"window":window,"interval":interval,"block_id":int(bid),
                    "trades":len(g),"wins":int((p>0).sum()),"win_rate":float((p>0).mean()),
                    "pnl_inr":float(p.sum())})
    return out


def block_summary(blocks):
    df=pd.DataFrame(blocks)
    if df.empty:return []
    out=[]
    for (window,interval),g in df.groupby(["window","interval"],sort=True):
        p=pd.to_numeric(g.pnl_inr)
        out.append({"window":window,"interval":interval,"blocks":len(g),
                    "positive_block_fraction":float((p>0).mean()),
                    "median_block_pnl_inr":float(p.median()),
                    "mean_block_pnl_inr":float(p.mean()),
                    "p10_block_pnl_inr":float(p.quantile(.10)),
                    "p90_block_pnl_inr":float(p.quantile(.90))})
    return out


def match_grids(rows):
    a=sorted([r for r in realized(rows) if r["interval"]=="500ms"],key=lambda x:x["entry_ts"])
    b=sorted([r for r in realized(rows) if r["interval"]=="1s"],key=lambda x:x["entry_ts"])
    used=set(); out=[]
    for x in a:
        best=None
        for j,y in enumerate(b):
            if j in used or y["window"]!=x["window"] or y["side"]!=x["side"]:continue
            dt=abs(float(y["entry_ts"])-float(x["entry_ts"]))
            if dt>120:continue
            key=(dt,j)
            if best is None or key<best[0]:best=(key,j,y)
        if best is None:continue
        _,j,y=best;used.add(j)
        out.append({"window":x["window"],"side":x["side"],
                    "entry_500ms":x["entry_ts"],"entry_1s":y["entry_ts"],
                    "entry_delta_sec":float(y["entry_ts"])-float(x["entry_ts"]),
                    "pnl_500ms":x["pnl_inr"],"pnl_1s":y["pnl_inr"],
                    "same_pnl_sign":bool(np.sign(float(x["pnl_inr"]))==np.sign(float(y["pnl_inr"])))})
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
        local=[]
        for sid,(s,e) in enumerate(ranges):
            local.extend(simulate_lane(arr,s,e,interval,window,sid))
        rows.extend(state_v2.overlay(path,local,window))
        del arr
    return rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("canonical_csv",type=Path)
    ap.add_argument("recent_csv_or_gz",type=Path)
    ap.add_argument("--output",type=Path,default=DEFAULT_OUT)
    a=ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True,exist_ok=True)

    historical=run_dataset(a.canonical_csv,"historical7d",True)
    recent=run_dataset(a.recent_csv_or_gz,"recent24h",False)
    rows=historical+recent
    summary_rows=stats(rows)
    blocks=block_rows(rows)
    block_stats=block_summary(blocks)
    matches=match_grids(rows)

    write_csv(a.output/"snapback_opportunities.csv",rows)
    write_csv(a.output/"summary_by_window.csv",summary_rows)
    write_csv(a.output/"four_hour_blocks.csv",blocks)
    write_csv(a.output/"block_robustness.csv",block_stats)
    write_csv(a.output/"cross_grid_matches.csv",matches)

    result={
        "schema":"xau-snapback-foundation-v1",
        "strategy_changed":False,
        "selection_performed":False,
        "engine":"SNAPBACK",
        "signal_constants":{
            "cooldown_sec":COOLDOWN_SEC,"range60_min_usd":2.0,"er60_max_exclusive":0.12,
            "qacc_min":0.65,"spread_to_range_max":0.25,"spread_max_usd":0.30,
            "background_m120_abs_min":6.0,"background_m60_abs_min":2.0,
            "prior_background_m10_extreme_abs_min":0.50,"reversal_m10_abs_min":0.20,
            "imbalance_agrees_reversal":True,
        },
        "lifecycle":{
            "stop_usd":STOP_USD,"take_profit_usd":TP_USD,"max_hold_sec":MAX_HOLD_SEC,
            "stagnation_after_sec":STAGNATION_AFTER_SEC,"stagnation_peak_usd":STAGNATION_PEAK_USD,
            "trail_trigger_usd":TRAIL_TRIGGER_USD,"trail_giveback_usd":TRAIL_GIVEBACK_USD,
            "m30_failure_exit":False,
        },
        "cost_stress_usd_per_side":SLIPPAGE_PER_SIDE_USD,
        "final20_opened":False,
        "promotion_evidence":False,
        "summary":summary_rows,
        "block_robustness":block_stats,
        "cross_grid_matches":{
            "matches":len(matches),
            "same_sign_fraction":float(np.mean([r["same_pnl_sign"] for r in matches])) if matches else 0.0,
            "median_abs_entry_delta_sec":float(np.median([abs(r["entry_delta_sec"]) for r in matches])) if matches else math.nan,
        },
        "decision":"Known-data rejection/diagnostic only. Do not tune SNAPBACK constants from these results.",
    }
    (a.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
