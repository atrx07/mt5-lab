"""Contract tests for the read-only Jev Choice integration."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jev_lab import (  # noqa: E402
    JevTransportError,
    JevValidationError,
    build_choice_payload,
    evaluate_choice,
    request_sha256,
)


class _Response:
    def __init__(self, data: dict):
        self._stream = BytesIO(json.dumps(data).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._stream.close()

    def read(self, size: int) -> bytes:
        return self._stream.read(size)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.payload = build_choice_payload(
            {"market": "synthetic", "candidate": "buy"},
            "Is this candidate worth reviewing?",
            {"take": "Review this setup", "skip": "Do not act"},
        )
        self.valid_response = {
            "model": "jev-1.13.0",
            "answers": {
                "decision": {
                    "type": "choice",
                    "choice": "skip",
                    "probabilities": {"take": 0.25, "skip": 0.75},
                    "confidence": 0.5,
                }
            },
            "usage": {"input_tokens": 100, "output_tokens": 12},
        }

    def test_rejects_moving_model_alias_and_non_json_state(self):
        with self.assertRaises(JevValidationError):
            build_choice_payload({}, "question", {"a": None, "b": None}, model="jev-latest")
        with self.assertRaises(JevValidationError):
            build_choice_payload({}, "question", {"a": None, "b": None}, model="mock")
        with self.assertRaises(JevValidationError):
            build_choice_payload({"nan": float("nan")}, "question", {"a": None, "b": None})

    def test_send_validates_response_and_hashes_request(self):
        def fake_open(request, timeout):
            self.assertEqual(timeout, 0.5)
            self.assertEqual(request.get_header("Authorization"), "Bearer dummy")
            self.assertEqual(json.loads(request.data), self.payload)
            return _Response(self.valid_response)

        with patch("jev_lab.client.urlopen", side_effect=fake_open):
            result = evaluate_choice(self.payload, api_key="dummy", timeout_seconds=0.5)
        self.assertEqual(result.choice, "skip")
        self.assertEqual(result.request_sha256, request_sha256(self.payload))
        self.assertEqual(result.model, "jev-1.13.0")
        self.assertGreaterEqual(result.latency_ms, 0)

    def test_malformed_probability_fails_closed(self):
        bad = json.loads(json.dumps(self.valid_response))
        bad["answers"]["decision"]["probabilities"]["take"] = 1.5
        with patch("jev_lab.client.urlopen", return_value=_Response(bad)):
            with self.assertRaises(JevValidationError):
                evaluate_choice(self.payload, api_key="dummy")

    def test_unexpected_model_fails_closed(self):
        bad = json.loads(json.dumps(self.valid_response))
        bad["model"] = "jev-future"
        with patch("jev_lab.client.urlopen", return_value=_Response(bad)):
            with self.assertRaises(JevValidationError):
                evaluate_choice(self.payload, api_key="dummy")

    def test_transport_error_does_not_expose_key(self):
        with patch("jev_lab.client.urlopen", side_effect=TimeoutError("secret")):
            with self.assertRaises(JevTransportError) as error:
                evaluate_choice(self.payload, api_key="dont-print-me")
        self.assertNotIn("dont-print-me", str(error.exception))


if __name__ == "__main__":
    unittest.main()
