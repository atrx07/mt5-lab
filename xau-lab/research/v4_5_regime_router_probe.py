from pathlib import Path
import math, sys, json
import numpy as np, pandas as pd
from numba import njit
sys.path.insert(0, str(Path(__file__).resolve().parent))
import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy

@njit(cache=True)
def simulate_router(t,bid,ask,mid,spread,ss,imb,qacc,m10,m30,m60,m120,m300,m1800,r60,r300,er60,min10,max10,min60,max60,chh,chl,reg_vol,reg_spread,reg_eff,reg_act,start,end,burst_cfg,gates):
    bal=500.; lp=-1e30; ls=-1e30; lm=-1e30; lb=-1e30
    pos=0; side=0; entry=0.; oz=0.; ptime=0.; peak=0.; partial=0.; partial_done=0; highopen=0
    prevss=-1; cont=0.; gp=0.; gl=0.; ntr=0; win=0; peakbal=500.; maxdd=0.; failure_since=-1e30
    for i in range(start,end):
        ts=t[i]
        if ss[i]!=prevss: cont=ts; prevss=ss[i]
        if pos!=0:
            move=(bid[i]-entry) if side==1 else (entry-ask[i]); held=ts-ptime
            if move>peak: peak=move
            if pos==3 and partial_done==0 and move>=5.5:
                closeoz=oz*.75; part=move*closeoz*canonical.INR_PER_USD; bal+=part; partial+=part; oz-=closeoz; partial_done=1
            reason=0; rev=1; trig=-1.; gb=0.; tp=12.; maxhold=900.
            if pos==3: tp=10.; maxhold=900.; trig=4.; gb=2.; rev=1
            elif pos==4: tp=burst_cfg[11]; maxhold=burst_cfg[12]; trig=burst_cfg[15]; gb=burst_cfg[16]; rev=0
            elif pos==1 and highopen==1: tp=25.; maxhold=900.; rev=0
            elif pos==2 and highopen==1: tp=8.; maxhold=1200.; rev=0; trig=12.; gb=3.
            elif pos==1: tp=21.; maxhold=1800.; rev=1
            if move<=-4.: reason=1
            elif move>=tp: reason=2
            if reason==0 and trig>0 and peak>=trig and move<=peak-gb: reason=3
            if reason==0 and pos==3 and held>=45. and peak<.75: reason=4
            if reason==0 and pos==4 and held>=burst_cfg[13] and peak<burst_cfg[14]: reason=4
            if pos==4 and math.isnan(m30[i]): failure_since=-1e30
            if reason==0 and pos==4 and not math.isnan(m30[i]):
                failure=(side==1 and m30[i]<=0) or (side==-1 and m30[i]>=0)
                if failure:
                    if failure_since < -1e20: failure_since=ts
                    if ts-failure_since>=1.: reason=5
                else: failure_since=-1e30
            if reason==0 and rev==1 and not math.isnan(m300[i]):
                if side==1 and m300[i]<=0: reason=5
                elif side==-1 and m300[i]>=0: reason=5
            if reason==0 and held>=maxhold: reason=7
            if reason!=0:
                pnl=move*oz*canonical.INR_PER_USD; total=pnl+partial; bal+=pnl; ntr+=1
                if total>0: gp+=total; win+=1
                elif total<0: gl-=total
                if bal>peakbal: peakbal=bal
                dd=peakbal-bal
                if dd>maxdd:maxdd=dd
                if pos==1:lp=ts
                elif pos==2:ls=ts
                elif pos==3:lm=ts
                else:lb=ts
                pos=0
            continue
        if spread[i]>.30:continue
        high=(not math.isnan(r300[i]) and not math.isnan(er60[i]) and r300[i]>=5. and er60[i]>=.03); pcool=450. if high else 900.; scool=90. if high else 450.
        chosen=0; sside=0
        if ts-cont>=1800. and ts-lp>=pcool and not(math.isnan(m60[i]) or math.isnan(m300[i]) or math.isnan(m1800[i]) or math.isnan(min60[i]) or math.isnan(max60[i])):
            sig=1 if (m1800[i]>=8 and m300[i]>=3 and min60[i]<=-.8 and m60[i]>=.5) else (-1 if (m1800[i]<=-8 and m300[i]<=-3 and max60[i]>=.8 and m60[i]<=-.5) else 0)
            if sig!=0:
                allow=1; cats=(reg_vol[i],reg_spread[i],reg_eff[i],reg_act[i])
                for d in range(4):
                    c=cats[d]
                    if c>=0 and gates[0,d,c]==0: allow=0
                if allow: chosen=1; sside=sig
        if chosen==0 and ts-ls>=scool and not(math.isnan(m30[i]) or math.isnan(chh[i]) or math.isnan(chl[i])):
            slowbuy=(not math.isnan(m300[i]) and not math.isnan(m1800[i]) and m1800[i]>=8 and m300[i]>=3); slowsell=(not math.isnan(m300[i]) and not math.isnan(m1800[i]) and m1800[i]<=-8 and m300[i]<=-3)
            if not((slowbuy or slowsell) and not high):
                rng=chh[i]-chl[i]; buf=max(.5,.02*rng)
                if rng>=4:
                    sig=1 if (mid[i]>=chh[i]+buf and m30[i]>=1.5) else (-1 if (mid[i]<=chl[i]-buf and m30[i]<=-1.5) else 0)
                    if sig!=0:
                        allow=1; cats=(reg_vol[i],reg_spread[i],reg_eff[i],reg_act[i])
                        for d in range(4):
                            c=cats[d]
                            if c>=0 and gates[1,d,c]==0:allow=0
                        if allow:chosen=2;sside=sig
        if chosen==0 and ts-lm>=60.:
            if not(math.isnan(m10[i]) or math.isnan(m60[i]) or math.isnan(m120[i]) or math.isnan(er60[i]) or math.isnan(r60[i]) or math.isnan(min10[i]) or math.isnan(max10[i])) and r60[i]>=2 and er60[i]>=.12 and qacc[i]>=.65 and spread[i]<=.25*r60[i]:
                sig=1 if (m120[i]>=6 and m60[i]>=2 and min10[i]<=-.5 and m10[i]>=.2 and imb[i]>=0) else (-1 if (m120[i]<=-6 and m60[i]<=-2 and max10[i]>=.5 and m10[i]<=-.2 and imb[i]<=0) else 0)
                if sig!=0:
                    allow=1; cats=(reg_vol[i],reg_spread[i],reg_eff[i],reg_act[i])
                    for d in range(4):
                        c=cats[d]
                        if c>=0 and gates[2,d,c]==0:allow=0
                    if allow:chosen=3;sside=sig
        if chosen==0 and burst_cfg[0]>.5 and ts-lb>=burst_cfg[1]:
            if not(math.isnan(m10[i]) or math.isnan(m30[i]) or math.isnan(m60[i]) or math.isnan(m120[i]) or math.isnan(er60[i]) or math.isnan(r60[i])) and r60[i]>=burst_cfg[8] and spread[i]<=burst_cfg[9]*r60[i] and spread[i]<=burst_cfg[10] and qacc[i]>=burst_cfg[6] and er60[i]>=burst_cfg[5]:
                sig=1 if (m10[i]>=burst_cfg[2] and m30[i]>=burst_cfg[3] and m60[i]>=burst_cfg[4] and m120[i]>0 and imb[i]>=burst_cfg[7]) else (-1 if (m10[i]<=-burst_cfg[2] and m30[i]<=-burst_cfg[3] and m60[i]<=-burst_cfg[4] and m120[i]<0 and imb[i]<=-burst_cfg[7]) else 0)
                if sig!=0:
                    allow=1; cats=(reg_vol[i],reg_spread[i],reg_eff[i],reg_act[i])
                    for d in range(4):
                        c=cats[d]
                        if c>=0 and gates[3,d,c]==0:allow=0
                    if allow:chosen=4;sside=sig
        if chosen!=0:
            entry=ask[i] if sside==1 else bid[i]; oz=min(bal*.03/(4*canonical.INR_PER_USD),(bal/canonical.INR_PER_USD*100)/entry)
            pos=chosen;side=sside;ptime=ts;peak=0.;partial=0.;partial_done=0;highopen=1 if high else 0;failure_since=-1e30
    return bal-500.,gp/gl if gl>0 else 999.,ntr,win,maxdd

