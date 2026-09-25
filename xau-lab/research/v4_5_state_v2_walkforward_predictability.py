"""Experiment 35: frozen walk-forward predictability test for xau-state-v2.

This is a diagnostic model, not a trading candidate. The specification is frozen
in docs/plans/V4_5_ADAPTIVE_ADMISSION_FEASIBILITY.md before execution.

No model/feature/threshold search is performed.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import v4_5_router_v2 as router
import v4_5_state_v2_freeze as state_v2

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_INPUT=ROOT/"results"/"simulations"/"2026-09-25-v4_5-independent-opportunity-atlas"/"shadow_opportunities.csv"
DEFAULT_OUT=ROOT/"results"/"simulations"/"2026-09-25-v4_5-state-v2-walkforward-predictability"
ALPHA=1.0
ENGINES=("PRIMARY","SECONDARY","MICRO","BURST")


def realized(df):
    c=df["censored"].astype(str).str.lower().eq("true")
    return df.loc[~c].copy()


def make_raw_matrix(df):
    cont=df[list(state_v2.FEATURES)].apply(pd.to_numeric,errors="coerce").to_numpy(dtype=float)
    onehot=np.column_stack([(df["engine"].astype(str).to_numpy()==e).astype(float) for e in ENGINES])
    return np.column_stack([cont,onehot])


def fit_preprocess(train_df):
    x=make_raw_matrix(train_df)
    n_cont=len(state_v2.FEATURES)
    med=np.nanmedian(x[:,:n_cont],axis=0)
    med=np.where(np.isfinite(med),med,0.0)
    x[:,:n_cont]=np.where(np.isfinite(x[:,:n_cont]),x[:,:n_cont],med)
    mean=np.mean(x,axis=0)
    std=np.std(x,axis=0)
    std=np.where(std>1e-12,std,1.0)
    return med,mean,std


def transform(df,med,mean,std):
    x=make_raw_matrix(df)
    n_cont=len(state_v2.FEATURES)
    x[:,:n_cont]=np.where(np.isfinite(x[:,:n_cont]),x[:,:n_cont],med)
    return (x-mean)/std


def ridge_fit(x,y,alpha=ALPHA):
    z=np.column_stack([np.ones(len(x)),x])
    reg=np.eye(z.shape[1])*alpha
    reg[0,0]=0.0
    return np.linalg.solve(z.T@z+reg,z.T@y)


def ridge_predict(x,beta):
    z=np.column_stack([np.ones(len(x)),x])
    return z@beta


def corr(a,b):
    a=np.asarray(a,dtype=float); b=np.asarray(b,dtype=float)
    if len(a)<2 or np.std(a)<1e-12 or np.std(b)<1e-12:
        return math.nan
    return float(np.corrcoef(a,b)[0,1])


def spearman(a,b):
    a=pd.Series(np.asarray(a,dtype=float)).rank(method="average").to_numpy()
    b=pd.Series(np.asarray(b,dtype=float)).rank(method="average").to_numpy()
    return corr(a,b)


def v2_scores(df):
    vals=[]
    for row in df.to_dict("records"):
        state={feat:float(row[feat]) if pd.notna(row[feat]) else math.nan for feat in state_v2.FEATURES}
        score,_=router.stronghold_score(str(row["engine"]),state)
        vals.append(float(score))
    return np.asarray(vals,dtype=float)


def evaluate_predictions(df,pred,train_mean,v2score,label,interval,fold):
    actual=pd.to_numeric(df["pnl_inr"],errors="coerce").to_numpy(dtype=float)
    keep=pred>0.0
    v2keep=v2score>=router.SCORE_FLOOR
    base_err=actual-train_mean
    err=actual-pred
    return {
        "label":label,"interval":interval,"fold":fold,
        "trades":int(len(df)),
        "actual_pnl_inr":float(actual.sum()),
        "actual_win_rate":float(np.mean(actual>0)) if len(actual) else 0.0,
        "prediction_mean_inr":float(np.mean(pred)) if len(pred) else 0.0,
        "pearson":corr(pred,actual),"spearman":spearman(pred,actual),
        "sign_accuracy":float(np.mean((pred>0)==(actual>0))) if len(actual) else 0.0,
        "mae_inr":float(np.mean(np.abs(err))) if len(actual) else 0.0,
        "rmse_inr":float(np.sqrt(np.mean(err**2))) if len(actual) else 0.0,
        "mean_baseline_mae_inr":float(np.mean(np.abs(base_err))) if len(actual) else 0.0,
        "mean_baseline_rmse_inr":float(np.sqrt(np.mean(base_err**2))) if len(actual) else 0.0,
        "predicted_positive_trades":int(keep.sum()),
        "predicted_positive_retention":float(keep.mean()) if len(keep) else 0.0,
        "predicted_positive_actual_pnl_inr":float(actual[keep].sum()) if keep.any() else 0.0,
        "predicted_positive_win_rate":float(np.mean(actual[keep]>0)) if keep.any() else 0.0,
        "predicted_nonpositive_actual_pnl_inr":float(actual[~keep].sum()) if (~keep).any() else 0.0,
        "v2_score_spearman":spearman(v2score,actual),
        "v2_positive_trades":int(v2keep.sum()),
        "v2_positive_retention":float(v2keep.mean()) if len(v2keep) else 0.0,
        "v2_positive_actual_pnl_inr":float(actual[v2keep].sum()) if v2keep.any() else 0.0,
        "v2_positive_win_rate":float(np.mean(actual[v2keep]>0)) if v2keep.any() else 0.0,
    }


def fit_predict(train_df,test_df):
    med,mean,std=fit_preprocess(train_df)
    xtr=transform(train_df,med,mean,std)
    xte=transform(test_df,med,mean,std)
    ytr=pd.to_numeric(train_df["pnl_inr"],errors="coerce").to_numpy(dtype=float)
    beta=ridge_fit(xtr,ytr)
    return ridge_predict(xte,beta),float(np.mean(ytr)),beta,med,mean,std


def per_engine(rows):
    df=pd.DataFrame(rows)
    if df.empty:return []
    out=[]
    for (label,interval,engine),g in df.groupby(["label","interval","engine"],sort=True):
        a=pd.to_numeric(g.actual_pnl_inr)
        keep=g.predicted_positive.astype(bool)
        out.append({
            "label":label,"interval":interval,"engine":engine,
            "trades":len(g),
            "actual_pnl_inr":float(a.sum()),
            "predicted_positive_trades":int(keep.sum()),
            "predicted_positive_actual_pnl_inr":float(a[keep].sum()) if keep.any() else 0.0,
            "predicted_nonpositive_actual_pnl_inr":float(a[~keep].sum()) if (~keep).any() else 0.0,
        })
    return out


def write_csv(path,rows):
    if not rows:
        path.write_text("",encoding="utf-8"); return
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields:fields.append(k)
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,default=DEFAULT_INPUT)
    ap.add_argument("--output",type=Path,default=DEFAULT_OUT)
    a=ap.parse_args()

    df=realized(pd.read_csv(a.input))
    a.output.mkdir(parents=True,exist_ok=True)

    metrics=[]; preds=[]; coeffs={}
    feature_names=["intercept",*state_v2.FEATURES,*[f"engine_{e.lower()}" for e in ENGINES]]

    for interval in ("500ms","1s"):
        hist=df[(df.window=="historical7d")&(df.interval==interval)].copy()
        recent=df[(df.window=="recent24h")&(df.interval==interval)].copy()

        for test_seg in (1,2,3,4):
            train=hist[pd.to_numeric(hist.segment_id)<=test_seg-1].copy()
            test=hist[pd.to_numeric(hist.segment_id)==test_seg].copy()
            if train.empty or test.empty:
                continue
            pred,train_mean,beta,med,mean,std=fit_predict(train,test)
            score=v2_scores(test)
            label="historical_walkforward"
            metrics.append(evaluate_predictions(test,pred,train_mean,score,label,interval,f"test_segment_{test_seg}"))
            coeffs[f"{interval}_test_segment_{test_seg}"]={feature_names[i]:float(beta[i]) for i in range(len(beta))}
            for row,p,s in zip(test.to_dict("records"),pred,score):
                preds.append({
                    "label":label,"interval":interval,"fold":f"test_segment_{test_seg}",
                    "engine":row["engine"],"entry_ts":row["entry_ts"],"segment_id":row["segment_id"],
                    "actual_pnl_inr":row["pnl_inr"],"predicted_pnl_inr":float(p),
                    "predicted_positive":bool(p>0),"v2_score":float(s),"v2_positive":bool(s>=router.SCORE_FLOOR),
                })

        train=hist.copy()
        if not train.empty and not recent.empty:
            pred,train_mean,beta,med,mean,std=fit_predict(train,recent)
            score=v2_scores(recent)
            metrics.append(evaluate_predictions(recent,pred,train_mean,score,"recent_after_first80",interval,"whole_recent"))
            coeffs[f"{interval}_recent_after_first80"]={feature_names[i]:float(beta[i]) for i in range(len(beta))}
            for row,p,s in zip(recent.to_dict("records"),pred,score):
                preds.append({
                    "label":"recent_after_first80","interval":interval,"fold":"whole_recent",
                    "engine":row["engine"],"entry_ts":row["entry_ts"],"segment_id":row["segment_id"],
                    "actual_pnl_inr":row["pnl_inr"],"predicted_pnl_inr":float(p),
                    "predicted_positive":bool(p>0),"v2_score":float(s),"v2_positive":bool(s>=router.SCORE_FLOOR),
                })

    # Aggregate OOS predictions without refitting or threshold changes.
    pdf=pd.DataFrame(preds)
    aggregate=[]
    for (label,interval),g in pdf.groupby(["label","interval"],sort=True):
        actual=pd.to_numeric(g.actual_pnl_inr).to_numpy(float)
        pred=pd.to_numeric(g.predicted_pnl_inr).to_numpy(float)
        score=pd.to_numeric(g.v2_score).to_numpy(float)
        # Aggregate rows use the training-mean baseline fields as NaN because
        # each historical fold has its own causal train mean.
        m=evaluate_predictions(g.rename(columns={"actual_pnl_inr":"pnl_inr"}),pred,math.nan,score,label,interval,"aggregate")
        m["mean_baseline_mae_inr"]=math.nan
        m["mean_baseline_rmse_inr"]=math.nan
        aggregate.append(m)

    engine_summary=per_engine(preds)
    write_csv(a.output/"fold_metrics.csv",metrics)
    write_csv(a.output/"predictions.csv",preds)
    write_csv(a.output/"aggregate_metrics.csv",aggregate)
    write_csv(a.output/"per_engine_prediction_summary.csv",engine_summary)
    (a.output/"coefficients.json").write_text(json.dumps(coeffs,indent=2)+"\n",encoding="utf-8")

    result={
        "schema":"xau-state-v2-walkforward-predictability-v1",
        "strategy_changed":False,
        "model_search_performed":False,
        "features":list(state_v2.FEATURES),
        "engine_one_hot":list(ENGINES),
        "side_feature_added":False,
        "target":"Experiment-33 fixed-size pnl_inr",
        "model":"ridge regression",
        "alpha":ALPHA,
        "threshold":"predicted expected P&L > 0 only; not tuned",
        "historical_folds":"expanding segments: 0->1, 0-1->2, 0-2->3, 0-3->4",
        "recent_training":"all historical first80 opportunities, then predict later recent24h",
        "final20_opened":False,
        "promotion_evidence":False,
        "aggregate_metrics":aggregate,
        "decision":"Predictability diagnostic only. A positive known-data result can justify freezing a future adaptive candidate, not promoting one.",
    }
    (a.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
