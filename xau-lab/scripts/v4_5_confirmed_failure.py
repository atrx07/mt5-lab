"""Experiment 19: short confirmed BURST momentum failure exits."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

import v4_5_burst_path_autopsy as autopsy
import canonical_replay as canonical


RESULT_DIR=Path(__file__).resolve().parents[1]/"results"/"simulations"/"2026-09-24-v4_5-confirmed-failure"


def summarize(segment_results,trade_rows):
    factor=1.0
    for s in segment_results:factor*=1+s["pnl_inr"]/canonical.START_BALANCE_INR
    pnl=sum(s["pnl_inr"] for s in segment_results)
    exposure=sum(r["hold_sec"] for r in trade_rows)/3600
    burst=[r for r in trade_rows if r["engine"]=="BURST"]
    burst_exposure=sum(r["hold_sec"] for r in burst)/3600
    return {"segments":segment_results,"compounded_pnl_inr":canonical.START_BALANCE_INR*(factor-1),
            "capture_ratio":canonical.START_BALANCE_INR*(factor-1)/canonical.OPPORTUNITY_CEILING_INR,
            "sum_segment_pnl_inr":pnl,"trades_sum":sum(s["trades"] for s in segment_results),
            "wins_sum":sum(s["wins"] for s in segment_results),
            "median_segment_pf":float(np.median([s["profit_factor"] for s in segment_results])),
            "max_segment_drawdown_inr":max(s["max_drawdown_inr"] for s in segment_results),
            "exposure_hours":exposure,"pnl_per_exposure_hour":pnl/exposure if exposure else 0.,
            "pnl_per_trade_inr":pnl/len(trade_rows) if trade_rows else 0.,
            "mean_hold_sec":3600*exposure/len(trade_rows) if trade_rows else 0.,
            "burst_trades":len(burst),"burst_pnl_inr":sum(r["pnl_inr"] for r in burst),
            "burst_exposure_hours":burst_exposure,
            "burst_pnl_per_exposure_hour":sum(r["pnl_inr"] for r in burst)/burst_exposure if burst_exposure else 0.}


def cost_stress(rows,extra_slippage_usd_per_side):
    # Fixed-size post-trade stress: subtract added adverse entry and exit slippage
    # from the actually filled trade. Does not re-size subsequent trades.
    segment_pnl=[]; segment_pf=[]; segment_dd=[]
    for sid in range(5):
        trades=[r for r in rows if r["segment_id"]==sid]
        pnls=[r["pnl_inr"]-2*extra_slippage_usd_per_side*r["entry_oz"]*canonical.INR_PER_USD for r in trades]
        segment_pnl.append(sum(pnls))
        gross_win=sum(x for x in pnls if x>0); gross_loss=-sum(x for x in pnls if x<0)
        segment_pf.append(gross_win/gross_loss if gross_loss else 999.)
        balance=500.; peak=500.; drawdown=0.
        for x in pnls:
            balance+=x; peak=max(peak,balance); drawdown=max(drawdown,peak-balance)
        segment_dd.append(drawdown)
    factor=1.
    for x in segment_pnl:factor*=1+x/500.
    return {"extra_slippage_usd_per_side":extra_slippage_usd_per_side,
            "compounded_pnl_inr_fixed_size":500*(factor-1),
            "median_segment_pf_fixed_size":float(np.median(segment_pf)),
            "max_segment_drawdown_inr_fixed_size":max(segment_dd),
            "segment_pnl_inr_fixed_size":segment_pnl}


def run_interval(csv_path,interval,confirm_seconds):
    arrays,bounds=canonical.build_features(csv_path,interval)
    baseline=canonical.run_strategy(arrays,bounds,"v4_4")
    canonical.assert_baseline(baseline,interval,canonical.DEFAULT_GOLDEN)
    b=canonical.run_strategy(arrays,bounds,"v4_5_b")
    for key,value in autopsy.REFERENCE[interval].items():
        if abs(b[key]-value)>1e-9:raise RuntimeError(f"Candidate B reference drift {interval} {key}")
    cfg=canonical.burst_config("v4_5_b"); args=[arrays[x] for x in canonical.FEATURE_NAMES]
    inds=autopsy.indices(arrays,bounds); candidate_segments=[]; rows=[]; control_rows=[]
    for sid,(a,z) in enumerate(inds):
        control=autopsy.simulate_trace(*args,a,z,cfg,0.)
        for k,v in enumerate(("pnl_inr","profit_factor","trades","wins","max_drawdown_inr")):
            if abs(control[k]-b["segments"][sid][v])>1e-9:
                raise RuntimeError(f"Candidate B instrumentation parity failed {interval} segment {sid} {v}")
        for r in control[5]:
            control_rows.append({"segment_id":sid,"engine":autopsy.ENGINES[int(r[2])],
                                 "hold_sec":float(r[6]-r[5]),"entry_oz":float(r[8]),"pnl_inr":float(r[9])})
        result=autopsy.simulate_trace(*args,a,z,cfg,confirm_seconds)
        candidate_segments.append({"segment_id":sid,"pnl_inr":float(result[0]),"profit_factor":float(result[1]),
                                   "trades":int(result[2]),"wins":int(result[3]),"max_drawdown_inr":float(result[4])})
        for tid,r in enumerate(result[5]):
            engine=int(r[2]); rows.append({"trade_id":f"{interval}-s{sid}-t{tid}","interval":interval,"segment_id":sid,
                 "engine":autopsy.ENGINES[engine],"side":"BUY" if r[3]==1 else "SELL",
                 "entry_ts":float(r[5]),"exit_ts":float(r[6]),"exit_reason":autopsy.REASONS[int(r[4])],
                 "hold_sec":float(r[6]-r[5]),"entry_oz":float(r[8]),"pnl_inr":float(r[9]),
                 "mfe_usd":float(r[10]),"mae_usd":float(r[11])})
    summary=summarize(candidate_segments,rows)
    return {"v4_4":baseline,"candidate_b":b,"candidate_b_velocity":summarize(b["segments"],control_rows),
            "confirmed_failure":summary,
            "candidate_b_instrumentation_parity":True,
            "candidate_b_cost_stress_fixed_size":[cost_stress(control_rows,slip) for slip in (0.,0.05,0.10,0.20)],
            "cost_stress_fixed_size":[cost_stress(rows,slip) for slip in (0.,0.05,0.10,0.20)]},rows


def seed_probe(csv_path):
    output={}
    for interval in ("500ms","1s"):
        arrays,bounds=canonical.build_features(csv_path,interval)
        baseline=canonical.run_strategy(arrays,bounds,"v4_4")
        canonical.assert_baseline(baseline,interval,canonical.DEFAULT_GOLDEN)
        reference=canonical.run_strategy(arrays,bounds,"v4_5_b")
        a,z=autopsy.indices(arrays,bounds)[0]
        args=[arrays[x] for x in canonical.FEATURE_NAMES]
        cfg=canonical.burst_config("v4_5_b")
        output[interval]={}
        for seconds in (0.,1.,2.,3.,5.):
            r=autopsy.simulate_trace(*args,a,z,cfg,seconds)
            if seconds==0.:
                for k,name in enumerate(("pnl_inr","profit_factor","trades","wins","max_drawdown_inr")):
                    if abs(r[k]-reference["segments"][0][name])>1e-9:
                        raise RuntimeError(f"seed Candidate B trace parity failed {interval} {name}")
            output[interval][str(seconds)]={"pnl_inr":float(r[0]),"profit_factor":float(r[1]),
                "trades":int(r[2]),"wins":int(r[3]),"max_drawdown_inr":float(r[4]),
                "burst_pnl_inr":float(sum(row[9] for row in r[5] if row[2]==4))}
    return output


def main():
    p=argparse.ArgumentParser();p.add_argument("csv",type=Path);p.add_argument("--output",type=Path,default=RESULT_DIR)
    p.add_argument("--confirm-sec",type=float,default=3.0)
    p.add_argument("--seed-probe",action="store_true",help="parity-gated 0/1/2/3/5 s seed comparison only")
    a=p.parse_args();digest=canonical.verify_dataset(a.csv);a.output.mkdir(parents=True,exist_ok=True)
    if a.seed_probe:
        (a.output/"seed_confirmation_probe.json").write_text(json.dumps(seed_probe(a.csv),indent=2)+"\n",encoding="utf-8")
        print("V4.4 and Candidate B seed gates PASS at 500 ms and 1 s",flush=True)
        return
    result={"dataset_sha256":digest,"research_rows":canonical.RESEARCH_ROWS,"raw_boundaries":canonical.BOUND_RAW,
            "holdout_evaluated":False,"candidate_config":{"burst_zero_cross_confirmation_sec":a.confirm_sec,
            "all_other_rules":"Candidate B canonical"},"intervals":{}}
    for interval in ("500ms","1s"):
        result["intervals"][interval],rows=run_interval(a.csv,interval,a.confirm_sec)
        autopsy.write_csv(a.output/f"confirm_{a.confirm_sec:g}s_{interval}_trades.csv",rows)
        c=result["intervals"][interval]["confirmed_failure"]
        print(f"{interval}: parity PASS; confirmed failure {a.confirm_sec:g}s P&L {c['compounded_pnl_inr']:.2f}; trades {c['trades_sum']}",flush=True)
    (a.output/f"confirm_{a.confirm_sec:g}s_metadata.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