def raw_support(path):
    raw=pd.read_csv(path,nrows=canonical.RESEARCH_ROWS,usecols=['timestamp_utc','bid','ask'])
    raw['t']=pd.to_datetime(raw.timestamp_utc,utc=True,format='mixed'); raw=raw.sort_values('t',kind='stable').reset_index(drop=True); raw['mid']=(raw.bid+raw.ask)/2; raw['spread']=raw.ask-raw.bid
    gap=raw.t.diff().dt.total_seconds().fillna(0); raw['session']=(gap>5).cumsum().astype('int32'); md=raw.mid.diff(); md[raw.session.diff().fillna(1)!=0]=0; raw['absdiff']=md.abs().fillna(0)
    x=raw.set_index('t'); minute=pd.DataFrame({'spread_med':x.spread.resample('1min').median(),'range1m':x.mid.resample('1min').max()-x.mid.resample('1min').min()}); minute['spread_base']=minute.spread_med.rolling(30,min_periods=10).median().shift(1); minute['range_base']=minute.range1m.rolling(30,min_periods=10).median().shift(1); q10=x.mid.resample('10s').size().to_frame('count10'); q10['activity_base']=q10.count10.rolling(180,min_periods=60).median().shift(1)
    t=raw.t.to_numpy(dtype='datetime64[ns]').astype(np.int64)/1e9; mid=raw.mid.to_numpy(); spr=raw.spread.to_numpy(); ss=raw.session.to_numpy(); idx=np.arange(len(raw),dtype=np.int64); starts=np.where(np.r_[True,ss[1:]!=ss[:-1]],idx,0); starts=np.maximum.accumulate(starts); cpath=np.cumsum(raw.absdiff.to_numpy(),dtype=np.float64)
    return raw,minute,q10,t,mid,spr,starts,cpath

