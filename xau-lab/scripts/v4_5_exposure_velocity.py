"""Experiment 20: parity-gated PRIMARY/SECONDARY exposure diagnostics and candidate replay."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
import v4_5_burst_path_autopsy as autopsy
import canonical_replay as canonical
from v4_5_confirmed_failure import summarize
njit=autopsy.njit
INR_PER_USD=canonical.INR_PER_USD
@njit(cache=True)
def simulate_velocity(
    t,bid,ask,mid,spread,ss,imb,qacc,m10,m30,m60,m120,m300,m1800,
    r60,r300,er60,min10,max10,min60,max60,chh,chl,start,end,burst_cfg,confirm_sec,checkpoint_sec,secondary_persist_sec,secondary_flow_mode
):
    # burst_cfg = enabled,cooldown,m10,m30,m60,er,qacc,imb,r60,maxspratio,abs_spread,tp,maxhold,stagsec,stagpeak,trailtrig,trailgb
    bal=500.; lp=-1e30; ls=-1e30; lm=-1e30; lb=-1e30
    pos=0; side=0; entry=0.; oz=0.; ptime=0.; peak=0.; trough=0.; mfe_time=0.; partial=0.; partial_done=0; highopen=0; entry_i=-1; entry_oz=0.
    prevss=-1; cont=0.; gp=0.; gl=0.; ntr=0; win=0; peakbal=500.; maxdd=0.
    failure_since=-1e30
    secondary_since=-1e30; secondary_side=0
    log=np.zeros((2048,14),dtype=np.float64); nlog=0
    checkpoints=np.full((2048,3,7),np.nan,dtype=np.float64)
    next_checkpoint=0; candidate_checkpoint_seen=0

    for i in range(start,end):
        ts=t[i]
        if ss[i] != prevss:
            cont=ts; prevss=ss[i]
            secondary_since=-1e30; secondary_side=0

        if pos != 0:
            move=(bid[i]-entry) if side==1 else (entry-ask[i])
            held=ts-ptime
            if move>peak: peak=move; mfe_time=ts-ptime
            if move<trough: trough=move
            if pos==1 or pos==2:
                while next_checkpoint<3 and held>=((60.,120.,300.)[next_checkpoint]):
                    j=next_checkpoint
                    checkpoints[nlog,j,0]=held; checkpoints[nlog,j,1]=move
                    checkpoints[nlog,j,2]=peak; checkpoints[nlog,j,3]=trough
                    checkpoints[nlog,j,4]=side*m60[i]
                    checkpoints[nlog,j,5]=side*imb[i]
                    checkpoints[nlog,j,6]=qacc[i]
                    next_checkpoint+=1

            if pos==3 and partial_done==0 and move>=5.5:
                closeoz=oz*0.75
                part=move*closeoz*INR_PER_USD
                bal+=part; partial+=part; oz-=closeoz; partial_done=1

            reason=0; rev=1; trig=-1.; gb=0.; tp=12.; maxhold=900.
            if pos==3:
                tp=10.; maxhold=900.; trig=4.; gb=2.; rev=1
            elif pos==4:
                tp=burst_cfg[11]; maxhold=burst_cfg[12]; trig=burst_cfg[15]; gb=burst_cfg[16]; rev=0
            elif pos==1 and highopen==1:
                tp=25.; maxhold=900.; rev=0
            elif pos==2 and highopen==1:
                tp=8.; maxhold=1200.; rev=0; trig=12.; gb=3.
            elif pos==1:
                tp=21.; maxhold=1800.; rev=1

            if move<=-4.: reason=1
            elif move>=tp: reason=2
            if reason==0 and trig>0 and peak>=trig and move<=peak-gb: reason=3
            if reason==0 and pos==3 and held>=45. and peak<0.75: reason=4
            if reason==0 and pos==4 and held>=burst_cfg[13] and peak<burst_cfg[14]: reason=4
            if pos==4 and math.isnan(m30[i]): failure_since=-1e30
            if reason==0 and pos==4 and not math.isnan(m30[i]):
                failure=(side==1 and m30[i]<=0) or (side==-1 and m30[i]>=0)
                if failure:
                    if failure_since < -1e20: failure_since=ts
                    if ts-failure_since>=confirm_sec: reason=5
                else: failure_since=-1e30
            if reason==0 and rev==1 and not math.isnan(m300[i]):
                if side==1 and m300[i]<=0: reason=5
                elif side==-1 and m300[i]>=0: reason=5
            if reason==0 and (pos==1 or pos==2) and checkpoint_sec>0 and candidate_checkpoint_seen==0 and held>=checkpoint_sec:
                candidate_checkpoint_seen=1
                if move<=0. and not math.isnan(m60[i]) and side*m60[i]<=0. and side*imb[i]<=0.:
                    reason=8
            if reason==0 and held>=maxhold: reason=7

            if reason!=0:
                pnl=move*oz*INR_PER_USD
                total=pnl+partial
                bal+=pnl; ntr+=1
                if total>0: gp+=total; win+=1
                elif total<0: gl-=total
                if bal>peakbal: peakbal=bal
                dd=peakbal-bal
                if dd>maxdd: maxdd=dd
                if nlog>=len(log): raise RuntimeError("trade log capacity exceeded")
                log[nlog,0]=entry_i; log[nlog,1]=i; log[nlog,2]=pos; log[nlog,3]=side
                log[nlog,4]=reason; log[nlog,5]=ptime; log[nlog,6]=ts
                log[nlog,7]=entry; log[nlog,8]=entry_oz; log[nlog,9]=total
                log[nlog,10]=peak; log[nlog,11]=trough; log[nlog,12]=mfe_time; log[nlog,13]=move
                nlog+=1
                if pos==1: lp=ts
                elif pos==2: ls=ts
                elif pos==3: lm=ts
                else: lb=ts
                pos=0
            continue

        if spread[i] > 0.30:
            secondary_since=-1e30; secondary_side=0
            continue

        high=(not math.isnan(r300[i]) and not math.isnan(er60[i]) and r300[i]>=5. and er60[i]>=0.03)
        pcool=450. if high else 900.
        scool=90. if high else 450.
        chosen=0; sside=0; seen_secondary_signal=False

        if ts-cont>=1800. and ts-lp>=pcool and not(
            math.isnan(m60[i]) or math.isnan(m300[i]) or math.isnan(m1800[i]) or math.isnan(min60[i]) or math.isnan(max60[i])
        ):
            if m1800[i]>=8 and m300[i]>=3 and min60[i]<=-0.8 and m60[i]>=0.5:
                chosen=1; sside=1
            elif m1800[i]<=-8 and m300[i]<=-3 and max60[i]>=0.8 and m60[i]<=-0.5:
                chosen=1; sside=-1

        if chosen==0 and ts-ls>=scool and not(math.isnan(m30[i]) or math.isnan(chh[i]) or math.isnan(chl[i])):
            slowbuy=(not math.isnan(m300[i]) and not math.isnan(m1800[i]) and m1800[i]>=8 and m300[i]>=3)
            slowsell=(not math.isnan(m300[i]) and not math.isnan(m1800[i]) and m1800[i]<=-8 and m300[i]<=-3)
            if not((slowbuy or slowsell) and not high):
                rng=chh[i]-chl[i]
                buf=max(0.5,0.02*rng)
                if rng>=4:
                    buy=mid[i]>=chh[i]+buf and m30[i]>=1.5
                    sell=mid[i]<=chl[i]-buf and m30[i]<=-1.5
                    signal_side=1 if buy else (-1 if sell else 0)
                    if signal_side!=0 and secondary_flow_mode>0.:
                        strong_m10=not math.isnan(m10[i]) and signal_side*m10[i]>=2.0
                        strong_qacc=qacc[i]>=1.0
                        if secondary_flow_mode==1. and not(strong_m10 and strong_qacc): signal_side=0
                        elif secondary_flow_mode==2. and not(strong_m10 or strong_qacc): signal_side=0
                        elif secondary_flow_mode==3. and not strong_m10: signal_side=0
                        elif secondary_flow_mode==4. and not strong_qacc: signal_side=0
                    if signal_side!=0:
                        seen_secondary_signal=True
                        if secondary_side!=signal_side:
                            secondary_since=ts; secondary_side=signal_side
                        if ts-secondary_since>=secondary_persist_sec:
                            chosen=2; sside=signal_side
        if not seen_secondary_signal:
            secondary_since=-1e30; secondary_side=0

        if chosen==0 and ts-lm>=60.:
            if not(
                math.isnan(m10[i]) or math.isnan(m60[i]) or math.isnan(m120[i]) or math.isnan(er60[i]) or
                math.isnan(r60[i]) or math.isnan(min10[i]) or math.isnan(max10[i])
            ) and r60[i]>=2 and er60[i]>=0.12 and qacc[i]>=0.65 and spread[i]<=0.25*r60[i]:
                if m120[i]>=6 and m60[i]>=2 and min10[i]<=-0.5 and m10[i]>=0.2 and imb[i]>=0:
                    chosen=3; sside=1
                elif m120[i]<=-6 and m60[i]<=-2 and max10[i]>=0.5 and m10[i]<=-0.2 and imb[i]<=0:
                    chosen=3; sside=-1

        if chosen==0 and burst_cfg[0]>0.5 and ts-lb>=burst_cfg[1]:
            if not(
                math.isnan(m10[i]) or math.isnan(m30[i]) or math.isnan(m60[i]) or math.isnan(m120[i]) or
                math.isnan(er60[i]) or math.isnan(r60[i])
            ) and r60[i]>=burst_cfg[8] and spread[i]<=burst_cfg[9]*r60[i] and spread[i]<=burst_cfg[10] and qacc[i]>=burst_cfg[6] and er60[i]>=burst_cfg[5]:
                buy=(m10[i]>=burst_cfg[2] and m30[i]>=burst_cfg[3] and m60[i]>=burst_cfg[4] and m120[i]>0 and imb[i]>=burst_cfg[7])
                sell=(m10[i]<=-burst_cfg[2] and m30[i]<=-burst_cfg[3] and m60[i]<=-burst_cfg[4] and m120[i]<0 and imb[i]<=-burst_cfg[7])
                if buy: chosen=4; sside=1
                elif sell: chosen=4; sside=-1

        if chosen!=0:
            entry=ask[i] if sside==1 else bid[i]
            oz=min(bal*0.03/(4*INR_PER_USD),(bal/INR_PER_USD*100)/entry)
            pos=chosen; side=sside; ptime=ts; peak=0.; trough=0.; mfe_time=0.; failure_since=-1e30; next_checkpoint=0; candidate_checkpoint_seen=0; secondary_since=-1e30; secondary_side=0; partial=0.; partial_done=0; highopen=1 if high else 0; entry_i=i; entry_oz=oz

    pf=gp/gl if gl>0 else 999.
    return bal-500.,pf,ntr,win,maxdd,log[:nlog],checkpoints[:nlog]


RESULT_DIR=Path(__file__).resolve().parents[1]/"results"/"simulations"/"2026-09-24-v4_5-exposure-velocity"
REFERENCE_D=json.loads((Path(__file__).resolve().parents[1]/"results"/"simulations"/"2026-09-24-v4_5-confirmed-failure"/"confirm_1s_metadata.json").read_text(encoding="utf-8"))
REASONS={**autopsy.REASONS,8:"conditional_release"}


def trace_grid(arrays,bounds,interval,checkpoint_sec,segment_ids,check_d=False,secondary_persist_sec=0.,secondary_flow_mode=0.):
    args=[arrays[x] for x in canonical.FEATURE_NAMES]
    inds=autopsy.indices(arrays,bounds)
    cfg=canonical.burst_config("v4_5_b")
    segments=[]; trades=[]; checkpoints=[]
    for sid in segment_ids:
        a,z=inds[sid]
        result=simulate_velocity(*args,a,z,cfg,1.,float(checkpoint_sec),float(secondary_persist_sec),float(secondary_flow_mode))
        metrics={"segment_id":sid,"pnl_inr":float(result[0]),"profit_factor":float(result[1]),
                 "trades":int(result[2]),"wins":int(result[3]),"max_drawdown_inr":float(result[4])}
        if check_d:
            expected=REFERENCE_D["intervals"][interval]["confirmed_failure"]["segments"][sid]
            for name in ("pnl_inr","profit_factor","trades","wins","max_drawdown_inr"):
                if abs(metrics[name]-expected[name])>1e-9:
                    raise RuntimeError(f"Candidate D trace parity failed: {interval} segment {sid} {name}")
        segments.append(metrics)
        for tid,r in enumerate(result[5]):
            engine=int(r[2]);side=int(r[3]);trade_id=f"{interval}-s{sid}-t{tid}"
            row={"trade_id":trade_id,"interval":interval,"segment_id":sid,"engine":autopsy.ENGINES[engine],
                 "side":"BUY" if side==1 else "SELL","side_sign":side,
                 "entry_ts":float(r[5]),"exit_ts":float(r[6]),"exit_reason":REASONS[int(r[4])],
                 "hold_sec":float(r[6]-r[5]),"entry_oz":float(r[8]),"pnl_inr":float(r[9]),
                 "mfe_usd":float(r[10]),"mae_usd":float(r[11])}
            entry_i=int(r[0])
            for name in ("m10","m30","m60","m120","qacc","imb10","range60","spread"):
                row[f"entry_{name}"]=float(arrays[name][entry_i])
            row["entry_directional_imb10"]=side*float(arrays["imb10"][entry_i])
            trades.append(row)
            if engine in (1,2):
                for j,nominal in enumerate((60,120,300)):
                    c=result[6][tid,j]
                    if np.isfinite(c[0]):
                        gate=(c[1]<=0 and np.isfinite(c[4]) and c[4]<=0 and c[5]<=0)
                        checkpoints.append({"trade_id":trade_id,"interval":interval,"segment_id":sid,
                            "engine":row["engine"],"side":row["side"],"checkpoint_nominal_sec":nominal,
                            "checkpoint_actual_sec":float(c[0]),"move_usd":float(c[1]),
                            "peak_favorable_usd":float(c[2]),"mae_usd":float(c[3]),
                            "directional_m60_usd":float(c[4]),"directional_imb10":float(c[5]),
                            "qacc":float(c[6]),"release_gate":bool(gate),
                            "checkpoint_pnl_inr_fixed_size":float(c[1]*r[8]*INR_PER_USD),
                            "eventual_pnl_inr":float(r[9]),
                            "potential_saved_exposure_sec":float(r[6]-r[5]-c[0])})
    return summarize(segments,trades),trades,checkpoints


def matched_trades(a,b):
    used=set();out=[]
    for x in a:
        if x["engine"] not in ("PRIMARY","SECONDARY"):continue
        options=[(abs(y["entry_ts"]-x["entry_ts"]),j,y) for j,y in enumerate(b)
                 if j not in used and y["segment_id"]==x["segment_id"] and y["engine"]==x["engine"]
                 and y["side"]==x["side"] and abs(y["entry_ts"]-x["entry_ts"])<=120]
        if options:
            _,j,y=min(options,key=lambda v:v[0]);used.add(j)
            out.append({"trade_500ms":x["trade_id"],"trade_1s":y["trade_id"],
                        "engine":x["engine"],"segment_id":x["segment_id"],
                        "entry_delay_sec":y["entry_ts"]-x["entry_ts"],
                        "pnl_delta_1s_minus_500ms_inr":y["pnl_inr"]-x["pnl_inr"],"match":"matched"})
        else:
            out.append({"trade_500ms":x["trade_id"],"trade_1s":"","engine":x["engine"],
                        "segment_id":x["segment_id"],"entry_delay_sec":"",
                        "pnl_delta_1s_minus_500ms_inr":"","match":"absent_within_120s"})
    return out


def build_grid(csv_path,interval):
    arrays,bounds=canonical.build_features(csv_path,interval)
    baseline=canonical.run_strategy(arrays,bounds,"v4_4")
    canonical.assert_baseline(baseline,interval,canonical.DEFAULT_GOLDEN)
    b=canonical.run_strategy(arrays,bounds,"v4_5_b")
    for key,value in autopsy.REFERENCE[interval].items():
        if abs(b[key]-value)>1e-9:raise RuntimeError(f"Candidate B reference drift {interval} {key}")
    cfg=canonical.burst_config("v4_5_b");args=[arrays[x] for x in canonical.FEATURE_NAMES]
    for sid,(a,z) in enumerate(autopsy.indices(arrays,bounds)):
        r=autopsy.simulate_trace(*args,a,z,cfg,0.)
        for j,name in enumerate(("pnl_inr","profit_factor","trades","wins","max_drawdown_inr")):
            if abs(r[j]-b["segments"][sid][name])>1e-9:
                raise RuntimeError(f"Candidate B trace parity failed: {interval} segment {sid} {name}")
    return arrays,bounds,baseline,b


def main():
    p=argparse.ArgumentParser();p.add_argument("csv",type=Path)
    p.add_argument("--output",type=Path,default=RESULT_DIR)
    p.add_argument("--full-checkpoint",type=int,choices=(120,300),
                   help="run one seed-selected conditional release on all first-80%% segments")
    p.add_argument("--full-persistence",type=int,choices=(2,),
                   help="run seed-selected SECONDARY persistence on all first-80%% segments")
    p.add_argument("--full-flow-mode",type=int,choices=(1,2,3,4),
                   help="run one seed-selected SECONDARY flow veto on all first-80%% segments")
    args=p.parse_args();digest=canonical.verify_dataset(args.csv);args.output.mkdir(parents=True,exist_ok=True)
    if sum((args.full_checkpoint is not None,args.full_persistence is not None,args.full_flow_mode is not None))>1:
        p.error("choose only one full variant")
    output={"dataset_sha256":digest,"research_rows":canonical.RESEARCH_ROWS,
            "raw_boundaries":canonical.BOUND_RAW,"holdout_evaluated":False,"intervals":{}}
    all_trades={};all_checkpoints={}
    for interval in ("500ms","1s"):
        arrays,bounds,baseline,b=build_grid(args.csv,interval)
        d,trades,checkpoints=trace_grid(arrays,bounds,interval,0,(0,1,2,3,4),check_d=True)
        output["intervals"][interval]={"v4_4":baseline,"candidate_b":b,"candidate_d":d,
            "candidate_d_trace_parity":True}
        all_trades[interval]=trades;all_checkpoints[interval]=checkpoints
        if args.full_checkpoint is None and args.full_persistence is None and args.full_flow_mode is None:
            autopsy.write_csv(args.output/f"candidate_d_{interval}_trades.csv",trades)
            autopsy.write_csv(args.output/f"candidate_d_{interval}_checkpoints.csv",checkpoints)
            output["intervals"][interval]["seed_variants"]={}
            for seconds in (120,300):
                summary,_,_=trace_grid(arrays,bounds,interval,seconds,(0,))
                output["intervals"][interval]["seed_variants"][f"release_{seconds}s"]=summary
            persistence,_,_=trace_grid(arrays,bounds,interval,0,(0,),secondary_persist_sec=2.)
            output["intervals"][interval]["seed_variants"]["secondary_persistence_2s"]=persistence
            for mode,name in ((1,"require_both"),(2,"veto_both_weak"),(3,"require_m10"),(4,"require_qacc")):
                flow,_,_=trace_grid(arrays,bounds,interval,0,(0,),secondary_flow_mode=mode)
                output["intervals"][interval]["seed_variants"][f"secondary_flow_{name}"]=flow
        else:
            summary,candidate_trades,_=trace_grid(arrays,bounds,interval,args.full_checkpoint or 0,(0,1,2,3,4),
                secondary_persist_sec=args.full_persistence or 0,secondary_flow_mode=args.full_flow_mode or 0.)
            output["intervals"][interval]["candidate"]=summary
            label=(f"release_{args.full_checkpoint}s" if args.full_checkpoint else
                   f"secondary_persistence_{args.full_persistence}s" if args.full_persistence else f"secondary_flow_mode_{args.full_flow_mode}")
            autopsy.write_csv(args.output/f"{label}_{interval}_trades.csv",candidate_trades)
        print(interval,"V4.4/B/D parity PASS",flush=True)
    if args.full_checkpoint is None and args.full_persistence is None and args.full_flow_mode is None:
        config={"dataset_sha256":digest,"research_rows":canonical.RESEARCH_ROWS,
            "raw_boundaries":canonical.BOUND_RAW,"baseline":"Candidate D; BURST zero-cross confirmation 1 second",
            "seed_segment_id":0,"evaluation_segment_ids":[1,2,3,4],"holdout_evaluated":False,
            "variants":{
                "release_120s":{"checkpoint_sec":120,"rule":"PRIMARY/SECONDARY move <= 0, directional m60 <= 0, directional imb10 <= 0"},
                "release_300s":{"checkpoint_sec":300,"rule":"PRIMARY/SECONDARY move <= 0, directional m60 <= 0, directional imb10 <= 0"},
                "secondary_persistence_2s":{"breakout_persistence_sec":2},
                "secondary_flow_require_both":{"directional_m10_min_usd":2,"qacc_min":1.0,"combine":"AND"},
                "secondary_flow_veto_both_weak":{"directional_m10_min_usd":2,"qacc_min":1.0,"combine":"OR"},
                "secondary_flow_require_m10":{"directional_m10_min_usd":2},
                "secondary_flow_require_qacc":{"qacc_min":1.0}},
            "unchanged":"Candidate D risk, other admission, exits, priority and bid/ask accounting"}
        (args.output/"run_config.json").write_text(json.dumps(config,indent=2)+"\n",encoding="utf-8")
        matches=matched_trades(all_trades["500ms"],all_trades["1s"])
        autopsy.write_csv(args.output/"primary_secondary_trade_matches.csv",matches)
        matched_1s_ids={r["trade_1s"] for r in matches if r["match"]=="matched"}
        output["sampling_attribution"]={}
        for engine in ("PRIMARY","SECONDARY"):
            unique=[r for r in all_trades["1s"] if r["engine"]==engine and r["trade_id"] not in matched_1s_ids]
            output["sampling_attribution"][f"unmatched_1s_{engine.lower()}"]={
                "trades":len(unique),"pnl_inr":sum(r["pnl_inr"] for r in unique),
                "exposure_hours":sum(r["hold_sec"] for r in unique)/3600,
                "emergency_stops":sum(r["exit_reason"]=="emergency_stop" for r in unique)}
        seed_rows=[]
        for interval in ("500ms","1s"):
            d=output["intervals"][interval]
            for name,s in {"candidate_d":d["candidate_d"],**d["seed_variants"]}.items():
                seed_hours=(sum(r["hold_sec"] for r in all_trades[interval] if r["segment_id"]==0)/3600
                            if name=="candidate_d" else s["exposure_hours"])
                seed_rows.append({"interval":interval,"variant":name,
                    "seed_pnl_inr":s["segments"][0]["pnl_inr"],
                    "seed_profit_factor":s["segments"][0]["profit_factor"],
                    "seed_max_drawdown_inr":s["segments"][0]["max_drawdown_inr"],
                    "seed_exposure_hours":seed_hours,
                    "seed_pnl_per_exposure_hour":s["segments"][0]["pnl_inr"]/seed_hours if seed_hours else 0})
        autopsy.write_csv(args.output/"seed_variant_summary.csv",seed_rows)
        (args.output/"diagnostic_metadata.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")
    else:
        label=(f"release_{args.full_checkpoint}s" if args.full_checkpoint else
               f"secondary_persistence_{args.full_persistence}s" if args.full_persistence else f"secondary_flow_mode_{args.full_flow_mode}")
        output["candidate_config"]={"checkpoint_sec":args.full_checkpoint or 0,
            "secondary_persistence_sec":args.full_persistence or 0,
            "secondary_flow_mode":args.full_flow_mode or 0,
            "secondary_flow_thresholds":{"directional_m10_usd":2.0,"qacc":1.0},
            "release_condition":"PRIMARY or SECONDARY nonpositive executable move and nonpositive directional m60 and imb10",
            "all_other_rules":"Candidate D canonical"}
        (args.output/f"{label}_metadata.json").write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
