"""Experiment 56: frozen Candidate O acceptance-thesis invalidation evaluation.

Candidate-O rules were frozen before this P&L run. Known data may reject O but cannot
promote it. The canonical final20 remains sealed.
"""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_candidate_m_pullback_acceptance as mbase
import v4_5_candidate_m_all_dataset_comparison as mcmp
import v4_5_candidate_o_acceptance_invalidation as obase
import v4_5_microstate_v1_freeze as microstate
import v4_5_router_v2_full_eval as full_eval
from v4_5_candidate_j_stage1_staged_validation import build_features_all_rows, inspect_block, make_combined_csv

ROOT=Path(__file__).resolve().parents[1]
HISTORICAL=ROOT/"xau_ticks_7d.csv"
RECENT=ROOT/"data"/"raw"/"xau_ticks_recent_24h_2026-09-24.csv.gz"
RECENT_MANIFEST=ROOT/"data"/"manifests"/"xau_ticks_recent_24h_2026-09-24.json"
CURRENT=ROOT/"data"/"raw"/"xau_ticks_7d_current_2026-10-06.csv.gz"
CURRENT_MANIFEST=ROOT/"data"/"manifests"/"xau_ticks_7d_2026-09-29_to_2026-10-06.json"
BLOCK_ROOT=ROOT/"data"/"prospective_restored"
OUT=ROOT/"results"/"simulations"/"2026-10-06-v4_5-candidate-o-acceptance-invalidation"
STRESS=(0.0,0.10)
RANDOM_SEEDS=(56011,56012,56013)
RANDOM_WINDOWS_PER_SEED=80
RANDOM_HOURS=4.0

EXPECTED={
"500ms":{"hist0":{"D":1430.311133793068,"H":1287.0890835318237,"M":-0.8733954326883842},"hist1":{"D":964.1613580745292,"H":875.1940743033928,"M":-42.51691082438275},"recent0":{"D":-223.27329174700338,"H":-208.4689762103303,"M":-28.65500915562137},"recent1":{"D":-232.58559413921654,"H":-219.15014645031755,"M":-36.07530713154273},"current0":{"D":-216.15801063833612,"H":-180.9269930375778,"M":-78.32761782314861},"current1":{"D":-232.30827508692408,"H":-198.58949002816848,"M":-115.28254284305058},"blocks":{"D":-165.31701569566403,"H":-97.90961515037145,"M":-95.11515192731815}},
"1s":{"hist0":{"D":385.2544619534224,"H":360.79357527974355,"M":59.60203209571713},"hist1":{"D":248.12032921993654,"H":240.97302084265993,"M":15.460567659327795},"recent0":{"D":-135.9095261798986,"H":-128.62645713776266,"M":-30.8186007688098},"recent1":{"D":-143.91095503479,"H":-138.60265758541567,"M":-39.29244526934701},"current0":{"D":-229.1744592962699,"H":-194.96479018295344,"M":-67.11594127568526},"current1":{"D":-284.6695952020659,"H":-257.8931486832781,"M":-112.26281891985792},"blocks":{"D":-130.26711793884755,"H":-74.45786116462,"M":-70.46879111404903}}}


def close(a:float,b:float,label:str,tol:float=.03)->None:
    if abs(float(a)-float(b))>tol: raise RuntimeError(f"{label} parity drift: {a} != {b}")


def write_csv(path:Path,rows:List[Dict])->None:
    if not rows: path.write_text("",encoding="utf-8"); return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


def norm_cont(label:str,x:Dict)->Dict:
    return {"candidate":label,"pnl_inr":float(x["terminal_equity_pnl_inr"]),"realized_pnl_inr":float(x["pnl_inr"]),"terminal_unrealized_inr":float(x.get("terminal_unrealized_inr",0.0)),"trades":int(x["trades"]),"wins":int(x["wins"]),"win_rate":float(x["win_rate"]),"profit_factor":float(x["profit_factor"]),"max_drawdown_inr":float(x["max_drawdown_inr"]),"open_position_at_end":bool(x.get("open_position_at_end",False)),**({k:int(x[k]) for k in ("thesis_invalidation_exits","thesis_timer_resets","entries") if k in x})}


