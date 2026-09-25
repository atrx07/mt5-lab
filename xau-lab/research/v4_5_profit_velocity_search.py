import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

import canonical_replay as canonical


EXPERIMENT_ID = "2026-09-24-v4_5-c-profit-velocity"
START_BALANCE_INR = canonical.START_BALANCE_INR
INR_PER_USD = canonical.INR_PER_USD

# Extended BURST config indices. Indices 0..16 intentionally match canonical Candidate B.
FLOW_EXTEND_SEC = 17
FLOW_QACC_MIN = 18
FLOW_IMB_MIN = 19
FLOW_TRAIL_TRIGGER_BONUS = 20
FLOW_TRAIL_GIVEBACK_BONUS = 21
DECAY_EXIT_ENABLED = 22
DECAY_EXIT_AFTER_SEC = 23
DECAY_EXIT_PEAK_LT = 24
DECAY_EXIT_QACC_LT = 25
DECAY_EXIT_DIR_IMB_LT = 26


def candidate_b_extended():
    base = canonical.burst_config("v4_5_b")
    return np.concatenate(
        [
            base,
            np.array(
                [
                    0.0,
                    1.25,
                    0.25,
                    0.0,
                    0.0,
                    0.0,
                    30.0,
                    0.80,
                    0.85,
                    0.05,
                ],
                dtype=np.float64,
            ),
        ]
    )


def make_variants():
    """
    V4.5-C phase 1 changes BURST lifecycle only.
    Entry admission, risk, stop and the other three engines remain equivalent
    to Candidate B semantics inside this simulator.
    """
    variants = []
    base = candidate_b_extended()

    for max_hold, trail_trigger, trail_giveback, flow_mode, decay_mode in itertools.product(
        [120.0, 180.0],
        [5.5, 6.5, 7.5],
        [2.0, 2.5],
        [0, 1],
        [0, 1],
    ):
        cfg = base.copy()
        cfg[12] = max_hold
        cfg[15] = trail_trigger
        cfg[16] = trail_giveback

        if flow_mode:
            cfg[FLOW_EXTEND_SEC] = 60.0
            cfg[FLOW_QACC_MIN] = 1.25
            cfg[FLOW_IMB_MIN] = 0.25
            cfg[FLOW_TRAIL_TRIGGER_BONUS] = 1.0
            cfg[FLOW_TRAIL_GIVEBACK_BONUS] = 0.5

        if decay_mode:
            cfg[DECAY_EXIT_ENABLED] = 1.0
            cfg[DECAY_EXIT_AFTER_SEC] = 30.0
            cfg[DECAY_EXIT_PEAK_LT] = 0.80
            cfg[DECAY_EXIT_QACC_LT] = 0.85
            cfg[DECAY_EXIT_DIR_IMB_LT] = 0.05

        name = (
            f"mh{int(max_hold)}_tt{trail_trigger:.1f}_gb{trail_giveback:.1f}"
            f"_flow{flow_mode}_decay{decay_mode}"
        )
        variants.append((name, cfg))

    return variants


