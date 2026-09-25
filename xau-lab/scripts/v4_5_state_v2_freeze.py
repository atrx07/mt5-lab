"""Experiment 27: freeze the xau-state-v2 causal continuous state representation.

No strategy rule or router threshold is selected by this script.
"""
from __future__ import annotations

import argparse, csv, json
from pathlib import Path
import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_regime_normalization as regime
import v4_5_regime_portability as portability

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results"/"simulations"/"2026-09-25-v4_5-state-v2-freeze"

FEATURES=[
    "range60_rel","spread_rel","activity_rel","er60","spread_to_range",
    "dir_m10_rel","dir_m30_rel","dir_m60_rel","dir_m300_rel",
    "dir_eff60","flow_align10","flow_align60","accel_10_60","accel_30_300",
    "short_long_balance","pullback60","pullback300","market_heat",
    "execution_heat","session_age_sec",
]

def safe_ratio(a,b):
    return float(a/b) if np.isfinite(a) and np.isfinite(b) and abs(b)>1e-12 else np.nan

def before(series,ts):
    i=series.index.searchsorted(ts,side="right")-1
    if i<0 or not np.isfinite(series.iloc[i]): return np.nan
    return float(series.iloc[i])

def load_raw(path):
    df=pd.read_csv(path,nrows=canonical.RESEARCH_ROWS,usecols=["timestamp_utc","bid","ask"])
    df["t"]=pd.to_datetime(df.timestamp_utc,utc=True,format="mixed")
    df=df.sort_values("t",kind="stable").reset_index(drop=True)
    df["mid"]=(df.bid+df.ask)/2.0; df["spread"]=df.ask-df.bid
    gap=df.t.diff().dt.total_seconds().fillna(0); df["session"]=(gap>5).cumsum().astype("int32")
    move=df.mid.diff(); move[df.session.diff().fillna(1)!=0]=0
    df["up"]=(move>0).astype(np.int8); df["down"]=(move<0).astype(np.int8); df["absdiff"]=move.abs().fillna(0.0)
    return df

def baselines(df):
    x=df.set_index("t")
    ten=pd.DataFrame({"last":x.mid.resample("10s").last(),"count":x.mid.resample("10s").size()})
    ten["absret"]=ten["last"].diff().abs()
    ten["m_base"]=ten.absret.rolling(180,min_periods=60).median().shift(1)
    ten["activity_base"]=ten["count"].rolling(180,min_periods=60).median().shift(1)
    thirty=x.mid.resample("30s").last().to_frame("last")
    thirty["absret"]=thirty["last"].diff().abs()
    thirty["m_base"]=thirty.absret.rolling(60,min_periods=20).median().shift(1)
    minute=pd.DataFrame({"last":x.mid.resample("1min").last(),"spread_med":x.spread.resample("1min").median(),"range":x.mid.resample("1min").max()-x.mid.resample("1min").min()})
    minute["absret"]=minute["last"].diff().abs()
    minute["m_base"]=minute.absret.rolling(30,min_periods=10).median().shift(1)
    minute["spread_base"]=minute.spread_med.rolling(30,min_periods=10).median().shift(1)
    minute["range_base"]=minute["range"].rolling(30,min_periods=10).median().shift(1)
    five=x.mid.resample("5min").last().to_frame("last")
    five["absret"]=five["last"].diff().abs()
    five["m_base"]=five.absret.rolling(24,min_periods=8).median().shift(1)
    return ten,thirty,minute,five

