"""Export development-only Jev entry requests without calling the model."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jev_lab.client import build_choice_payload, request_sha256  # noqa: E402
from jev_lab.paper import parse_bars, run_paper  # noqa: E402
from jev_lab.shadow import candidate_state  # noqa: E402


def main() -> int:
    experiment_id = "2026-09-24-01-jev-entry-shadow"
    try:
        shadow_config = json.loads((ROOT / "configs" / f"{experiment_id}.json").read_text(encoding="utf-8"))
        baseline_id = shadow_config["source_experiment_id"]
        baseline_config = json.loads((ROOT / "configs" / f"{baseline_id}.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "data/manifests" / f"{baseline_id}.json").read_text(encoding="utf-8"))
        prior = json.loads((ROOT / "results/backtests" / baseline_id / "summary.json").read_text(encoding="utf-8"))
        raw = (ROOT / manifest["raw_path"]).read_bytes()
        data_hash = sha256(raw).hexdigest()
        if data_hash != manifest["raw_sha256"] or data_hash != shadow_config["dataset_sha256"] or data_hash != prior["dataset_sha256"]:
            raise ValueError("raw data does not match every frozen source hash")
        source = json.loads(raw)
        rows = source["rows"]
        if len(rows) != manifest["row_count"] or source["symbol"] != baseline_config["market_data"]["symbol"] or source["interval"] != baseline_config["market_data"]["interval"]:
            raise ValueError("source metadata differs from frozen manifest or baseline")
        split = [0, int(len(rows) * baseline_config["split"]["development_end_fraction"]), int(len(rows) * baseline_config["split"]["evaluation_end_fraction"]), len(rows)]
        if (shadow_config["development_rows"] != split[:2]
                or shadow_config["evaluation_rows_reserved"] != split[1:3]
                or shadow_config["final_holdout_rows_sealed"] != split[2:]
                or not baseline_config["split"]["final_holdout_stays_sealed"]):
            raise ValueError("shadow split does not match the frozen baseline")

        # Only development rows are parsed or passed to feature construction.
        bars = parse_bars(rows[:split[1]], source["interval"])
        account = baseline_config["paper_account"]
        rule = baseline_config["baseline"]
        records = []

        def capture(index, history):
            state = candidate_state(
                history,
                symbol=source["symbol"],
                source=baseline_config["market_data"]["source"],
                interval=source["interval"],
                breakout_bars=rule["entry_prior_high_bars"],
                sma_bars=rule["trend_sma_bars"],
                fee_bps=account["taker_fee_bps_per_side"],
                penalty_bps=account["additional_execution_penalty_bps_per_side"],
            )
            question = shadow_config["question"]
            payload = build_choice_payload(state, question["instructions"], question["criteria"], model=shadow_config["model"])
            records.append({"signal_row": index, "request_sha256": request_sha256(payload), "payload": payload})

        summary, trades = run_paper(
            bars,
            mode="rule",
            starting_usdt=account["starting_usdt"],
            allocation_fraction=account["max_position_fraction"],
            fee_bps=account["taker_fee_bps_per_side"],
            penalty_bps=account["additional_execution_penalty_bps_per_side"],
            breakout_bars=rule["entry_prior_high_bars"],
            sma_bars=rule["trend_sma_bars"],
            max_hold_bars=rule["max_hold_bars"],
            on_candidate=capture,
        )
        expected = prior["summaries"]["development"][f"penalty_{int(account['additional_execution_penalty_bps_per_side'])}bps"]["rule"]
        if summary != expected or len(records) != len(trades) or len(records) != expected["trades"]:
            raise ValueError("baseline parity or one-request-per-entry check failed")

        derived_path = ROOT / "data/derived" / f"{experiment_id}.jsonl"
        output_dir = ROOT / "results/benchmarks" / experiment_id
        if derived_path.exists() or output_dir.exists():
            raise FileExistsError("shadow export or result already exists; preserve the original run")
        content = b"".join((json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8") for record in records)
        digest = sha256(content).hexdigest()
        derived_path.write_bytes(content)
        output_dir.mkdir(parents=True)
        (output_dir / "config.json").write_text(json.dumps(shadow_config, indent=2) + "\n", encoding="utf-8")
        result = {
            "schema_version": "jev-lab-shadow-result-v1",
            "experiment_id": experiment_id,
            "source_experiment_id": baseline_id,
            "source_dataset_sha256": data_hash,
            "development_rows": shadow_config["development_rows"],
            "candidate_count": len(records),
            "candidate_jsonl_path": derived_path.relative_to(ROOT).as_posix(),
            "candidate_jsonl_sha256": digest,
            "baseline_parity": {"matched_entire_development_rule_summary": True, "net_pnl_usdt": summary["net_pnl_usdt"], "trades": summary["trades"]},
            "model_calls": 0,
            "evaluation_rows_inspected": False,
            "holdout_rows_inspected": False,
            "execution_mode": "offline shadow request export",
        }
        (output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        (output_dir / "README.md").write_text(
            f"# {experiment_id} result\n\n"
            f"Reproduce from the local raw capture: `python scripts/export_jev_shadow.py`. The capture must match SHA-256 `{data_hash}`. "
            f"This command preserves an existing export; remove or archive it intentionally before rerunning.\n\n"
            f"Development only: {len(records)} baseline entry candidates, one local Choice request each. The ignored JSONL has SHA-256 `{digest}`. "
            f"The entire frozen development rule summary matched Experiment 00, including {summary['net_pnl_usdt']:.2f} USDT net P&L and {summary['trades']} trades.\n\n"
            "No Jev API call, response, trade decision, or live order was made. Evaluation and final holdout rows were not passed to bar parsing, feature construction, or replay. "
            "This validates request construction only and supplies no evidence of Jev trading value.\n",
            encoding="utf-8",
        )
        print(json.dumps({"candidate_count": len(records), "candidate_jsonl_sha256": digest, "baseline_parity": True, "model_calls": 0}, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
