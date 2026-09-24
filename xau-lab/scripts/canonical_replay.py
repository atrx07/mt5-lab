import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

SCHEMA_VERSION = "xau-canonical-replay-v1"
DATASET_SHA256 = "007e7ab10cc16519b544003dbe81521f46cf868bf267780932638d1e8cec86e5"
FULL_RAW_ROWS = 2_337_474
RESEARCH_ROWS = 1_869_979
BOUND_RAW = [0, 934_989, 1_168_737, 1_402_484, 1_636_231, 1_869_979]
OPPORTUNITY_CEILING_INR = 7_482.60
START_BALANCE_INR = 500.0
INR_PER_USD = 95.7021

DEFAULT_GOLDEN = Path(__file__).resolve().parents[1] / "results" / "regression" / "canonical_v4_4_reference.json"

FEATURE_NAMES = [
    "t","bid","ask","mid","spread","ss","imb10","qacc",
    "m10","m30","m60","m120","m300","m1800","range60","range300","er60",
    "min_m10_30","max_m10_30","min_m60_300","max_m60_300","ch_high120","ch_low120",
]


def sha256_file(path: Path, chunk_size=8 * 1024 * 1024):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def verify_dataset(path: Path):
    digest = sha256_file(path)
    if digest != DATASET_SHA256:
        raise RuntimeError(f"dataset sha mismatch: {digest} != {DATASET_SHA256}")
    return digest


def build_features(path: Path, interval: str):
    raw = pd.read_csv(path, nrows=RESEARCH_ROWS, usecols=["timestamp_utc", "bid", "ask"])
    raw["t"] = pd.to_datetime(raw.timestamp_utc, utc=True, format="mixed")
    raw = raw.sort_values("t", kind="stable").reset_index(drop=True)
    raw["mid"] = (raw.bid + raw.ask) / 2.0

    gap = raw.t.diff().dt.total_seconds().fillna(0)
    raw["session"] = (gap > 5.0).cumsum().astype("int32")
    md = raw.mid.diff()
    md[raw.session.diff().fillna(1) != 0] = 0
    raw["up"] = (md > 0).astype("int8")
    raw["down"] = (md < 0).astype("int8")

    bounds = []
    for b in BOUND_RAW:
        if b >= len(raw):
            bounds.append(raw.t.iloc[-1].value / 1e9 + 1e-6)
        else:
            bounds.append(raw.t.iloc[b].value / 1e9)

    # Canonical sampling: floor raw event timestamps to interval, keep the LAST quote in each
    # (raw continuity session, interval bucket). Empty buckets are not synthesized.
    raw["bin"] = raw.t.dt.floor(interval)
    agg = (
        raw.groupby(["session", "bin"], sort=False)
        .agg(
            t=("t", "last"), bid=("bid", "last"), ask=("ask", "last"), mid=("mid", "last"),
            raw_count=("mid", "size"), up=("up", "sum"), down=("down", "sum"),
        )
        .reset_index()
    )
    agg["spread"] = agg.ask - agg.bid

    pieces = []
    for _, z in agg.groupby("session", sort=False):
        z = z.copy().set_index("t", drop=False)
        c10 = z.raw_count.rolling("10s").sum()
        c30 = z.raw_count.rolling("30s").sum()
        u10 = z.up.rolling("10s").sum()
        d10 = z.down.rolling("10s").sum()
        den = u10 + d10
        z["imb10"] = ((u10 - d10) / den.replace(0, np.nan)).fillna(0.0)
        z["qacc"] = (3.0 * c10 / c30.replace(0, np.nan)).fillna(0.0)
        pieces.append(z.reset_index(drop=True))
    df = pd.concat(pieces, ignore_index=True)

    # Any sampled gap >5s resets ALL time-dependent state/features.
    df["ss"] = (df.t.diff().dt.total_seconds().fillna(0) > 5.0).cumsum().astype("int32")
    for h in [10, 30, 60, 120, 300, 1800]:
        df[f"m{h}"] = np.nan
    for col in [
        "range60","range300","er60","min_m10_30","max_m10_30",
        "min_m60_300","max_m60_300","ch_high120","ch_low120",
    ]:
        df[col] = np.nan

    for _, ids in df.groupby("ss", sort=False).groups.items():
        ii = np.asarray(list(ids), dtype=np.int64)
        z = df.loc[ii]
        ts = z.t.astype("int64").to_numpy() / 1e9
        mids = z.mid.to_numpy()

        for h in [10, 30, 60, 120, 300, 1800]:
            j = np.searchsorted(ts, ts - h, side="right") - 1
            vals = np.full(len(ii), np.nan)
            valid = np.where(j >= 0)[0]
            jj = j[valid]
            age = ts[valid] - ts[jj]
            ok = age <= h + 5.0
            kk = valid[ok]
            vals[kk] = mids[kk] - mids[j[kk]]
            df.loc[ii, f"m{h}"] = vals

        zz = z.set_index("t")
        df.loc[ii, "range60"] = (zz.mid.rolling("60s").max() - zz.mid.rolling("60s").min()).to_numpy()
        df.loc[ii, "range300"] = (zz.mid.rolling("300s").max() - zz.mid.rolling("300s").min()).to_numpy()
        path = zz.mid.diff().abs().rolling("60s").sum().to_numpy()
        m60 = df.loc[ii, "m60"].to_numpy()
        df.loc[ii, "er60"] = np.divide(np.abs(m60), path, out=np.full(len(ii), np.nan), where=path > 0)

        m10s = pd.Series(df.loc[ii, "m10"].to_numpy(), index=zz.index)
        m60s = pd.Series(df.loc[ii, "m60"].to_numpy(), index=zz.index)
        df.loc[ii, "min_m10_30"] = m10s.rolling("30s").min().to_numpy()
        df.loc[ii, "max_m10_30"] = m10s.rolling("30s").max().to_numpy()
        df.loc[ii, "min_m60_300"] = m60s.rolling("300s").min().to_numpy()
        df.loc[ii, "max_m60_300"] = m60s.rolling("300s").max().to_numpy()
        df.loc[ii, "ch_high120"] = zz.mid.rolling("120s").max().shift(1).to_numpy()
        df.loc[ii, "ch_low120"] = zz.mid.rolling("120s").min().shift(1).to_numpy()

    arrays = {
        c: (df[c].astype("int64").to_numpy() / 1e9 if c == "t" else df[c].to_numpy())
        for c in FEATURE_NAMES
    }
    return arrays, bounds


