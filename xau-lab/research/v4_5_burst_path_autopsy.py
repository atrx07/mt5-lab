"""Parity-gated Candidate B trade-path diagnostics. First-80% research only."""
import argparse
import csv
import json
import math
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
try:
    from numba import njit
except ImportError:
    # Research remains executable on local Python builds without a Numba wheel.
    # This changes speed only; the canonical and trace parity gates remain mandatory.
    def njit(*args, **kwargs):
        return lambda function: function
    sys.modules["numba"] = types.SimpleNamespace(njit=njit)

import canonical_replay as canonical

INR_PER_USD = canonical.INR_PER_USD
@njit(cache=True)
def simulate_trace(
    t,bid,ask,mid,spread,ss,imb,qacc,m10,m30,m60,m120,m300,m1800,
    r60,r300,er60,min10,max10,min60,max60,chh,chl,start,end,burst_cfg,confirm_sec
):
    # burst_cfg = enabled,cooldown,m10,m30,m60,er,qacc,imb,r60,maxspratio,abs_spread,tp,maxhold,stagsec,stagpeak,trailtrig,trailgb
    bal=500.; lp=-1e30; ls=-1e30; lm=-1e30; lb=-1e30
    pos=0; side=0; entry=0.; oz=0.; ptime=0.; peak=0.; trough=0.; mfe_time=0.; partial=0.; partial_done=0; highopen=0; entry_i=-1; entry_oz=0.
    prevss=-1; cont=0.; gp=0.; gl=0.; ntr=0; win=0; peakbal=500.; maxdd=0.
    failure_since=-1e30
    log=np.zeros((2048,14),dtype=np.float64); nlog=0

    for i in range(start,end):
        ts=t[i]
        if ss[i] != prevss:
            cont=ts; prevss=ss[i]

        if pos != 0:
            move=(bid[i]-entry) if side==1 else (entry-ask[i])
            held=ts-ptime
            if move>peak: peak=move; mfe_time=ts-ptime
            if move<trough: trough=move

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
            continue

        high=(not math.isnan(r300[i]) and not math.isnan(er60[i]) and r300[i]>=5. and er60[i]>=0.03)
        pcool=450. if high else 900.
        scool=90. if high else 450.
        chosen=0; sside=0

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
                    if buy: chosen=2; sside=1
                    elif sell: chosen=2; sside=-1

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
            pos=chosen; side=sside; ptime=ts; peak=0.; trough=0.; mfe_time=0.; failure_since=-1e30; partial=0.; partial_done=0; highopen=1 if high else 0; entry_i=i; entry_oz=oz

    pf=gp/gl if gl>0 else 999.
    return bal-500.,pf,ntr,win,maxdd,log[:nlog]


REASONS={1:"emergency_stop",2:"take_profit",3:"trail",4:"stagnation",5:"momentum_zero_cross",7:"max_hold"}
ENGINES={1:"PRIMARY",2:"SECONDARY",3:"MICRO",4:"BURST"}
REFERENCE={"500ms":{"compounded_pnl_inr":1299.367875231396,"trades_sum":163,"wins_sum":79},
           "1s":{"compounded_pnl_inr":365.25390229096365,"trades_sum":156,"wins_sum":70}}


def indices(arrays,bounds):
    return [(int(np.searchsorted(arrays["t"],bounds[i],"left")),
             int(np.searchsorted(arrays["t"],bounds[i+1],"left"))) for i in range(5)]


def state(arrays,i):
    return {name:float(arrays[name][i]) for name in
            ("m10","m30","m60","m120","qacc","imb10","spread","range60")}


def excursions(arrays,exit_i,segment_end,side):
    # Incremental executable-side price from the actual exit quote. No segment leakage.
    t=arrays["t"]; quote=arrays["bid"] if side==1 else arrays["ask"]
    base=quote[exit_i]; out={}
    for seconds in (10,30,60):
        end=min(segment_end,int(np.searchsorted(t,t[exit_i]+seconds,"right")))
        path=side*(quote[exit_i:end]-base)
        out[f"post_{seconds}s_favorable_usd"]=float(np.max(path))
        out[f"post_{seconds}s_adverse_usd"]=float(np.min(path))
        out[f"post_{seconds}s_observed_sec"]=float(t[end-1]-t[exit_i])
    out["continued_hold_benefit_60s"]=out["post_60s_favorable_usd"]>0
    return out


