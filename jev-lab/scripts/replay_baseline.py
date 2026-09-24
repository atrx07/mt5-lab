"""Run frozen first-80% BTC/USDT paper comparisons; leave holdout sealed."""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jev_lab.paper import parse_bars, run_paper  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/2026-09-24-00-btc-spot-baseline.json")
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        experiment_id = config["experiment_id"]
        manifest_path = ROOT / "data/manifests" / f"{experiment_id}.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_path = ROOT / manifest["raw_path"]
        raw_bytes = raw_path.read_bytes()
        if sha256(raw_bytes).hexdigest() != manifest["raw_sha256"]:
            raise ValueError("dataset SHA-256 differs from frozen manifest")
        source = json.loads(raw_bytes)
        rows = source["rows"]
        if len(rows) != manifest["row_count"] or source["symbol"] != config["market_data"]["symbol"] or source["interval"] != config["market_data"]["interval"]:
            raise ValueError("dataset metadata differs from frozen config or manifest")
        n = len(rows)
        seed_end = int(n * config["split"]["development_end_fraction"])
        eval_end = int(n * config["split"]["evaluation_end_fraction"])
        if not 0 < seed_end < eval_end < n or not config["split"]["final_holdout_stays_sealed"]:
            raise ValueError("invalid or unsealed split")
        # Parse only the first 80%. The last 20% is not passed into any strategy.
        bars = parse_bars(rows[:eval_end], source["interval"])
        slices = {"development": bars[:seed_end], "evaluation": bars[seed_end:eval_end]}
        account = config["paper_account"]
        rule = config["baseline"]
        summaries = {}
        main_trades = []
        for segment_name, segment_bars in slices.items():
            comparisons = {}
            for penalty in (0.0, 5.0, 10.0):
                label = f"penalty_{int(penalty)}bps"
                comparisons[label] = {}
                for mode in ("rule", "buy_hold", "no_trade"):
                    summary, trades = run_paper(
                        segment_bars,
                        mode=mode,
                        starting_usdt=account["starting_usdt"],
                        allocation_fraction=account["max_position_fraction"],
                        fee_bps=account["taker_fee_bps_per_side"],
                        penalty_bps=penalty,
                        breakout_bars=rule["entry_prior_high_bars"],
                        sma_bars=rule["trend_sma_bars"],
                        max_hold_bars=rule["max_hold_bars"],
                    )
                    comparisons[label][mode] = summary
                    if penalty == account["additional_execution_penalty_bps_per_side"] and mode == "rule":
                        main_trades.extend({"segment": segment_name, **trade} for trade in trades)
            summaries[segment_name] = comparisons

        output_dir = ROOT / "results/backtests" / experiment_id
        if output_dir.exists():
            raise FileExistsError("result bundle already exists; preserve the original run")
        output_dir.mkdir(parents=True)
        effective = {**config, "dataset_sha256": manifest["raw_sha256"], "dataset_manifest": manifest_path.relative_to(ROOT).as_posix(), "raw_row_count": n, "split_rows": [0, seed_end, eval_end, n]}
        (output_dir / "config.json").write_text(json.dumps(effective, indent=2) + "\n", encoding="utf-8")
        result = {
            "schema_version": "jev-lab-paper-result-v1",
            "experiment_id": experiment_id,
            "dataset_sha256": manifest["raw_sha256"],
            "split_rows": [0, seed_end, eval_end, n],
            "holdout_evaluated": False,
            "execution_mode": "historical candle paper replay",
            "summaries": summaries,
        }
        (output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        with (output_dir / "trades.csv").open("w", newline="", encoding="utf-8") as handle:
            fields = ["segment", "entry_open_ms", "exit_open_ms", "entry_price", "exit_price", "quantity_btc", "entry_fee_usdt", "exit_fee_usdt", "net_pnl_usdt", "hold_bars", "exit_reason"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(main_trades)
        primary = summaries["evaluation"]["penalty_5bps"]
        note = (
            f"# {experiment_id} result\n\n"
            f"Dataset: `{manifest_path.relative_to(ROOT).as_posix()}` (SHA-256 `{manifest['raw_sha256']}`).\n"
            f"Reproduce: `python scripts/replay_baseline.py --config configs/{experiment_id}.json` after restoring the raw capture.\n\n"
            f"Evaluation at 10 bp fee + 5 bp adverse penalty per side: rule {primary['rule']['net_pnl_usdt']:+.2f} USDT "
            f"({primary['rule']['trades']} trades); buy-and-hold {primary['buy_hold']['net_pnl_usdt']:+.2f} USDT; no trade 0.00 USDT.\n\n"
            "Candle-only historical paper replay. Spread and actual fills are not observed; the penalty is assumed. "
            "The final 20% was not evaluated. This run cannot establish a live trading edge.\n"
        )
        (output_dir / "README.md").write_text(note, encoding="utf-8")
        print(json.dumps({"experiment_id": experiment_id, "development_rule_pnl_usdt": summaries["development"]["penalty_5bps"]["rule"]["net_pnl_usdt"], "evaluation_rule_pnl_usdt": primary["rule"]["net_pnl_usdt"], "evaluation_trades": primary["rule"]["trades"], "holdout_evaluated": False}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