@njit(cache=True)
def simulate(
    t,bid,ask,mid,spread,ss,imb,qacc,m10,m30,m60,m120,m300,m1800,
    r60,r300,er60,min10,max10,min60,max60,chh,chl,start,end,burst_cfg
):
    # burst_cfg = enabled,cooldown,m10,m30,m60,er,qacc,imb,r60,maxspratio,abs_spread,tp,maxhold,stagsec,stagpeak,trailtrig,trailgb
    bal=500.; lp=-1e30; ls=-1e30; lm=-1e30; lb=-1e30
    pos=0; side=0; entry=0.; oz=0.; ptime=0.; peak=0.; partial=0.; partial_done=0; highopen=0
    prevss=-1; cont=0.; gp=0.; gl=0.; ntr=0; win=0; peakbal=500.; maxdd=0.

    for i in range(start,end):
        ts=t[i]
        if ss[i] != prevss:
            cont=ts; prevss=ss[i]

        if pos != 0:
            move=(bid[i]-entry) if side==1 else (entry-ask[i])
            held=ts-ptime
            if move>peak: peak=move

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
            if reason==0 and pos==4 and not math.isnan(m30[i]):
                if side==1 and m30[i]<=0: reason=5
                elif side==-1 and m30[i]>=0: reason=5
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
            pos=chosen; side=sside; ptime=ts; peak=0.; partial=0.; partial_done=0; highopen=1 if high else 0

    pf=gp/gl if gl>0 else 999.
    return bal-500.,pf,ntr,win,maxdd


def burst_config(strategy: str):
    if strategy == "v4_4":
        return np.array([0,999,99,99,99,99,99,99,99,0.01,0.01,8,300,45,0.75,4,2],dtype=np.float64)
    if strategy == "v4_5_b":
        # Candidate B, canonicalized with its documented absolute $0.28 spread cap.
        return np.array([1,60,0.6,1.5,2.0,0.12,1.20,0.20,4.0,0.18,0.28,12.0,120.0,60.0,0.80,5.5,2.0],dtype=np.float64)
    raise ValueError(strategy)