def opportunity_episodes(arrays,inds,interval):
    # Raw threshold opportunity, even if another engine owns the shared slot.
    # An episode restarts after a 10 s absence or direction change.
    cfg=canonical.burst_config("v4_5_b"); rows=[]; t=arrays["t"]
    for sid,(a,z) in enumerate(inds):
        side=0; previous=-1e30; count=0; start_i=-1
        for i in range(a,z):
            sign=0
            if arrays["spread"][i]<=0.30 and all(np.isfinite(arrays[x][i]) for x in ("m10","m30","m60","m120","er60","range60")):
                if (arrays["range60"][i]>=cfg[8] and arrays["spread"][i]<=cfg[9]*arrays["range60"][i]
                    and arrays["spread"][i]<=cfg[10] and arrays["qacc"][i]>=cfg[6] and arrays["er60"][i]>=cfg[5]):
                    if (arrays["m10"][i]>=cfg[2] and arrays["m30"][i]>=cfg[3] and arrays["m60"][i]>=cfg[4]
                        and arrays["m120"][i]>0 and arrays["imb10"][i]>=cfg[7]): sign=1
                    elif (arrays["m10"][i]<=-cfg[2] and arrays["m30"][i]<=-cfg[3] and arrays["m60"][i]<=-cfg[4]
                        and arrays["m120"][i]<0 and arrays["imb10"][i]<=-cfg[7]): sign=-1
            if sign:
                if sign!=side or t[i]-previous>10:
                    if count:
                        rows.append({"interval":interval,"segment_id":sid,"side":side,"start_ts":float(t[start_i]),
                                     "end_ts":float(previous),"sample_count":count})
                    side=sign; start_i=i; count=0
                count+=1; previous=t[i]
        if count:
            rows.append({"interval":interval,"segment_id":sid,"side":side,"start_ts":float(t[start_i]),
                         "end_ts":float(previous),"sample_count":count})
    return rows


def run_interval(path,interval,out):
    arrays,bounds=canonical.build_features(path,interval)
    baseline=canonical.run_strategy(arrays,bounds,"v4_4")
    canonical.assert_baseline(baseline,interval,canonical.DEFAULT_GOLDEN)
    expected=canonical.run_strategy(arrays,bounds,"v4_5_b")
    for key,value in REFERENCE[interval].items():
        if abs(expected[key]-value)>1e-9: raise RuntimeError(f"Candidate B reference drift {interval} {key}")
    cfg=canonical.burst_config("v4_5_b"); args=[arrays[x] for x in canonical.FEATURE_NAMES]
    inds=indices(arrays,bounds); ledger=[]; trace_segments=[]
    for sid,(a,z) in enumerate(inds):
        result=simulate_trace(*args,a,z,cfg,0.)
        metrics=dict(zip(("pnl_inr","profit_factor","trades","wins","max_drawdown_inr"),result[:5]))
        for k,v in metrics.items():
            if abs(v-expected["segments"][sid][k])>1e-9:
                raise RuntimeError(f"Instrumented Candidate B parity failure {interval} segment {sid} {k}: {v} != {expected['segments'][sid][k]}")
        trace_segments.append({"segment_id":sid,**{k:float(v) for k,v in metrics.items()}})
        for trade_id,r in enumerate(result[5]):
            ei,xi,engine,side,reason=map(int,r[:5]); row={
                "trade_id":f"{interval}-s{sid}-t{trade_id}","interval":interval,"segment_id":sid,
                "engine":ENGINES[engine],"side":"BUY" if side==1 else "SELL","side_sign":side,
                "entry_ts":float(r[5]),"exit_ts":float(r[6]),"entry_utc":datetime.fromtimestamp(float(r[5]),timezone.utc).isoformat(timespec="microseconds"),
                "exit_utc":datetime.fromtimestamp(float(r[6]),timezone.utc).isoformat(timespec="microseconds"),
                "exit_reason":REASONS[reason],"hold_sec":float(r[6]-r[5]),"entry_price_usd":float(r[7]),
                "entry_oz":float(r[8]),"pnl_inr":float(r[9]),"mfe_usd":float(r[10]),"mae_usd":float(r[11]),
                "time_to_mfe_sec":float(r[12]),"exit_move_usd":float(r[13]),
                "peak_favorable_before_exit_usd":float(r[10]),
            }
            for prefix,i in (("entry",ei),("exit",xi)):
                for k,v in state(arrays,i).items():row[f"{prefix}_{k}"]=v
                row[f"{prefix}_directional_imb10"]=side*float(arrays["imb10"][i])
                row[f"{prefix}_spread_range_ratio"]=(float(arrays["spread"][i]/arrays["range60"][i])
                                                       if arrays["range60"][i]>0 else float("nan"))
            row.update(excursions(arrays,xi,z,side)); ledger.append(row)
    opportunities=opportunity_episodes(arrays,inds,interval)
    return {"interval":interval,"feature_rows":len(arrays["t"]),"v4_4":baseline,"candidate_b":expected,
            "instrumented_segments":trace_segments,"instrumentation_parity":True},ledger,opportunities


def match_rows(first,second,time_key,max_delay):
    matches=[]; used=set()
    for a in first:
        possibilities=[(abs(b[time_key]-a[time_key]),j,b) for j,b in enumerate(second)
                       if j not in used and a["segment_id"]==b["segment_id"] and a["side_sign"]==b["side_sign"]
                       and abs(b[time_key]-a[time_key])<=max_delay]
        if possibilities:
            delta,j,b=min(possibilities,key=lambda x:x[0]); used.add(j)
            matches.append({"source_id":a["trade_id"],"target_id":b["trade_id"],
                            "source_entry_ts":a[time_key],"target_entry_ts":b[time_key],
                            "delay_sec":b[time_key]-a[time_key],"match":"matched"})
        else:
            matches.append({"source_id":a["trade_id"],"target_id":"","source_entry_ts":a[time_key],
                            "target_entry_ts":"","delay_sec":"","match":"absent_within_120s"})
    return matches


