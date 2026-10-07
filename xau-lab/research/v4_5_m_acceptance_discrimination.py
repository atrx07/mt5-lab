"""Experiment 58 offline Candidate-M acceptance-discrimination extractor.

Replays frozen Candidate M, asserts exact summary parity, then records causal
`feature_*` fields at actual M entries. `label_*` fields are future/outcome-only
and are written only outside `--count-only` mode. This script does not define Q.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import v4_5_candidate_m_pullback_acceptance as mbase
import v4_5_microstate_v1_freeze as microstate
import v4_5_m_acceptance_discrimination_features as features
import v4_5_m_acceptance_discrimination_sim as sim
from v4_5_candidate_j_stage1_staged_validation import build_features_all_rows, make_combined_csv

ROOT=Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: List[Dict]) -> None:
    fields=[]
    for row in rows:
        for key in row:
            if key not in fields: fields.append(key)
    if not fields:
        path.write_text("",encoding="utf-8"); return
    with path.open("w",newline="",encoding="utf-8") as fh:
        w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows(rows)


def inspect_session(session_dir: Path) -> Dict:
    manifest_path=session_dir/"block_manifest.json"
    if not manifest_path.exists(): raise RuntimeError(f"missing Experiment-58 manifest: {manifest_path}")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8")); contract=manifest.get("score_contract",{})
    if manifest.get("schema")!="xau-exp58-m-acceptance-shadow-block-v1": raise RuntimeError(f"unexpected schema: {manifest.get('schema')}")
    if contract.get("complete") is not True or contract.get("valid_for_experiment58") is not True: raise RuntimeError(f"session not complete/valid: {session_dir.name}")
    if manifest.get("candidate_m_reference_frozen") is not True: raise RuntimeError("candidate_m_reference_frozen is not true")
    if manifest.get("external_data_used") is not False or manifest.get("final20_opened") is not False: raise RuntimeError("invalid provenance flags")

    def resolve(section: str, fallback: str) -> Path:
        raw=str(manifest.get(section,{}).get("path") or "").strip()
        if raw:
            p=Path(raw)
            if p.exists(): return p
            local=session_dir/p.name
            if local.exists(): return local
        return session_dir/fallback

    warmup=resolve("warmup","warmup_ticks.csv"); score=resolve("score","score_ticks.csv")
    for section,path in (("warmup",warmup),("score",score)):
        if not path.exists(): raise RuntimeError(f"missing {section}: {path}")
        declared=str(manifest.get(section,{}).get("sha256") or ""); actual=sha256_file(path)
        if not declared or actual!=declared: raise RuntimeError(f"{section} SHA mismatch: {actual} != {declared}")
    return {"session":session_dir.name,"manifest":manifest,"warmup":warmup,"score":score,"start":contract["score_start_mt5_reported_utc"]}


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session-dir",type=Path,required=True)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--count-only",action="store_true",help="report score-window M entry counts only; write no outcome labels")
    args=ap.parse_args(); block=inspect_session(args.session_dir)
    output=args.output or (ROOT/"results"/"simulations"/"2026-10-07-v4_5-m-acceptance-discrimination-shadow"/block["session"])
    score_start=datetime.fromisoformat(str(block["start"]).replace("Z","+00:00")).timestamp()
    all_events=[]; interval_rows={}

    with tempfile.TemporaryDirectory() as td:
        combined=make_combined_csv(block,Path(td)); raw=microstate.load_raw(combined)
        for interval in ("500ms","1s"):
            arr=build_features_all_rows(combined,interval); cache_ref: Dict[Tuple[float,int],Dict[str,float]]={}
            reference=mbase.simulate_m(arr,0,len(arr["t"]),raw=raw,cache=cache_ref)
            instrumented,events=sim.simulate_instrumented(arr,raw=raw,interval=interval,capture_labels=not args.count_only)
            sim.assert_parity(reference,instrumented,interval)
            filtered=[e for e in events if float(e["entry_ts"])>=score_start]
            interval_rows[interval]={"candidate_m_parity":True,"score_m_entries":len(filtered),"all_context_m_entries":len(events)}
            if not args.count_only:
                for e in filtered: e["source_session"]=block["session"]
                all_events.extend(filtered)

    if args.count_only:
        print(json.dumps({"schema":features.SCHEMA,"session":block["session"],"count_only":True,"outcomes_exposed":False,"500ms_score_m_entries":interval_rows["500ms"]["score_m_entries"],"1s_score_m_entries":interval_rows["1s"]["score_m_entries"],"candidate_m_parity":True},indent=2)); return

    output.mkdir(parents=True,exist_ok=True); write_csv(output/"m_acceptance_events.csv",all_events)
    summary={"schema":features.SCHEMA,"status":"prospective shadow discrimination extraction; no Candidate-Q rule selected","plan":features.PLAN_REF,"session":block["session"],"manifest":str(args.session_dir/"block_manifest.json"),"score_start_utc":block["start"],"final20_opened":False,"intervals":interval_rows,"event_rows":len(all_events),"feature_prefix":"feature_","label_prefix":"label_","feature_label_separation_rule":"future/outcome columns are labels only and may not be used to reconstruct the same entry","candidate_q_defined":False}
    (output/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8"); print(json.dumps(summary,indent=2))


if __name__=="__main__": main()
