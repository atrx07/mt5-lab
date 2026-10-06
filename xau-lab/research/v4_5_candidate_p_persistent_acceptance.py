"""Candidate P: Candidate-M setup with two time-separated entry confirmations.

Frozen by docs/plans/V4_5_CANDIDATE_P_PERSISTENT_ACCEPTANCE.md before P&L evaluation.
Known data may reject this candidate but cannot promote it. Final20 remains sealed.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np

import canonical_replay as canonical
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_candidate_l_normalized_resumption as lbase
import v4_5_candidate_m_pullback_acceptance as mbase

SECOND_CONFIRM_SEC = mbase.ACCEPT_SEC

CONFIG = {
    "schema": "xau-candidate-p-persistent-acceptance-v1",
    "base_setup": "Candidate M unchanged through first qualification",
    "external_data_used": False,
    "model_search": False,
    "threshold_search": False,
    "final20_opened": False,
    "confirmation_A": mbase.CONFIG["entry_confirmation"],
    "confirmation_B_delay_sec": SECOND_CONFIRM_SEC,
    "confirmation_B": "same execution + qacc/raw-flow test after another full acceptance clock",
    "price_must_remain_accepted_between_confirmations": True,
    "risk_fraction": mbase.CONFIG["risk_fraction"],
    "stop_usd": mbase.CONFIG["stop_usd"],
    "take_profit_usd": mbase.CONFIG["take_profit_usd"],
    "max_hold_sec": mbase.CONFIG["max_hold_sec"],
    "flow_exit": mbase.CONFIG["flow_exit"],
}


def compact(m: Dict) -> Dict:
    keys=("pnl_inr","terminal_unrealized_inr","terminal_equity_pnl_inr","open_position_at_end","profit_factor","trades","wins","win_rate","max_drawdown_inr","arms","arm_expiries","arm_trend_cancels","acceptance_timer_resets","confirmation_a","confirmation_a_resets","confirmation_b_failures","entries","flow_exits","trend_failure_exits","stop_exits","tp_exits","time_exits")
    return {k:m[k] for k in keys if k in m}


def simulate_p(
    arr: Dict[str,np.ndarray], start:int, end:int, *,
    raw: Dict[str,np.ndarray], cache: Dict[Tuple[float,int],Dict[str,float]],
    extra_slippage_usd_per_side:float=0.0,
    capture_trades:bool=False, context:str="",
)->Dict:
    t=np.asarray(arr["t"],float); bid=np.asarray(arr["bid"],float); ask=np.asarray(arr["ask"],float); mid=np.asarray(arr["mid"],float)
    session_starts=lbase.session_start_times(arr); slip=float(extra_slippage_usd_per_side)

    bal=canonical.START_BALANCE_INR; gp=gl=0.0; peakbal=bal; maxdd=0.0; ntr=wins=0
    pos=0; side=0; entry=oz=ptime=peak=0.0; next_check=math.inf; neg_conf=0

    arm_side=0; arm_time=0.0; arm_anchor=math.nan; arm_spread=math.nan; accept_since=-1e30; latch_side=0; confirm_a_ts=-1e30
    arms=arm_expiries=arm_trend_cancels=acceptance_timer_resets=0
    confirmation_a=confirmation_a_resets=confirmation_b_failures=entries=0
    flow_exits=trend_failure_exits=stop_exits=tp_exits=time_exits=0
    trade_rows:List[Dict]=[]

    for i in range(start,end):
        ts=float(t[i])
        if pos:
            exit_px=(bid[i]-slip) if side==1 else (ask[i]+slip)
            move=float((exit_px-entry) if side==1 else (entry-exit_px)); held=ts-ptime; peak=max(peak,move); reason=0
            if move<=-lbase.STOP_USD: reason=1; stop_exits+=1
            elif move>=lbase.TP_USD: reason=2; tp_exits+=1
            if reason==0 and ts>=next_check:
                while next_check<=ts: next_check+=lbase.FLOW_CHECK_SEC
                armed=peak>=lbase.FLOW_ARM_MFE_USD and (peak-move)>=lbase.FLOW_MIN_GIVEBACK_USD
                if armed:
                    bad,_=hbase.decay_state(raw,ts,side,cache); neg_conf=neg_conf+1 if bad else 0
                else: neg_conf=0
                if neg_conf>=lbase.FLOW_CONFIRMATIONS: reason=8; flow_exits+=1
            if reason==0:
                m300=float(arr["m300"][i])
                if math.isfinite(m300) and side*m300<=0: reason=5; trend_failure_exits+=1
            if reason==0 and held>=lbase.MAX_HOLD_SEC: reason=7; time_exits+=1
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
        if latch_side and (s!=latch_side or not mbase.current_pullback(arr,i,latch_side)): latch_side=0

        if arm_side:
            if s!=arm_side:
                arm_side=0; accept_since=-1e30; confirm_a_ts=-1e30; arm_trend_cancels+=1; continue
            if ts-arm_time>mbase.ARM_TIMEOUT_SEC:
                arm_side=0; accept_since=-1e30; confirm_a_ts=-1e30; arm_expiries+=1; continue
            beyond=arm_side*(float(mid[i])-float(arm_anchor))>=float(arm_spread)
            if not beyond:
                if accept_since>-1e20: acceptance_timer_resets+=1
                if confirm_a_ts>-1e20: confirmation_a_resets+=1
                accept_since=-1e30; confirm_a_ts=-1e30; continue

            if accept_since<-1e20: accept_since=ts
            if ts-accept_since<mbase.ACCEPT_SEC: continue

            # Confirmation A is exactly the point where Candidate M would qualify for entry.
            if confirm_a_ts<-1e20:
                if lbase.execution_ok(arr,i):
                    ok,_=mbase.entry_flow_ok(arr,i,arm_side,raw,cache)
                    if ok:
                        confirm_a_ts=ts; confirmation_a+=1
                continue

            if ts-confirm_a_ts<SECOND_CONFIRM_SEC: continue
            if not lbase.execution_ok(arr,i):
                confirm_a_ts=-1e30; confirmation_b_failures+=1; continue
            ok,_=mbase.entry_flow_ok(arr,i,arm_side,raw,cache)
            if not ok:
                confirm_a_ts=-1e30; confirmation_b_failures+=1; continue

            px=float((ask[i]+slip) if arm_side==1 else (bid[i]-slip))
            oz_new=min(bal*0.03/(lbase.STOP_USD*canonical.INR_PER_USD),(bal/canonical.INR_PER_USD*100.0)/px)
            if math.isfinite(oz_new) and oz_new>0:
                pos=1; side=arm_side; entry=px; oz=oz_new; ptime=ts; peak=0.0; next_check=ts+lbase.FLOW_CHECK_SEC; neg_conf=0; entries+=1
                arm_side=0; accept_since=-1e30; confirm_a_ts=-1e30
            continue

        if s==0 or latch_side: continue
        if mbase.current_pullback(arr,i,s):
            m10=float(arr["m10"][i]); spread=float(arr["spread"][i])
            arm_side=s; arm_time=ts; arm_anchor=float(mid[i]-m10); arm_spread=spread; accept_since=-1e30; confirm_a_ts=-1e30; latch_side=s; arms+=1

    pf=gp/gl if gl>0 else (999.0 if gp>0 else 0.0); terminal=0.0
    if pos and end>start:
        j=end-1; px=float((bid[j]-slip) if side==1 else (ask[j]+slip)); mv=float((px-entry) if side==1 else (entry-px)); terminal=mv*oz*canonical.INR_PER_USD
    return {"pnl_inr":float(bal-canonical.START_BALANCE_INR),"terminal_unrealized_inr":float(terminal),"terminal_equity_pnl_inr":float(bal-canonical.START_BALANCE_INR+terminal),"open_position_at_end":bool(pos),"profit_factor":float(pf),"trades":int(ntr),"wins":int(wins),"win_rate":float(wins/ntr) if ntr else 0.0,"max_drawdown_inr":float(maxdd),"arms":int(arms),"arm_expiries":int(arm_expiries),"arm_trend_cancels":int(arm_trend_cancels),"acceptance_timer_resets":int(acceptance_timer_resets),"confirmation_a":int(confirmation_a),"confirmation_a_resets":int(confirmation_a_resets),"confirmation_b_failures":int(confirmation_b_failures),"entries":int(entries),"flow_exits":int(flow_exits),"trend_failure_exits":int(trend_failure_exits),"stop_exits":int(stop_exits),"tp_exits":int(tp_exits),"time_exits":int(time_exits),"trade_rows":trade_rows if capture_trades else None}


def compounded(rows:List[Dict])->Dict:
    factor=1.0; trades=wins=0; dds=[]; counters={k:0 for k in ("arms","arm_expiries","arm_trend_cancels","confirmation_a","confirmation_a_resets","confirmation_b_failures","entries","flow_exits","trend_failure_exits","stop_exits","tp_exits","time_exits")}
    for m in rows:
        factor*=1.0+float(m["pnl_inr"])/canonical.START_BALANCE_INR; trades+=int(m["trades"]); wins+=int(m["wins"]); dds.append(float(m["max_drawdown_inr"]))
        for k in counters: counters[k]+=int(m.get(k,0))
    return {"compounded_pnl_inr":float(canonical.START_BALANCE_INR*(factor-1.0)),"trades":trades,"wins":wins,"win_rate":wins/trades if trades else 0.0,"max_segment_drawdown_inr":max(dds) if dds else 0.0,**counters}
