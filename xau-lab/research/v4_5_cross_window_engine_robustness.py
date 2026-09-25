"""Experiment 25: compare Candidate D engine behavior across historical and recent windows.
No strategy search occurs here. The script reads committed result ledgers only.
"""
from __future__ import annotations
import csv, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / "results" / "simulations" / "2026-09-25-v4_5-regime-normalization" / "engine_robustness_4h.csv"
RECENT = ROOT / "results" / "simulations" / "2026-09-24-recent-micro-long-validation"
OUT = ROOT / "results" / "simulations" / "2026-09-25-v4_5-cross-window-engine-robustness"
ENGINE_NAME = {"1.0":"PRIMARY","2.0":"SECONDARY","3.0":"MICRO","4.0":"BURST"}
FILES = {("500ms","seed"):"candidate_d_seed_500ms_trades.csv",("500ms","eval"):"candidate_d_evaluation_500ms_trades.csv",("1s","seed"):"candidate_d_seed_1s_trades.csv",("1s","eval"):"candidate_d_evaluation_1s_trades.csv"}
def read(path):
    with path.open(newline="", encoding="utf-8") as f: return list(csv.DictReader(f))
def agg(rows):
    out={}
    for row in rows:
        e=row.get("engine_name") or ENGINE_NAME.get(row.get("engine"),row.get("engine")); x=out.setdefault(e,{"trades":0,"wins":0,"pnl":0.0}); p=float(row["pnl_inr"]); x["trades"]+=1; x["wins"]+=int(p>0); x["pnl"]+=p
    for x in out.values(): x["win_rate"]=x["wins"]/x["trades"] if x["trades"] else 0.0
    return out
def main():
    hist=read(HIST); recent={(g,s):agg(read(RECENT/name)) for (g,s),name in FILES.items()}; rows=[]
    for h in hist:
        g,e=h["interval"],h["engine"]; zero={"trades":0,"wins":0,"pnl":0.0,"win_rate":0.0}; seed=recent[(g,"seed")].get(e,zero); ev=recent[(g,"eval")].get(e,zero); rt=seed["trades"]+ev["trades"]; rw=seed["wins"]+ev["wins"]
        rows.append({"interval":g,"engine":e,"historical_trades":int(h["trades"]),"historical_wins":int(h["wins"]),"historical_win_rate":int(h["wins"])/int(h["trades"]),"historical_pnl_inr":float(h["total_pnl_inr"]),"historical_profit_factor":float(h["profit_factor"]),"historical_positive_4h_windows":int(h["positive_4h_windows"]),"historical_negative_4h_windows":int(h["negative_4h_windows"]),"recent_seed_trades":seed["trades"],"recent_seed_wins":seed["wins"],"recent_seed_win_rate":seed["win_rate"],"recent_seed_pnl_inr":seed["pnl"],"recent_eval_trades":ev["trades"],"recent_eval_wins":ev["wins"],"recent_eval_win_rate":ev["win_rate"],"recent_eval_pnl_inr":ev["pnl"],"recent_split_realized_trades":rt,"recent_split_realized_wins":rw,"recent_split_realized_win_rate":rw/rt if rt else 0.0,"recent_split_realized_pnl_inr":seed["pnl"]+ev["pnl"]})
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/"cross_window_engine_summary.csv").open("w",newline="",encoding="utf-8") as f: w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    summary={"schema_version":"xau-cross-window-engine-robustness-v1","strategy_changed":False,"router_selected":False,"decision":"No global engine allow/deny rule; validate frozen raw-event regimes on independent raw snapshots before another router search."}
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8"); print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
