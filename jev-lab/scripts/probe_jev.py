"""Validate a Choice request locally or send one explicit Jev API probe."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jev_lab import (  # noqa: E402
    DEFAULT_MODEL,
    JevClientError,
    build_choice_payload,
    evaluate_choice,
    request_sha256,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request_file", type=Path, help="JSON with state, instructions, criteria, and optional pinned model")
    parser.add_argument("--send", action="store_true", help="make one paid API call; default only validates locally")
    parser.add_argument("--timeout-seconds", type=float, default=2.0)
    args = parser.parse_args()

    try:
        specification = json.loads(args.request_file.read_text(encoding="utf-8"))
        if not isinstance(specification, dict) or set(specification) - {"state", "instructions", "criteria", "model"}:
            raise ValueError("request file must contain only state, instructions, criteria, and optional model")
        payload = build_choice_payload(
            specification["state"],
            specification["instructions"],
            specification["criteria"],
            model=specification.get("model", DEFAULT_MODEL),
        )
        if args.send:
            result = evaluate_choice(
                payload,
                api_key=os.environ.get("TYPESAFE_API_KEY", ""),
                timeout_seconds=args.timeout_seconds,
            )
            output = {"mode": "api_probe", **asdict(result)}
        else:
            output = {
                "mode": "local_validation",
                "model": payload["model"],
                "options": list(payload["questions"]["decision"]["criteria"]),
                "request_sha256": request_sha256(payload),
            }
        print(json.dumps(output, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, JevClientError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