def static_signal_indices(arr):
    mid,spread=arr['mid'],arr['spread']; m10,m30,m60,m120,m300,m1800=arr['m10'],arr['m30'],arr['m60'],arr['m120'],arr['m300'],arr['m1800']; r60,r300,er=arr['range60'],arr['range300'],arr['er60']; min10,max10,min60,max60=arr['min_m10_30'],arr['max_m10_30'],arr['min_m60_300'],arr['max_m60_300']; chh,chl=arr['ch_high120'],arr['ch_low120']; imb,qacc=arr['imb10'],arr['qacc']; valid=spread<=.30
    primary=valid & np.isfinite(m60)&np.isfinite(m300)&np.isfinite(m1800)&np.isfinite(min60)&np.isfinite(max60) & (((m1800>=8)&(m300>=3)&(min60<=-.8)&(m60>=.5))|((m1800<=-8)&(m300<=-3)&(max60>=.8)&(m60<=-.5)))
    high=np.isfinite(r300)&np.isfinite(er)&(r300>=5)&(er>=.03); slowbuy=np.isfinite(m300)&np.isfinite(m1800)&(m1800>=8)&(m300>=3); slowsell=np.isfinite(m300)&np.isfinite(m1800)&(m1800<=-8)&(m300<=-3); rng=chh-chl; buf=np.maximum(.5,.02*rng); secondary=valid&np.isfinite(m30)&np.isfinite(chh)&np.isfinite(chl)&(~((slowbuy|slowsell)&(~high)))&(rng>=4)&(((mid>=chh+buf)&(m30>=1.5))|((mid<=chl-buf)&(m30<=-1.5)))
    micro=valid&np.isfinite(m10)&np.isfinite(m60)&np.isfinite(m120)&np.isfinite(er)&np.isfinite(r60)&np.isfinite(min10)&np.isfinite(max10)&(r60>=2)&(er>=.12)&(qacc>=.65)&(spread<=.25*r60)&(((m120>=6)&(m60>=2)&(min10<=-.5)&(m10>=.2)&(imb>=0))|((m120<=-6)&(m60<=-2)&(max10>=.5)&(m10<=-.2)&(imb<=0)))
    burst=valid&np.isfinite(m10)&np.isfinite(m30)&np.isfinite(m60)&np.isfinite(m120)&np.isfinite(er)&np.isfinite(r60)&(r60>=4)&(spread<=.18*r60)&(spread<=.28)&(qacc>=1.2)&(er>=.12)&(((m10>=.6)&(m30>=1.5)&(m60>=2)&(m120>0)&(imb>=.2))|((m10<=-.6)&(m30<=-1.5)&(m60<=-2)&(m120<0)&(imb<=-.2)))
    return np.flatnonzero(primary|secondary|micro|burst)

