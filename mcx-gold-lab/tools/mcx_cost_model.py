#!/usr/bin/env python3
"""MCX gold futures — capital-efficiency / cost model (mcx-gold-lab Experiment 0).

Gate-0 tool. Answers BEFORE any strategy code runs:
  1. What does one round trip cost per contract?
  2. What margin must be posted per lot?
  3. For a given account size and risk rule, which contracts are tradable?
  4. What per-trade expectancy must a strategy clear just to beat costs?

This model optimizes the CONTAINER (costs, margins, contract choice).
It cannot manufacture EDGE. A strategy that loses money gross loses money
faster here; the model only tells you where the drag is smallest.

Cost schedule (Zerodha-published MCX schedule, verified 2026-10-08):
  brokerage  Rs 20 / executed order (or 0.03% of turnover, whichever lower)
  CTT        0.01% on SELL turnover (non-agri commodity)
  exch txn   0.0021% on turnover
  stamp      0.002% on BUY turnover
  SEBI       Rs 10 / crore of turnover
  GST        18% on (brokerage + txn + SEBI)

Contract specs (MCX circulars; Gold Guinea tick marked VERIFY against live):
  GOLDPETAL   1 g / lot,  tick Rs 1 per lot,  margin 6% + 1% ELM
  GOLDGUINEA  8 g / lot,  tick Rs 1 per lot,  margin 6% + 1% ELM  (tick: verify live)
  GOLDM     100 g / lot,  tick Rs 10 per lot, margin 6% + 1% ELM  (scale-up reference)

Usage:
  python tools/mcx_cost_model.py [--gold-inr-per-gram 15125] [--save results/cost_model/exp0.json]
  (default 15125 = MCX GOLDPETAL bhavcopy close on 2026-10-06; pass a fresh
  close to re-price the container as gold moves)
"""

import argparse
import json
import math
import os
import sys

# ----------------------------------------------------------------------------
# Inputs
# ----------------------------------------------------------------------------

COST = dict(
    brokerage_flat=20.0,      # Rs per executed order
    brokerage_pct=0.0003,     # 0.03%, whichever lower
    ctt_sell=0.0001,          # 0.01% on sell turnover
    txn=0.000021,             # 0.0021% on turnover
    stamp_buy=0.00002,        # 0.002% on buy turnover
    sebi_per_crore=10.0,      # Rs 10 / crore
    gst=0.18,                 # 18% on (brokerage + txn + SEBI)
)

MARGIN_PCT = 0.07  # 6% initial + 1% extreme loss margin (minimum; SPAN may be higher)

CONTRACTS = {
    # name: (grams_per_lot, tick_rs_per_lot, tick_note)
    "GOLDPETAL":  (1,   1.0,  "Rs 1 / 1 g lot  (MCX circular)"),
    "GOLDGUINEA": (8,   1.0,  "Rs 1 / 8 g lot  (VERIFY against live feed)"),
    "GOLDM":      (100, 10.0, "Rs 1 / 10 g  => Rs 10 / 100 g lot (scale-up ref)"),
}

ACCOUNT_SIZES = [10_000, 25_000, 50_000, 100_000]
RISK_PCT = 0.03          # per-trade risk rule (same as xau-lab V4.4)
STOP_TICKS = 100         # reference stop distance for sizing math


# ----------------------------------------------------------------------------
# Cost engine
# ----------------------------------------------------------------------------

def order_cost(turnover: float, side: str) -> dict:
    """Cost of ONE executed order (one side)."""
    brokerage = min(COST["brokerage_flat"], COST["brokerage_pct"] * turnover)
    ctt = COST["ctt_sell"] * turnover if side == "sell" else 0.0
    txn = COST["txn"] * turnover
    stamp = COST["stamp_buy"] * turnover if side == "buy" else 0.0
    sebi = COST["sebi_per_crore"] * turnover / 10_000_000
    gst = COST["gst"] * (brokerage + txn + sebi)
    total = brokerage + ctt + txn + stamp + sebi + gst
    return dict(brokerage=brokerage, ctt=ctt, txn=txn, stamp=stamp,
                sebi=sebi, gst=gst, total=total)


def roundtrip_cost(notional_per_lot: float) -> dict:
    """Cost of one round trip (buy 1 lot + sell 1 lot)."""
    buy = order_cost(notional_per_lot, "buy")
    sell = order_cost(notional_per_lot, "sell")
    total = buy["total"] + sell["total"]
    return dict(buy=buy, sell=sell, total=total)


# ----------------------------------------------------------------------------
# Capital-efficiency table
# ----------------------------------------------------------------------------

