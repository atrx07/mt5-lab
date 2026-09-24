"""Experiment 21: independent, risk-budgeted XAUUSD research tickets.

This is an offline replay. It contains no broker connection or order submission.
The canonical feature builder and V4.4 golden gate are intentionally reused.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

import canonical_replay as canonical


OUT = Path(__file__).resolve().parents[1] / "results" / "simulations" / "2026-09-24-v4_5-multi-ticket-horizon"
REFERENCE_D = Path(__file__).resolve().parents[1] / "results" / "simulations" / "2026-09-24-v4_5-confirmed-failure" / "confirm_1s_metadata.json"
LEDGER_COLUMNS = [
    "entry_epoch_sec", "exit_epoch_sec", "side", "horizon", "entry_usd",
    "exit_usd", "oz", "pnl_inr", "hold_sec", "exit_reason", "peak_move_usd",
]
REASONS = {1: "emergency_stop", 2: "profit_confirmed", 3: "profit_target", 4: "max_hold", 5: "session_gap", 6: "segment_end"}
COMMON_CONFIG = {
    "max_tickets": 3,
    "per_ticket_entry_risk_fraction": 0.01,
    "aggregate_entry_risk_fraction": 0.03,
    "emergency_stop_usd": 4.0,
    "aggregate_leverage_cap": 100.0,
    "absolute_spread_cap_usd": 0.25,
    "minimum_mid_move_between_entries_usd": 0.8,
    "trend_entry_gap_sec": 180.0,
    "impulse_entry_gap_sec": 60.0,
    "cost_stress_per_side_usd": 0.20,
    "forced_liquidation": "first quote after session gap and last quote of each segment",
}
PROTOTYPES = {
    0: {
        "short_signal": "impulse momentum: r60>=4, er60>=0.12, qacc>=1.2, directional m120>=6, m30>=1.5, m10>=0.6, imb10>=0.2; short evaluated after trend",
        "trend_signal": "r300>=5, er60>=0.05, directional m1800>=8, m300>=3, m60>=0.5, m10>=0.2, recent opposite m10<=-0.4; 30min session warmup",
        "trend_slots": 2, "short_slots": 1,
        "trend_exit": "trigger 8, floor 4, giveback 2.5, target 13, max hold 3600 s",
        "short_exit": "trigger 5, floor 2, giveback 1.5, target 8, max hold 300 s",
    },
    1: {
        "short_signal": "impulse momentum: r60>=3, er60>=0.06, qacc>=0.85, directional m120>=4, m30>=1, m10>=0.35, imb10>=0.05; short evaluated first",
        "trend_signal": "r300>=5, er60>=0.05, directional m1800>=10, m300>=4, m60>=0.5, m10>=0.2, recent opposite m10<=-0.4; 30min session warmup",
        "trend_slots": 1, "short_slots": 2,
        "trend_exit": "trigger 6, floor 3, giveback 2.5, target 10, max hold 1800 s",
        "short_exit": "trigger 3, floor 1.2, giveback 1, target 5, max hold 180 s",
    },
    2: {
        "short_signal": "reversal: r60>=4, er60<=0.40, qacc<=1.0, opposite 10s momentum and imbalance after directional m60>=4 and m30>=2; short evaluated first",
        "trend_signal": "r300>=5, er60>=0.05, directional m1800>=10, m300>=4, m60>=0.5, m10>=0.2, recent opposite m10<=-0.4; 30min session warmup",
        "trend_slots": 1, "short_slots": 2,
        "trend_exit": "trigger 6, floor 3, giveback 2.5, target 10, max hold 1800 s",
        "short_exit": "trigger 3, floor 1.2, giveback 1, target 5, max hold 180 s",
    },
}


@njit(cache=True)
def simulate_multi(
    t, bid, ask, mid, spread, ss, imb, qacc, m10, m30, m60,
    m120, m300, m1800, r60, r300, er60, min10, max10, start, end,
    adverse_per_side, mode,
):
    # Three independent tickets, but one basket risk and one direction at a time.
    active = np.zeros(3, dtype=np.int8)
    sides = np.zeros(3, dtype=np.int8)
    kinds = np.zeros(3, dtype=np.int8)
    entries = np.zeros(3)
    ounces = np.zeros(3)
    entered = np.zeros(3)
    peaks = np.zeros(3)
    ledger = np.empty((20000, 11))
    balance = 500.0
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    ntrades = 0
    peak_equity = 500.0
    max_drawdown = 0.0
    exposure_sec = 0.0
    max_slots = 0
    last_trend = -1e30
    last_impulse = -1e30
    last_entry_mid = -1e30
    prior_session = -1
    session_start = t[start]

    for i in range(start, end):
        now = t[i]
        gap = prior_session >= 0 and ss[i] != prior_session
        if ss[i] != prior_session:
            session_start = now
            prior_session = ss[i]

        # Mark to executable bid/ask, not midpoint. Stops may gap past $4.
        equity = balance
        slots = 0
        for k in range(3):
            if active[k] == 1:
                slots += 1
                move = (bid[i] - adverse_per_side - entries[k]) if sides[k] == 1 else (entries[k] - ask[i] - adverse_per_side)
                equity += move * ounces[k] * canonical.INR_PER_USD
        if equity > peak_equity:
            peak_equity = equity
        dd = peak_equity - equity
        if dd > max_drawdown:
            max_drawdown = dd
        if slots > max_slots:
            max_slots = slots

        for k in range(3):
            if active[k] == 0:
                continue
            move = (bid[i] - adverse_per_side - entries[k]) if sides[k] == 1 else (entries[k] - ask[i] - adverse_per_side)
            held = now - entered[k]
            if move > peaks[k]:
                peaks[k] = move
            trend = kinds[k] == 1
            trigger = (6.0 if mode > 0 else 8.0) if trend else (3.0 if mode > 0 else 5.0)
            floor = (3.0 if mode > 0 else 4.0) if trend else (1.2 if mode > 0 else 2.0)
            giveback = 2.5 if trend else (1.0 if mode > 0 else 1.5)
            target = (10.0 if mode > 0 else 13.0) if trend else (5.0 if mode > 0 else 8.0)
            max_hold = (1800.0 if mode > 0 else 3600.0) if trend else (180.0 if mode > 0 else 300.0)
            reason = 0
            if move <= -4.0:
                reason = 1
            elif gap:
                reason = 5
            elif i == end - 1:
                reason = 6
            elif move >= target and held >= 3.0:
                reason = 3
            elif peaks[k] >= trigger and move >= floor and (
                peaks[k] - move >= giveback or
                (held >= 30.0 and not np.isnan(m10[i]) and sides[k] * m10[i] <= -0.5)
            ):
                reason = 2
            elif held >= max_hold:
                reason = 4
            if reason == 0:
                continue
            pnl = move * ounces[k] * canonical.INR_PER_USD
            balance += pnl
            exposure_sec += held
            if pnl > 0:
                gross_profit += pnl
                wins += 1
            elif pnl < 0:
                gross_loss -= pnl
            if ntrades >= len(ledger):
                raise RuntimeError("trade ledger capacity exceeded")
            ledger[ntrades, 0] = entered[k]
            ledger[ntrades, 1] = now
            ledger[ntrades, 2] = sides[k]
            ledger[ntrades, 3] = kinds[k]
            ledger[ntrades, 4] = entries[k]
            ledger[ntrades, 5] = bid[i] - adverse_per_side if sides[k] == 1 else ask[i] + adverse_per_side
            ledger[ntrades, 6] = ounces[k]
            ledger[ntrades, 7] = pnl
            ledger[ntrades, 8] = held
            ledger[ntrades, 9] = reason
            ledger[ntrades, 10] = peaks[k]
            ntrades += 1
            active[k] = 0

        if gap or i == end - 1 or balance <= 0 or spread[i] > 0.25:
            continue
        if np.isnan(m10[i]) or np.isnan(m30[i]) or np.isnan(m60[i]) or np.isnan(m120[i]):
            continue
        if np.isnan(r60[i]) or np.isnan(er60[i]):
            continue

        slots = 0
        trend_count = 0
        impulse_count = 0
        basket_side = 0
        open_oz = 0.0
        open_risk_inr = 0.0
        for k in range(3):
            if active[k] == 1:
                slots += 1
                basket_side = sides[k]
                open_oz += ounces[k]
                open_risk_inr += ounces[k] * 4.0 * canonical.INR_PER_USD
                if kinds[k] == 1:
                    trend_count += 1
                else:
                    impulse_count += 1
        if slots == 3:
            continue

        # Horizon is chosen at each admission using only features available now.
        kind = 0
        side = 0
        if mode == 1 and impulse_count < 2 and now - last_impulse >= 60.0:
            if r60[i] >= 3.0 and er60[i] >= 0.06 and qacc[i] >= 0.85:
                if m120[i] >= 4.0 and m30[i] >= 1.0 and m10[i] >= 0.35 and imb[i] >= 0.05:
                    kind = 2
                    side = 1
                elif m120[i] <= -4.0 and m30[i] <= -1.0 and m10[i] <= -0.35 and imb[i] <= -0.05:
                    kind = 2
                    side = -1
        if mode == 2 and impulse_count < 2 and now - last_impulse >= 60.0:
            if r60[i] >= 4.0 and er60[i] <= 0.40 and qacc[i] <= 1.0:
                if m60[i] >= 4.0 and m30[i] >= 2.0 and m10[i] <= -0.5 and imb[i] <= -0.1:
                    kind = 2
                    side = -1
                elif m60[i] <= -4.0 and m30[i] <= -2.0 and m10[i] >= 0.5 and imb[i] >= 0.1:
                    kind = 2
                    side = 1
        trend_limit = 1 if mode > 0 else 2
        if kind == 0 and (
            trend_count < trend_limit and now - last_trend >= 180.0 and
            now - session_start >= 1800.0 and
            not np.isnan(m1800[i]) and not np.isnan(m300[i]) and
            not np.isnan(min10[i]) and not np.isnan(max10[i]) and not np.isnan(r300[i]) and
            r300[i] >= 5.0 and er60[i] >= 0.05
        ):
            trend_30m = 10.0 if mode > 0 else 8.0
            trend_5m = 4.0 if mode > 0 else 3.0
            if m1800[i] >= trend_30m and m300[i] >= trend_5m and m60[i] >= 0.5 and m10[i] >= 0.2 and min10[i] <= -0.4:
                kind = 1
                side = 1
            elif m1800[i] <= -trend_30m and m300[i] <= -trend_5m and m60[i] <= -0.5 and m10[i] <= -0.2 and max10[i] >= 0.4:
                kind = 1
                side = -1
        if mode == 0 and kind == 0 and impulse_count < 1 and now - last_impulse >= 60.0:
            if r60[i] >= 4.0 and er60[i] >= 0.12 and qacc[i] >= 1.2:
                if m120[i] >= 6.0 and m30[i] >= 1.5 and m10[i] >= 0.6 and imb[i] >= 0.2:
                    kind = 2
                    side = 1
                elif m120[i] <= -6.0 and m30[i] <= -1.5 and m10[i] <= -0.6 and imb[i] <= -0.2:
                    kind = 2
                    side = -1
        if kind == 0 or (basket_side != 0 and side != basket_side):
            continue
        if abs(mid[i] - last_entry_mid) < 0.8:
            continue
        marked_equity = balance
        for k in range(3):
            if active[k] == 1:
                move = (bid[i] - adverse_per_side - entries[k]) if sides[k] == 1 else (entries[k] - ask[i] - adverse_per_side)
                marked_equity += move * ounces[k] * canonical.INR_PER_USD
        if marked_equity <= 0:
            continue
        entry_quote = ask[i] if side == 1 else bid[i]
        room_risk = max(0.0, 0.03 * marked_equity - open_risk_inr)
        room_notional_usd = max(0.0, 100.0 * marked_equity / canonical.INR_PER_USD - open_oz * mid[i])
        oz = min(0.01 * marked_equity / (4.0 * canonical.INR_PER_USD),
                 room_risk / (4.0 * canonical.INR_PER_USD),
                 room_notional_usd / entry_quote)
        if oz <= 0:
            continue
        for k in range(3):
            if active[k] == 0:
                active[k] = 1
                sides[k] = side
                kinds[k] = kind
                ounces[k] = oz
                entries[k] = entry_quote + adverse_per_side if side == 1 else entry_quote - adverse_per_side
                entered[k] = now
                peaks[k] = 0.0
                break
        if kind == 1:
            last_trend = now
        else:
            last_impulse = now
        last_entry_mid = mid[i]

    pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
    return balance - 500.0, pf, ntrades, wins, max_drawdown, exposure_sec, max_slots, ledger[:ntrades]


def summarize_grid(arrays, bounds, adverse_per_side=0.0, mode=0, segment_ids=(0, 1, 2, 3, 4)):
    args = [arrays[key] for key in [
        "t", "bid", "ask", "mid", "spread", "ss", "imb10", "qacc", "m10", "m30",
        "m60", "m120", "m300", "m1800", "range60", "range300", "er60", "min_m10_30", "max_m10_30",
    ]]
    segments = []
    ledgers = []
    for sid in segment_ids:
        start = int(np.searchsorted(arrays["t"], bounds[sid], "left"))
        end = int(np.searchsorted(arrays["t"], bounds[sid + 1], "left"))
        row = simulate_multi(*args, start, end, adverse_per_side, mode)
        segments.append({
            "segment_id": sid, "pnl_inr": float(row[0]), "profit_factor": float(row[1]),
            "trades": int(row[2]), "wins": int(row[3]),
            "max_marked_drawdown_inr": float(row[4]), "ticket_exposure_hours": float(row[5] / 3600.0),
            "peak_open_tickets": int(row[6]),
        })
        z = pd.DataFrame(row[7], columns=LEDGER_COLUMNS)
        z.insert(0, "segment_id", sid)
        ledgers.append(z)
    ledger = pd.concat(ledgers, ignore_index=True)
    ledger["entry_utc"] = pd.to_datetime(ledger.entry_epoch_sec, unit="s", utc=True)
    ledger["exit_utc"] = pd.to_datetime(ledger.exit_epoch_sec, unit="s", utc=True)
    ledger["exit_day_utc"] = ledger.exit_utc.dt.strftime("%Y-%m-%d")
    ledger["horizon"] = ledger.horizon.map({1.0: "trend", 2.0: "reversal" if mode == 2 else "impulse"})
    ledger["exit_reason"] = ledger.exit_reason.map(REASONS)
    reconstructed = np.where(
        ledger.side.to_numpy() == 1,
        ledger.exit_usd.to_numpy() - ledger.entry_usd.to_numpy(),
        ledger.entry_usd.to_numpy() - ledger.exit_usd.to_numpy(),
    ) * ledger.oz.to_numpy() * canonical.INR_PER_USD
    if not np.allclose(reconstructed, ledger.pnl_inr.to_numpy(), rtol=0, atol=1e-8):
        raise RuntimeError("ticket P&L differs from executable entry/exit quotes")
    if not np.isclose(ledger.pnl_inr.sum(), sum(s["pnl_inr"] for s in segments), rtol=0, atol=1e-8):
        raise RuntimeError("trade ledger and segment P&L differ")
    if (ledger.loc[ledger.exit_reason.isin(("profit_confirmed", "profit_target")), "pnl_inr"] <= 0).any():
        raise RuntimeError("profit-confirmed exit was not profitable after spread/cost")
    factor = 1.0
    for segment in segments:
        factor *= 1.0 + segment["pnl_inr"] / 500.0
    compounded = 500.0 * (factor - 1.0)
    daily = ledger.groupby("exit_day_utc", as_index=False).agg(pnl_inr=("pnl_inr", "sum"), trades=("pnl_inr", "size"))
    quote_days = set()
    for sid in segment_ids:
        start = int(np.searchsorted(arrays["t"], bounds[sid], "left"))
        end = int(np.searchsorted(arrays["t"], bounds[sid + 1], "left"))
        quote_days.update(pd.to_datetime(arrays["t"][start:end], unit="s", utc=True).strftime("%Y-%m-%d").unique())
    daily = daily.set_index("exit_day_utc").reindex(sorted(quote_days), fill_value=0).rename_axis("exit_day_utc").reset_index()
    summary = {
        "compounded_pnl_inr": compounded,
        "capture_ratio": compounded / canonical.OPPORTUNITY_CEILING_INR,
        "trades_sum": int(sum(s["trades"] for s in segments)),
        "wins_sum": int(sum(s["wins"] for s in segments)),
        "median_segment_pf": float(np.median([s["profit_factor"] for s in segments])),
        "max_segment_marked_drawdown_inr": max(s["max_marked_drawdown_inr"] for s in segments),
        "ticket_exposure_hours": sum(s["ticket_exposure_hours"] for s in segments),
        "pnl_per_ticket_exposure_hour_inr": compounded / sum(s["ticket_exposure_hours"] for s in segments) if segments else 0,
        "peak_open_tickets": max(s["peak_open_tickets"] for s in segments),
        "mean_hold_sec": float(ledger.hold_sec.mean()),
        "days_at_or_above_100_inr": int((daily.pnl_inr >= 100).sum()),
        "observed_quote_utc_days": int(len(daily)),
        "mean_realized_pnl_per_observed_quote_day_inr": float(daily.pnl_inr.mean()),
        "segments": segments,
    }
    return summary, ledger, daily


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--mode", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--seed-only", action="store_true")
    args = parser.parse_args()
    if args.mode in (1, 2) and not args.seed_only:
        parser.error("rejected prototypes 1 and 2 are seed-only research; use --seed-only")
    digest = canonical.verify_dataset(args.csv)
    reference = json.loads(REFERENCE_D.read_text(encoding="utf-8"))
    output = {
        "schema_version": canonical.SCHEMA_VERSION,
        "dataset_sha256": digest,
        "research_rows": canonical.RESEARCH_ROWS,
        "raw_boundaries": canonical.BOUND_RAW,
        "holdout_evaluated": False,
        "config": {"common": COMMON_CONFIG, "prototype": PROTOTYPES[args.mode]},
        "mode": args.mode,
        "segment_ids": [0] if args.seed_only else [0, 1, 2, 3, 4],
        "intervals": {},
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for interval in ("500ms", "1s"):
        arrays, bounds = canonical.build_features(args.csv, interval)
        baseline = canonical.run_strategy(arrays, bounds, "v4_4")
        canonical.assert_baseline(baseline, interval, canonical.DEFAULT_GOLDEN)
        print(interval, "V4.4 golden parity PASS", flush=True)
        segment_ids = (0,) if args.seed_only else (0, 1, 2, 3, 4)
        candidate, ledger, daily = summarize_grid(arrays, bounds, mode=args.mode, segment_ids=segment_ids)
        stressed, _, _ = summarize_grid(arrays, bounds, COMMON_CONFIG["cost_stress_per_side_usd"], mode=args.mode, segment_ids=segment_ids)
        prefix = f"prototype_{args.mode}_{'seed' if args.seed_only else 'full'}"
        ledger.to_csv(args.output / f"{prefix}_{interval}_trades.csv", index=False)
        daily.to_csv(args.output / f"{prefix}_{interval}_daily.csv", index=False)
        output["intervals"][interval] = {
            "v4_4": baseline,
            "candidate_d_reference": reference["intervals"][interval]["confirmed_failure"],
            "multi_ticket": candidate,
            "multi_ticket_cost_stress": stressed,
        }
        print(interval, "P&L", round(candidate["compounded_pnl_inr"], 2),
              "stressed", round(stressed["compounded_pnl_inr"], 2),
              "trades", candidate["trades_sum"], flush=True)
    (args.output / f"prototype_{args.mode}_{'seed' if args.seed_only else 'full'}_metadata.json").write_text(json.dumps(output, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
