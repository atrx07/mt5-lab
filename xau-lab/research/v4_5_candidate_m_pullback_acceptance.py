"""Experiment 53: Candidate M pullback price-acceptance state machine.

Frozen by docs/plans/V4_5_CANDIDATE_M_PULLBACK_ACCEPTANCE.md before P&L
inspection. Candidate M is structurally different from rejected Candidate L:
a pullback only arms a setup; price must reclaim the pre-pullback level and
remain accepted beyond it for two clock seconds before execution confirmation.

Known data may reject M but cannot promote it. Final20 remains sealed.
"""
from __future__ import annotations

import argparse
import json
import math
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import canonical_replay as canonical
import v4_5_burst_path_autopsy as autopsy
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_candidate_l_normalized_resumption as lbase
import v4_5_microstate_v1_freeze as microstate
import v4_5_router_v2_full_eval as full_eval
from v4_5_candidate_j_stage1_staged_validation import build_features_all_rows, inspect_block, make_combined_csv

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OLD = ROOT / "xau_ticks_7d.csv"
DEFAULT_NEW = ROOT / "data" / "raw" / "xau_ticks_7d_current_2026-10-06.csv.gz"
DEFAULT_NEW_MANIFEST = ROOT / "data" / "manifests" / "xau_ticks_7d_2026-09-29_to_2026-10-06.json"
DEFAULT_BLOCKS = ROOT / "data" / "prospective_restored"
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-10-06-v4_5-candidate-m-pullback-acceptance"

ARM_TIMEOUT_SEC = 60.0
ACCEPT_SEC = 2.0
RANDOM_SEED = 51051
RANDOM_WINDOWS = 80
RANDOM_HOURS = 4.0
STRESS = (0.0, 0.05, 0.10, 0.20)

CONFIG = {
    "schema": "xau-candidate-m-pullback-acceptance-v1",
    "base_context": "Candidate-L normalized trend state, not its entry rule",
    "external_data_used": False,
    "model_search": False,
    "threshold_search": False,
    "final20_opened": False,
    "continuity_sec": lbase.CONTINUITY_SEC,
    "trend_dominance_ratio": lbase.TREND_DOMINANCE,
    "arm_pullback": "direction-normalized current m10 <= -current spread",
    "anchor": "mid - m10 at arm time (causal approx mid 10s earlier)",
    "arm_timeout_sec": ARM_TIMEOUT_SEC,
    "acceptance_level": "anchor +/- frozen arm_spread",
    "acceptance_clock_sec": ACCEPT_SEC,
    "entry_confirmation": "qacc>=1 AND raw dir_mid_move2>0 AND raw dir_event_imb2>0",
    "max_spread_usd": lbase.MAX_SPREAD_USD,
    "max_spread_fraction_range60": lbase.MAX_SPREAD_RANGE60,
    "risk_fraction": 0.03,
    "stop_usd": lbase.STOP_USD,
    "take_profit_usd": lbase.TP_USD,
    "max_hold_sec": lbase.MAX_HOLD_SEC,
    "flow_exit": lbase.CONFIG["flow_exit"],
    "random_seed": RANDOM_SEED,
    "random_windows_per_grid": RANDOM_WINDOWS,
}


def current_pullback(arr: Dict[str, np.ndarray], i: int, side: int) -> bool:
    spread = float(arr["spread"][i]); m10 = float(arr["m10"][i])
    return math.isfinite(spread) and spread > 0 and math.isfinite(m10) and side * m10 <= -spread


def entry_flow_ok(
    arr: Dict[str, np.ndarray], i: int, side: int,
    raw: Dict[str, np.ndarray], cache: Dict[Tuple[float, int], Dict[str, float]],
) -> Tuple[bool, Dict[str, float]]:
    qacc = float(arr["qacc"][i])
    if not math.isfinite(qacc) or qacc < 1.0:
        return False, {}
    ts = float(arr["t"][i]); key = (ts, int(side))
    feat = cache.get(key)
    if feat is None:
        feat = microstate.features_at(raw, ts, int(side)); cache[key] = feat
    dm = float(feat.get("dir_mid_move2", math.nan)); di = float(feat.get("dir_event_imb2", math.nan))
    return (math.isfinite(dm) and math.isfinite(di) and dm > 0 and di > 0), feat


def compact(m: Dict) -> Dict:
    keys=(
        "pnl_inr","terminal_unrealized_inr","terminal_equity_pnl_inr","open_position_at_end",
        "profit_factor","trades","wins","win_rate","max_drawdown_inr",
        "arms","arm_expiries","arm_trend_cancels","acceptance_timer_resets","entries",
        "flow_exits","trend_failure_exits","stop_exits","tp_exits","time_exits",
    )
    return {k:m[k] for k in keys if k in m}