def norm_hist(label:str,x:Dict)->Dict:
    return {"candidate":label,"pnl_inr":float(x["compounded_pnl_inr"]),"trades":int(x["trades"]),"wins":int(x["wins"]),"win_rate":float(x["win_rate"]),"profit_factor":None,"max_drawdown_inr":float(x["max_segment_drawdown_inr"]),"pnl_semantics":"five-segment reset/compound first80",**({k:int(x[k]) for k in ("thesis_invalidation_exits","thesis_timer_resets","entries") if k in x})}


def run_set(arr:Dict[str,np.ndarray],ranges:List[Tuple[int,int]],raw:Dict[str,np.ndarray],slip:float,historical:bool,capture_o:bool=False,ctx:str="")->Dict[str,Dict]:
    cache={}; dseg=[]; hseg=[]; mseg=[]; oseg=[]
    for sid,(s,e) in enumerate(ranges):
        dseg.append(hbase.simulate(arr,s,e,candidate_h=False,extra_slippage_usd_per_side=slip))
        hseg.append(hbase.simulate(arr,s,e,candidate_h=True,raw=raw,feature_cache=cache,extra_slippage_usd_per_side=slip))
        mseg.append(mbase.simulate_m(arr,s,e,raw=raw,cache=cache,extra_slippage_usd_per_side=slip))
        oseg.append(obase.simulate_o(arr,s,e,raw=raw,cache=cache,extra_slippage_usd_per_side=slip,capture_trades=capture_o,context=f"{ctx}:seg{sid}"))
    if historical:
        return {"D":norm_hist("D",hbase.summarize(dseg)),"H":norm_hist("H",hbase.summarize(hseg)),"M":norm_hist("M",mbase.compounded(mseg)),"O":norm_hist("O",obase.compounded(oseg)),"o_trade_rows":[z for x in oseg for z in (x.get("trade_rows") or [])]}
    return {"D":norm_cont("D",dseg[0]),"H":norm_cont("H",hseg[0]),"M":norm_cont("M",mseg[0]),"O":norm_cont("O",oseg[0]),"o_trade_rows":oseg[0].get("trade_rows") or []}


def random_stats(rows:List[Dict],label:str)->Dict:
    x=np.asarray([float(r[f"{label}_pnl"]) for r in rows],float)
    return {"windows":len(x),"mean_pnl_inr":float(np.mean(x)),"median_pnl_inr":float(np.median(x)),"p05_pnl_inr":float(np.quantile(x,.05)),"p95_pnl_inr":float(np.quantile(x,.95)),"positive_fraction":float(np.mean(x>0))}