def overlay(path,rows,window):
    df=load_raw(path); ten,thirty,minute,five=baselines(df)
    t=df.t.to_numpy(dtype="datetime64[ns]").astype(np.int64)/1e9
    mid=df.mid.to_numpy(); spr=df.spread.to_numpy(); ss=df.session.to_numpy()
    up=df.up.to_numpy(); dn=df.down.to_numpy(); ad=df.absdiff.to_numpy()
    idx=np.arange(len(df),dtype=np.int64)
    starts=np.where(np.r_[True,ss[1:]!=ss[:-1]],idx,0); starts=np.maximum.accumulate(starts)
    cup=np.cumsum(up,dtype=np.int64); cdn=np.cumsum(dn,dtype=np.int64); cpath=np.cumsum(ad,dtype=np.float64)
    def csum(c,a,b): return c[b]-(c[a-1] if a else 0)
    out=[]
    for r in rows:
        ts=float(r["entry_ts"]); i=int(np.searchsorted(t,ts,side="right")-1)
        if i<0: continue
        s0=int(starts[i]); side=int(r.get("side_sign",1 if r["side"]=="BUY" else -1))
        def ai(sec): return max(s0,int(np.searchsorted(t,t[i]-sec,side="left")))
        def ji(sec): return int(np.searchsorted(t,t[i]-sec,side="right")-1)
        a10,a60,a300=ai(10),ai(60),ai(300); j10,j30,j60,j300=ji(10),ji(30),ji(60),ji(300)
        def mom(j): return mid[i]-mid[j] if j>=s0 else np.nan
        m10,m30,m60,m300=map(mom,(j10,j30,j60,j300))
        lo60,hi60=float(np.min(mid[a60:i+1])),float(np.max(mid[a60:i+1])); range60=hi60-lo60
        lo300,hi300=float(np.min(mid[a300:i+1])),float(np.max(mid[a300:i+1])); range300=hi300-lo300
        path60=csum(cpath,a60,i)
        u10,d10=csum(cup,a10,i),csum(cdn,a10,i); flow10=(u10-d10)/(u10+d10) if u10+d10 else 0.0
        u60,d60=csum(cup,a60,i),csum(cdn,a60,i); flow60=(u60-d60)/(u60+d60) if u60+d60 else 0.0
        count10=i-a10+1
        dt=pd.Timestamp(t[i],unit="s",tz="UTC")
        k10=dt.floor("10s")-pd.Timedelta("1ns"); k30=dt.floor("30s")-pd.Timedelta("1ns")
        k60=dt.floor("min")-pd.Timedelta("1ns"); k300=dt.floor("5min")-pd.Timedelta("1ns")
        d10r=safe_ratio(side*m10,before(ten.m_base,k10)); d30r=safe_ratio(side*m30,before(thirty.m_base,k30))
        d60r=safe_ratio(side*m60,before(minute.m_base,k60)); d300r=safe_ratio(side*m300,before(five.m_base,k300))
        rr=safe_ratio(range60,before(minute.range_base,k60)); sr=safe_ratio(spr[i],before(minute.spread_base,k60)); ar=safe_ratio(count10,before(ten.activity_base,k10))
        er=abs(m60)/path60 if np.isfinite(m60) and path60>1e-12 else np.nan
        pb60=((hi60-mid[i]) if side==1 else (mid[i]-lo60))/range60 if range60>1e-12 else np.nan
        pb300=((hi300-mid[i]) if side==1 else (mid[i]-lo300))/range300 if range300>1e-12 else np.nan
        z=dict(r); z["window"]=window
        z.update({
            "range60_rel":rr,"spread_rel":sr,"activity_rel":ar,"er60":er,"spread_to_range":safe_ratio(spr[i],range60),
            "dir_m10_rel":d10r,"dir_m30_rel":d30r,"dir_m60_rel":d60r,"dir_m300_rel":d300r,
            "dir_eff60":side*m60/path60 if np.isfinite(m60) and path60>1e-12 else np.nan,
            "flow_align10":side*flow10,"flow_align60":side*flow60,
            "accel_10_60":d10r-d60r if np.isfinite(d10r) and np.isfinite(d60r) else np.nan,
            "accel_30_300":d30r-d300r if np.isfinite(d30r) and np.isfinite(d300r) else np.nan,
            "short_long_balance":0.5*(d10r+d30r-d60r-d300r) if all(np.isfinite(x) for x in (d10r,d30r,d60r,d300r)) else np.nan,
            "pullback60":pb60,"pullback300":pb300,
            "market_heat":rr*ar if np.isfinite(rr) and np.isfinite(ar) else np.nan,
            "execution_heat":sr*ar if np.isfinite(sr) and np.isfinite(ar) else np.nan,
            "session_age_sec":float(t[i]-t[s0]),
        })
        out.append(z)
    return out