def simulate_m(
    arr: Dict[str, np.ndarray], start: int, end: int, *,
    raw: Dict[str, np.ndarray], cache: Dict[Tuple[float, int], Dict[str, float]],
    extra_slippage_usd_per_side: float = 0.0,
    capture_trades: bool = False, context: str = "",
) -> Dict:
    t=np.asarray(arr["t"],float); bid=np.asarray(arr["bid"],float); ask=np.asarray(arr["ask"],float); mid=np.asarray(arr["mid"],float)
    session_starts=lbase.session_start_times(arr); slip=float(extra_slippage_usd_per_side)

    bal=canonical.START_BALANCE_INR; gp=gl=0.0; peakbal=bal; maxdd=0.0; ntr=wins=0
    pos=0; side=0; entry=oz=ptime=peak=0.0; next_check=math.inf; neg_conf=0

    arm_side=0; arm_time=0.0; arm_anchor=math.nan; arm_spread=math.nan; accept_since=-1e30; latch_side=0
    arms=arm_expiries=arm_trend_cancels=acceptance_timer_resets=entries=0
    flow_exits=trend_failure_exits=stop_exits=tp_exits=time_exits=0
    trade_rows: List[Dict]=[]

    for i in range(start,end):
        ts=float(t[i])
        if pos:
            exit_px=(bid[i]-slip) if side==1 else (ask[i]+slip)
            move=float((exit_px-entry) if side==1 else (entry-exit_px)); held=ts-ptime; peak=max(peak,move)
            reason=0
            if move <= -lbase.STOP_USD:
                reason=1; stop_exits+=1
            elif move >= lbase.TP_USD:
                reason=2; tp_exits+=1

            if reason==0 and ts>=next_check:
                while next_check<=ts: next_check+=lbase.FLOW_CHECK_SEC
                armed=peak>=lbase.FLOW_ARM_MFE_USD and (peak-move)>=lbase.FLOW_MIN_GIVEBACK_USD
                if armed:
                    bad,_=hbase.decay_state(raw,ts,side,cache); neg_conf=neg_conf+1 if bad else 0
                else:
                    neg_conf=0
                if neg_conf>=lbase.FLOW_CONFIRMATIONS:
                    reason=8; flow_exits+=1

            if reason==0:
                m300=float(arr["m300"][i])
                if math.isfinite(m300) and side*m300<=0:
                    reason=5; trend_failure_exits+=1
            if reason==0 and held>=lbase.MAX_HOLD_SEC:
                reason=7; time_exits+=1

            if reason:
                pnl=move*oz*canonical.INR_PER_USD; bal+=pnl; ntr+=1
                if pnl>0: gp+=pnl; wins+=1
                elif pnl<0: gl-=pnl
                peakbal=max(peakbal,bal); maxdd=max(maxdd,peakbal-bal)
                if capture_trades:
                    trade_rows.append({"context":context,"entry_ts":ptime,"exit_ts":ts,"side":"BUY" if side==1 else "SELL","exit_move_usd":move,"mfe_usd":peak,"held_sec":held,"pnl_inr":pnl,"exit_reason":reason})
                pos=0; side=0; neg_conf=0; next_check=math.inf
            continue

        s=lbase.structural_side(arr,i,session_starts)

        # A latch prevents one continuous adverse m10 condition from producing
        # repeated arm attempts. The arm itself may survive while m10 recovers.
        if latch_side and (s!=latch_side or not current_pullback(arr,i,latch_side)):
            latch_side=0

        if arm_side:
            if s!=arm_side:
                arm_side=0; accept_since=-1e30; arm_trend_cancels+=1
                continue
            if ts-arm_time>ARM_TIMEOUT_SEC:
                arm_side=0; accept_since=-1e30; arm_expiries+=1
                continue
            beyond=arm_side*(float(mid[i])-float(arm_anchor))>=float(arm_spread)
            if beyond:
                if accept_since < -1e20: accept_since=ts
                if ts-accept_since>=ACCEPT_SEC:
                    if lbase.execution_ok(arr,i):
                        ok,_=entry_flow_ok(arr,i,arm_side,raw,cache)
                        if ok:
                            px=float((ask[i]+slip) if arm_side==1 else (bid[i]-slip))
                            oz_new=min(bal*0.03/(lbase.STOP_USD*canonical.INR_PER_USD),(bal/canonical.INR_PER_USD*100.0)/px)
                            if math.isfinite(oz_new) and oz_new>0:
                                pos=1; side=arm_side; entry=px; oz=oz_new; ptime=ts; peak=0.0
                                next_check=ts+lbase.FLOW_CHECK_SEC; neg_conf=0; entries+=1
                                arm_side=0; accept_since=-1e30
            else:
                if accept_since>-1e20: acceptance_timer_resets+=1
                accept_since=-1e30
            continue

        if s==0 or latch_side:
            continue
        if current_pullback(arr,i,s):
            m10=float(arr["m10"][i]); spread=float(arr["spread"][i])
            arm_side=s; arm_time=ts; arm_anchor=float(mid[i]-m10); arm_spread=spread; accept_since=-1e30; latch_side=s; arms+=1

    pf=gp/gl if gl>0 else (999.0 if gp>0 else 0.0); terminal=0.0
    if pos and end>start:
        j=end-1; px=float((bid[j]-slip) if side==1 else (ask[j]+slip)); mv=float((px-entry) if side==1 else (entry-px)); terminal=mv*oz*canonical.INR_PER_USD
    return {
        "pnl_inr":float(bal-canonical.START_BALANCE_INR),"terminal_unrealized_inr":float(terminal),
        "terminal_equity_pnl_inr":float(bal-canonical.START_BALANCE_INR+terminal),"open_position_at_end":bool(pos),
        "profit_factor":float(pf),"trades":int(ntr),"wins":int(wins),"win_rate":float(wins/ntr) if ntr else 0.0,"max_drawdown_inr":float(maxdd),
        "arms":int(arms),"arm_expiries":int(arm_expiries),"arm_trend_cancels":int(arm_trend_cancels),"acceptance_timer_resets":int(acceptance_timer_resets),"entries":int(entries),
        "flow_exits":int(flow_exits),"trend_failure_exits":int(trend_failure_exits),"stop_exits":int(stop_exits),"tp_exits":int(tp_exits),"time_exits":int(time_exits),
        "trade_rows":trade_rows if capture_trades else None,
    }


