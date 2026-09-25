"""Experiment 26: replay the frozen Experiment-23 regime state on recent raw XAU data.

No strategy or regime thresholds are tuned here.
"""
from __future__ import annotations

import argparse, gzip, hashlib, json
from pathlib import Path

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_regime_normalization as regime

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results"/"simulations"/"2026-09-25-v4_5-regime-portability"
RECENT_RAW_SHA="9243ac73c3d180417ff634fe9371a28939713a531c9ccfa63f919c94eb9a28b1"
RECENT_GZ_SHA="2d3c963f678aa0341224efe5f6859651018e11a43c8c5797bb5685f8dce19aeb"

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def verify_recent(path):
    if path.suffix==".gz":
        if sha256(path)!=RECENT_GZ_SHA: raise RuntimeError("recent archive hash mismatch")
        h=hashlib.sha256()
        with gzip.open(path,"rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
        if h.hexdigest()!=RECENT_RAW_SHA: raise RuntimeError("recent raw hash mismatch")
    elif sha256(path)!=RECENT_RAW_SHA:
        raise RuntimeError("recent raw hash mismatch")

def recent_candidate_rows(path, interval):
    times=pd.read_csv(path,usecols=["timestamp_utc"])["timestamp_utc"]
    cut_row=int(len(times)*0.6)
    cut_ts=pd.to_datetime(times.iloc[cut_row],utc=True).timestamp()
    arrays,_=canonical.build_features(path,interval)
    cut=int(np.searchsorted(arrays["t"],cut_ts,"left"))
    args=[arrays[k] for k in canonical.FEATURE_NAMES]
    rows=[]
    for segment_id,(split,start,end) in enumerate((("seed",0,cut),("evaluation",cut,len(arrays["t"])))):
        r=autopsy.simulate_trace(*args,start,end,canonical.burst_config("v4_5_b"),1.0)
        for tid,x in enumerate(r[5]):
            rows.append({
                "trade_id":f"{interval}-{split}-{tid}",
                "interval":interval,"segment_id":segment_id,"split":split,
                "engine":autopsy.ENGINES[int(x[2])],
                "side":"BUY" if int(x[3])==1 else "SELL",
                "side_sign":int(x[3]),"entry_ts":float(x[5]),"exit_ts":float(x[6]),
                "pnl_inr":float(x[9]),"exit_reason":autopsy.REASONS[int(x[4])]
            })
    return rows

def match_recent(rows):
    a=[r for r in rows if r["interval"]=="500ms"]; b=[r for r in rows if r["interval"]=="1s"]
    used=set(); out=[]
    for x in sorted(a,key=lambda r:r["entry_ts"]):
        opts=[]
        for j,y in enumerate(b):
            if j in used or y["segment_id"]!=x["segment_id"] or y["engine"]!=x["engine"] or y["side"]!=x["side"]: continue
            dt=abs(y["entry_ts"]-x["entry_ts"])
            if dt<=120: opts.append((dt,j,y))
        if not opts: continue
        _,j,y=min(opts,key=lambda z:z[0]); used.add(j)
        out.append({k:(x[k]==y[k]) for k in ("raw_vol_regime","raw_spread_regime","raw_efficiency_regime","raw_activity_regime","raw_regime_key")})
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("canonical_csv",type=Path)
    ap.add_argument("recent_csv_or_gz",type=Path)
    ap.add_argument("--output",type=Path,default=OUT)
    args=ap.parse_args()
    canonical.verify_dataset(args.canonical_csv); verify_recent(args.recent_csv_or_gz)

    historical=[]; recent=[]
    for interval in ("500ms","1s"):
        _,hrows=regime.candidate_d_rows(args.canonical_csv,interval); historical.extend(hrows)
        recent.extend(recent_candidate_rows(args.recent_csv_or_gz,interval))
    historical=regime.overlay(args.canonical_csv,historical)
    recent=regime.overlay(args.recent_csv_or_gz,recent)

    h=pd.DataFrame(historical); r=pd.DataFrame(recent)
    lookup=h.groupby(["interval","engine","raw_regime_key"]).pnl_inr.agg(["size","sum"]).reset_index()
    lookup.columns=["interval","engine","raw_regime_key","hist_trades","hist_pnl"]
    r=r.merge(lookup,on=["interval","engine","raw_regime_key"],how="left")
    r["hist_class"]=np.where(r.hist_trades.isna(),"unseen",np.where(r.hist_pnl>0,"historical_positive","historical_nonpositive"))

    transfer=r.groupby(["interval","hist_class"]).agg(trades=("pnl_inr","size"),wins=("pnl_inr",lambda s:int((s>0).sum())),pnl_inr=("pnl_inr","sum")).reset_index()
    transfer["win_rate"]=transfer.wins/transfer.trades

    matches=match_recent(recent)
    agreement={k:float(np.mean([m[k] for m in matches])) for k in matches[0]} if matches else {}

    args.output.mkdir(parents=True,exist_ok=True)
    r.to_csv(args.output/"recent_candidate_d_regime_overlay.csv",index=False)
    transfer.to_csv(args.output/"historical_key_transfer.csv",index=False)
    summary={"schema_version":"xau-regime-portability-v1","matched_pairs":len(matches),"agreement":agreement,"strategy_changed":False,"router_promoted":False}
    (args.output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__=="__main__": main()
