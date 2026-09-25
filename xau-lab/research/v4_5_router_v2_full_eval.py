"""Experiment 30: full raw-tick Router-v2 diagnostic replay.

Runs Candidate D and the frozen stronghold-aware Router v2 through the same
sampled feature/lifecycle engine on:
  1) canonical seven-day first-80% research pool,
  2) the separate recent 24-hour snapshot, and
  3) deterministic random four-hour windows sampled from both real datasets.

Known-data results are diagnostic only. They must not be used to tune the
Experiment-28 score definition.
"""
from __future__ import annotations

import argparse, csv, json
from pathlib import Path
import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_regime_portability as portability
import v4_5_router_v2 as router

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_OUT=ROOT/"results"/"simulations"/"2026-09-25-v4_5-router-v2-full-replay"

EXPECTED_D={
    "500ms":{"pnl":1430.311133793068,"trades":163,"wins":81},
    "1s":{"pnl":385.2544619534224,"trades":156,"wins":71},
}
RANDOM_SEED=20260925
RANDOM_WINDOWS=100
RANDOM_HOURS=4.0


def compact(m):
    return {k:m[k] for k in (
        "pnl_inr","terminal_unrealized_inr","terminal_equity_pnl_inr",
        "open_position_at_end","profit_factor","trades","wins","win_rate",
        "max_drawdown_inr","routed_entries","hold_decisions"
    )}


def summarize_segments(rows):
    factor=1.0; trades=wins=0; dds=[]
    for m in rows:
        factor*=1.0+m["pnl_inr"]/canonical.START_BALANCE_INR
        trades+=m["trades"]; wins+=m["wins"]; dds.append(m["max_drawdown_inr"])
    pnl=canonical.START_BALANCE_INR*(factor-1.0)
    return {
        "compounded_pnl_inr":pnl,
        "trades":trades,
        "wins":wins,
        "win_rate":wins/trades if trades else 0.0,
        "max_segment_drawdown_inr":max(dds) if dds else 0.0,
    }


def assert_candidate_d(summary,interval):
    exp=EXPECTED_D[interval]
    if abs(summary["compounded_pnl_inr"]-exp["pnl"])>1e-6:
        raise RuntimeError(f"Candidate D P&L parity drift {interval}: {summary['compounded_pnl_inr']} != {exp['pnl']}")
    if summary["trades"]!=exp["trades"] or summary["wins"]!=exp["wins"]:
        raise RuntimeError(f"Candidate D count parity drift {interval}: {summary}")


def run_segment_pair(arr,start,end,cache):
    return (
        router.simulate(arr,start,end,legacy=True),
        router.simulate(arr,start,end,cache=cache,legacy=False),
    )


def random_window_from_ranges(arr,ranges,rng,hours):
    """Sample one chronological real window from one or more valid index ranges."""
    t=arr["t"]; seconds=hours*3600.0
    valid=[]
    for range_id,(start,end) in enumerate(ranges):
        if end<=start:
            continue
        lo=float(t[start]); last=float(t[end-1]); available=last-lo-seconds
        if available>=0:
            valid.append((range_id,start,end,lo,last,available))
    if not valid:
        raise RuntimeError("no chronological range can hold requested random window")

    weights=np.asarray([x[5]+1.0 for x in valid],dtype=float)
    weights/=weights.sum()
    pick=valid[int(rng.choice(len(valid),p=weights))]
    range_id,start,end,lo,last,available=pick
    target=lo if available<=0 else float(rng.uniform(lo,lo+available))
    a=max(start,int(np.searchsorted(t,target,"left")))
    z=min(end,int(np.searchsorted(t,target+seconds,"right")))
    if z<=a or float(t[z-1])<float(t[a]):
        raise RuntimeError(f"invalid random window: range={range_id} start={a} end={z}")
    return a,z,range_id


def random_summary(rows,key_prefix):
    cp=np.array([r[f"{key_prefix}_pnl"] for r in rows],dtype=float)
    tr=np.array([r[f"{key_prefix}_trades"] for r in rows],dtype=float)
    wi=np.array([r[f"{key_prefix}_wins"] for r in rows],dtype=float)
    return {
        "windows":len(rows),
        "median_terminal_equity_pnl_inr":float(np.median(cp)) if len(cp) else 0.0,
        "mean_terminal_equity_pnl_inr":float(np.mean(cp)) if len(cp) else 0.0,
        "p05_terminal_equity_pnl_inr":float(np.quantile(cp,.05)) if len(cp) else 0.0,
        "p95_terminal_equity_pnl_inr":float(np.quantile(cp,.95)) if len(cp) else 0.0,
        "positive_window_fraction":float(np.mean(cp>0)) if len(cp) else 0.0,
        "total_trades":int(tr.sum()),
        "total_wins":int(wi.sum()),
        "aggregate_win_rate":float(wi.sum()/tr.sum()) if tr.sum() else 0.0,
    }