def compounded(rows: List[Dict]) -> Dict:
    factor=1.0; trades=wins=0; dds=[]; counters={k:0 for k in ("arms","arm_expiries","arm_trend_cancels","entries","flow_exits","trend_failure_exits","stop_exits","tp_exits","time_exits")}
    for m in rows:
        factor*=1.0+float(m["pnl_inr"])/canonical.START_BALANCE_INR; trades+=int(m["trades"]); wins+=int(m["wins"]); dds.append(float(m["max_drawdown_inr"]))
        for k in counters: counters[k]+=int(m.get(k,0))
    return {"compounded_pnl_inr":float(canonical.START_BALANCE_INR*(factor-1.0)),"trades":trades,"wins":wins,"win_rate":wins/trades if trades else 0.0,"max_segment_drawdown_inr":max(dds) if dds else 0.0,**counters}


def random_summary(rows: List[Dict], key: str) -> Dict:
    x=np.asarray([float(r[key]) for r in rows],float)
    return {"windows":len(x),"mean_pnl_inr":float(np.mean(x)),"median_pnl_inr":float(np.median(x)),"p05_pnl_inr":float(np.quantile(x,.05)),"p95_pnl_inr":float(np.quantile(x,.95)),"positive_fraction":float(np.mean(x>0))}