def cats_for_candidates(support,arr):
    raw,minute,q10,rt,mid,spr,starts,cpath=support; n=len(arr['t']); rv=np.full(n,-1,np.int8); rs=np.full(n,-1,np.int8); re=np.full(n,-1,np.int8); ra=np.full(n,-1,np.int8); cand=static_signal_indices(arr); st=arr['t'][cand]
    j=np.searchsorted(rt,st,side='right')-1; j=np.clip(j,0,len(rt)-1); s0=starts[j]; a10=np.maximum(s0,np.searchsorted(rt,rt[j]-10,side='left')); a60=np.maximum(s0,np.searchsorted(rt,rt[j]-60,side='left')); j60=np.searchsorted(rt,rt[j]-60,side='right')-1
    ranges=np.fromiter((mid[a:b+1].max()-mid[a:b+1].min() for a,b in zip(a60,j)),dtype=float,count=len(j)); paths=cpath[j]-np.where(a60>0,cpath[a60-1],0); m60=np.where(j60>=s0,mid[j]-mid[np.maximum(j60,0)],np.nan); eff=np.divide(np.abs(m60),paths,out=np.full(len(j),np.nan),where=paths>1e-12); counts=j-a10+1
    dti=pd.to_datetime(rt[j],unit='s',utc=True); mk=dti.floor('min')-pd.Timedelta('1ns'); qk=dti.floor('10s')-pd.Timedelta('1ns'); mi=minute.index.searchsorted(mk,side='right')-1; qi=q10.index.searchsorted(qk,side='right')-1
    sb=np.full(len(j),np.nan); rb=np.full(len(j),np.nan); ab=np.full(len(j),np.nan); ok=mi>=0; sb[ok]=minute.spread_base.to_numpy()[mi[ok]]; rb[ok]=minute.range_base.to_numpy()[mi[ok]]; ok=qi>=0; ab[ok]=q10.activity_base.to_numpy()[qi[ok]]
    vr=np.divide(ranges,rb,out=np.full(len(j),np.nan),where=np.isfinite(rb)&(rb>1e-12)); sr=np.divide(spr[j],sb,out=np.full(len(j),np.nan),where=np.isfinite(sb)&(sb>1e-12)); ar=np.divide(counts,ab,out=np.full(len(j),np.nan),where=np.isfinite(ab)&(ab>1e-12))
    def enc(v,lo,hi):
        o=np.full(len(v),-1,np.int8); ok=np.isfinite(v); o[ok&(v<lo)]=0; o[ok&(v>=lo)&(v<=hi)]=1; o[ok&(v>hi)]=2; return o
    for dest,vals in zip((rv,rs,re,ra),(enc(vr,.75,1.5),enc(sr,.75,1.25),enc(eff,.10,.25),enc(ar,.75,1.5))): dest[cand]=vals
    return rv,rs,re,ra