@njit(cache=True)
def simulate_velocity(
    t,bid,ask,mid,spread,ss,imb,qacc,m10,m30,m60,m120,m300,m1800,
    r60,r300,er60,min10,max10,min60,max60,chh,chl,start,end,burst_cfg
):
    bal=500.; lp=-1e30; ls=-1e30; lm=-1e30; lb=-1e30
    pos=0; side=0; entry=0.; oz=0.; ptime=0.; peak=0.; trough=0.; partial=0.; partial_done=0; highopen=0
    prevss=-1; cont=0.; gp=0.; gl=0.; ntr=0; win=0; peakbal=500.; maxdd=0.

    exposure_sec=0.; burst_pnl=0.; burst_trades=0; burst_exposure_sec=0.
    sum_mfe=0.; sum_mae=0.

    for i in range(start,end):
        ts=t[i]
        if ss[i] != prevss:
            cont=ts; prevss=ss[i]

        if pos != 0:
            move=(bid[i]-entry) if side==1 else (entry-ask[i])
            held=ts-ptime
            if move>peak: peak=move
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

                strong_flow=False
                if burst_cfg[FLOW_EXTEND_SEC] > 0.0 and not math.isnan(m30[i]):
                    dir_imb=imb[i]*side
                    dir_m30=m30[i]*side
                    strong_flow=(
                        qacc[i] >= burst_cfg[FLOW_QACC_MIN]
                        and dir_imb >= burst_cfg[FLOW_IMB_MIN]
                        and dir_m30 > 0.0
                    )
                if strong_flow:
                    maxhold += burst_cfg[FLOW_EXTEND_SEC]
                    trig += burst_cfg[FLOW_TRAIL_TRIGGER_BONUS]
                    gb += burst_cfg[FLOW_TRAIL_GIVEBACK_BONUS]

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
            if reason==0 and pos==4 and not math.isnan(m30[i]):
                if side==1 and m30[i]<=0: reason=5
                elif side==-1 and m30[i]>=0: reason=5

            if (
                reason==0
                and pos==4
                and burst_cfg[DECAY_EXIT_ENABLED] > 0.5
                and held >= burst_cfg[DECAY_EXIT_AFTER_SEC]
                and peak < burst_cfg[DECAY_EXIT_PEAK_LT]
            ):
                dir_imb=imb[i]*side
                if qacc[i] < burst_cfg[DECAY_EXIT_QACC_LT] and dir_imb < burst_cfg[DECAY_EXIT_DIR_IMB_LT]:
                    reason=6

            if reason==0 and rev==1 and not math.isnan(m300[i]):
                if side==1 and m300[i]<=0: reason=5
                elif side==-1 and m300[i]>=0: reason=5
            if reason==0 and held>=maxhold: reason=7

            if reason!=0:
                pnl=move*oz*INR_PER_USD
                total=pnl+partial
                bal+=pnl; ntr+=1
                exposure_sec += held
                sum_mfe += peak
                sum_mae += trough

                if pos==4:
                    burst_pnl += total
                    burst_trades += 1
                    burst_exposure_sec += held

                if total>0: gp+=total; win+=1
                elif total<0: gl-=total
                if bal>peakbal: peakbal=bal
                dd=peakbal-bal
                if dd>maxdd: maxdd=dd
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

        if chosen==0 and ts-lb>=burst_cfg[1]:
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
            pos=chosen; side=sside; ptime=ts; peak=0.; trough=0.; partial=0.; partial_done=0; highopen=1 if high else 0

    pf=gp/gl if gl>0 else 999.
    return (
        bal-500.,pf,ntr,win,maxdd,exposure_sec,burst_pnl,burst_trades,
        burst_exposure_sec,sum_mfe,sum_mae
    )


def segment_indices(arrays, bounds):
    return [
        (
            int(np.searchsorted(arrays["t"],bounds[i],"left")),
            int(np.searchsorted(arrays["t"],bounds[i+1],"left")),
        )
        for i in range(5)
    ]


