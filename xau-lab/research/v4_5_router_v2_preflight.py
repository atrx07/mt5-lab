"""Experiment 29: trade-ledger Router-v2 gate proxy and variable-regime bootstrap.

This is NOT a full raw-tick Router-v2 replay because simultaneous candidate
fall-through cannot be reconstructed from realized Candidate-D trade ledgers.
"""
from __future__ import annotations
import csv, json, math, random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"results"/"simulations"/"2026-09-25-v4_5-router-v2-preflight"
INR_PER_USD=95.7021

COMPONENTS={
 "PRIMARY":["dir_m300_rel","dir_m60_rel","flow_align60","pullback60_edge","short_long_balance_stability","market_heat_penalty","execution_heat_penalty"],
 "SECONDARY":["dir_m30_rel","dir_m60_rel","flow_align10","accel_10_60","pullback60_edge","range_expansion","execution_heat_penalty"],
 "MICRO":["dir_m10_rel","dir_m60_rel","flow_align10","flow_align60","accel_10_60","pullback60_edge","execution_heat_penalty"],
 "BURST":["dir_m10_rel","dir_m30_rel","flow_align10","accel_10_60","activity_expansion","range_expansion","execution_heat_penalty"],
}
def f(x):
    try:return float(x)
    except:return float("nan")
def squash(x,s=3.0): return math.tanh(x/s) if math.isfinite(x) else 0.0
def pos(x): return squash(max(0.0,x if math.isfinite(x) else 0.0))
def expansion(x): return math.tanh(x-1.0) if math.isfinite(x) else 0.0
def penalty(x): return -math.tanh(max(0.0,x-1.0)) if math.isfinite(x) else 0.0
def edge(x):
    if not math.isfinite(x): return 0.0
    x=min(1.0,max(0.0,x)); return 1.0-2.0*x
def score(r):
    x={k:f(r.get(k,"")) for k in ["dir_m10_rel","dir_m30_rel","dir_m60_rel","dir_m300_rel","flow_align10","flow_align60","accel_10_60","pullback60","range60_rel","activity_rel","market_heat","execution_heat","short_long_balance"]}
    c={"dir_m10_rel":pos(x["dir_m10_rel"]),"dir_m30_rel":pos(x["dir_m30_rel"]),"dir_m60_rel":pos(x["dir_m60_rel"]),"dir_m300_rel":pos(x["dir_m300_rel"]),"flow_align10":max(-1,min(1,x["flow_align10"] if math.isfinite(x["flow_align10"]) else 0)),"flow_align60":max(-1,min(1,x["flow_align60"] if math.isfinite(x["flow_align60"]) else 0)),"accel_10_60":squash(x["accel_10_60"]),"pullback60_edge":edge(x["pullback60"]),"range_expansion":expansion(x["range60_rel"]),"activity_expansion":expansion(x["activity_rel"]),"market_heat_penalty":penalty(x["market_heat"]),"execution_heat_penalty":penalty(x["execution_heat"]),"short_long_balance_stability":-abs(squash(x["short_long_balance"]))}
    q=COMPONENTS[r["engine"]]; return sum(c[k] for k in q)/len(q)
def read(path):
    with path.open(newline="",encoding="utf-8") as h:return list(csv.DictReader(h))
def trade_return(r):
    oz=f(r["entry_oz"]); bal=oz*4*INR_PER_USD/0.03
    return f(r["pnl_inr"])/bal if bal>0 else 0.0
def quantile(a,p):
    a=sorted(a); z=(len(a)-1)*p; lo=int(math.floor(z)); hi=int(math.ceil(z))
    return a[lo] if lo==hi else a[lo]*(hi-z)+a[hi]*(z-lo)
def bootstrap(hist,recent,interval,n=10000,k=40,seed=0x5A17C0DE):
    rng=random.Random(seed+(0 if interval=="500ms" else 1)); hp=[x for x in hist if x["interval"]==interval]; rp=[x for x in recent if x["interval"]==interval]
    base=[]; proxy=[]; retention=[]
    for _ in range(n):
        share=rng.random(); b=500.; q=500.; kept=0
        for __ in range(k):
            pool=rp if rng.random()<share else hp; r=rng.choice(pool); rr=trade_return(r); b*=1+rr
            if score(r)>=0: q*=1+rr; kept+=1
        base.append(b-500); proxy.append(q-500); retention.append(kept/k)
    return {"candidate_median":quantile(base,.5),"proxy_median":quantile(proxy,.5),"candidate_profitable_share":sum(x>0 for x in base)/n,"proxy_profitable_share":sum(x>0 for x in proxy)/n,"proxy_median_retention":quantile(retention,.5)}
def main():
    hist=read(OUT/"historical_state_v2_trades.csv"); recent=read(OUT/"recent_state_v2_trades.csv")
    result={i:bootstrap(hist,recent,i) for i in ("500ms","1s")}
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
