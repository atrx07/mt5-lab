"""Experiment 52: outcome-known structural autopsy of rejected Candidate L.

Candidate L is already rejected. This diagnostic uses its frozen trade ledger to
separate entry-quality failure from exit-management failure. It does not define,
search, or evaluate another candidate and must not be used to tune Candidate L's
numeric thresholds.
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

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRADES = ROOT / "results" / "simulations" / "2026-10-06-v4_5-candidate-l-normalized-resumption" / "candidate_l_trades.csv"
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-10-06-v4_5-candidate-l-failure-autopsy"
REASON = {1:"STOP",2:"TP",5:"M300_FAILURE",7:"TIME",8:"FLOW_EXIT"}


def write_csv(path: Path, rows: List[Dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8"); return
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


def q(x, p):
    a=np.asarray(x,float); a=a[np.isfinite(a)]
    return float(np.quantile(a,p)) if len(a) else math.nan


def parse_context(s: str):
    p=s.split(":")
    if p[0]=="historical":
        return "historical_first80", p[1], p[2] if len(p)>2 else ""
    if p[0]=="current7d":
        return "current7d", p[1], "whole"
    if p[0]=="block":
        return f"stage1:{p[1]}", p[2], "block"
    return p[0], p[1] if len(p)>1 else "unknown", ":".join(p[2:])


def aggregate(g: pd.DataFrame, source: str, interval: str, scope: str, reason: str="ALL") -> Dict:
    pnl=g.pnl_inr.to_numpy(float); held=g.held_sec.to_numpy(float); mfe=g.mfe_usd.to_numpy(float); exitm=g.exit_move_usd.to_numpy(float)
    neg=pnl<0
    return {
        "source":source,"interval":interval,"scope":scope,"exit_reason":reason,
        "trades":int(len(g)),"wins":int(np.sum(pnl>0)),"win_rate":float(np.mean(pnl>0)) if len(g) else 0.0,
        "pnl_sum":float(np.sum(pnl)),"pnl_mean":float(np.mean(pnl)) if len(g) else math.nan,
        "pnl_median":float(np.median(pnl)) if len(g) else math.nan,
        "held_median_sec":float(np.median(held)) if len(g) else math.nan,
        "held_p90_sec":q(held,.90),
        "mfe_median_usd":float(np.median(mfe)) if len(g) else math.nan,
        "mfe_p75_usd":q(mfe,.75),"mfe_p90_usd":q(mfe,.90),
        "exit_move_median_usd":float(np.median(exitm)) if len(g) else math.nan,
        "exit_le_30s_fraction":float(np.mean(held<=30)) if len(g) else math.nan,
        "exit_le_60s_fraction":float(np.mean(held<=60)) if len(g) else math.nan,
        "exit_le_120s_fraction":float(np.mean(held<=120)) if len(g) else math.nan,
        "mfe_ge_1r_fraction":float(np.mean(mfe>=4.0)) if len(g) else math.nan,
        "mfe_ge_2r_fraction":float(np.mean(mfe>=8.0)) if len(g) else math.nan,
        "losers_that_reached_1r_fraction":float(np.mean(mfe[neg]>=4.0)) if np.any(neg) else math.nan,
        "losers_mfe_lt_0_5r_fraction":float(np.mean(mfe[neg]<2.0)) if np.any(neg) else math.nan,
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trades",type=Path,default=DEFAULT_TRADES)
    ap.add_argument("--output",type=Path,default=DEFAULT_OUT)
    a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(a.trades)
    parsed=df.context.astype(str).map(parse_context)
    df["source"]=[x[0] for x in parsed]; df["interval"]=[x[1] for x in parsed]; df["segment"]=[x[2] for x in parsed]
    df["reason_name"]=df.exit_reason.map(lambda x:REASON.get(int(x),str(int(x))))

    summary_rows=[]
    for (source,interval),g in df.groupby(["source","interval"],sort=False):
        summary_rows.append(aggregate(g,source,interval,"all"))
        for reason,rg in g.groupby("reason_name",sort=False):
            summary_rows.append(aggregate(rg,source,interval,"by_reason",str(reason)))

    # Churn/re-entry diagnostics are outcome-independent timing summaries of the
    # rejected ledger; no threshold is selected from them.
    churn=[]
    for (source,interval),g in df.sort_values("entry_ts").groupby(["source","interval"],sort=False):
        e=g.entry_ts.to_numpy(float); sides=g.side.astype(str).to_numpy()
        dt=np.diff(e)
        same=sides[1:]==sides[:-1] if len(g)>1 else np.array([],bool)
        churn.append({
            "source":source,"interval":interval,"trades":int(len(g)),
            "median_inter_entry_sec":float(np.median(dt)) if len(dt) else math.nan,
            "same_side_reentry_le_30s":int(np.sum(same & (dt<=30))) if len(dt) else 0,
            "same_side_reentry_le_60s":int(np.sum(same & (dt<=60))) if len(dt) else 0,
            "same_side_reentry_le_120s":int(np.sum(same & (dt<=120))) if len(dt) else 0,
            "same_side_reentry_le_300s":int(np.sum(same & (dt<=300))) if len(dt) else 0,
        })

    # Pool six Stage-1 blocks without pretending they are independent of current7d.
    pooled=[]
    for interval,g in df[df.source.str.startswith("stage1:")].groupby("interval",sort=False):
        pooled.append(aggregate(g,"stage1_pooled",interval,"all"))
        for reason,rg in g.groupby("reason_name",sort=False):
            pooled.append(aggregate(rg,"stage1_pooled",interval,"by_reason",str(reason)))

    all_rows=summary_rows+pooled
    write_csv(a.output/"exit_reason_diagnostics.csv",all_rows)
    write_csv(a.output/"reentry_churn.csv",churn)

    headline={}
    for source in ("historical_first80","current7d","stage1_pooled"):
        headline[source]={}
        for interval in ("500ms","1s"):
            rows=[r for r in all_rows if r["source"]==source and r["interval"]==interval and r["scope"]=="all"]
            if rows: headline[source][interval]=rows[0]
    reason_headline={}
    for interval in ("500ms","1s"):
        g=df[(df.source=="current7d") & (df.interval==interval)]
        reason_headline[interval]={}
        for reason,rg in g.groupby("reason_name"):
            reason_headline[interval][str(reason)]={
                "trades":int(len(rg)),"pnl_sum":float(rg.pnl_inr.sum()),
                "pnl_mean":float(rg.pnl_inr.mean()),"held_median_sec":float(rg.held_sec.median()),
                "mfe_median_usd":float(rg.mfe_usd.median()),
            }
    result={
        "schema":"xau-candidate-l-failure-autopsy-v1",
        "status":"outcome-known diagnostic after Candidate L rejection",
        "strategy_changed":False,"threshold_search":False,"candidate_l_retuning_allowed":False,"final20_opened":False,
        "headline":headline,"current7d_by_exit_reason":reason_headline,
        "interpretation":"Separate false-entry/commitment failure from exit-management failure. Any next candidate must be structurally different and frozen before P&L evaluation.",
    }
    (a.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
