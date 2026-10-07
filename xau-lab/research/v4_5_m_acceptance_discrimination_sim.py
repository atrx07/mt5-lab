"""Parity-guarded instrumented Candidate-M simulator for Experiment 58."""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np

import canonical_replay as canonical
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_candidate_l_normalized_resumption as lbase
import v4_5_candidate_m_pullback_acceptance as mbase
import v4_5_m_acceptance_discrimination_features as feat


def simulate_instrumented(
    arr: Dict[str, np.ndarray], *, raw: Dict[str, np.ndarray], interval: str,
    capture_labels: bool = True,
) -> Tuple[Dict, List[Dict]]:
    t=np.asarray(arr["t"],float); bid=np.asarray(arr["bid"],float); ask=np.asarray(arr["ask"],float); mid=np.asarray(arr["mid"],float)
    session_starts=lbase.session_start_times(arr); cache={}
    bal=canonical.START_BALANCE_INR; gp=gl=0.0; peakbal=bal; maxdd=0.0; ntr=wins=0
    pos=0; side=0; entry=oz=ptime=peak=0.0; next_check=math.inf; neg_conf=0
    arm_side=0; arm_time=0.0; arm_anchor=arm_spread=arm_qacc=arm_mid=math.nan; accept_since=-1e30; latch_side=0; arm_resets=0
    arms=arm_expiries=arm_trend_cancels=acceptance_timer_resets=entries=0
    flow_exits=trend_failure_exits=stop_exits=tp_exits=time_exits=0
    events: List[Dict]=[]; open_event_idx=None

    for i in range(len(t)):
        ts=float(t[i])
        if pos:
            exit_px=float(bid[i]) if side==1 else float(ask[i]); move=float((exit_px-entry) if side==1 else (entry-exit_px)); held=ts-ptime; peak=max(peak,move); reason=0
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
                m300=feat.value(arr,"m300",i)
                if math.isfinite(m300) and side*m300<=0: reason=5; trend_failure_exits+=1
            if reason==0 and held>=lbase.MAX_HOLD_SEC: reason=7; time_exits+=1
            if reason:
                pnl=move*oz*canonical.INR_PER_USD; bal+=pnl; ntr+=1
                if pnl>0: gp+=pnl; wins+=1
                elif pnl<0: gl-=pnl
                peakbal=max(peakbal,bal); maxdd=max(maxdd,peakbal-bal)
                if capture_labels and open_event_idx is not None:
                    events[open_event_idx].update({"label_actual_exit_ts":ts,"label_actual_exit_reason":int(reason),"label_actual_exit_move_usd":move,"label_actual_mfe_usd":peak,"label_actual_held_sec":held,"label_actual_pnl_inr":pnl,"label_actual_win":bool(pnl>0)})
                pos=0; side=0; neg_conf=0; next_check=math.inf; open_event_idx=None
            continue

        s=lbase.structural_side(arr,i,session_starts)
        if latch_side and (s!=latch_side or not mbase.current_pullback(arr,i,latch_side)): latch_side=0
        if arm_side:
            if s!=arm_side:
                arm_side=0; accept_since=-1e30; arm_trend_cancels+=1; arm_resets=0; continue
            if ts-arm_time>mbase.ARM_TIMEOUT_SEC:
                arm_side=0; accept_since=-1e30; arm_expiries+=1; arm_resets=0; continue
            beyond=arm_side*(float(mid[i])-float(arm_anchor))>=float(arm_spread)
            if beyond:
                if accept_since<-1e20: accept_since=ts
                if ts-accept_since>=mbase.ACCEPT_SEC and lbase.execution_ok(arr,i):
                    ok,flow=mbase.entry_flow_ok(arr,i,arm_side,raw,cache)
                    if ok:
                        px=float(ask[i]) if arm_side==1 else float(bid[i])
                        oz_new=min(bal*0.03/(lbase.STOP_USD*canonical.INR_PER_USD),(bal/canonical.INR_PER_USD*100.0)/px)
                        if math.isfinite(oz_new) and oz_new>0:
                            row=feat.entry_feature_row(arr,i,arm_side,arm_time=arm_time,arm_anchor=arm_anchor,arm_spread=arm_spread,accept_since=accept_since,arm_qacc=arm_qacc,arm_mid=arm_mid,acceptance_timer_resets=arm_resets,flow_feat=flow,entry_px=px)
                            if capture_labels: row.update(feat.future_labels(arr,i,arm_side,px))
                            row["interval"]=interval; row["event_id"]=f"{interval}:{len(events):06d}:{ts:.3f}"; events.append(row); open_event_idx=len(events)-1
                            pos=1; side=arm_side; entry=px; oz=oz_new; ptime=ts; peak=0.0; next_check=ts+lbase.FLOW_CHECK_SEC; neg_conf=0; entries+=1
                            arm_side=0; accept_since=-1e30; arm_resets=0
            else:
                if accept_since>-1e20: acceptance_timer_resets+=1; arm_resets+=1
                accept_since=-1e30
            continue

        if s==0 or latch_side: continue
        if mbase.current_pullback(arr,i,s):
            m10=feat.value(arr,"m10",i); spread=feat.value(arr,"spread",i)
            arm_side=s; arm_time=ts; arm_anchor=float(mid[i]-m10); arm_spread=spread; arm_qacc=feat.value(arr,"qacc",i); arm_mid=float(mid[i]); accept_since=-1e30; latch_side=s; arm_resets=0; arms+=1

    terminal=0.0
    if pos and len(t):
        j=len(t)-1; px=float(bid[j]) if side==1 else float(ask[j]); mv=float((px-entry) if side==1 else (entry-px)); terminal=mv*oz*canonical.INR_PER_USD
    pf=gp/gl if gl>0 else (999.0 if gp>0 else 0.0)
    return {
        "pnl_inr":float(bal-canonical.START_BALANCE_INR),"terminal_unrealized_inr":float(terminal),"terminal_equity_pnl_inr":float(bal-canonical.START_BALANCE_INR+terminal),"open_position_at_end":bool(pos),
        "profit_factor":float(pf),"trades":int(ntr),"wins":int(wins),"win_rate":float(wins/ntr) if ntr else 0.0,"max_drawdown_inr":float(maxdd),
        "arms":int(arms),"arm_expiries":int(arm_expiries),"arm_trend_cancels":int(arm_trend_cancels),"acceptance_timer_resets":int(acceptance_timer_resets),"entries":int(entries),
        "flow_exits":int(flow_exits),"trend_failure_exits":int(trend_failure_exits),"stop_exits":int(stop_exits),"tp_exits":int(tp_exits),"time_exits":int(time_exits),
    },events


def assert_parity(reference: Dict, instrumented: Dict, interval: str) -> None:
    exact=("open_position_at_end","trades","wins","arms","arm_expiries","arm_trend_cancels","acceptance_timer_resets","entries","flow_exits","trend_failure_exits","stop_exits","tp_exits","time_exits")
    for key in exact:
        if reference.get(key)!=instrumented.get(key): raise RuntimeError(f"Experiment-58 parity drift {interval} {key}: {instrumented.get(key)} != {reference.get(key)}")
    for key in ("pnl_inr","terminal_unrealized_inr","terminal_equity_pnl_inr","max_drawdown_inr"):
        if abs(float(reference.get(key,0.0))-float(instrumented.get(key,0.0)))>1e-6: raise RuntimeError(f"Experiment-58 parity drift {interval} {key}")
