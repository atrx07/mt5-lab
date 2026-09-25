"""Experiment 34: structurally frozen SNAPBACK countertrend engine.

SNAPBACK is a new independent opportunity generator, not a router tweak.
Its entry logic is defined as the natural low-efficiency complement of the
existing MICRO continuation setup, reusing Candidate-D thresholds rather than
searching new values on known P&L.

Known data may reject the engine but cannot promote it.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_regime_portability as portability

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OUT=ROOT/"results"/"simulations"/"2026-09-25-v4_5-snapback-foundation"
FIXED_BALANCE=500.0
COOLDOWN_SEC=60.0
BLOCK_SEC=4*3600.0
ADVERSE_SLIPPAGE_PER_SIDE_USD=0.20

# Entry constants are deliberately inherited from MICRO/global Candidate-D gates.
MIN_RANGE60=2.0
ER_SPLIT=0.12
MIN_QACC=0.65
MAX_SPREAD_RANGE=0.25
MAX_ABS_SPREAD=0.30
BACKGROUND_M120=6.0
BACKGROUND_M60=2.0
REVERSAL_M10=0.2
RECENT_M10_EXTREME=0.5

# Lifecycle is inherited from BURST except that momentum-zero-cross is disabled:
# a countertrend trade would otherwise fail immediately by construction.
STOP_USD=4.0
TP_USD=12.0
MAX_HOLD_SEC=120.0
STAGNATION_SEC=60.0
STAGNATION_PEAK_USD=0.80
TRAIL_TRIGGER_USD=5.5
TRAIL_GIVEBACK_USD=2.0


def fixed_oz(entry):
    return min(
        FIXED_BALANCE*0.03/(STOP_USD*canonical.INR_PER_USD),
        (FIXED_BALANCE/canonical.INR_PER_USD*100)/entry,
    )


def snapback_signal(arr,i,last_exit):
    t=arr["t"]; spread=arr["spread"]; imb=arr["imb10"]; qacc=arr["qacc"]
    m10,m60,m120=arr["m10"],arr["m60"],arr["m120"]
    r60,er60=arr["range60"],arr["er60"]
    min10,max10=arr["min_m10_30"],arr["max_m10_30"]
    ts=float(t[i])

    if ts-last_exit<COOLDOWN_SEC:
        return 0
    vals=(m10[i],m60[i],m120[i],r60[i],er60[i],min10[i],max10[i])
    if not all(np.isfinite(x) for x in vals):
        return 0
    if spread[i]>MAX_ABS_SPREAD:
        return 0
    if r60[i]<MIN_RANGE60 or er60[i]>=ER_SPLIT or qacc[i]<MIN_QACC:
        return 0
    if spread[i]>MAX_SPREAD_RANGE*r60[i]:
        return 0

    # Failed upward continuation -> short snapback.
    if (
        m120[i]>=BACKGROUND_M120 and m60[i]>=BACKGROUND_M60
        and max10[i]>=RECENT_M10_EXTREME and m10[i]<=-REVERSAL_M10
        and imb[i]<=0
    ):
        return -1

    # Failed downward continuation -> long snapback.
    if (
        m120[i]<=-BACKGROUND_M120 and m60[i]<=-BACKGROUND_M60
        and min10[i]<=-RECENT_M10_EXTREME and m10[i]>=REVERSAL_M10
        and imb[i]>=0
    ):
        return 1
    return 0


def simulate(arr,start,end,interval,window,segment_id):
    t,bid,ask=arr["t"],arr["bid"],arr["ask"]
    rows=[]; pos=0; side=0; entry=0.0; oz=0.0; ptime=0.0
    peak=0.0; trough=0.0; entry_index=-1; last_exit=-1e30

    for i in range(start,end):
        ts=float(t[i])
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
            elif held>=STAGNATION_SEC and peak<STAGNATION_PEAK_USD:
                reason="stagnation"
            elif held>=MAX_HOLD_SEC:
                reason="max_hold"

            if reason is not None:
                pnl=float(move)*oz*canonical.INR_PER_USD
                stressed=pnl-(2*ADVERSE_SLIPPAGE_PER_SIDE_USD*oz*canonical.INR_PER_USD)
                rows.append({
                    "window":window,"interval":interval,"segment_id":segment_id,
                    "engine":"SNAPBACK","side":"BUY" if side==1 else "SELL","side_sign":side,
                    "entry_index":entry_index,"exit_index":i,
                    "entry_ts":ptime,"exit_ts":ts,"hold_sec":held,
                    "exit_reason":reason,"entry_oz":oz,
                    "pnl_inr":pnl,"cost_stress_pnl_inr":stressed,
                    "mfe_usd":peak,"mae_usd":trough,"censored":False,
                })
                last_exit=ts; pos=0
            continue

        s=snapback_signal(arr,i,last_exit)
        if s==0:
            continue
        entry=float(ask[i] if s==1 else bid[i])
        oz=fixed_oz(entry)
        pos=1; side=s; ptime=ts; entry_index=i; peak=0.0; trough=0.0

    if pos and end>start:
        j=end-1
        move=(bid[j]-entry) if side==1 else (entry-ask[j])
        peak=max(peak,float(move)); trough=min(trough,float(move))
        pnl=float(move)*oz*canonical.INR_PER_USD
        stressed=pnl-(2*ADVERSE_SLIPPAGE_PER_SIDE_USD*oz*canonical.INR_PER_USD)
        rows.append({
            "window":window,"interval":interval,"segment_id":segment_id,
            "engine":"SNAPBACK","side":"BUY" if side==1 else "SELL","side_sign":side,
            "entry_index":entry_index,"exit_index":j,
            "entry_ts":ptime,"exit_ts":float(t[j]),"hold_sec":float(t[j]-ptime),
            "exit_reason":"terminal_mark","entry_oz":oz,
            "pnl_inr":pnl,"cost_stress_pnl_inr":stressed,
            "mfe_usd":peak,"mae_usd":trough,"censored":True,
        })
    return rows


def write_csv(path,rows):
    if not rows:
        path.write_text("",encoding="utf-8"); return
    with path.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)


def summarize(rows):
    realized=[r for r in rows if not r["censored"]]
    if not realized:
        return {"trades":0,"wins":0,"win_rate":0.0,"pnl_inr":0.0,"profit_factor":0.0}
    p=np.asarray([r["pnl_inr"] for r in realized],dtype=float)
    ps=np.asarray([r["cost_stress_pnl_inr"] for r in realized],dtype=float)
    gp=float(p[p>0].sum());gl=float(-p[p<0].sum())
    curve=np.cumsum(p);peak=np.maximum.accumulate(np.maximum(curve,0.0));dd=float(np.max(peak-curve))
    return {
        "trades":len(realized),"wins":int(np.sum(p>0)),"win_rate":float(np.mean(p>0)),
        "pnl_inr":float(p.sum()),"mean_pnl_inr":float(p.mean()),"median_pnl_inr":float(np.median(p)),
        "profit_factor":gp/gl if gl>0 else 999.0,"fixed_size_max_drawdown_inr":dd,
        "cost_stress_pnl_inr":float(ps.sum()),
        "emergency_stops":int(sum(r["exit_reason"]=="emergency_stop" for r in realized)),
        "take_profits":int(sum(r["exit_reason"]=="take_profit" for r in realized)),
    }


def block_rows(rows):
    realized=[r for r in rows if not r["censored"]]
    if not realized:return []
    df=pd.DataFrame(realized)
    df["block_id"]=(pd.to_numeric(df.entry_ts)//BLOCK_SEC).astype("int64")
    out=[]
    for (window,interval,bid),g in df.groupby(["window","interval","block_id"],sort=True):
        p=pd.to_numeric(g.pnl_inr)
        out.append({
            "window":window,"interval":interval,"block_id":int(bid),
            "trades":len(g),"wins":int((p>0).sum()),"pnl_inr":float(p.sum()),
            "win_rate":float((p>0).mean()),
        })
    return out


def block_summary(blocks):
    df=pd.DataFrame(blocks)
    if df.empty:return []
    out=[]
    for (window,interval),g in df.groupby(["window","interval"],sort=True):
        p=pd.to_numeric(g.pnl_inr)
        out.append({
            "window":window,"interval":interval,"blocks":len(g),
            "positive_block_fraction":float((p>0).mean()),
            "median_block_pnl_inr":float(p.median()),"mean_block_pnl_inr":float(p.mean()),
            "p10_block_pnl_inr":float(p.quantile(.10)),"p90_block_pnl_inr":float(p.quantile(.90)),
        })
    return out


def match_grids(rows):
    a=[r for r in rows if r["interval"]=="500ms" and not r["censored"]]
    b=[r for r in rows if r["interval"]=="1s" and not r["censored"]]
    used=set(); pairs=[]
    for x in sorted(a,key=lambda z:z["entry_ts"]):
        opts=[]
        for j,y in enumerate(b):
            if j in used or y["window"]!=x["window"] or y["side"]!=x["side"]:
                continue
            d=abs(float(y["entry_ts"])-float(x["entry_ts"]))
            if d<=120:
                opts.append((d,j,y))
        if not opts:continue
        d,j,y=min(opts,key=lambda q:q[0]);used.add(j)
        pairs.append({
            "window":x["window"],"entry_delta_sec":float(y["entry_ts"])-float(x["entry_ts"]),
            "side":x["side"],"pnl_500ms":x["pnl_inr"],"pnl_1s":y["pnl_inr"],
            "same_outcome_sign":bool(np.sign(x["pnl_inr"])==np.sign(y["pnl_inr"])),
        })
    return pairs


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("canonical_csv",type=Path)
    ap.add_argument("recent_csv_or_gz",type=Path)
    ap.add_argument("--output",type=Path,default=DEFAULT_OUT)
    a=ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True,exist_ok=True)

    all_rows=[]; result={
        "schema":"xau-snapback-foundation-v1",
        "strategy_changed":False,
        "engine_promoted":False,
        "parameter_search_performed":False,
        "final20_opened":False,
        "signal":{
            "description":"low-efficiency failed continuation; exact natural complement of MICRO direction logic",
            "cooldown_sec":COOLDOWN_SEC,"range60_min":MIN_RANGE60,"er60_max_exclusive":ER_SPLIT,
            "qacc_min":MIN_QACC,"spread_range_max":MAX_SPREAD_RANGE,"spread_abs_max":MAX_ABS_SPREAD,
            "background_m120_abs_min":BACKGROUND_M120,"background_m60_abs_min":BACKGROUND_M60,
            "reversal_m10_abs_min":REVERSAL_M10,"recent_m10_extreme_abs_min":RECENT_M10_EXTREME,
        },
        "lifecycle":{
            "stop_usd":STOP_USD,"tp_usd":TP_USD,"max_hold_sec":MAX_HOLD_SEC,
            "stagnation_sec":STAGNATION_SEC,"stagnation_peak_usd":STAGNATION_PEAK_USD,
            "trail_trigger_usd":TRAIL_TRIGGER_USD,"trail_giveback_usd":TRAIL_GIVEBACK_USD,
            "momentum_zero_cross":False,
        },
        "windows":{},
    }

    for window,path,canonical_mode in (
        ("historical7d",a.canonical_csv,True),
        ("recent24h",a.recent_csv_or_gz,False),
    ):
        result["windows"][window]={}
        for interval in ("500ms","1s"):
            print(f"{window} {interval}",flush=True)
            arr,bounds=canonical.build_features(path,interval)
            if canonical_mode:
                canonical.assert_baseline(canonical.run_strategy(arr,bounds,"v4_4"),interval,canonical.DEFAULT_GOLDEN)
                ranges=autopsy.indices(arr,bounds)
            else:
                ranges=[(0,len(arr["t"]))]
            rows=[]
            for sid,(s,e) in enumerate(ranges):
                rows.extend(simulate(arr,s,e,interval,window,sid))
            all_rows.extend(rows)
            result["windows"][window][interval]=summarize(rows)
            del arr

    blocks=block_rows(all_rows); bsum=block_summary(blocks); pairs=match_grids(all_rows)
    write_csv(a.output/"snapback_trades.csv",all_rows)
    write_csv(a.output/"four_hour_blocks.csv",blocks)
    write_csv(a.output/"block_robustness.csv",bsum)
    write_csv(a.output/"cross_grid_pairs.csv",pairs)

    result["block_robustness"]=bsum
    result["cross_grid"]={
        "pairs":len(pairs),
        "same_outcome_sign_fraction":float(np.mean([p["same_outcome_sign"] for p in pairs])) if pairs else 0.0,
        "median_abs_entry_delta_sec":float(np.median(np.abs([p["entry_delta_sec"] for p in pairs]))) if pairs else None,
    }
    result["decision"]="Known-data diagnostic only. Do not tune SNAPBACK from these outcomes; future promotion requires a new non-overlapping snapshot."
    (a.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