def run_segments(arrays, bounds, cfg, segment_ids):
    inds=segment_indices(arrays,bounds)
    args=[arrays[x] for x in canonical.FEATURE_NAMES]

    a0,z0=inds[segment_ids[0]]
    simulate_velocity(*args,a0,min(z0,a0+2),cfg)

    seg=[]
    for sid in segment_ids:
        a,z=inds[sid]
        r=simulate_velocity(*args,a,z,cfg)
        seg.append(
            {
                "segment_id":sid,
                "pnl_inr":float(r[0]),
                "profit_factor":float(r[1]),
                "trades":int(r[2]),
                "wins":int(r[3]),
                "max_drawdown_inr":float(r[4]),
                "exposure_sec":float(r[5]),
                "burst_pnl_inr":float(r[6]),
                "burst_trades":int(r[7]),
                "burst_exposure_sec":float(r[8]),
                "sum_mfe_usd":float(r[9]),
                "sum_mae_usd":float(r[10]),
            }
        )

    factor=1.0
    for r in seg:
        factor*=1.0+r["pnl_inr"]/START_BALANCE_INR
    compounded=START_BALANCE_INR*factor-START_BALANCE_INR
    sum_pnl=sum(r["pnl_inr"] for r in seg)
    exposure_sec=sum(r["exposure_sec"] for r in seg)
    burst_exposure_sec=sum(r["burst_exposure_sec"] for r in seg)
    trades=sum(r["trades"] for r in seg)
    burst_trades=sum(r["burst_trades"] for r in seg)

    return {
        "segments":seg,
        "compounded_pnl_inr":compounded,
        "sum_segment_pnl_inr":sum_pnl,
        "capture_ratio":compounded/canonical.OPPORTUNITY_CEILING_INR,
        "trades_sum":trades,
        "wins_sum":sum(r["wins"] for r in seg),
        "median_segment_pf":float(np.median([r["profit_factor"] for r in seg])),
        "max_segment_drawdown_inr":max(r["max_drawdown_inr"] for r in seg),
        "negative_segments":sum(1 for r in seg if r["pnl_inr"] < 0),
        "exposure_hours":exposure_sec/3600.0,
        "pnl_per_exposure_hour":sum_pnl/(exposure_sec/3600.0) if exposure_sec>0 else 0.0,
        "mean_hold_sec":exposure_sec/trades if trades>0 else 0.0,
        "pnl_per_trade_inr":sum_pnl/trades if trades>0 else 0.0,
        "burst_pnl_inr":sum(r["burst_pnl_inr"] for r in seg),
        "burst_trades":burst_trades,
        "burst_exposure_hours":burst_exposure_sec/3600.0,
        "burst_pnl_per_exposure_hour":(
            sum(r["burst_pnl_inr"] for r in seg)/(burst_exposure_sec/3600.0)
            if burst_exposure_sec>0 else 0.0
        ),
        "mean_mfe_usd":sum(r["sum_mfe_usd"] for r in seg)/trades if trades>0 else 0.0,
        "mean_mae_usd":sum(r["sum_mae_usd"] for r in seg)/trades if trades>0 else 0.0,
    }


def assert_candidate_b_parity(arrays, bounds):
    canonical_b=canonical.run_strategy(arrays,bounds,"v4_5_b")
    instrumented=run_segments(arrays,bounds,candidate_b_extended(),list(range(5)))

    failures=[]
    for sid,(a,b) in enumerate(zip(canonical_b["segments"],instrumented["segments"])):
        for key,tol in [
            ("pnl_inr",1e-6),
            ("profit_factor",1e-12),
            ("trades",0),
            ("wins",0),
            ("max_drawdown_inr",1e-6),
        ]:
            av=a[key]; bv=b[key]
            if abs(av-bv)>tol:
                failures.append(f"segment {sid} {key}: canonical={av} instrumented={bv}")

    if failures:
        raise RuntimeError("CANDIDATE B INSTRUMENTATION DRIFT\n"+"\n".join(failures))
    return instrumented


def safe_ratio(value, baseline):
    if baseline <= 1e-12:
        return 0.0
    return value / baseline


def score_pair(m500,m1,b500,b1):
    score=(
        0.40*safe_ratio(m500["compounded_pnl_inr"],b500["compounded_pnl_inr"])
        +0.20*safe_ratio(m1["compounded_pnl_inr"],b1["compounded_pnl_inr"])
        +0.25*safe_ratio(m500["pnl_per_exposure_hour"],b500["pnl_per_exposure_hour"])
        +0.15*safe_ratio(m1["pnl_per_exposure_hour"],b1["pnl_per_exposure_hour"])
    )
    for m,b in [(m500,b500),(m1,b1)]:
        if b["max_segment_drawdown_inr"]>0:
            score-=0.10*max(0.0,m["max_segment_drawdown_inr"]/b["max_segment_drawdown_inr"]-1.0)
        if b["median_segment_pf"]>0:
            score-=0.10*max(0.0,1.0-m["median_segment_pf"]/b["median_segment_pf"])
    return score