def match_pairs(rows):
    a=[r for r in rows if r["interval"]=="500ms"]; b=[r for r in rows if r["interval"]=="1s"]; used=set(); out=[]
    for x in sorted(a,key=lambda r:r["entry_ts"]):
        opts=[]
        for j,y in enumerate(b):
            if j in used or y["segment_id"]!=x["segment_id"] or y["engine"]!=x["engine"] or y["side"]!=x["side"]: continue
            d=abs(y["entry_ts"]-x["entry_ts"])
            if d<=120: opts.append((d,j,y))
        if not opts: continue
        _,j,y=min(opts,key=lambda q:q[0]); used.add(j)
        out.append((x,y))
    return out

def spearman(a,b):
    x=pd.DataFrame({"a":a,"b":b}).replace([np.inf,-np.inf],np.nan).dropna()
    return float(x.a.rank().corr(x.b.rank())) if len(x)>=3 else np.nan

def write_csv(path,rows):
    if not rows: return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("canonical_csv",type=Path); ap.add_argument("recent_csv_or_gz",type=Path)
    ap.add_argument("--output",type=Path,default=OUT); a=ap.parse_args()
    canonical.verify_dataset(a.canonical_csv); portability.verify_recent(a.recent_csv_or_gz)
    historical=[]; recent=[]
    for interval in ("500ms","1s"):
        _,rows=regime.candidate_d_rows(a.canonical_csv,interval); historical.extend(rows)
        recent.extend(portability.recent_candidate_rows(a.recent_csv_or_gz,interval))
    historical=overlay(a.canonical_csv,historical,"historical7d")
    recent=overlay(a.recent_csv_or_gz,recent,"recent24h")
    all_rows=historical+recent
    a.output.mkdir(parents=True,exist_ok=True)

    dist=[]
    for window in ("historical7d","recent24h"):
        g=pd.DataFrame([r for r in all_rows if r["window"]==window])
        for feat in FEATURES:
            s=pd.to_numeric(g[feat],errors="coerce").replace([np.inf,-np.inf],np.nan)
            dist.append({"window":window,"feature":feat,"trades":len(g),"finite":int(s.notna().sum()),"coverage":float(s.notna().mean()),"median":float(s.median()),"q25":float(s.quantile(.25)),"q75":float(s.quantile(.75))})
    write_csv(a.output/"feature_distribution.csv",dist)

    stability=[]
    for window,rows in (("historical7d",historical),("recent24h",recent)):
        pairs=match_pairs(rows)
        for feat in FEATURES:
            aa=[x[feat] for x,y in pairs]; bb=[y[feat] for x,y in pairs]
            good=[(x,y) for x,y in zip(aa,bb) if np.isfinite(x) and np.isfinite(y)]
            va=[x for x,y in good]; vb=[y for x,y in good]
            stability.append({"window":window,"feature":feat,"pairs":len(good),"spearman":spearman(va,vb),"median_abs_diff":float(np.median(np.abs(np.asarray(va)-np.asarray(vb)))) if good else np.nan})
    write_csv(a.output/"cross_grid_feature_stability.csv",stability)

    primary=[]
    df=pd.DataFrame(all_rows)
    for (window,interval,reason),g in df[df.engine=="PRIMARY"].groupby(["window","interval","exit_reason"]):
        row={"window":window,"interval":interval,"exit_reason":reason,"trades":len(g),"wins":int((g.pnl_inr>0).sum()),"pnl_inr":float(g.pnl_inr.sum())}
        for feat in FEATURES: row[feat]=float(pd.to_numeric(g[feat],errors="coerce").median())
        primary.append(row)
    write_csv(a.output/"primary_outcome_profiles.csv",primary)

    catalog={"schema_version":"xau-state-v2","selection_policy":"feature formulas frozen structurally; no feature threshold or router selected from outcome P&L","features":FEATURES,"known_data_policy":"known seven-day/recent windows are descriptive benchmarks; next promotion evidence requires a new non-overlapping snapshot","router_v2_trade_retention_floor":0.95}
    (a.output/"state_v2_catalog.json").write_text(json.dumps(catalog,indent=2)+"\n",encoding="utf-8")
    summary={"schema_version":"xau-state-v2","historical_trades":len(historical),"recent_trades":len(recent),"historical_cross_grid_pairs":len(match_pairs(historical)),"recent_cross_grid_pairs":len(match_pairs(recent)),"strategy_changed":False,"router_selected":False,"holdout_opened":False,"decision":"Freeze formulas only; validate unchanged on a new non-overlapping snapshot before Router v2 promotion."}
    (a.output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__=="__main__": main()