def run_strategy(arrays, bounds, strategy):
    inds=[
        (np.searchsorted(arrays["t"],bounds[i],"left"),np.searchsorted(arrays["t"],bounds[i+1],"left"))
        for i in range(5)
    ]
    args=[arrays[x] for x in FEATURE_NAMES]
    cfg=burst_config(strategy)
    simulate(*args,*inds[0],cfg)  # numba compile
    seg=[]
    for a,z in inds:
        r=simulate(*args,a,z,cfg)
        seg.append({"pnl_inr":float(r[0]),"profit_factor":float(r[1]),"trades":int(r[2]),"wins":int(r[3]),"max_drawdown_inr":float(r[4])})
    f=1.0
    for r in seg:
        f*=1.0+r["pnl_inr"]/START_BALANCE_INR
    compounded=START_BALANCE_INR*f-START_BALANCE_INR
    return {
        "strategy":strategy,
        "segments":seg,
        "compounded_pnl_inr":compounded,
        "capture_ratio":compounded/OPPORTUNITY_CEILING_INR,
        "trades_sum":sum(r["trades"] for r in seg),
        "wins_sum":sum(r["wins"] for r in seg),
        "median_segment_pf":float(np.median([r["profit_factor"] for r in seg])),
        "max_segment_drawdown_inr":max(r["max_drawdown_inr"] for r in seg),
    }


def assert_baseline(baseline, interval, golden_path: Path):
    golden=json.loads(golden_path.read_text(encoding="utf-8"))
    expected=golden["intervals"][interval]
    checks={
        "compounded_pnl_inr": (baseline["compounded_pnl_inr"], expected["compounded_pnl_inr"], 1e-6),
        "capture_ratio": (baseline["capture_ratio"], expected["capture_ratio"], 1e-12),
        "trades_sum": (baseline["trades_sum"], expected["trades_sum"], 0),
        "wins_sum": (baseline["wins_sum"], expected["wins_sum"], 0),
        "median_segment_pf": (baseline["median_segment_pf"], expected["median_segment_pf"], 1e-12),
        "max_segment_drawdown_inr": (baseline["max_segment_drawdown_inr"], expected["max_segment_drawdown_inr"], 1e-6),
    }
    failures=[]
    for name,(actual,exp,tol) in checks.items():
        if abs(actual-exp)>tol:
            failures.append(f"{name}: actual={actual} expected={exp} tol={tol}")
    if failures:
        raise RuntimeError("CANONICAL BASELINE DRIFT\n"+"\n".join(failures))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("csv",type=Path)
    ap.add_argument("--interval",choices=["500ms","1s"],required=True)
    ap.add_argument("--strategy",choices=["v4_4","v4_5_b"],default="v4_4")
    ap.add_argument("--compare",action="store_true",help="also run canonical V4.4 in same feature build")
    ap.add_argument("--output",type=Path)
    ap.add_argument("--skip-sha",action="store_true")
    ap.add_argument("--golden",type=Path,default=DEFAULT_GOLDEN)
    ap.add_argument("--no-baseline-assert",action="store_true",help="diagnostic escape hatch only")
    args=ap.parse_args()

    digest="SKIPPED" if args.skip_sha else verify_dataset(args.csv)
    arrays,bounds=build_features(args.csv,args.interval)
    baseline=run_strategy(arrays,bounds,"v4_4")
    if not args.no_baseline_assert:
        assert_baseline(baseline,args.interval,args.golden)

    payload={
        "schema_version":SCHEMA_VERSION,
        "dataset_sha256":digest,
        "research_rows":RESEARCH_ROWS,
        "raw_boundaries":BOUND_RAW,
        "interval":args.interval,
        "feature_rows":len(arrays["t"]),
        "baseline_asserted":not args.no_baseline_assert,
        "strategy":baseline if args.strategy=="v4_4" else run_strategy(arrays,bounds,args.strategy),
    }
    if args.strategy!="v4_4":
        payload["baseline_v4_4"]=baseline
        b=baseline; c=payload["strategy"]
        payload["delta_vs_v4_4"]={
            "pnl_inr":c["compounded_pnl_inr"]-b["compounded_pnl_inr"],
            "capture_points":c["capture_ratio"]-b["capture_ratio"],
            "trades":c["trades_sum"]-b["trades_sum"],
            "median_pf":c["median_segment_pf"]-b["median_segment_pf"],
            "max_segment_dd_inr":c["max_segment_drawdown_inr"]-b["max_segment_drawdown_inr"],
        }
    text=json.dumps(payload,indent=2)
    if args.output:
        args.output.write_text(text+"\n",encoding="utf-8")
    print(text)

if __name__=="__main__":
    main()
