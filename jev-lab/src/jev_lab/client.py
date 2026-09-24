"""Small, pinned-model TypeSafe Choice client for research and shadow decisions.

This module does not create signals, calculate risk, or place orders. Callers own
their market-data snapshot and may treat any exception as NO_DECISION.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from json import JSONDecodeError
import json
import math
import re
from time import perf_counter
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-1.13.0"
MAX_RESPONSE_BYTES = 1_000_000


class JevClientError(Exception):
    """Base class for Jev request failures."""


class JevTransportError(JevClientError):
    """The service was unavailable or missed the caller's deadline."""


class JevValidationError(JevClientError):
    """The request or response did not satisfy the frozen contract."""


@dataclass(frozen=True)
class ChoiceResult:
    choice: str
    probabilities: dict[str, float]
    confidence: float
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    request_sha256: str


def build_choice_payload(
    state: Any,
    instructions: str,
    criteria: Mapping[str, str | None],
    *,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    """Validate and build one typed Choice request with a pinned model ID."""
    if state is None:
        raise JevValidationError("state is required")
    if not isinstance(instructions, str) or not instructions.strip():
        raise JevValidationError("instructions must be a nonempty string")
    if not isinstance(model, str) or re.fullmatch(r"jev-\d+\.\d+\.\d+", model) is None:
        raise JevValidationError("use a versioned Jev model ID, such as jev-1.13.0")
    if not isinstance(criteria, Mapping) or not 2 <= len(criteria) <= 255:
        raise JevValidationError("criteria must have 2 to 255 options")
    for label, description in criteria.items():
        if not isinstance(label, str) or not label.strip():
            raise JevValidationError("each option label must be a nonempty string")
        if description is not None and not isinstance(description, str):
            raise JevValidationError("option descriptions must be strings or null")

    payload = {
        "model": model,
        "state": state,
        "questions": {
            "decision": {
                "type": "choice",
                "instructions": instructions,
                "criteria": dict(criteria),
            }
        },
    }
    _canonical_bytes(payload)
    return payload


def request_sha256(payload: Mapping[str, Any]) -> str:
    """Hash the full request without logging its potentially sensitive state."""
    return sha256(_canonical_bytes(payload)).hexdigest()


def evaluate_choice(
    payload: Mapping[str, Any],
    *,
    api_key: str,
    timeout_seconds: float = 2.0,
) -> ChoiceResult:
    """Make one API request, with no automatic retries or trading side effects."""
    if not isinstance(api_key, str) or not api_key.strip():
        raise JevValidationError("TYPESAFE_API_KEY is required for a live API call")
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise JevValidationError("timeout_seconds must be positive and finite")

    model, option_labels = _request_contract(payload)
    body = _canonical_bytes(payload)
    digest = sha256(body).hexdigest()
    request = Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    start = perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise JevTransportError(f"TypeSafe HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise JevTransportError(f"TypeSafe request failed: {type(exc).__name__}") from None
    latency_ms = (perf_counter() - start) * 1_000

    if len(raw) > MAX_RESPONSE_BYTES:
        raise JevValidationError("response exceeds size limit")
    try:
        parsed = json.loads(raw)
    except (JSONDecodeError, UnicodeDecodeError):
        raise JevValidationError("response is not valid JSON") from None
    return _parse_choice(parsed, model, option_labels, latency_ms, digest)


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise JevValidationError("request must contain finite JSON values") from exc


def _request_contract(payload: Mapping[str, Any]) -> tuple[str, set[str]]:
    if not isinstance(payload, Mapping):
        raise JevValidationError("request must be an object")
    try:
        model = payload["model"]
        question = payload["questions"]["decision"]
        criteria = question["criteria"]
        instructions = question["instructions"]
        state = payload["state"]
    except (KeyError, TypeError):
        raise JevValidationError("request is missing the Choice contract") from None
    validated = build_choice_payload(state, instructions, criteria, model=model)
    if dict(payload) != validated:
        raise JevValidationError("request must contain exactly one supported Choice question")
    return model, set(criteria)


def _parse_choice(
    response: Any,
    expected_model: str,
    option_labels: set[str],
    latency_ms: float,
    digest: str,
) -> ChoiceResult:
    try:
        if not isinstance(response, dict):
            raise TypeError
        model = response["model"]
        answer = response["answers"]["decision"]
        usage = response["usage"]
        choice = answer["choice"]
        probabilities = answer["probabilities"]
        confidence = answer["confidence"]
        input_tokens = usage["input_tokens"]
        output_tokens = usage["output_tokens"]
    except (KeyError, TypeError):
        raise JevValidationError("response is missing required Choice fields") from None

    if model != expected_model:
        raise JevValidationError("response model differs from pinned request model")
    if answer.get("type") != "choice" or choice not in option_labels:
        raise JevValidationError("response has an invalid choice")
    if not isinstance(probabilities, dict) or set(probabilities) != option_labels:
        raise JevValidationError("response probabilities do not match request options")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 1
        for value in probabilities.values()
    ):
        raise JevValidationError("response probabilities must be finite values in [0, 1]")
    if not math.isclose(sum(probabilities.values()), 1.0, abs_tol=0.01):
        raise JevValidationError("response probabilities do not sum to 1")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise JevValidationError("response confidence is invalid")
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (input_tokens, output_tokens)):
        raise JevValidationError("response usage is invalid")
    return ChoiceResult(
        choice=choice,
        probabilities={key: float(value) for key, value in probabilities.items()},
        confidence=float(confidence),
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        request_sha256=digest,
    )