def write_csv(path,rows):
    if not rows:return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    p=argparse.ArgumentParser(); p.add_argument("csv",type=Path)
    p.add_argument("--output",type=Path,default=Path(__file__).resolve().parents[1]/"results"/"simulations"/"2026-09-24-v4_5-burst-path-autopsy")
    a=p.parse_args(); digest=canonical.verify_dataset(a.csv); a.output.mkdir(parents=True,exist_ok=True)
    summaries={}; ledgers={}; episodes={}
    for interval in ("500ms","1s"):
        summaries[interval],ledgers[interval],episodes[interval]=run_interval(a.csv,interval,a.output)
        write_csv(a.output/f"candidate_b_{interval}_trades_instrumented.csv",ledgers[interval])
        write_csv(a.output/f"burst_{interval}_opportunity_episodes.csv",episodes[interval])
        print(f"{interval}: V4.4 and Candidate B trace parity PASS; {len(ledgers[interval])} trades; {len(episodes[interval])} BURST episodes",flush=True)
    burst500=[r for r in ledgers["500ms"] if r["engine"]=="BURST"]
    burst1=[r for r in ledgers["1s"] if r["engine"]=="BURST"]
    matches=match_rows(burst500,burst1,"entry_ts",120)
    write_csv(a.output/"burst_trade_matches.csv",matches)
    missing=[]
    for trade,match in zip(burst500,matches):
        if match["match"]=="matched":continue
        near=[e for e in episodes["1s"] if e["segment_id"]==trade["segment_id"]
              and e["side"]==trade["side_sign"] and e["start_ts"]<=trade["entry_ts"]+30
              and e["end_ts"]>=trade["entry_ts"]-30]
        occupying=[r for r in ledgers["1s"] if r["segment_id"]==trade["segment_id"]
                   and r["entry_ts"]<=trade["entry_ts"]<=r["exit_ts"]]
        cause=("sampled_signal_absent_near_entry" if not near else
               "shared_slot_occupied" if occupying else "signal_present_no_burst_admission")
        missing.append({"trade_id_500ms":trade["trade_id"],"segment_id":trade["segment_id"],
                        "side":trade["side"],"entry_utc_500ms":trade["entry_utc"],
                        "pnl_500ms_inr":trade["pnl_inr"],"classification":cause,
                        "near_1s_episode_count":len(near),
                        "occupying_1s_trade_id":occupying[0]["trade_id"] if occupying else ""})
    write_csv(a.output/"burst_unmatched_500ms_trades.csv",missing)
    episode_matches=[]; used=set()
    for i,e in enumerate(episodes["500ms"]):
        possible=[(abs(x["start_ts"]-e["start_ts"]),j,x) for j,x in enumerate(episodes["1s"])
                  if j not in used and x["segment_id"]==e["segment_id"] and x["side"]==e["side"]
                  and x["start_ts"]<=e["end_ts"]+30 and x["end_ts"]>=e["start_ts"]-30]
        if possible:
            _,j,x=min(possible,key=lambda y:y[0]); used.add(j)
            episode_matches.append({"episode_500ms":i,"episode_1s":j,"segment_id":e["segment_id"],
                                    "side":e["side"],"start_500ms_ts":e["start_ts"],"start_1s_ts":x["start_ts"],
                                    "delay_sec":x["start_ts"]-e["start_ts"],"match":"matched"})
        else:
            episode_matches.append({"episode_500ms":i,"episode_1s":"","segment_id":e["segment_id"],
                                    "side":e["side"],"start_500ms_ts":e["start_ts"],"start_1s_ts":"",
                                    "delay_sec":"","match":"absent"})
    write_csv(a.output/"burst_opportunity_matches.csv",episode_matches)
    meta={"dataset_sha256":digest,"research_rows":canonical.RESEARCH_ROWS,"raw_boundaries":canonical.BOUND_RAW,
          "holdout_evaluated":False,"canonical_schema":canonical.SCHEMA_VERSION,"intervals":summaries,
          "burst_trade_matches":{"500ms_trades":len(burst500),"1s_trades":len(burst1),
                                 "matched":sum(r["match"]=="matched" for r in matches),
                                 "unmatched":sum(r["match"]!="matched" for r in matches),
                                 "unmatched_classification":{name:sum(r["classification"]==name for r in missing)
                                     for name in ("sampled_signal_absent_near_entry","shared_slot_occupied","signal_present_no_burst_admission")}},
          "burst_episode_matches":{"500ms_episodes":len(episodes["500ms"]),"1s_episodes":len(episodes["1s"]),
                                   "matched":sum(r["match"]=="matched" for r in episode_matches)}}
    (a.output/"run_metadata.json").write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