def write_csv(path,rows):
    if not rows:return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


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
        "schema":"xau-router-v2-full-replay-v1",
        "promotion_evidence":False,
        "score_tuned":False,
        "final20_opened":False,
        "random_window_method":"real contiguous four-hour windows sampled from canonical first80 and recent24h; no fabricated price paths",
        "random_seed":a.seed,
        "random_windows_per_grid":a.random_windows,
        "random_hours":a.random_hours,
        "intervals":{},
    }
    all_random=[]

    for interval in ("500ms","1s"):
        print(f"{interval}: building canonical features",flush=True)
        h_arr,h_bounds=canonical.build_features(a.canonical_csv,interval)
        canonical.assert_baseline(canonical.run_strategy(h_arr,h_bounds,"v4_4"),interval,canonical.DEFAULT_GOLDEN)
        print(f"{interval}: building canonical Router-v2 state cache",flush=True)
        h_cache=router.build_state_cache(a.canonical_csv,h_arr)
        h_inds=autopsy.indices(h_arr,h_bounds)
        h_d=[]; h_r=[]
        for sid,(s,e) in enumerate(h_inds):
            d,r=run_segment_pair(h_arr,s,e,h_cache); h_d.append(d); h_r.append(r)
        h_ds=summarize_segments(h_d); h_rs=summarize_segments(h_r)
        assert_candidate_d(h_ds,interval)

        print(f"{interval}: building recent features",flush=True)
        r_arr,_=canonical.build_features(a.recent_csv_or_gz,interval)
        print(f"{interval}: building recent Router-v2 state cache",flush=True)
        r_cache=router.build_state_cache(a.recent_csv_or_gz,r_arr)
        r_d,r_v=run_segment_pair(r_arr,0,len(r_arr["t"]),r_cache)

        times=pd.read_csv(a.recent_csv_or_gz,usecols=["timestamp_utc"])["timestamp_utc"]
        cut_ts=pd.to_datetime(times.iloc[int(len(times)*.6)],utc=True).timestamp()
        cut=int(np.searchsorted(r_arr["t"],cut_ts,"left"))
        recent_split=[]
        for name,s,e in (("seed",0,cut),("evaluation",cut,len(r_arr["t"]))):
            d,v=run_segment_pair(r_arr,s,e,r_cache)
            recent_split.append({"split":name,"candidate_d":compact(d),"router_v2":compact(v)})

        if np.any(np.diff(h_arr["t"])<0) or np.any(np.diff(r_arr["t"])<0):
            raise RuntimeError("sampled feature timestamps are not monotonic")

        rng=np.random.default_rng(a.seed + (0 if interval=="500ms" else 1))
        rows=[]
        hist_ranges=h_inds
        recent_ranges=[(0,len(r_arr["t"]))]
        for wid in range(a.random_windows):
            source="historical7d" if wid%2==0 else "recent24h"
            if source=="historical7d":
                arr,cache,ranges=h_arr,h_cache,hist_ranges
            else:
                arr,cache,ranges=r_arr,r_cache,recent_ranges
            s,e,range_id=random_window_from_ranges(arr,ranges,rng,a.random_hours)
            d,v=run_segment_pair(arr,s,e,cache)
            rows.append({
                "interval":interval,"window_id":wid,"source":source,"source_range_id":range_id,
                "start_ts":float(arr["t"][s]),"end_ts":float(arr["t"][e-1]),
                "candidate_d_pnl":float(d["terminal_equity_pnl_inr"]),
                "router_v2_pnl":float(v["terminal_equity_pnl_inr"]),
                "candidate_d_trades":int(d["trades"]),"router_v2_trades":int(v["trades"]),
                "candidate_d_wins":int(d["wins"]),"router_v2_wins":int(v["wins"]),
                "router_hold_decisions":int(v["hold_decisions"]),
                "router_routed_entries":int(v["routed_entries"]),
            })
        all_random.extend(rows)
        d_rand=random_summary(rows,"candidate_d"); v_rand=random_summary(rows,"router_v2")
        router_better=float(np.mean([x["router_v2_pnl"]>x["candidate_d_pnl"] for x in rows])) if rows else 0.0
        retention=(v_rand["total_trades"]/d_rand["total_trades"]) if d_rand["total_trades"] else 0.0

        result["intervals"][interval]={
            "canonical_first80":{
                "candidate_d":h_ds,"router_v2":h_rs,
                "pnl_delta_inr":h_rs["compounded_pnl_inr"]-h_ds["compounded_pnl_inr"],
                "trade_retention":h_rs["trades"]/h_ds["trades"] if h_ds["trades"] else 0.0,
                "win_rate_delta":h_rs["win_rate"]-h_ds["win_rate"],
                "candidate_d_segments":[compact(x) for x in h_d],
                "router_v2_segments":[compact(x) for x in h_r],
            },
            "recent24h_whole":{
                "candidate_d":compact(r_d),"router_v2":compact(r_v),
                "terminal_equity_pnl_delta_inr":r_v["terminal_equity_pnl_inr"]-r_d["terminal_equity_pnl_inr"],
                "trade_retention":r_v["trades"]/r_d["trades"] if r_d["trades"] else 0.0,
                "win_rate_delta":r_v["win_rate"]-r_d["win_rate"],
            },
            "recent24h_split":recent_split,
            "random_real_windows":{
                "candidate_d":d_rand,"router_v2":v_rand,
                "router_better_window_fraction":router_better,
                "trade_retention":retention,
            }
        }

        del h_arr,h_cache,r_arr,r_cache

    write_csv(a.output/"random_real_windows.csv",all_random)
    (a.output/"full_replay_summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