def flatten(prefix, metrics):
    return {
        f"{prefix}_pnl":metrics["compounded_pnl_inr"],
        f"{prefix}_capture":metrics["capture_ratio"],
        f"{prefix}_trades":metrics["trades_sum"],
        f"{prefix}_median_pf":metrics["median_segment_pf"],
        f"{prefix}_max_dd":metrics["max_segment_drawdown_inr"],
        f"{prefix}_neg_segments":metrics["negative_segments"],
        f"{prefix}_exposure_h":metrics["exposure_hours"],
        f"{prefix}_pnl_per_exposure_h":metrics["pnl_per_exposure_hour"],
        f"{prefix}_mean_hold_s":metrics["mean_hold_sec"],
        f"{prefix}_pnl_per_trade":metrics["pnl_per_trade_inr"],
        f"{prefix}_burst_pnl":metrics["burst_pnl_inr"],
        f"{prefix}_burst_trades":metrics["burst_trades"],
        f"{prefix}_burst_pnl_per_exposure_h":metrics["burst_pnl_per_exposure_hour"],
        f"{prefix}_mean_mfe_usd":metrics["mean_mfe_usd"],
        f"{prefix}_mean_mae_usd":metrics["mean_mae_usd"],
    }


def evaluate_cfg(name,cfg,features,segment_ids):
    m500=run_segments(features["500ms"][0],features["500ms"][1],cfg,segment_ids)
    m1=run_segments(features["1s"][0],features["1s"][1],cfg,segment_ids)
    return name,m500,m1