def main()->None:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("--out",type=Path,default=OUT); ap.add_argument("--blocks",type=Path,default=BLOCK_ROOT); a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    hist_sha=canonical.verify_dataset(HISTORICAL); recent_manifest=mcmp.verify_archive(RECENT,RECENT_MANIFEST); current_manifest=mcmp.verify_archive(CURRENT,CURRENT_MANIFEST)
    result={"schema":"xau-v4-5-candidate-o-acceptance-invalidation-eval-v1","config":obase.CONFIG,"status":"known-data development/rejection evaluation","threshold_search":False,"model_search":False,"final20_opened":False,"historical_raw_sha256":hist_sha,"recent_dataset_id":recent_manifest["dataset_id"],"current_dataset_id":current_manifest["dataset_id"],"intervals":{},"decision":"PENDING"}
    full_rows=[]; block_rows=[]; random_rows=[]; o_trade_rows=[]

    for interval in ("500ms","1s"):
        print(f"=== {interval} load ===",flush=True)
        h_arr,h_bounds=canonical.build_features(HISTORICAL,interval); canonical.assert_baseline(canonical.run_strategy(h_arr,h_bounds,"v4_4"),interval,canonical.DEFAULT_GOLDEN); h_ranges=autopsy.indices(h_arr,h_bounds); h_raw=microstate.load_raw(HISTORICAL,nrows=canonical.RESEARCH_ROWS)
        r_arr=build_features_all_rows(RECENT,interval); r_raw=microstate.load_raw(RECENT)
        c_arr=build_features_all_rows(CURRENT,interval); c_raw=microstate.load_raw(CURRENT)
        sets={}
        for slip in STRESS:
            print(f"{interval} full datasets slip={slip}",flush=True)
            hist=run_set(h_arr,h_ranges,h_raw,slip,True,capture_o=(slip==0),ctx=f"historical:{interval}")
            recent=run_set(r_arr,[(0,len(r_arr["t"]))],r_raw,slip,False,capture_o=(slip==0),ctx=f"recent24h:{interval}")
            current=run_set(c_arr,[(0,len(c_arr["t"]))],c_raw,slip,False,capture_o=(slip==0),ctx=f"current7d:{interval}")
            if slip==0: o_trade_rows.extend(hist.pop("o_trade_rows")); o_trade_rows.extend(recent.pop("o_trade_rows")); o_trade_rows.extend(current.pop("o_trade_rows"))
            else: hist.pop("o_trade_rows",None); recent.pop("o_trade_rows",None); current.pop("o_trade_rows",None)
            suffix="0" if slip==0 else "1"
            for ds,res,ekey in (("historical_first80",hist,"hist"+suffix),("recent24h",recent,"recent"+suffix),("current7d",current,"current"+suffix)):
                for lab in ("D","H","M"): close(res[lab]["pnl_inr"],EXPECTED[interval][ekey][lab],f"{interval} {ds} {slip} {lab}")
                sets[f"{ds}|slip={slip:.2f}"]=res
                for lab in ("D","H","M","O"):
                    x=res[lab]; full_rows.append({"dataset":ds,"interval":interval,"slip_usd_per_side":slip,"candidate":lab,"pnl_inr":x["pnl_inr"],"trades":x["trades"],"wins":x["wins"],"win_rate":x["win_rate"],"profit_factor":x.get("profit_factor"),"max_drawdown_inr":x["max_drawdown_inr"],"thesis_invalidation_exits":x.get("thesis_invalidation_exits")})

        print(f"{interval} Stage1 blocks",flush=True)
        br=[]
        with tempfile.TemporaryDirectory(prefix="candidate-o-") as td:
            temp=Path(td)
            for sd in sorted(p for p in a.blocks.iterdir() if p.is_dir() and (p/"block_manifest.json").exists()):
                block=inspect_block(sd); combined=make_combined_csv(block,temp); arr=build_features_all_rows(combined,interval); raw=microstate.load_raw(combined); cache={}
                s=int(np.searchsorted(arr["t"],block["start"].timestamp(),side="left")); e=int(np.searchsorted(arr["t"],block["end"].timestamp(),side="right"))
                d=hbase.simulate(arr,s,e,candidate_h=False); h=hbase.simulate(arr,s,e,candidate_h=True,raw=raw,feature_cache=cache); m=mbase.simulate_m(arr,s,e,raw=raw,cache=cache); o=obase.simulate_o(arr,s,e,raw=raw,cache=cache,capture_trades=True,context=f"block:{sd.name}:{interval}")
                o_trade_rows.extend(o.get("trade_rows") or [])
                row={"session":sd.name,"interval":interval}
                for lab,x in (("D",d),("H",h),("M",m),("O",o)):
                    row[f"{lab}_pnl"]=float(x["terminal_equity_pnl_inr"]); row[f"{lab}_trades"]=int(x["trades"]); row[f"{lab}_wins"]=int(x["wins"]); row[f"{lab}_win_rate"]=float(x["win_rate"]); row[f"{lab}_max_dd"]=float(x["max_drawdown_inr"])
                row["O_thesis_invalidation_exits"]=int(o["thesis_invalidation_exits"]); br.append(row); block_rows.append(row)
        pooled={}
        for lab in ("D","H","M","O"):
            tr=sum(r[f"{lab}_trades"] for r in br); wi=sum(r[f"{lab}_wins"] for r in br)
            pooled[lab]={"pnl_inr":float(sum(r[f"{lab}_pnl"] for r in br)),"trades":int(tr),"wins":int(wi),"win_rate":float(wi/tr) if tr else 0.0,"positive_blocks":int(sum(r[f"{lab}_pnl"]>0 for r in br)),"blocks":len(br)}
        for lab in ("D","H","M"): close(pooled[lab]["pnl_inr"],EXPECTED[interval]["blocks"][lab],f"{interval} pooled {lab}")

        print(f"{interval} random multi-seed",flush=True)
        hranges=full_eval.continuous_ranges(h_arr,h_ranges); cranges=full_eval.continuous_ranges(c_arr,[(0,len(c_arr["t"]))]); seed_stats={}; all_rr=[]
        for seed in RANDOM_SEEDS:
            rng=np.random.default_rng(seed+(0 if interval=="500ms" else 1000)); rr=[]
            for wid in range(RANDOM_WINDOWS_PER_SEED):
                if wid%2==0: source="historical"; arr=h_arr; ranges=hranges; raw=h_raw
                else: source="current7d"; arr=c_arr; ranges=cranges; raw=c_raw
                s,e,rid=full_eval.random_window_from_ranges(arr,ranges,rng,RANDOM_HOURS); cache={}
                d=hbase.simulate(arr,s,e,candidate_h=False); h=hbase.simulate(arr,s,e,candidate_h=True,raw=raw,feature_cache=cache); m=mbase.simulate_m(arr,s,e,raw=raw,cache=cache); o=obase.simulate_o(arr,s,e,raw=raw,cache=cache)
                row={"interval":interval,"seed":seed,"window_id":wid,"source":source,"range_id":rid,"start_ts":float(arr["t"][s]),"end_ts":float(arr["t"][e-1])}
                for lab,x in (("D",d),("H",h),("M",m),("O",o)): row[f"{lab}_pnl"]=float(x["terminal_equity_pnl_inr"]); row[f"{lab}_trades"]=int(x["trades"])
                rr.append(row); all_rr.append(row); random_rows.append(row)
            seed_stats[str(seed)]={lab:random_stats(rr,lab) for lab in ("D","H","M","O")}
        pooled_random={lab:random_stats(all_rr,lab) for lab in ("D","H","M","O")}

        hist0=sets["historical_first80|slip=0.00"]; recent0=sets["recent24h|slip=0.00"]; current0=sets["current7d|slip=0.00"]
        hist1=sets["historical_first80|slip=0.10"]; recent1=sets["recent24h|slip=0.10"]; current1=sets["current7d|slip=0.10"]
        gates={"historical_positive":hist0["O"]["pnl_inr"]>0,"recent_nonnegative":recent0["O"]["pnl_inr"]>=0,"current_nonnegative":current0["O"]["pnl_inr"]>=0,"historical_trades_ge_20":hist0["O"]["trades"]>=20,"current_trades_ge_20":current0["O"]["trades"]>=20,"stage1_pooled_nonnegative":pooled["O"]["pnl_inr"]>=0,"stage1_positive_blocks_ge_3":pooled["O"]["positive_blocks"]>=3,"every_random_seed_mean_positive":all(seed_stats[str(seed)]["O"]["mean_pnl_inr"]>0 for seed in RANDOM_SEEDS),"pooled_random_median_nonnegative":pooled_random["O"]["median_pnl_inr"]>=0,"pooled_random_positive_fraction_ge_50pct":pooled_random["O"]["positive_fraction"]>=.50,"historical_stress_nonnegative":hist1["O"]["pnl_inr"]>=0,"recent_stress_nonnegative":recent1["O"]["pnl_inr"]>=0,"current_stress_nonnegative":current1["O"]["pnl_inr"]>=0,"comparator_parity":True}
        result["intervals"][interval]={"full_datasets":sets,"stage1":{"blocks":br,"pooled":pooled},"random_by_seed":seed_stats,"random_pooled":pooled_random,"development_survival_gates":gates}

    all_gates=[v for x in result["intervals"].values() for v in x["development_survival_gates"].values()]; result["development_survival_pass"]=bool(all(all_gates)); result["decision"]=("PASS known-data development-survival screen; freeze Candidate O unchanged for a brand-new non-overlapping prospective validation." if result["development_survival_pass"] else "FAIL known-data development-survival screen; reject Candidate O unchanged. Do not tune the frozen acceptance-invalidation rules against these outcomes.")
    write_csv(a.out/"full_dataset_comparison.csv",full_rows); write_csv(a.out/"stage1_block_comparison.csv",block_rows); write_csv(a.out/"random_4h_multiseed.csv",random_rows); write_csv(a.out/"candidate_o_trades.csv",o_trade_rows); (a.out/"candidate_o_config.json").write_text(json.dumps(obase.CONFIG,indent=2)+"\n",encoding="utf-8"); (a.out/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8"); print(json.dumps(result,indent=2),flush=True)

if __name__=="__main__": main()