def analyze(gold_inr_per_gram: float) -> dict:
    contracts = {}
    for name, (grams, tick_rs, tick_note) in CONTRACTS.items():
        notional = grams * gold_inr_per_gram
        margin = MARGIN_PCT * notional
        rt = roundtrip_cost(notional)
        cost_pct_notion = rt["total"] / notional * 100
        contracts[name] = dict(
            grams_per_lot=grams, tick_rs_per_lot=tick_rs, tick_note=tick_note,
            notional_per_lot=round(notional, 2),
            margin_per_lot=round(margin, 2),
            roundtrip_cost=round(rt["total"], 2),
            cost_breakdown={k: round(v["total"], 2) for k, v in
                            (("buy", rt["buy"]), ("sell", rt["sell"]))},
            cost_pct_of_notional=round(cost_pct_notion, 4),
            # ticks of gross profit needed to cover costs alone:
            breakeven_ticks=round(rt["total"] / tick_rs, 1),
        )

    accounts = {}
    for acct in ACCOUNT_SIZES:
        rows = {}
        for name, c in contracts.items():
            margin_lots = math.floor(acct / c["margin_per_lot"])
            # risk sizing: lots such that STOP_TICKS * tick_value <= RISK_PCT * account
            risk_lots = math.floor(acct * RISK_PCT / (STOP_TICKS * CONTRACTS[name][1]))
            tradable_lots = min(margin_lots, risk_lots)
            # cost drag if you did 5 round trips/day on 1 lot:
            drag_5rt = 5 * c["roundtrip_cost"] / acct * 100
            rows[name] = dict(
                lots_by_margin=margin_lots,
                lots_by_risk=max(risk_lots, 0),
                tradable_lots=max(tradable_lots, 0),
                cost_drag_5rt_per_day_pct=round(drag_5rt, 3),
                # expectancy a strategy must average per trade to beat costs:
                breakeven_expectancy_rs=round(c["roundtrip_cost"], 2),
            )
        accounts[str(acct)] = rows

    return dict(
        gold_inr_per_gram=gold_inr_per_gram,
        cost_schedule="Zerodha MCX schedule, verified 2026-10-08",
        margin_rule="6% initial + 1% ELM (minimum; SPAN may exceed)",
        risk_rule=f"{RISK_PCT*100:.0f}% per trade, {STOP_TICKS}-tick reference stop",
        contracts=contracts,
        accounts=accounts,
    )


def render_text(r: dict) -> str:
    L = []
    L.append("=" * 72)
    L.append("MCX GOLD — CAPITAL-EFFICIENCY MODEL  (Experiment 0)")
    L.append(f"Gold assumed Rs {r['gold_inr_per_gram']:,.0f} / gram | {r['margin_rule']}")
    L.append("=" * 72)
    L.append("")
    L.append("PER-CONTRACT ECONOMICS (1 lot, 1 round trip):")
    L.append(f"{'contract':<12}{'notional':>12}{'margin':>10}{'RT cost':>10}"
             f"{'cost%':>9}{'breakeven':>11}")
    L.append(f"{'':<12}{'Rs':>12}{'Rs':>10}{'Rs':>10}{'of not.':>9}{'ticks':>11}")
    L.append("-" * 72)
    for name, c in r["contracts"].items():
        L.append(f"{name:<12}{c['notional_per_lot']:>12,.0f}{c['margin_per_lot']:>10,.0f}"
                 f"{c['roundtrip_cost']:>10.2f}{c['cost_pct_of_notional']:>8.3f}%"
                 f"{c['breakeven_ticks']:>10.1f}")
    L.append("")
    L.append("Cost breakdown per round trip (Rs):")
    for name, c in r["contracts"].items():
        b = c["cost_breakdown"]
        L.append(f"  {name:<12} buy {b['buy']:.2f} + sell {b['sell']:.2f} = {c['roundtrip_cost']:.2f}")
    L.append("")
    L.append(f"ACCOUNT FIT  (risk rule {r['risk_rule']}):")
    for acct, rows in r["accounts"].items():
        L.append(f"  Rs {int(acct):>6,} account:")
        for name, row in rows.items():
            flag = "TRADABLE" if row["tradable_lots"] > 0 else "---"
            L.append(f"    {name:<12} lots(margin)={row['lots_by_margin']:>4}  "
                     f"lots(risk)={row['lots_by_risk']:>4}  => {row['tradable_lots']:>3} [{flag}]  "
                     f"5 RT/day drag={row['cost_drag_5rt_per_day_pct']:.2f}%  "
                     f"breakeven/trade=Rs {row['breakeven_expectancy_rs']:.2f}")
    L.append("")
    L.append("READING THE TABLE:")
    L.append("- 'breakeven ticks' is the gross profit a trade must average BEFORE it")
    L.append("  earns a single rupee. Everything below that line is cost donation.")
    L.append("- Costs are NOT the binding constraint on MCX (compare crypto's 31.2%")
    L.append("  tax bleed). The binding constraints are: (1) whether any edge exists")
    L.append("  at all, (2) the bid/ask SPREAD — at Rs 1 ticks a Rs 2-3 spread costs")
    L.append("  Rs 2-4 per round trip per lot, i.e. 20-40% on top of the fee schedule")
    L.append("  above. Model spread explicitly; it is part of the strategy.")
    L.append("- Petal wins on absolute minimum capital (tradable from ~Rs 5-10k);")
    L.append("  Guinea becomes the efficiency sweet spot above ~Rs 25k (lower cost")
    L.append("  drag per rupee of exposure, fewer tickets for the same size).")
    L.append("- This model prices the CONTAINER. It says nothing about whether any")
    L.append("  strategy has edge. A negative-expectancy strategy loses FASTER here.")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-inr-per-gram", type=float, default=15125.0,
                    help="default = MCX GOLDPETAL bhavcopy close 2026-10-06")
    ap.add_argument("--save", type=str, default="")
    a = ap.parse_args()
    r = analyze(a.gold_inr_per_gram)
    print(render_text(r))
    if a.save:
        os.makedirs(os.path.dirname(a.save) or ".", exist_ok=True)
        with open(a.save, "w") as f:
            json.dump(r, f, indent=2)
        print(f"\nsaved -> {a.save}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