def main(path):
    path=Path(path); canonical.verify_dataset(path); support=raw_support(path); interval_data={}; search={}; gates_all=np.ones((4,4,3),np.int8)
    for interval in ('500ms','1s'):
        arr,bounds=canonical.build_features(path,interval); base=canonical.run_strategy(arr,bounds,'v4_4'); canonical.assert_baseline(base,interval,canonical.DEFAULT_GOLDEN); regs=cats_for_candidates(support,arr); inds=autopsy.indices(arr,bounds); args=[arr[x] for x in canonical.FEATURE_NAMES]; cfg=canonical.burst_config('v4_5_b'); simulate_router(*args,*regs,*inds[0],cfg,gates_all); seed=simulate_router(*args,*regs,*inds[0],cfg,gates_all); variants=[]
        for e in range(4):
            for d in range(4):
                for cat in range(3):
                    g=gates_all.copy(); g[e,d,cat]=0; q=simulate_router(*args,*regs,*inds[0],cfg,g); variants.append({'engine':e,'dimension':d,'category':cat,'pnl_inr':float(q[0]),'trades':int(q[2]),'wins':int(q[3]),'max_drawdown_inr':float(q[4])})
        interval_data[interval]=(arr,regs,inds,args,cfg); search[interval]={'baseline':{'pnl_inr':float(seed[0]),'trades':int(seed[2]),'wins':int(seed[3]),'max_drawdown_inr':float(seed[4])},'variants':variants}
    candidates=[]
    for a in search['500ms']['variants']:
        b=next(x for x in search['1s']['variants'] if (x['engine'],x['dimension'],x['category'])==(a['engine'],a['dimension'],a['category'])); b5=search['500ms']['baseline']; b1=search['1s']['baseline']; eligible=(a['pnl_inr']>b5['pnl_inr'] and b['pnl_inr']>b1['pnl_inr'] and a['trades']>=.95*b5['trades'] and b['trades']>=.95*b1['trades'] and a['wins']/a['trades']>=b5['wins']/b5['trades'] and b['wins']/b['trades']>=b1['wins']/b1['trades'] and a['max_drawdown_inr']<=1.02*b5['max_drawdown_inr'] and b['max_drawdown_inr']<=1.02*b1['max_drawdown_inr']); candidates.append({'engine':a['engine'],'dimension':a['dimension'],'category':a['category'],'eligible':eligible,'score':min(a['pnl_inr']/b5['pnl_inr']-1,b['pnl_inr']/b1['pnl_inr']-1)})
    selected=sorted((x for x in candidates if x['eligible']),key=lambda x:x['score'],reverse=True)[0]; evaluation={}
    for interval in ('500ms','1s'):
        arr,regs,inds,args,cfg=interval_data[interval]; g=gates_all.copy(); g[selected['engine'],selected['dimension'],selected['category']]=0; base_rows=[]; cand_rows=[]
        for sid,(s,e) in enumerate(inds):
            rb=simulate_router(*args,*regs,s,e,cfg,gates_all); rc=simulate_router(*args,*regs,s,e,cfg,g); base_rows.append((rb,sid)); cand_rows.append((rc,sid))
        def sm(rows):
            f=1.; trades=0; wins=0; dds=[]
            for q,_ in rows: f*=1+q[0]/500.; trades+=q[2]; wins+=q[3]; dds.append(q[4])
            return {'compounded_pnl_inr':500*(f-1),'trades':trades,'wins':wins,'win_rate':wins/trades,'max_segment_drawdown_inr':max(dds)}
        evaluation[interval]={'baseline':sm(base_rows),'candidate':sm(cand_rows)}
    print(json.dumps({'selected':selected,'evaluation':evaluation},indent=2))

if __name__=='__main__': main(Path(sys.argv[1]))
