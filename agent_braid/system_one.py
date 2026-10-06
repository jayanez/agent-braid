# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded, immutable synthetic decision contracts; no execution authority."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import re
import threading
from time import monotonic_ns
from types import MappingProxyType
from typing import Any, Callable

VERSION = "decision-stdlib-v1"
MAX_BYTES = 1048576
BACKEND_ID = "stdlib-rule-fixture-v1"
CAPABILITY_ID = "synthetic-reference-v1"
CONTEXT_VERSION = "synthetic-v1"
STRICT_POLICY = "strict-uncalibrated-v1"
DIAGNOSTIC_POLICY = "synthetic-diagnostic-v1"
HASH = re.compile(r"[0-9a-f]{64}\Z")
REASONS = frozenset({"invalid-envelope", "unsupported-identity", "state-digest-mismatch",
    "input-budget-exceeded", "render-budget-exceeded", "invalid-backend-output",
    "calibration-absent", "fixture-mapping-missing", "overloaded", "cancelled",
    "deadline-exceeded", "backend-closed"})


class InvalidDecision(ValueError):
    """Sanitized contract failure containing a fixed reason code only."""
    def __init__(self, reason: str = "invalid-envelope"):
        self.reason = reason
        super().__init__(reason)


def freeze(value: Any) -> Any:
    """Recursively copy JSON containers into immutable records."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(child) for child in value)
    return value


def thaw(value: Any) -> Any:
    """Return independent mutable JSON containers."""
    if isinstance(value, Mapping):
        return {key: thaw(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [thaw(child) for child in value]
    return value


def canonical(value: Any) -> bytes:
    return json.dumps(thaw(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical(value)).hexdigest()


def _keys(value: Any, keys: set[str]) -> None:
    if type(value) is not dict or set(value) != keys:
        raise InvalidDecision()


def _text(value: Any, maximum: int, *, identifier: bool = False) -> None:
    if type(value) is not str or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise InvalidDecision()
    if len(value.encode("utf-8")) > maximum:
        raise InvalidDecision()
    if identifier and (not value or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value)):
        raise InvalidDecision()


def _finite(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def parse_json(raw: bytes) -> dict:
    """Bounded UTF-8 finite JSON with pre-parse depth and duplicate checks."""
    if type(raw) is not bytes:
        raise InvalidDecision()
    if len(raw) > MAX_BYTES:
        raise InvalidDecision("input-budget-exceeded")
    try:
        text = raw.decode("utf-8")
        quoted = escaped = False
        depth = 0
        for char in text:
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                depth += 1
                if depth > 16:
                    raise InvalidDecision()
            elif char in "]}":
                depth -= 1
                if depth < 0:
                    raise InvalidDecision()
        def members(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise InvalidDecision()
                result[key] = value
            return result
        def integer(token):
            if len(token.lstrip("-")) > 20:
                raise InvalidDecision()
            number = int(token)
            if not -(2 ** 63) <= number < 2 ** 63:
                raise InvalidDecision()
            return number
        def floating(token):
            number = float(token)
            if not math.isfinite(number):
                raise InvalidDecision()
            return number
        def constant(_token):
            raise InvalidDecision()
        value = json.loads(text, object_pairs_hook=members, parse_int=integer,
                           parse_float=floating, parse_constant=constant)
        if type(value) is not dict:
            raise InvalidDecision()
        # JSON accepts escaped lone surrogates: reject throughout, including keys.
        stack = [value]
        while stack:
            item = stack.pop()
            if type(item) is dict:
                stack.extend(item.keys())
                stack.extend(item.values())
            elif type(item) is list:
                stack.extend(item)
            elif type(item) is str:
                _text(item, MAX_BYTES)
        return value
    except (UnicodeError, ValueError, RecursionError, OverflowError) as exc:
        if isinstance(exc, InvalidDecision):
            raise
        raise InvalidDecision() from None


@dataclass(frozen=True)
class Option:
    id: str
    description: str
    value: int | float | None = None


@dataclass(frozen=True)
class Question:
    id: str
    type: str
    instructions: str
    options: tuple[Option, ...]


@dataclass(frozen=True)
class Budgets:
    max_input_bytes: int
    max_questions: int
    max_options: int
    max_tokens: int
    deadline_ms: int


@dataclass(frozen=True)
class DecisionRequest:
    envelope: Mapping
    questions: tuple[Question, ...]
    budgets: Budgets
    canonical_bytes: bytes
    input_bytes: int
    render_tokens: int
    render_ms: float

    @property
    def state(self) -> Mapping:
        return self.envelope["state"]

    def to_dict(self) -> dict:
        return thaw(self.envelope)


@dataclass(frozen=True)
class DecisionResponse:
    envelope: Mapping

    def to_dict(self) -> dict:
        return thaw(self.envelope)


def validate_request(raw: bytes, *, clock: Callable[[], int] = monotonic_ns) -> DecisionRequest:
    """Validate every field/budget before backend admission, returning frozen data."""
    value = parse_json(raw)
    _keys(value, {"contractVersion", "requestId", "state", "stateDigest", "questions",
                  "capabilityId", "contextVersion", "backendId", "policyId", "budgets"})
    for key in ("requestId", "capabilityId", "contextVersion", "backendId", "policyId"):
        _text(value[key], 64, identifier=True)
    if (value["contractVersion"] != VERSION or value["capabilityId"] != CAPABILITY_ID
            or value["contextVersion"] != CONTEXT_VERSION or value["backendId"] != BACKEND_ID
            or value["policyId"] not in (STRICT_POLICY, DIAGNOSTIC_POLICY)):
        raise InvalidDecision("unsupported-identity")
    limits = {"maxInputBytes": (1, MAX_BYTES), "maxQuestions": (1, 32),
              "maxOptions": (2, 32), "maxTokens": (1, MAX_BYTES), "deadlineMs": (1, 5000)}
    _keys(value["budgets"], set(limits))
    for key, (minimum, maximum) in limits.items():
        item = value["budgets"][key]
        if type(item) is not int or not minimum <= item <= maximum:
            raise InvalidDecision()
    budget = value["budgets"]
    if len(raw) > budget["maxInputBytes"]:
        raise InvalidDecision("input-budget-exceeded")
    questions = value["questions"]
    if type(questions) is not list or not 1 <= len(questions) <= budget["maxQuestions"]:
        raise InvalidDecision()
    records = []
    question_ids = set()
    for question in questions:
        _keys(question, {"id", "type", "instructions", "options"})
        _text(question["id"], 64, identifier=True)
        _text(question["instructions"], 4096)
        if question["id"] in question_ids or question["type"] not in ("boolean", "choice", "score"):
            raise InvalidDecision()
        question_ids.add(question["id"])
        options = question["options"]
        if type(options) is not list or not 2 <= len(options) <= budget["maxOptions"]:
            raise InvalidDecision()
        option_records = []
        option_ids = set()
        previous = None
        for option in options:
            _keys(option, {"id", "description", "value"} if question["type"] == "score" else {"id", "description"})
            _text(option["id"], 64, identifier=True)
            _text(option["description"], 4096)
            if option["id"] in option_ids:
                raise InvalidDecision()
            option_ids.add(option["id"])
            score = option.get("value")
            if question["type"] == "score":
                if not _finite(score) or abs(score) > 1000000 or (previous is not None and score <= previous):
                    raise InvalidDecision()
                previous = score
            option_records.append(Option(option["id"], option["description"], score))
        if question["type"] == "boolean" and [option.id for option in option_records] != ["false", "true"]:
            raise InvalidDecision()
        records.append(Question(question["id"], question["type"], question["instructions"], tuple(option_records)))
    _keys(value["state"], {"sourceKind", "ruleAnswers"})
    if value["state"]["sourceKind"] != "synthetic" or type(value["state"]["ruleAnswers"]) is not dict:
        raise InvalidDecision()
    allowed = {question.id: {option.id for option in question.options} for question in records}
    for key, item in value["state"]["ruleAnswers"].items():
        if key not in allowed or type(item) is not str or item not in allowed[key]:
            raise InvalidDecision()
    if (type(value["stateDigest"]) is not str or HASH.fullmatch(value["stateDigest"]) is None
            or digest(value["state"]) != value["stateDigest"]):
        raise InvalidDecision("state-digest-mismatch")
    start = clock()
    rendered = canonical(value)
    tokens = len(rendered.decode("utf-8"))
    if len(rendered) > budget["maxInputBytes"]:
        raise InvalidDecision("input-budget-exceeded")
    if tokens > budget["maxTokens"]:
        raise InvalidDecision("render-budget-exceeded")
    return DecisionRequest(freeze(value), tuple(records), Budgets(*(budget[key] for key in limits)),
                           rendered, len(raw), tokens, max(0.0, (clock() - start) / 1000000))


def build_answers(request: DecisionRequest, distributions: Any) -> list[dict]:
    """Validate complete backend masses and derive all readouts independently."""
    if not isinstance(distributions, (list, tuple)) or len(distributions) != len(request.questions):
        raise InvalidDecision("invalid-backend-output")
    result = []
    for question, masses in zip(request.questions, distributions):
        if (not isinstance(masses, (list, tuple)) or len(masses) != len(question.options)
                or any(not _finite(mass) or mass < 0 or mass > 1 for mass in masses)
                or abs(math.fsum(masses) - 1) > 1e-6):
            raise InvalidDecision("invalid-backend-output")
        probabilities = tuple(float(mass) for mass in masses)
        top = max(probabilities)
        chosen = min((option for option, mass in zip(question.options, probabilities) if mass == top), key=lambda option: option.id)
        entropy = -math.fsum(mass * math.log(mass) for mass in probabilities if mass)
        result.append({"questionId": question.id, "type": question.type,
            "distribution": [{"optionId": option.id, "probability": mass} for option, mass in zip(question.options, probabilities)],
            "choiceId": chosen.id, "pTrue": probabilities[1] if question.type == "boolean" else None,
            "expectedScore": math.fsum(option.value * mass for option, mass in zip(question.options, probabilities)) if question.type == "score" else None,
            "argmaxScore": chosen.value if question.type == "score" else None,
            "rawTopProbability": top, "concentration": {"formula": "normalized-entropy-v1", "value": min(1.0, max(0.0, 1 - entropy / math.log(len(probabilities))))}})
    return result


MODEL_MANIFEST = freeze({"backendId": BACKEND_ID, "version": VERSION, "capability": CAPABILITY_ID,
                         "numericRepresentation": "binary64", "tokenUnit": "character-token-v1", "calibration": "absent"})


def policy_manifest(policy_id: str) -> Mapping:
    if policy_id not in (STRICT_POLICY, DIAGNOSTIC_POLICY):
        raise InvalidDecision("unsupported-identity")
    return freeze({"policyId": policy_id, "version": VERSION, "executionAuthorization": False,
                   "calibrationRequired": policy_id == STRICT_POLICY})


def make_response(request: DecisionRequest | None, *, status: str, reasons: list[str],
                  answers: list[dict] | None = None, usage: dict) -> DecisionResponse:
    envelope = request.envelope if request is not None else {}
    value = {"contractVersion": VERSION, "requestId": envelope.get("requestId"),
        "requestDigest": digest(envelope) if request is not None else None,
        "stateDigest": envelope.get("stateDigest"),
        "questionsDigest": digest(envelope["questions"]) if request is not None else None,
        "backendId": envelope.get("backendId"), "capabilityId": envelope.get("capabilityId"),
        "capabilityVersion": CAPABILITY_ID, "contextVersion": envelope.get("contextVersion"),
        "policyId": envelope.get("policyId"), "status": status, "answers": answers if answers is not None else [],
        "calibrationStatus": "absent", "reasonCodes": reasons, "inputCoverage": 1.0 if status == "answered" else 0.0,
        "usage": usage, "modelManifestDigest": digest(MODEL_MANIFEST) if request is not None else None,
        "calibrationManifestDigest": None,
        "policyDigest": digest(policy_manifest(envelope["policyId"])) if request is not None else None,
        "evidenceClass": "heuristic", "executionAuthorization": False}
    value["responseDigest"] = digest(value)
    return validate_response(value, request=request)


def validate_response(value: Any, *, request: DecisionRequest | None) -> DecisionResponse:
    """Check authority, provenance, status and recomputed readouts before consumption."""
    try:
        _keys(value, {"contractVersion", "requestId", "requestDigest", "stateDigest", "questionsDigest", "backendId",
            "capabilityId", "capabilityVersion", "contextVersion", "policyId", "status", "answers", "calibrationStatus",
            "reasonCodes", "inputCoverage", "usage", "modelManifestDigest", "calibrationManifestDigest", "policyDigest",
            "evidenceClass", "executionAuthorization", "responseDigest"})
        if (value["contractVersion"] != VERSION or value["capabilityVersion"] != CAPABILITY_ID
                or value["executionAuthorization"] is not False or value["evidenceClass"] != "heuristic"
                or value["calibrationStatus"] != "absent" or value["calibrationManifestDigest"] is not None):
            raise InvalidDecision()
        if value["responseDigest"] != digest({key: item for key, item in value.items() if key != "responseDigest"}):
            raise InvalidDecision()
        identity_fields = ("requestId", "stateDigest", "backendId", "capabilityId", "contextVersion", "policyId")
        if request is None:
            if value["status"] != "refused" or any(value[field] is not None for field in identity_fields + ("requestDigest", "questionsDigest", "modelManifestDigest", "policyDigest")):
                raise InvalidDecision()
        else:
            if (any(value[field] != request.envelope[field] for field in identity_fields)
                    or value["requestDigest"] != digest(request.envelope)
                    or value["questionsDigest"] != digest(request.envelope["questions"])
                    or value["modelManifestDigest"] != digest(MODEL_MANIFEST)
                    or value["policyDigest"] != digest(policy_manifest(request.envelope["policyId"]))):
                raise InvalidDecision()
        status = value["status"]
        reasons = value["reasonCodes"]
        if type(reasons) is not list or any(type(reason) is not str or reason not in REASONS for reason in reasons):
            raise InvalidDecision()
        if status not in ("answered", "abstain", "defer", "refused") or type(value["answers"]) is not list or not _finite(value["inputCoverage"]):
            raise InvalidDecision()
        if status == "answered":
            if (request is None or request.envelope["policyId"] != DIAGNOSTIC_POLICY or reasons or value["inputCoverage"] != 1
                    or len(value["answers"]) != len(request.questions)):
                raise InvalidDecision()
            distributions = []
            for answer, question in zip(value["answers"], request.questions):
                _keys(answer, {"questionId", "type", "distribution", "choiceId", "pTrue", "expectedScore", "argmaxScore", "rawTopProbability", "concentration"})
                if type(answer["distribution"]) is not list or len(answer["distribution"]) != len(question.options):
                    raise InvalidDecision()
                masses = []
                for item, option in zip(answer["distribution"], question.options):
                    _keys(item, {"optionId", "probability"})
                    if item["optionId"] != option.id:
                        raise InvalidDecision()
                    masses.append(item["probability"])
                for field in ("pTrue", "expectedScore", "argmaxScore", "rawTopProbability"):
                    if answer[field] is not None and not _finite(answer[field]):
                        raise InvalidDecision()
                _keys(answer["concentration"], {"formula", "value"})
                if not _finite(answer["concentration"]["value"]):
                    raise InvalidDecision()
                distributions.append(masses)
            if value["answers"] != build_answers(request, distributions):
                raise InvalidDecision()
        elif value["answers"] or value["inputCoverage"] != 0 or not reasons:
            raise InvalidDecision()
        status_reasons = {"abstain": {"calibration-absent", "fixture-mapping-missing"},
                          "defer": {"overloaded", "cancelled", "deadline-exceeded", "backend-closed"},
                          "refused": REASONS - {"calibration-absent", "fixture-mapping-missing", "overloaded", "cancelled", "deadline-exceeded", "backend-closed"}}
        if status != "answered" and any(reason not in status_reasons[status] for reason in reasons):
            raise InvalidDecision()
        _keys(value["usage"], {"queueMs", "loadMs", "renderMs", "inferenceMs", "totalMs", "inputBytes", "renderTokens"})
        for field, item in value["usage"].items():
            if field in ("inputBytes", "renderTokens"):
                if type(item) is not int or item < 0:
                    raise InvalidDecision()
            elif not _finite(item) or item < 0:
                raise InvalidDecision()
        if request is not None and (value["usage"]["inputBytes"] != request.input_bytes or value["usage"]["renderTokens"] != request.render_tokens):
            raise InvalidDecision()
        return DecisionResponse(freeze(value))
    except (InvalidDecision, ValueError, TypeError, OverflowError, UnicodeError, KeyError):
        raise InvalidDecision("invalid-backend-output") from None


class CancellationToken:
    """Request-local irreversible cancellation and atomic publication boundary."""
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cancelled = False
        self._in_use = False
        self._wakers: set[Callable[[], None]] = set()

    def claim(self) -> None:
        """Prevent a caller from sharing live cancellation across requests."""
        with self._lock:
            if self._in_use:
                raise ValueError("cancellation token already belongs to an active request")
            self._in_use = True

    def release(self) -> None:
        with self._lock:
            self._in_use = False

    def cancel(self) -> None:
        with self._lock:
            self._cancelled = True
            wakers = tuple(self._wakers)
        for wake in wakers:
            wake()

    @property
    def cancelled(self) -> bool:
        with self._lock:
            return self._cancelled

    def add_waker(self, wake: Callable[[], None]) -> Callable[[], None]:
        with self._lock:
            self._wakers.add(wake)
        def remove() -> None:
            with self._lock:
                self._wakers.discard(wake)
        return remove

    def publish(self, factory: Callable[[bool], Any]) -> Any:
        """Cancellation before this locked call wins; delivered responses are final."""
        with self._lock:
            return factory(self._cancelled)


def evaluate(raw: bytes, *, cancellation: CancellationToken | None = None) -> dict:
    """Evaluate one materialized-byte request with an isolated reference runtime.

    Use an explicit DecisionRuntime instance for bounded concurrent admission.
    """
    from agent_braid.system_one_backends import DecisionRuntime
    with DecisionRuntime() as runtime:
        return runtime.evaluate(raw, cancellation=cancellation)
