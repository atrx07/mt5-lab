"""Experiment 44: MT5 tick-tape field audit.

Representation-only audit of archived MqlTick fields that previous microstate
features did not use: last, volume, volume_real and flags. No P&L labels are
loaded and no strategy decision is changed.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

import canonical_replay as canonical
import v4_5_regime_portability as portability

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATLAS = ROOT / "results" / "simulations" / "2026-09-25-v4_5-independent-opportunity-atlas" / "shadow_opportunities.csv"
DEFAULT_OUT = ROOT / "results" / "simulations" / "2026-09-26-v4_5-tick-tape-field-audit"

FLAG_BID = 2
FLAG_ASK = 4
FLAG_LAST = 8
FLAG_VOLUME = 16
FLAG_BUY = 32
FLAG_SELL = 64

FEATURES = (
    "bid_update_frac2","ask_update_frac2","both_update_frac2","bid_ask_update_imb2",
    "bid_update_frac10","ask_update_frac10","both_update_frac10","bid_ask_update_imb10",
    "trade_count2","trade_count10","trade_quote_ratio2","trade_quote_ratio10",
    "buy_trade_count2","sell_trade_count2","dir_trade_count_imb2",
    "buy_trade_count10","sell_trade_count10","dir_trade_count_imb10",
    "buy_volume2","sell_volume2","dir_trade_volume_imb2",
    "buy_volume10","sell_volume10","dir_trade_volume_imb10",
    "last_move2","last_move10","dir_last_move2","dir_last_move10",
)


def epoch_seconds(series):
    return series.to_numpy(dtype="datetime64[ns]").astype(np.int64) / 1e9


def load_raw(path: Path, nrows=None):
    cols = ["timestamp_utc","bid","ask","last","volume","flags","volume_real"]
    df = pd.read_csv(path, nrows=nrows, usecols=cols)
    df["t"] = pd.to_datetime(df.timestamp_utc, utc=True, format="mixed")
    df = df.sort_values("t", kind="stable").reset_index(drop=True)
    t = epoch_seconds(df.t)
    gap = np.r_[True, np.diff(t) > 5.0]
    start = np.empty(len(df), dtype=np.int64)
    cur = 0
    for i in range(len(df)):
        if gap[i]:
            cur = i
        start[i] = cur
    return {
        "t": t,
        "bid": pd.to_numeric(df.bid, errors="coerce").to_numpy(float),
        "ask": pd.to_numeric(df.ask, errors="coerce").to_numpy(float),
        "last": pd.to_numeric(df["last"], errors="coerce").to_numpy(float),
        "volume": pd.to_numeric(df.volume, errors="coerce").to_numpy(float),
        "volume_real": pd.to_numeric(df.volume_real, errors="coerce").to_numpy(float),
        "flags": pd.to_numeric(df.flags, errors="coerce").fillna(0).to_numpy(np.int64),
        "session_start": start,
    }


def write_csv(path: Path, rows: List[Dict]):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def safe_ratio(a, b):
    return float(a / b) if np.isfinite(a) and np.isfinite(b) and abs(b) > 1e-12 else 0.0


def window(raw, j: int, seconds: float):
    t = raw["t"]
    ss = int(raw["session_start"][j])
    lo = max(ss, int(np.searchsorted(t, float(t[j]) - seconds, side="left")))
    return lo, j + 1


def tape_window(raw, a: int, b: int, side: int, seconds: int):
    flags = raw["flags"][a:b]
    bid = (flags & FLAG_BID) != 0
    ask = (flags & FLAG_ASK) != 0
    both = bid & ask
    last_flag = (flags & FLAG_LAST) != 0
    vol_flag = (flags & FLAG_VOLUME) != 0
    buy = (flags & FLAG_BUY) != 0
    sell = (flags & FLAG_SELL) != 0
    trade = last_flag | vol_flag | buy | sell

    n = len(flags)
    quote = bid | ask
    bid_n = int(bid.sum()); ask_n = int(ask.sum()); both_n = int(both.sum())
    quote_n = int(quote.sum()); trade_n = int(trade.sum())
    buy_n = int(buy.sum()); sell_n = int(sell.sum())

    vr = raw["volume_real"][a:b]
    vi = raw["volume"][a:b]
    vv = np.where(np.isfinite(vr) & (vr > 0), vr, np.where(np.isfinite(vi), vi, 0.0))
    buy_vol = float(vv[buy].sum()) if n else 0.0
    sell_vol = float(vv[sell].sum()) if n else 0.0

    last = raw["last"][a:b]
    actual_last = last[last_flag & np.isfinite(last) & (last > 0)]
    last_move = float(actual_last[-1] - actual_last[0]) if len(actual_last) >= 2 else 0.0

    denom_updates = bid_n + ask_n
    trade_count_imb = safe_ratio(buy_n - sell_n, buy_n + sell_n)
    trade_vol_imb = safe_ratio(buy_vol - sell_vol, buy_vol + sell_vol)

    return {
        f"bid_update_frac{seconds}": bid_n / n if n else 0.0,
        f"ask_update_frac{seconds}": ask_n / n if n else 0.0,
        f"both_update_frac{seconds}": both_n / n if n else 0.0,
        f"bid_ask_update_imb{seconds}": safe_ratio(bid_n - ask_n, denom_updates),
        f"trade_count{seconds}": float(trade_n),
        f"trade_quote_ratio{seconds}": safe_ratio(trade_n, quote_n),
        f"buy_trade_count{seconds}": float(buy_n),
        f"sell_trade_count{seconds}": float(sell_n),
        f"dir_trade_count_imb{seconds}": float(side) * trade_count_imb,
        f"buy_volume{seconds}": buy_vol,
        f"sell_volume{seconds}": sell_vol,
        f"dir_trade_volume_imb{seconds}": float(side) * trade_vol_imb,
        f"last_move{seconds}": last_move,
        f"dir_last_move{seconds}": float(side) * last_move,
    }


def features_at(raw, ts: float, side: int):
    t = raw["t"]
    j = int(np.searchsorted(t, float(ts), side="right") - 1)
    if j < 0:
        return {k: math.nan for k in FEATURES}
    out = {}
    for sec in (2, 10):
        a, b = window(raw, j, float(sec))
        out.update(tape_window(raw, a, b, side, sec))
    return {k: out.get(k, 0.0) for k in FEATURES}


def support_stats(raw, window_name: str):
    f = raw["flags"]
    last = raw["last"]; vol = raw["volume"]; vr = raw["volume_real"]
    bits = {
        "bid": FLAG_BID, "ask": FLAG_ASK, "last": FLAG_LAST,
        "volume": FLAG_VOLUME, "buy": FLAG_BUY, "sell": FLAG_SELL,
    }
    row = {
        "window": window_name,
        "rows": int(len(f)),
        "unique_flags": int(len(np.unique(f))),
        "last_nonzero_fraction": float(np.mean(np.isfinite(last) & (last > 0))),
        "volume_nonzero_fraction": float(np.mean(np.isfinite(vol) & (vol > 0))),
        "volume_real_nonzero_fraction": float(np.mean(np.isfinite(vr) & (vr > 0))),
    }
    for name, bit in bits.items():
        row[f"flag_{name}_fraction"] = float(np.mean((f & bit) != 0))
        row[f"flag_{name}_count"] = int(np.sum((f & bit) != 0))
    row["trade_flag_fraction"] = float(np.mean((f & (FLAG_LAST|FLAG_VOLUME|FLAG_BUY|FLAG_SELL)) != 0))
    return row


def match_rows(rows, max_delta: float):
    a = sorted([r for r in rows if r["interval"] == "500ms"], key=lambda x: float(x["entry_ts"]))
    b = sorted([r for r in rows if r["interval"] == "1s"], key=lambda x: float(x["entry_ts"]))
    used = set(); out = []
    for x in a:
        best = None
        for j, y in enumerate(b):
            if j in used:
                continue
            if y["window"] != x["window"] or y["engine"] != x["engine"] or y["side"] != x["side"]:
                continue
            dt = abs(float(y["entry_ts"]) - float(x["entry_ts"]))
            if dt > max_delta:
                continue
            if best is None or dt < best[0]:
                best = (dt, j, y)
        if best is None:
            continue
        dt, j, y = best
        used.add(j)
        z = {
            "window": x["window"], "engine": x["engine"], "side": x["side"],
            "entry_500ms": x["entry_ts"], "entry_1s": y["entry_ts"], "abs_delta_sec": dt,
        }
        for feat in FEATURES:
            z[f"{feat}_500ms"] = x[feat]
            z[f"{feat}_1s"] = y[feat]
        out.append(z)
    return out


def spearman(a, b):
    x = pd.DataFrame({"a": a, "b": b}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(x) < 3:
        return math.nan
    return float(x.a.rank(method="average").corr(x.b.rank(method="average")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("canonical_csv", type=Path)
    ap.add_argument("recent_csv_or_gz", type=Path)
    ap.add_argument("--atlas", type=Path, default=DEFAULT_ATLAS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    canonical.verify_dataset(a.canonical_csv)
    portability.verify_recent(a.recent_csv_or_gz)
    a.output.mkdir(parents=True, exist_ok=True)

    atlas = pd.read_csv(a.atlas)
    atlas = atlas[atlas.censored.astype(str).str.lower().eq("false")].copy()
    atlas = atlas[["window","interval","segment_id","engine","side","side_sign","entry_ts"]]

    print("loading full MT5 tape fields", flush=True)
    h = load_raw(a.canonical_csv, nrows=canonical.RESEARCH_ROWS)
    r = load_raw(a.recent_csv_or_gz)
    support = [support_stats(h, "historical7d"), support_stats(r, "recent24h")]

    rows = []
    for rec in atlas.to_dict("records"):
        raw = h if rec["window"] == "historical7d" else r
        z = dict(rec)
        z.update(features_at(raw, float(rec["entry_ts"]), int(rec["side_sign"])))
        rows.append(z)

    strict = match_rows(rows, 10.0)
    broad = match_rows(rows, 120.0)
    stability = []
    for label, pairs in (("strict_10s", strict), ("broad_120s", broad)):
        p = pd.DataFrame(pairs)
        for window in ("historical7d","recent24h"):
            q = p[p.window == window] if not p.empty else p
            for feat in FEATURES:
                stability.append({
                    "match_set": label, "window": window, "feature": feat,
                    "pairs": len(q),
                    "spearman": spearman(q.get(f"{feat}_500ms"), q.get(f"{feat}_1s")) if len(q) else math.nan,
                })

    write_csv(a.output / "field_support.csv", support)
    write_csv(a.output / "tape_opportunities.csv", rows)
    write_csv(a.output / "cross_grid_strict_matches.csv", strict)
    write_csv(a.output / "cross_grid_broad_matches.csv", broad)
    write_csv(a.output / "cross_grid_stability.csv", stability)

    sdf = pd.DataFrame(stability)
    strict_df = sdf[sdf.match_set == "strict_10s"]
    result = {
        "schema": "xau-tick-tape-audit-v1",
        "strategy_changed": False,
        "outcome_labels_used": False,
        "selection_performed": False,
        "flag_constants": {
            "BID": FLAG_BID, "ASK": FLAG_ASK, "LAST": FLAG_LAST,
            "VOLUME": FLAG_VOLUME, "BUY": FLAG_BUY, "SELL": FLAG_SELL,
        },
        "features": list(FEATURES),
        "field_support": support,
        "rows": len(rows),
        "strict_matches": len(strict),
        "broad_matches": len(broad),
        "strict_median_spearman_by_window": {
            w: float(pd.to_numeric(strict_df[strict_df.window == w].spearman, errors="coerce").median())
            for w in ("historical7d","recent24h")
        },
        "final20_opened": False,
        "decision": "Representation audit only. Promote no entry/exit rule from this result.",
    }
    (a.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
