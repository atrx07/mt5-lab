"""Experiment 36: xau-microstate-v1 representation freeze.

Representation-only. No P&L label is read or written into the feature-validation
dataset. Features use raw events strictly before/at each independent opportunity.
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
import v4_5_regime_portability as portability

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_ATLAS=ROOT/"results"/"simulations"/"2026-09-25-v4_5-independent-opportunity-atlas"/"shadow_opportunities.csv"
DEFAULT_OUT=ROOT/"results"/"simulations"/"2026-09-25-v4_5-microstate-v1-freeze"

FEATURES=(
    "raw_count2","raw_count10","event_rate_accel_2_10",
    "median_iat2_ms","median_iat10_ms","iat_ratio_2_10",
    "mid_move2","mid_move10","dir_mid_move2","dir_mid_move10",
    "event_eff2","event_eff10",
    "event_imb2","event_imb10","dir_event_imb2","dir_event_imb10",
    "dir_imbalance_delta_2_10",
    "quote_sidedness2","two_sided_update_frac2",
    "spread_rel10","spread_change_rel2","spread_compression10",
    "dir_range_position10",
)


def epoch_seconds(series):
    return series.to_numpy(dtype="datetime64[ns]").astype(np.int64)/1e9


def load_raw(path,nrows=None):
    df=pd.read_csv(path,nrows=nrows,usecols=["timestamp_utc","bid","ask"])
    df["t"]=pd.to_datetime(df.timestamp_utc,utc=True,format="mixed")
    df=df.sort_values("t",kind="stable").reset_index(drop=True)
    df["mid"]=(df.bid+df.ask)/2.0
    df["spread"]=df.ask-df.bid
    t=epoch_seconds(df["t"])
    gap=np.r_[True,np.diff(t)>5.0]
    session=np.cumsum(gap)-1
    start=np.empty(len(df),dtype=np.int64)
    cur=0
    for i in range(len(df)):
        if gap[i]:cur=i
        start[i]=cur
    return {
        "t":t,
        "bid":df.bid.to_numpy(float),"ask":df.ask.to_numpy(float),
        "mid":df.mid.to_numpy(float),"spread":df.spread.to_numpy(float),
        "session":session,"session_start":start,
    }


def safe_div(a,b):
    return float(a/b) if np.isfinite(a) and np.isfinite(b) and abs(b)>1e-12 else math.nan


def window(raw,j,seconds):
    t=raw["t"]; ss=int(raw["session_start"][j])
    lo=max(ss,int(np.searchsorted(t,float(t[j])-seconds,side="left")))
    return lo,j+1


def iat_ms(t):
    if len(t)<2:return math.nan
    d=np.diff(t)
    d=d[d>=0]
    return float(np.median(d)*1000.0) if len(d) else math.nan


def efficiency(mid):
    if len(mid)<2:return math.nan
    path=float(np.abs(np.diff(mid)).sum())
    return abs(float(mid[-1]-mid[0]))/path if path>1e-12 else 0.0


def imbalance(mid):
    if len(mid)<2:return 0.0
    d=np.diff(mid)
    up=int((d>0).sum()); dn=int((d<0).sum())
    return float((up-dn)/(up+dn)) if up+dn else 0.0


def features_at(raw,ts,side):
    t=raw["t"]
    j=int(np.searchsorted(t,float(ts),side="right")-1)
    if j<0:return {k:math.nan for k in FEATURES}
    a2,b2=window(raw,j,2.0); a10,b10=window(raw,j,10.0)
    t2=t[a2:b2]; t10=t[a10:b10]
    m2=raw["mid"][a2:b2]; m10=raw["mid"][a10:b10]
    s2=raw["spread"][a2:b2]; s10=raw["spread"][a10:b10]
    bid2=raw["bid"][a2:b2]; ask2=raw["ask"][a2:b2]

    c2=len(t2); c10=len(t10)
    ia2=iat_ms(t2); ia10=iat_ms(t10)
    mm2=float(m2[-1]-m2[0]) if len(m2)>=2 else 0.0
    mm10=float(m10[-1]-m10[0]) if len(m10)>=2 else 0.0
    imb2=imbalance(m2); imb10=imbalance(m10)

    if len(bid2)>=2:
        bd=np.diff(bid2)!=0; ad=np.diff(ask2)!=0
        anyu=bd|ad; both=bd&ad
        denom=int(anyu.sum())
        sided=float((int(bd.sum())-int(ad.sum()))/denom) if denom else 0.0
        both_frac=float(int(both.sum())/denom) if denom else 0.0
    else:
        sided=0.0; both_frac=0.0

    medspread=float(np.median(s10)) if len(s10) else math.nan
    curspread=float(raw["spread"][j])
    maxspread=float(np.max(s10)) if len(s10) else math.nan
    spread_first2=float(s2[0]) if len(s2) else math.nan

    if len(m10):
        lo=float(np.min(m10)); hi=float(np.max(m10))
        pos=(2.0*(float(m10[-1])-lo)/(hi-lo)-1.0) if hi-lo>1e-12 else 0.0
    else:
        pos=math.nan

    return {
        "raw_count2":float(c2),"raw_count10":float(c10),
        "event_rate_accel_2_10":safe_div(c2/2.0,c10/10.0),
        "median_iat2_ms":ia2,"median_iat10_ms":ia10,
        "iat_ratio_2_10":safe_div(ia2,ia10),
        "mid_move2":mm2,"mid_move10":mm10,
        "dir_mid_move2":float(side)*mm2,"dir_mid_move10":float(side)*mm10,
        "event_eff2":efficiency(m2),"event_eff10":efficiency(m10),
        "event_imb2":imb2,"event_imb10":imb10,
        "dir_event_imb2":float(side)*imb2,"dir_event_imb10":float(side)*imb10,
        "dir_imbalance_delta_2_10":float(side)*(imb2-imb10),
        "quote_sidedness2":sided,"two_sided_update_frac2":both_frac,
        "spread_rel10":safe_div(curspread,medspread),
        "spread_change_rel2":safe_div(curspread-spread_first2,medspread),
        "spread_compression10":safe_div(maxspread-curspread,medspread),
        "dir_range_position10":float(side)*pos,
    }


def write_csv(path,rows):
    if not rows:
        path.write_text("",encoding="utf-8");return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields:fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def spearman(a,b):
    a=pd.Series(a,dtype=float);b=pd.Series(b,dtype=float)
    ok=a.notna()&b.notna()
    if int(ok.sum())<3:return math.nan
    return float(a[ok].rank().corr(b[ok].rank()))


def match_rows(rows,max_delta):
    a=sorted([r for r in rows if r["interval"]=="500ms"],key=lambda x:float(x["entry_ts"]))
    b=sorted([r for r in rows if r["interval"]=="1s"],key=lambda x:float(x["entry_ts"]))
    used=set();out=[]
    for x in a:
        best=None
        for j,y in enumerate(b):
            if j in used or y["window"]!=x["window"] or y["engine"]!=x["engine"] or y["side"]!=x["side"]:continue
            dt=abs(float(y["entry_ts"])-float(x["entry_ts"]))
            if dt>max_delta:continue
            if best is None or dt<best[0]:best=(dt,j,y)
        if best is None:continue
        dt,j,y=best;used.add(j)
        row={"window":x["window"],"engine":x["engine"],"side":x["side"],
             "entry_500ms":x["entry_ts"],"entry_1s":y["entry_ts"],"abs_delta_sec":dt}
        for feat in FEATURES:
            row[f"{feat}_500ms"]=x[feat];row[f"{feat}_1s"]=y[feat]
        out.append(row)
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("canonical_csv",type=Path)
    ap.add_argument("recent_csv_or_gz",type=Path)
    ap.add_argument("--atlas",type=Path,default=DEFAULT_ATLAS)
    ap.add_argument("--output",type=Path,default=DEFAULT_OUT)
    a=ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True,exist_ok=True)

    atlas=pd.read_csv(a.atlas)
    atlas=atlas[atlas["censored"].astype(str).str.lower().eq("false")].copy()
    # Deliberately retain only metadata, never outcome labels.
    cols=["window","interval","segment_id","engine","side","side_sign","entry_ts"]
    atlas=atlas[cols]

    print("loading canonical raw first80",flush=True)
    h=load_raw(a.canonical_csv,nrows=canonical.RESEARCH_ROWS)
    print("loading recent raw",flush=True)
    r=load_raw(a.recent_csv_or_gz)

    rows=[]
    for rec in atlas.to_dict("records"):
        raw=h if rec["window"]=="historical7d" else r
        row=dict(rec)
        row.update(features_at(raw,float(rec["entry_ts"]),int(rec["side_sign"])))
        rows.append(row)

    coverage=[]
    df=pd.DataFrame(rows)
    for (window,interval),g in df.groupby(["window","interval"],sort=True):
        for feat in FEATURES:
            x=pd.to_numeric(g[feat],errors="coerce")
            coverage.append({"window":window,"interval":interval,"feature":feat,
                             "rows":len(g),"finite":int(np.isfinite(x).sum()),
                             "finite_fraction":float(np.isfinite(x).mean())})

    strict=match_rows(rows,10.0)
    broad=match_rows(rows,120.0)
    stability=[]
    for label,pairs in (("strict_10s",strict),("broad_120s",broad)):
        p=pd.DataFrame(pairs)
        for window in ("historical7d","recent24h"):
            q=p[p.window==window] if not p.empty else p
            for feat in FEATURES:
                c=spearman(pd.to_numeric(q.get(f"{feat}_500ms"),errors="coerce"),
                           pd.to_numeric(q.get(f"{feat}_1s"),errors="coerce")) if len(q) else math.nan
                stability.append({"match_set":label,"window":window,"feature":feat,
                                  "pairs":len(q),"spearman":c})

    drift=[]
    for interval in ("500ms","1s"):
        hdf=df[(df.window=="historical7d")&(df.interval==interval)]
        rdf=df[(df.window=="recent24h")&(df.interval==interval)]
        for feat in FEATURES:
            hv=pd.to_numeric(hdf[feat],errors="coerce");rv=pd.to_numeric(rdf[feat],errors="coerce")
            drift.append({"interval":interval,"feature":feat,
                          "historical_median":float(hv.median()),"recent_median":float(rv.median()),
                          "historical_iqr":float(hv.quantile(.75)-hv.quantile(.25)),
                          "recent_iqr":float(rv.quantile(.75)-rv.quantile(.25))})

    write_csv(a.output/"microstate_opportunities.csv",rows)
    write_csv(a.output/"coverage.csv",coverage)
    write_csv(a.output/"cross_grid_strict_matches.csv",strict)
    write_csv(a.output/"cross_grid_broad_matches.csv",broad)
    write_csv(a.output/"cross_grid_stability.csv",stability)
    write_csv(a.output/"distribution_drift.csv",drift)

    strict_df=pd.DataFrame(stability)
    strict_df=strict_df[strict_df.match_set=="strict_10s"]
    result={
        "schema":"xau-microstate-v1",
        "strategy_changed":False,"outcome_labels_used":False,"selection_performed":False,
        "features":list(FEATURES),"final20_opened":False,
        "rows":len(rows),"historical_rows":int((df.window=="historical7d").sum()),
        "recent_rows":int((df.window=="recent24h").sum()),
        "strict_matches":len(strict),"broad_matches":len(broad),
        "strict_median_spearman_by_window":{
            w:float(pd.to_numeric(strict_df[strict_df.window==w].spearman,errors="coerce").median())
            for w in ("historical7d","recent24h")
        },
        "decision":"Representation-only. Do not select an admission/signal rule from known outcomes.",
    }
    (a.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