def close(actual: float, expected: float, label: str, tol: float=1e-3):
    if abs(float(actual)-float(expected))>tol: raise RuntimeError(f"{label} parity drift: {actual} != {expected}")


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--historical",type=Path,default=DEFAULT_OLD); ap.add_argument("--current",type=Path,default=DEFAULT_NEW)
    ap.add_argument("--current-manifest",type=Path,default=DEFAULT_NEW_MANIFEST); ap.add_argument("--prospective-root",type=Path,default=DEFAULT_BLOCKS)
    ap.add_argument("--output",type=Path,default=DEFAULT_OUT); a=ap.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
    canonical.verify_dataset(a.historical); new_manifest=lbase.verify_current(a.current,a.current_manifest)
    (a.output/"candidate_m_config.json").write_text(json.dumps(CONFIG,indent=2)+"\n",encoding="utf-8")
    result={"schema":"xau-v4-5-candidate-m-eval-v1","config":CONFIG,"status":"known-data development/rejection evaluation","current_dataset_id":new_manifest["dataset_id"],"final20_opened":False,"external_data_used":False,"intervals":{}}
    block_rows=[]; random_rows=[]; stress_rows=[]; trade_rows=[]

    for interval in ("500ms","1s"):
        print(f"{interval}: historical",flush=True)
        h_arr,h_bounds=canonical.build_features(a.historical,interval); v44=canonical.run_strategy(h_arr,h_bounds,"v4_4"); canonical.assert_baseline(v44,interval,canonical.DEFAULT_GOLDEN)
        h_ranges=autopsy.indices(h_arr,h_bounds); h_raw=microstate.load_raw(a.historical,nrows=canonical.RESEARCH_ROWS); h_cache={}
        dseg=[hbase.simulate(h_arr,s,e,candidate_h=False) for s,e in h_ranges]
        hseg=[hbase.simulate(h_arr,s,e,candidate_h=True,raw=h_raw,feature_cache=h_cache) for s,e in h_ranges]
        mseg=[simulate_m(h_arr,s,e,raw=h_raw,cache=h_cache,capture_trades=True,context=f"historical:{interval}:seg{sid}") for sid,(s,e) in enumerate(h_ranges)]
        for m in mseg: trade_rows.extend(m.get("trade_rows") or [])
        ds=hbase.summarize(dseg); hs=hbase.summarize(hseg); ms=compounded(mseg)
        close(ds["compounded_pnl_inr"],lbase.EXPECTED_HIST_D[interval],f"hist D {interval}",1e-6); close(hs["compounded_pnl_inr"],lbase.EXPECTED_HIST_H[interval],f"hist H {interval}",.02)

        print(f"{interval}: current7d",flush=True)
        c_arr=build_features_all_rows(a.current,interval); c_raw=microstate.load_raw(a.current); c_cache={}
        cd=hbase.simulate(c_arr,0,len(c_arr["t"]),candidate_h=False); ch=hbase.simulate(c_arr,0,len(c_arr["t"]),candidate_h=True,raw=c_raw,feature_cache=c_cache)
        cm=simulate_m(c_arr,0,len(c_arr["t"]),raw=c_raw,cache=c_cache,capture_trades=True,context=f"current7d:{interval}"); trade_rows.extend(cm.get("trade_rows") or [])
        close(cd["terminal_equity_pnl_inr"],lbase.EXPECTED_CURRENT[interval]["D"],f"current D {interval}",1e-6); close(ch["terminal_equity_pnl_inr"],lbase.EXPECTED_CURRENT[interval]["H"],f"current H {interval}",1e-6)

        print(f"{interval}: Stage1 blocks",flush=True)
        br=[]
        with tempfile.TemporaryDirectory(prefix="candidate-m-") as td:
            temp=Path(td)
            for session_dir in sorted(p for p in a.prospective_root.iterdir() if p.is_dir() and (p/"block_manifest.json").exists()):
                block=inspect_block(session_dir); combined=make_combined_csv(block,temp); arr=build_features_all_rows(combined,interval); raw=microstate.load_raw(combined); cache={}
                s=int(np.searchsorted(arr["t"],block["start"].timestamp(),side="left")); e=int(np.searchsorted(arr["t"],block["end"].timestamp(),side="right"))
                dm=hbase.simulate(arr,s,e,candidate_h=False); hm=hbase.simulate(arr,s,e,candidate_h=True,raw=raw,feature_cache=cache); mm=simulate_m(arr,s,e,raw=raw,cache=cache,capture_trades=True,context=f"block:{session_dir.name}:{interval}")
                trade_rows.extend(mm.get("trade_rows") or [])
                row={"session":session_dir.name,"interval":interval}
                for label,m in (("D",dm),("H",hm),("M",mm)):
                    row[f"{label}_pnl"]=float(m["terminal_equity_pnl_inr"]); row[f"{label}_trades"]=int(m["trades"]); row[f"{label}_wins"]=int(m["wins"])
                br.append(row); block_rows.append(row)
        pooled={label:float(sum(r[f"{label}_pnl"] for r in br)) for label in ("D","H","M")}
        close(pooled["D"],lbase.EXPECTED_BLOCK_POOLED[interval]["D"],f"blocks D {interval}",1e-6); close(pooled["H"],lbase.EXPECTED_BLOCK_POOLED[interval]["H"],f"blocks H {interval}",1e-6)

        print(f"{interval}: random 4h",flush=True)
        rng=np.random.default_rng(RANDOM_SEED+(0 if interval=="500ms" else 1)); hranges=full_eval.continuous_ranges(h_arr,h_ranges); cranges=full_eval.continuous_ranges(c_arr,[(0,len(c_arr["t"]))]); rr=[]
        for wid in range(RANDOM_WINDOWS):
            if wid%2==0: source="historical"; arr=h_arr; ranges=hranges; raw=h_raw; cache=h_cache
            else: source="current7d"; arr=c_arr; ranges=cranges; raw=c_raw; cache=c_cache
            s,e,rid=full_eval.random_window_from_ranges(arr,ranges,rng,RANDOM_HOURS)
            dm=hbase.simulate(arr,s,e,candidate_h=False); hm=hbase.simulate(arr,s,e,candidate_h=True,raw=raw,feature_cache=cache); mm=simulate_m(arr,s,e,raw=raw,cache=cache)
            row={"interval":interval,"window_id":wid,"source":source,"range_id":rid,"start_ts":float(arr["t"][s]),"end_ts":float(arr["t"][e-1]),"D_pnl":float(dm["terminal_equity_pnl_inr"]),"H_pnl":float(hm["terminal_equity_pnl_inr"]),"M_pnl":float(mm["terminal_equity_pnl_inr"]),"D_trades":int(dm["trades"]),"H_trades":int(hm["trades"]),"M_trades":int(mm["trades"])}
            rr.append(row); random_rows.append(row)
        rstats={label:random_summary(rr,f"{label}_pnl") for label in ("D","H","M")}

        print(f"{interval}: stress",flush=True)
        stresses={}
        for slip in STRESS:
            dcur=hbase.simulate(c_arr,0,len(c_arr["t"]),candidate_h=False,extra_slippage_usd_per_side=slip); hcur=hbase.simulate(c_arr,0,len(c_arr["t"]),candidate_h=True,raw=c_raw,feature_cache=c_cache,extra_slippage_usd_per_side=slip); mcur=simulate_m(c_arr,0,len(c_arr["t"]),raw=c_raw,cache=c_cache,extra_slippage_usd_per_side=slip)
            mhist=[simulate_m(h_arr,s,e,raw=h_raw,cache=h_cache,extra_slippage_usd_per_side=slip) for s,e in h_ranges]; mhs=compounded(mhist)
            sr={"interval":interval,"slip":slip,"D_current_pnl":float(dcur["terminal_equity_pnl_inr"]),"H_current_pnl":float(hcur["terminal_equity_pnl_inr"]),"M_current_pnl":float(mcur["terminal_equity_pnl_inr"]),"M_historical_compounded_pnl":float(mhs["compounded_pnl_inr"]),"M_current_trades":int(mcur["trades"]),"M_historical_trades":int(mhs["trades"])}
            stress_rows.append(sr); stresses[str(slip)]=sr

        gates={
            "historical_positive":ms["compounded_pnl_inr"]>0,
            "current_positive":cm["terminal_equity_pnl_inr"]>0,
            "historical_trades_ge_20":ms["trades"]>=20,
            "current_trades_ge_20":cm["trades"]>=20,
            "random_mean_positive":rstats["M"]["mean_pnl_inr"]>0,
            "random_median_nonnegative":rstats["M"]["median_pnl_inr"]>=0,
            "random_positive_fraction_ge_45pct":rstats["M"]["positive_fraction"]>=0.45,
            "historical_plus_0_10_slip_positive":stresses["0.1"]["M_historical_compounded_pnl"]>0,
            "current_plus_0_10_slip_positive":stresses["0.1"]["M_current_pnl"]>0,
            "comparator_parity":True,
        }
        result["intervals"][interval]={"historical_first80":{"D":ds,"H":hs,"M":ms},"current7d":{"D":hbase.compact(cd),"H":hbase.compact(ch),"M":compact(cm)},"stage1_blocks":{"pooled_pnl":pooled,"positive_M_blocks":int(sum(r["M_pnl"]>0 for r in br)),"blocks":len(br)},"random_real_4h":rstats,"cost_stress":stresses,"development_survival_gates":gates}

    all_gates=[v for item in result["intervals"].values() for v in item["development_survival_gates"].values()]; result["development_survival_pass"]=bool(all(all_gates)); result["decision"]=("PASS development-survival screen; Candidate M may be frozen unchanged for a brand-new prospective validation." if result["development_survival_pass"] else "FAIL development-survival screen; reject frozen Candidate M unchanged. Do not tune its numeric boundaries against these known outcomes.")
    lbase.write_csv(a.output/"stage1_block_comparison.csv",block_rows); lbase.write_csv(a.output/"random_real_4h_windows.csv",random_rows); lbase.write_csv(a.output/"cost_stress.csv",stress_rows); lbase.write_csv(a.output/"candidate_m_trades.csv",trade_rows)
    (a.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8"); print(json.dumps(result,indent=2),flush=True)

if __name__=="__main__": main()
