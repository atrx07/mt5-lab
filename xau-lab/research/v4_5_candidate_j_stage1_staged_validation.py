"""Experiment 48 Stage-1 validator for six staged fresh Candidate-J blocks.

This evaluator is frozen before prospective D/H/J outcomes are inspected.
It validates exactly six locally captured block directories, verifies their
manifests/hashes/overlap/day coverage, then runs frozen Candidate D, H and J on
500 ms and 1 s grids. Warmup ticks are feature context only; performance starts
at each block's declared score-start boundary.

No external market data. No parameter search. No final20 access.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_candidate_h_flow_confirmed_ghost_exit as hbase
import v4_5_microstate_v1_freeze as microstate
import v4_5_quote_flow_phase_controller as qflow
import v4_5_tick_tape_field_audit as tape

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_REF = "docs/experiments/2026-09-26/48-v4-5-candidate-j-fresh-validation.md"
STRESS = (0.0, 0.05, 0.10, 0.20)
RAW_COLS = ["timestamp_utc", "bid", "ask", "last", "volume", "flags", "volume_real", "spread", "mid"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: List[Dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: List[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def resolve_manifest_path(session_dir: Path, manifest: Dict, section: str, fallback: str) -> Path:
    raw = str(manifest.get(section, {}).get("path") or "").strip()
    if raw:
        p = Path(raw)
        if p.exists():
            return p
        # Absolute paths in manifests are machine-local provenance. When moved
        # or restored, resolve by basename inside the frozen session directory.
        candidate = session_dir / p.name
        if candidate.exists():
            return candidate
    return session_dir / fallback


def ts(value) -> pd.Timestamp:
    return pd.Timestamp(value).tz_convert("UTC") if pd.Timestamp(value).tzinfo else pd.Timestamp(value, tz="UTC")


def inspect_block(session_dir: Path) -> Dict:
    manifest_path = session_dir / "block_manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"missing block_manifest.json: {session_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    contract = manifest.get("score_contract", {})
    if not bool(contract.get("complete")):
        raise RuntimeError(f"block not complete: {session_dir.name}")
    if not bool(contract.get("valid_for_stage1")):
        raise RuntimeError(f"block not Stage-1 valid: {session_dir.name}")
    if manifest.get("candidate_j_frozen") is not True:
        raise RuntimeError(f"candidate_j_frozen is not true: {session_dir.name}")
    if manifest.get("external_data_used") is not False:
        raise RuntimeError(f"external_data_used is not false: {session_dir.name}")
    if manifest.get("final20_opened") is not False:
        raise RuntimeError(f"final20_opened is not false: {session_dir.name}")

    warmup = resolve_manifest_path(session_dir, manifest, "warmup", "warmup_ticks.csv")
    score = resolve_manifest_path(session_dir, manifest, "score", "score_ticks.csv")
    for label, p in (("warmup", warmup), ("score", score)):
        if not p.exists():
            raise RuntimeError(f"missing {label} file for {session_dir.name}: {p}")
        declared = str(manifest.get(label, {}).get("sha256") or "")
        actual = sha256_file(p)
        if not declared or actual != declared:
            raise RuntimeError(f"{label} SHA mismatch for {session_dir.name}: {actual} != {declared}")

    start = ts(contract["score_start_mt5_reported_utc"])
    end = ts(contract["score_end_target_mt5_reported_utc"])
    if end <= start:
        raise RuntimeError(f"invalid score interval: {session_dir.name}")

    score_rows = int(manifest.get("score", {}).get("rows", 0))
    if score_rows <= 0:
        raise RuntimeError(f"score rows missing/zero: {session_dir.name}")

    return {
        "session": session_dir.name,
        "session_dir": session_dir,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "warmup": warmup,
        "score": score,
        "start": start,
        "end": end,
        "score_rows": score_rows,
        "score_sha256": manifest["score"]["sha256"],
        "warmup_sha256": manifest["warmup"]["sha256"],
        "schema": manifest.get("schema"),
    }


def verify_set(blocks: List[Dict]) -> Dict:
    if len(blocks) != 6:
        raise RuntimeError(f"Stage 1 requires exactly 6 blocks, got {len(blocks)}")
    ordered = sorted(blocks, key=lambda x: x["start"])
    seen = set()
    for b in ordered:
        if b["session"] in seen:
            raise RuntimeError(f"duplicate session: {b['session']}")
        seen.add(b["session"])
    for a, b in zip(ordered, ordered[1:]):
        if b["start"] < a["end"]:
            raise RuntimeError(f"score overlap: {a['session']} and {b['session']}")
    market_days = sorted({b["start"].date().isoformat() for b in ordered})
    if len(market_days) < 3:
        raise RuntimeError(f"Stage 1 requires >=3 market days, got {market_days}")
    return {
        "blocks": 6,
        "market_days": market_days,
        "market_day_count": len(market_days),
        "no_overlap": True,
        "final20_opened": False,
        "external_data_used": False,
    }


def make_combined_csv(block: Dict, temp_dir: Path) -> Path:
    warm = pd.read_csv(block["warmup"])
    score = pd.read_csv(block["score"])
    missing = [c for c in RAW_COLS if c not in warm.columns or c not in score.columns]
    if missing:
        raise RuntimeError(f"missing raw columns in {block['session']}: {missing}")
    df = pd.concat([warm[RAW_COLS], score[RAW_COLS]], ignore_index=True)
    t = pd.to_datetime(df["timestamp_utc"], utc=True, format="mixed")
    # Dedup only exact duplicate raw rows introduced at the warmup/score boundary.
    df = df.assign(_t=t).sort_values("_t", kind="stable").drop_duplicates(subset=RAW_COLS, keep="first")
    df = df.drop(columns=["_t"]).reset_index(drop=True)
    out = temp_dir / f"{block['session']}_combined.csv"
    df.to_csv(out, index=False)
    return out


def build_features_all_rows(path: Path, interval: str):
    """Canonical feature builder without the historical RESEARCH_ROWS cap."""
    raw = pd.read_csv(path, usecols=["timestamp_utc", "bid", "ask"])
    raw["t"] = pd.to_datetime(raw.timestamp_utc, utc=True, format="mixed")
    raw = raw.sort_values("t", kind="stable").reset_index(drop=True)
    raw["mid"] = (raw.bid + raw.ask) / 2.0
    gap = raw.t.diff().dt.total_seconds().fillna(0)
    raw["session"] = (gap > 5.0).cumsum().astype("int32")
    md = raw.mid.diff()
    md[raw.session.diff().fillna(1) != 0] = 0
    raw["up"] = (md > 0).astype("int8")
    raw["down"] = (md < 0).astype("int8")
    raw["bin"] = raw.t.dt.floor(interval)
    agg = (
        raw.groupby(["session", "bin"], sort=False)
        .agg(t=("t", "last"), bid=("bid", "last"), ask=("ask", "last"), mid=("mid", "last"),
             raw_count=("mid", "size"), up=("up", "sum"), down=("down", "sum"))
        .reset_index()
    )
    agg["spread"] = agg.ask - agg.bid
    pieces = []
    for _, z in agg.groupby("session", sort=False):
        z = z.copy().set_index("t", drop=False)
        c10 = z.raw_count.rolling("10s").sum(); c30 = z.raw_count.rolling("30s").sum()
        u10 = z.up.rolling("10s").sum(); d10 = z.down.rolling("10s").sum(); den = u10 + d10
        z["imb10"] = ((u10 - d10) / den.replace(0, np.nan)).fillna(0.0)
        z["qacc"] = (3.0 * c10 / c30.replace(0, np.nan)).fillna(0.0)
        pieces.append(z.reset_index(drop=True))
    df = pd.concat(pieces, ignore_index=True)
    df["ss"] = (df.t.diff().dt.total_seconds().fillna(0) > 5.0).cumsum().astype("int32")
    for h in [10, 30, 60, 120, 300, 1800]: df[f"m{h}"] = np.nan
    for col in ["range60","range300","er60","min_m10_30","max_m10_30","min_m60_300","max_m60_300","ch_high120","ch_low120"]:
        df[col] = np.nan
    epoch = canonical._epoch_seconds_ns
    for _, ids in df.groupby("ss", sort=False).groups.items():
        ii = np.asarray(list(ids), dtype=np.int64); z = df.loc[ii]
        tt = epoch(z["t"]); mids = z.mid.to_numpy()
        for h in [10,30,60,120,300,1800]:
            j = np.searchsorted(tt, tt-h, side="right")-1
            vals = np.full(len(ii), np.nan); valid = np.where(j>=0)[0]; jj=j[valid]
            age = tt[valid]-tt[jj]; ok=age<=h+5.0; kk=valid[ok]
            vals[kk]=mids[kk]-mids[j[kk]]; df.loc[ii,f"m{h}"]=vals
        zz=z.set_index("t")
        df.loc[ii,"range60"]=(zz.mid.rolling("60s").max()-zz.mid.rolling("60s").min()).to_numpy()
        df.loc[ii,"range300"]=(zz.mid.rolling("300s").max()-zz.mid.rolling("300s").min()).to_numpy()
        path=zz.mid.diff().abs().rolling("60s").sum().to_numpy(); m60=df.loc[ii,"m60"].to_numpy()
        df.loc[ii,"er60"]=np.divide(np.abs(m60),path,out=np.full(len(ii),np.nan),where=path>0)
        m10s=pd.Series(df.loc[ii,"m10"].to_numpy(),index=zz.index); m60s=pd.Series(m60,index=zz.index)
        df.loc[ii,"min_m10_30"]=m10s.rolling("30s").min().to_numpy(); df.loc[ii,"max_m10_30"]=m10s.rolling("30s").max().to_numpy()
        df.loc[ii,"min_m60_300"]=m60s.rolling("300s").min().to_numpy(); df.loc[ii,"max_m60_300"]=m60s.rolling("300s").max().to_numpy()
        df.loc[ii,"ch_high120"]=zz.mid.rolling("120s").max().shift(1).to_numpy(); df.loc[ii,"ch_low120"]=zz.mid.rolling("120s").min().shift(1).to_numpy()
    arrays={c:(epoch(df[c]) if c=="t" else df[c].to_numpy()) for c in canonical.FEATURE_NAMES}
    return arrays


def run_one(arr, start, end, *, label, traw, mraw, qcache, mcache, slip=0.0, capture_trace=False):
    if label == "D":
        return hbase.simulate(arr, start, end, candidate_h=False, extra_slippage_usd_per_side=slip, capture_trace=capture_trace)
    if label == "H":
        return hbase.simulate(arr, start, end, candidate_h=True, raw=mraw, feature_cache=mcache,
                              extra_slippage_usd_per_side=slip, capture_trace=capture_trace)
    if label == "J":
        return qflow.simulate_overlay(arr, start, end, variant="Candidate-J", tape_raw=traw,
                                      micro_raw=mraw, quote_cache=qcache, micro_cache=mcache,
                                      extra_slippage_usd_per_side=slip, capture_shadow_trace=capture_trace)
    raise ValueError(label)


def metric(m: Dict, key: str, default=0.0):
    return m[key] if key in m and m[key] is not None else default


def evaluate_block(block: Dict, combined: Path, interval: str) -> Dict:
    arr = build_features_all_rows(combined, interval)
    traw = tape.load_raw(combined)
    mraw = microstate.load_raw(combined)
    qcache: Dict = {}; mcache: Dict = {}
    start_ts = block["start"].timestamp(); end_ts = block["end"].timestamp()
    start = int(np.searchsorted(arr["t"], start_ts, side="left"))
    end = int(np.searchsorted(arr["t"], end_ts, side="right"))
    if end <= start:
        raise RuntimeError(f"empty sampled score window: {block['session']} {interval}")

    base = {}
    traces = {}
    for label in ("D","H","J"):
        m = run_one(arr,start,end,label=label,traw=traw,mraw=mraw,qcache=qcache,mcache=mcache,capture_trace=True)
        base[label]=m
        traces[label]=m
    parity = base["J"].get("shadow_trace") == base["D"].get("entry_trace")
    if not parity:
        raise RuntimeError(f"Candidate J baseline-shadow parity failed: {block['session']} {interval}")

    stress = {}
    for slip in STRESS:
        stress[slip] = {}
        for label in ("D","H","J"):
            stress[slip][label] = run_one(arr,start,end,label=label,traw=traw,mraw=mraw,qcache=qcache,mcache=mcache,slip=slip)

    row = {
        "session": block["session"], "interval": interval,
        "score_start_utc": block["start"].isoformat(), "score_end_utc": block["end"].isoformat(),
        "sampled_rows": end-start, "shadow_parity": parity,
    }
    for label in ("D","H","J"):
        m=base[label]
        row[f"{label}_pnl"] = float(metric(m,"terminal_equity_pnl_inr"))
        row[f"{label}_trades"] = int(metric(m,"trades",0))
        row[f"{label}_wins"] = int(metric(m,"wins",0))
        row[f"{label}_win_rate"] = float(metric(m,"win_rate",0.0))
        row[f"{label}_profit_factor"] = float(metric(m,"profit_factor",math.nan))
        row[f"{label}_max_drawdown"] = float(metric(m,"max_drawdown_inr",0.0))
    row["J_ge_D"] = row["J_pnl"] >= row["D_pnl"]
    row["J_positive"] = row["J_pnl"] > 0
    row["J_immediate_entries"] = int(metric(base["J"],"immediate_entries",0))
    row["J_delayed_entries"] = int(metric(base["J"],"delayed_entries",0))
    row["J_skipped_entries"] = int(metric(base["J"],"skipped_entries",0))
    row["J_phase_exits"] = int(metric(base["J"],"phase_exits",0))
    return row, stress


def aggregate(rows: List[Dict], interval: str, stress_by_block: Dict) -> Dict:
    r=[x for x in rows if x["interval"]==interval]
    if len(r)!=6: raise RuntimeError(f"expected 6 rows for {interval}, got {len(r)}")
    out={}
    for label in ("D","H","J"):
        pnl=np.asarray([x[f"{label}_pnl"] for x in r],float)
        trades=sum(int(x[f"{label}_trades"]) for x in r); wins=sum(int(x[f"{label}_wins"]) for x in r)
        out[label]={
            "pooled_pnl_inr":float(pnl.sum()), "mean_block_pnl_inr":float(pnl.mean()),
            "median_block_pnl_inr":float(np.median(pnl)), "p05_block_pnl_inr":float(np.quantile(pnl,.05)),
            "p95_block_pnl_inr":float(np.quantile(pnl,.95)), "positive_blocks":int((pnl>0).sum()),
            "positive_block_fraction":float((pnl>0).mean()), "aggregate_trades":trades,
            "aggregate_wins":wins, "aggregate_win_rate":float(wins/trades) if trades else 0.0,
        }
    out["J"]["blocks_ge_D"] = int(sum(bool(x["J_ge_D"]) for x in r))
    stress_summary={}
    for slip in STRESS:
        sr={}
        for label in ("D","H","J"):
            vals=[]
            for x in r:
                m=stress_by_block[(x["session"],interval)][slip][label]
                vals.append(float(metric(m,"terminal_equity_pnl_inr")))
            sr[label]={"pooled_pnl_inr":float(np.sum(vals)),"mean_block_pnl_inr":float(np.mean(vals))}
        stress_summary[f"{slip:.2f}"]=sr
    out["cost_stress"]=stress_summary
    return out


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("block_root",type=Path,help="data/prospective_4h directory")
    ap.add_argument("sessions",nargs=6,help="exact six Stage-1 session IDs in collection set")
    ap.add_argument("--output",type=Path,default=ROOT/"results"/"simulations"/"2026-10-06-v4_5-candidate-j-stage1-prospective")
    a=ap.parse_args()

    blocks=[inspect_block(a.block_root/s) for s in a.sessions]
    set_check=verify_set(blocks)
    a.output.mkdir(parents=True,exist_ok=True)
    integrity_rows=[]
    for b in sorted(blocks,key=lambda x:x["start"]):
        integrity_rows.append({
            "session":b["session"],"schema":b["schema"],"score_start_utc":b["start"].isoformat(),
            "score_end_utc":b["end"].isoformat(),"score_rows":b["score_rows"],
            "score_sha256":b["score_sha256"],"warmup_sha256":b["warmup_sha256"],
            "complete":True,"valid_for_stage1":True,
        })
    write_csv(a.output/"stage1_integrity.csv",integrity_rows)

    rows=[]; stress_by_block={}
    with tempfile.TemporaryDirectory(prefix="xau_stage1_") as td:
        td=Path(td)
        for b in sorted(blocks,key=lambda x:x["start"]):
            print(f"{b['session']}: preparing causal warmup + score",flush=True)
            combined=make_combined_csv(b,td)
            for interval in ("500ms","1s"):
                print(f"  {interval}: D/H/J",flush=True)
                row,stress=evaluate_block(b,combined,interval)
                rows.append(row); stress_by_block[(b["session"],interval)]=stress

    write_csv(a.output/"stage1_block_results.csv",rows)
    intervals={i:aggregate(rows,i,stress_by_block) for i in ("500ms","1s")}
    gates={}
    for interval,x in intervals.items():
        j=x["J"]; d=x["D"]
        j010=x["cost_stress"]["0.10"]["J"]["pooled_pnl_inr"]
        gates[interval]={
            "pooled_j_positive":j["pooled_pnl_inr"]>0,
            "pooled_j_ge_d":j["pooled_pnl_inr"]>=d["pooled_pnl_inr"],
            "mean_block_j_positive":j["mean_block_pnl_inr"]>0,
            "positive_blocks_ge_3_of_6":j["positive_blocks"]>=3,
            "j_ge_d_blocks_ge_4_of_6":j["blocks_ge_D"]>=4,
            "stress_0_10_j_nonnegative":j010>=0,
            "shadow_parity_all_blocks":all(bool(r["shadow_parity"]) for r in rows if r["interval"]==interval),
        }
    pass_all=all(all(v.values()) for v in gates.values())
    result={
        "schema":"xau-candidate-j-stage1-staged-validation-v1",
        "experiment":EXPERIMENT_REF,
        "candidate_j_source":"Experiment 47 frozen unchanged",
        "candidate_set":["D","H","J"],
        "integrity":set_check,
        "sessions":a.sessions,
        "external_data_used":False,"threshold_search":False,"final20_opened":False,
        "intervals":intervals,"predeclared_stage1_gate":gates,
        "stage1_pass":bool(pass_all),
        "decision":("PASS Stage 1; Candidate J remains frozen and advances to Stage 2."
                    if pass_all else
                    "FAIL Stage 1; reject this frozen Candidate J prospectively. Do not tune on these six blocks and relabel it unseen."),
    }
    (a.output/"summary.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