def main():
    ap=argparse.ArgumentParser(description="V4.5-C profit-velocity lifecycle search")
    ap.add_argument("csv",type=Path)
    ap.add_argument("--output-dir",type=Path,default=Path("results")/"simulations"/EXPERIMENT_ID)
    ap.add_argument("--top-seed",type=int,default=8)
    ap.add_argument("--top-full",type=int,default=3)
    ap.add_argument("--skip-sha",action="store_true")
    args=ap.parse_args()

    args.output_dir.mkdir(parents=True,exist_ok=True)

    digest="SKIPPED" if args.skip_sha else canonical.verify_dataset(args.csv)
    features={}
    baselines={}
    b_full={}

    for interval in ["500ms","1s"]:
        print(f"[build] {interval}")
        arrays,bounds=canonical.build_features(args.csv,interval)
        baseline=canonical.run_strategy(arrays,bounds,"v4_4")
        canonical.assert_baseline(baseline,interval,canonical.DEFAULT_GOLDEN)
        print(f"[gate] V4.4 {interval} canonical parity PASS")
        b_full[interval]=assert_candidate_b_parity(arrays,bounds)
        print(f"[gate] Candidate B {interval} instrumentation parity PASS")
        features[interval]=(arrays,bounds)
        baselines[interval]=baseline

    b_seed={
        interval:run_segments(features[interval][0],features[interval][1],candidate_b_extended(),[0])
        for interval in ["500ms","1s"]
    }
    b_eval={
        interval:run_segments(features[interval][0],features[interval][1],candidate_b_extended(),[1,2,3,4])
        for interval in ["500ms","1s"]
    }

    seed_rows=[]
    cfg_lookup={}
    variants=make_variants()
    print(f"[search] {len(variants)} lifecycle variants on 0-40% seed")

    for idx,(name,cfg) in enumerate(variants,1):
        cfg_lookup[name]=cfg
        _,m500,m1=evaluate_cfg(name,cfg,features,[0])
        row={"candidate":name,"seed_score":score_pair(m500,m1,b_seed["500ms"],b_seed["1s"])}
        row.update(flatten("500ms",m500))
        row.update(flatten("1s",m1))
        seed_rows.append(row)
        print(f"[seed {idx:02d}/{len(variants)}] {name} score={row['seed_score']:.4f}")

    seed_df=pd.DataFrame(seed_rows).sort_values("seed_score",ascending=False)
    seed_df.to_csv(args.output_dir/"seed_search.csv",index=False)

    shortlist=seed_df.head(args.top_seed)["candidate"].tolist()
    eval_rows=[]
    print(f"[eval] evaluating top {len(shortlist)} on chronological 40-80%")

    for name in shortlist:
        cfg=cfg_lookup[name]
        _,m500,m1=evaluate_cfg(name,cfg,features,[1,2,3,4])
        eval_score=score_pair(m500,m1,b_eval["500ms"],b_eval["1s"])
        eligible=(
            m500["compounded_pnl_inr"] >= 0.95*b_eval["500ms"]["compounded_pnl_inr"]
            and m1["compounded_pnl_inr"] >= 0.95*b_eval["1s"]["compounded_pnl_inr"]
            and m500["pnl_per_exposure_hour"] >= 0.95*b_eval["500ms"]["pnl_per_exposure_hour"]
            and m1["pnl_per_exposure_hour"] >= 0.95*b_eval["1s"]["pnl_per_exposure_hour"]
            and m500["median_segment_pf"] >= 0.90*b_eval["500ms"]["median_segment_pf"]
            and m1["median_segment_pf"] >= 0.90*b_eval["1s"]["median_segment_pf"]
            and m500["max_segment_drawdown_inr"] <= 1.15*b_eval["500ms"]["max_segment_drawdown_inr"]
            and m1["max_segment_drawdown_inr"] <= 1.15*b_eval["1s"]["max_segment_drawdown_inr"]
        )
        row={"candidate":name,"eval_score":eval_score,"eligible":bool(eligible)}
        row.update(flatten("500ms",m500))
        row.update(flatten("1s",m1))
        eval_rows.append(row)
        print(f"[eval] {name} score={eval_score:.4f} eligible={eligible}")

    eval_df=pd.DataFrame(eval_rows).sort_values(["eligible","eval_score"],ascending=[False,False])
    eval_df.to_csv(args.output_dir/"evaluation_shortlist.csv",index=False)

    full_names=eval_df.head(args.top_full)["candidate"].tolist()
    full_rows=[]
    print(f"[full] canonical first-80% replay for top {len(full_names)}")

    for name in full_names:
        cfg=cfg_lookup[name]
        _,m500,m1=evaluate_cfg(name,cfg,features,[0,1,2,3,4])
        full_score=score_pair(m500,m1,b_full["500ms"],b_full["1s"])
        row={"candidate":name,"full_score":full_score}
        row.update(flatten("500ms",m500))
        row.update(flatten("1s",m1))
        full_rows.append(row)
        print(
            f"[full] {name}: 500ms={100*m500['capture_ratio']:.3f}% "
            f"1s={100*m1['capture_ratio']:.3f}% "
            f"vel500=₹{m500['pnl_per_exposure_hour']:.2f}/exposure-h "
            f"vel1s=₹{m1['pnl_per_exposure_hour']:.2f}/exposure-h"
        )

    full_df=pd.DataFrame(full_rows).sort_values("full_score",ascending=False)
    full_df.to_csv(args.output_dir/"full_shortlist.csv",index=False)

    best=full_df.iloc[0].to_dict() if len(full_df) else None
    if best:
        best={k:(v.item() if isinstance(v,np.generic) else v) for k,v in best.items()}

    metadata={
        "experiment_id":EXPERIMENT_ID,
        "dataset_sha256":digest,
        "research_rows":canonical.RESEARCH_ROWS,
        "holdout_evaluated":False,
        "objective":"maximize profit velocity with canonical capture/PF/DD robustness; 1s is a fragility diagnostic, not the primary trading grid",
        "candidate_b_full":{
            "500ms":b_full["500ms"],
            "1s":b_full["1s"],
        },
        "variant_count":len(variants),
        "top_seed":args.top_seed,
        "top_full":args.top_full,
        "provisional_leader":best,
        "notes":[
            "V4.4 parity is asserted before any search.",
            "The instrumented simulator must reproduce Candidate B exactly before variants run.",
            "Phase C1 changes BURST lifecycle only; BURST admission and all V4.4 engines remain unchanged.",
            "Selection occurs on 0-40%; shortlisted candidates are evaluated on 40-80% before a full first-80% summary.",
            "No candidate is automatically promoted or locked by this script.",
            "The final 20% holdout remains unopened.",
            "Cost stress is a required later gate before V4.5 lock.",
        ],
    }
    (args.output_dir/"run_metadata.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")

    print(f"[done] outputs -> {args.output_dir}")
    if best:
        print(
            "[leader] "
            f"{best['candidate']} | "
            f"500ms capture={100*best['500ms_capture']:.3f}% | "
            f"1s capture={100*best['1s_capture']:.3f}%"
        )


if __name__=="__main__":
    main()
