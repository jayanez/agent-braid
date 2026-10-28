# SPDX-License-Identifier: AGPL-3.0-only
"""Independent outcome verifiers and adjudication records; offline, deterministic, no authority.

Deterministic oracles implement the SPEC-048 ``OutcomeVerifier`` handoff: a fixture
oracle checks the expected outputs and a serial-reference oracle requires exactly the
files an independent serial run wrote. Grading reads only committed outputs: a
commitment binds unit, source, candidate, observation and the hashes of exactly the
files the observed attempt created or modified; any other bytes are refused. Candidate
files such as a forged ``score.json`` are compared as outputs, never read as acceptance.

Oracle, blinded human and model-proxy results stay in separate sections and are never
blended. Human labels need at least two distinct blind annotators; any disagreement
stays unresolved until an independent adjudication record covers every non-abstaining
label, and a majority is not a consensus. Abstentions, failed attempts and inconclusive
oracles are recorded as missing labels.

Held-out records are refused by ``selection_view``, which derives the partition from the
registered units rather than from a record field, and ``check_context`` refuses
held-out grader bytes or identity hashes (any case) in context keys or values. It does
not detect encoded or paraphrased material. A record's ``sha256`` is the digest of its
data and consumers check its exact shape, but records prove binding, not authenticity:
human, proxy and adjudication records are self-asserted documents, and deletions are
not compared by the serial oracle. ``executionAuthorization`` is always false.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from hashlib import sha256
import re
from types import MappingProxyType
from typing import Any

from .harness_host_codex import OutcomeVerifier, VerifierRequest
from .harness_observation import MAX_ARTIFACT_BYTES, MAX_ARTIFACTS, Observation, _is_relative
from .system_one import canonical, digest, freeze, thaw

COMMITMENT_FORMAT = "braid-harness-commitment/v0.1"
LABEL_FORMAT = "braid-harness-label/v0.1"
ADJUDICATION_FORMAT = "braid-harness-adjudication/v0.1"
UNIT_FORMAT = "braid-harness-unit-verdict/v0.1"
PARTITIONS = ("discovery", "holdout")
VERDICTS = ("pass", "fail")
MIN_ANNOTATORS = 2  # frozen protocol D5
MAX_LABELS = 16
MAX_SCORE_MICROS = 1_000_000
MAX_TICK = 1 << 40
MAX_RECORD_BYTES = 1_048_576
MIN_LEAK_BYTES = 16  # shorter material is matched only as a whole context key or value
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_BINDING = {"unitId", "unitSha256", "partition", "sourceSha256", "candidateSha256",
            "commitmentSha256"}
_KEYS = {
    COMMITMENT_FORMAT: {"format", "unitId", "unitSha256", "partition", "sourceSha256",
                        "candidateSha256", "observationSha256", "attemptId", "manifestSha256",
                        "terminal", "outputs", "outputsSha256", "committedAt",
                        "executionAuthorization"},
    (LABEL_FORMAT, "human"): {"format", "provenance", *_BINDING, "annotator", "verdict", "blind",
                              "rubricSha256"},
    (LABEL_FORMAT, "proxy"): {"format", "provenance", *_BINDING, "model", "scoreMicros",
                              "countsAsCorrectness"},
    ADJUDICATION_FORMAT: {"format", *_BINDING, "adjudicator", "verdict", "rationaleSha256",
                          "labelSha256s"},
    UNIT_FORMAT: {"format", *_BINDING, "rubricSha256", "terminal", "oracle", "human", "proxy",
                  "crossProvenanceDisagreement", "missingLabels", "executionAuthorization"},
}


class VerificationError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-verification"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-verification") -> None:
    if not condition:
        raise VerificationError(reason)


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _id(value: Any) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _outputs(value: Any, reason: str = "invalid-outputs") -> dict[str, bytes]:
    _require(isinstance(value, Mapping) and len(value) <= MAX_ARTIFACTS, reason)
    _require(all(_is_relative(p) and type(c) is bytes and len(c) <= MAX_ARTIFACT_BYTES
                 for p, c in value.items()), reason)
    return dict(value)


def _hashes(outputs: Mapping[str, bytes]) -> dict[str, str]:
    return {path: sha256(content).hexdigest() for path, content in sorted(outputs.items())}


# --- deterministic oracles ------------------------------------------------------------


class _Oracle(OutcomeVerifier):
    """Holds grader material privately; renders only its kind and identity hash."""

    kind = ""

    def __init__(self, material: Mapping[str, bytes], extra: Mapping[str, str]):
        material = _outputs(material, "invalid-grader-material")
        _require(bool(material), "invalid-grader-material")
        self._material = MappingProxyType(material)
        self._identity = digest({"kind": self.kind, "outputs": _hashes(material), **extra})
        hexes = (self._identity, *extra.values(), *_hashes(material).values())
        self._hexes = tuple(h.encode() for h in hexes)

    @property
    def sha256(self) -> str:
        return self._identity

    def _leaks_into(self, value: bytes) -> bool:
        """Whether ``value`` carries this oracle's material or identifying hashes."""
        lowered = value.lower()
        return any(h in lowered for h in self._hexes) or any(
            (c in value) if len(c) >= MIN_LEAK_BYTES else c == value
            for c in self._material.values())

    def verify(self, request: VerifierRequest) -> str:
        if not isinstance(request, VerifierRequest) or not isinstance(request.artifacts, Mapping):
            return "inconclusive"
        return "pass" if self._accepts(request.artifacts) else "fail"

    def _accepts(self, artifacts: Mapping[str, bytes]) -> bool:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{type(self).__name__}(sha256={self._identity})"


class FixtureOracle(_Oracle):
    """Fixture correctness: every expected output is present with exact bytes."""

    kind = "fixture-correctness"

    def __init__(self, expected: Mapping[str, bytes]):
        super().__init__(expected, {})

    def _accepts(self, artifacts: Mapping[str, bytes]) -> bool:
        return all(artifacts.get(path) == content for path, content in self._material.items())


class SerialReferenceOracle(_Oracle):
    """Serial/effect reference: the committed writes equal the serial run's exactly."""

    kind = "serial-reference"

    def __init__(self, reference: Mapping[str, bytes], *, reference_observation_sha256: str):
        _require(_hash(reference_observation_sha256), "invalid-grader-material")
        super().__init__(reference, {"referenceObservationSha256": reference_observation_sha256})

    def _accepts(self, artifacts: Mapping[str, bytes]) -> bool:
        return dict(artifacts) == dict(self._material)


_ORACLE_TYPES = (FixtureOracle, SerialReferenceOracle)


# --- units and records ------------------------------------------------------------------


@dataclass(frozen=True)
class Unit:
    """One registered evaluation unit with its frozen rubric and label sources."""

    unit_id: str
    partition: str
    source_sha256: str
    rubric_sha256: str
    oracles: tuple[FixtureOracle | SerialReferenceOracle, ...]
    human_required: bool

    def __post_init__(self):
        _require(_id(self.unit_id) and self.partition in PARTITIONS
                 and _hash(self.source_sha256) and _hash(self.rubric_sha256)
                 and type(self.human_required) is bool and type(self.oracles) is tuple)
        # Exact types: a model judge or subclass cannot pose as a deterministic oracle.
        _require(all(type(o) in _ORACLE_TYPES for o in self.oracles), "not-deterministic-oracle")
        _require(len({o.sha256 for o in self.oracles}) == len(self.oracles), "duplicate-oracle")
        _require(bool(self.oracles) or self.human_required, "no-label-source")

    @cached_property
    def sha256(self) -> str:
        return digest({"unitId": self.unit_id, "partition": self.partition,
                       "sourceSha256": self.source_sha256, "rubricSha256": self.rubric_sha256,
                       "oracles": [o.sha256 for o in self.oracles],
                       "humanRequired": self.human_required})


@dataclass(frozen=True)
class VerificationRecord:
    """Immutable commitment, label, adjudication or unit record; ``sha256`` digests its data."""

    data: Mapping[str, Any]

    @property
    def canonical_bytes(self) -> bytes:
        return canonical(self.data)

    @property
    def sha256(self) -> str:
        return digest(self.data)

    def to_dict(self) -> dict:
        return thaw(self.data)


def _record(value: dict) -> VerificationRecord:
    _require(len(canonical(value)) <= MAX_RECORD_BYTES, "record-too-large")
    return VerificationRecord(freeze(value))


def _shape(record: Any) -> Mapping[str, Any]:
    """Return a record's data if its exact key set matches its declared format."""
    data = record.data if isinstance(record, VerificationRecord) else None
    _require(isinstance(data, Mapping), "invalid-record")
    fmt = data.get("format")
    keys = _KEYS.get((fmt, data.get("provenance")) if fmt == LABEL_FORMAT else fmt)
    _require(keys is not None and set(data) == keys, "invalid-record")
    return data


def _binding(unit: Unit, commitment: Any) -> dict:
    """Validate that a commitment belongs to the unit; return the shared binding fields."""
    _require(isinstance(unit, Unit), "invalid-unit")
    _require(isinstance(commitment, VerificationRecord)
             and _shape(commitment)["format"] == COMMITMENT_FORMAT, "invalid-commitment")
    _require(commitment.data["unitSha256"] == unit.sha256, "commitment-binding-mismatch")
    return {"unitId": unit.unit_id, "unitSha256": unit.sha256, "partition": unit.partition,
            "sourceSha256": unit.source_sha256,
            "candidateSha256": commitment.data["candidateSha256"],
            "commitmentSha256": commitment.sha256}


def commit(unit: Unit, *, candidate_sha256: str, observation: Observation | None,
           outputs: Mapping[str, bytes] | None, now: int) -> VerificationRecord:
    """Commit a candidate attempt's outputs before grading; only these bytes are graded.

    ``outputs`` must be exactly the files the observation records as created or
    modified. Failed, refused, interrupted and unstarted attempts commit no outputs and
    still produce a record, so they remain in the denominator.
    """
    _require(isinstance(unit, Unit), "invalid-unit")
    _require(_hash(candidate_sha256) and type(now) is int and 0 <= now <= MAX_TICK)
    _require(observation is None or isinstance(observation, Observation), "invalid-observation")
    obs = observation.to_dict() if observation is not None else {}
    terminal = obs.get("terminal", "unobserved")
    hashes = None
    if outputs is not None:
        _require(terminal == "completed", "outputs-without-completion")
        hashes = _hashes(_outputs(outputs))
        written = {a["path"]: a["afterSha256"] for a in obs["artifacts"] if a["afterSha256"]}
        _require(obs["artifactsObserved"] and hashes == written, "output-observation-mismatch")
    else:
        _require(terminal != "completed", "completion-without-outputs")
    return _record({
        "format": COMMITMENT_FORMAT, "unitId": unit.unit_id, "unitSha256": unit.sha256,
        "partition": unit.partition, "sourceSha256": unit.source_sha256,
        "candidateSha256": candidate_sha256,
        "observationSha256": observation.sha256 if observation is not None else None,
        "attemptId": obs.get("attemptId"), "manifestSha256": obs.get("manifestSha256"),
        "terminal": terminal, "outputs": hashes,
        "outputsSha256": digest(hashes) if hashes is not None else None,
        "committedAt": now, "executionAuthorization": False})


def human_label(unit: Unit, commitment: VerificationRecord, *, annotator: str, verdict: str,
                blind: bool, rubric_sha256: str) -> VerificationRecord:
    """Record one blinded annotator's rubric verdict; ``abstain`` is a missing label."""
    binding = _binding(unit, commitment)
    _require(_id(annotator) and verdict in (*VERDICTS, "abstain"), "invalid-label")
    _require(blind is True, "unblinded-annotator")
    _require(rubric_sha256 == unit.rubric_sha256, "rubric-drift")
    return _record({"format": LABEL_FORMAT, "provenance": "human", **binding,
                    "annotator": annotator, "verdict": verdict, "blind": True,
                    "rubricSha256": rubric_sha256})


def proxy_label(unit: Unit, commitment: VerificationRecord, *, model: str,
                score_micros: int) -> VerificationRecord:
    """Record a model score as a proxy: it never becomes correctness."""
    binding = _binding(unit, commitment)
    _require(_id(model) and type(score_micros) is int and 0 <= score_micros <= MAX_SCORE_MICROS,
             "invalid-label")
    return _record({"format": LABEL_FORMAT, "provenance": "proxy", **binding,
                    "model": model, "scoreMicros": score_micros, "countsAsCorrectness": False})


def _bound(records: Any, binding: dict, fmt: str, provenance: str | None = None,
           wrong: str = "wrong-provenance") -> list[VerificationRecord]:
    """Validate records of one format/provenance bound to the same commitment."""
    _require(type(records) in (list, tuple) and len(records) <= MAX_LABELS, "invalid-label")
    for r in records:
        data = _shape(r)
        _require(data["format"] == fmt and data.get("provenance") == provenance, wrong)
        _require(data["commitmentSha256"] == binding["commitmentSha256"], "label-binding-mismatch")
    return list(records)


def adjudication(unit: Unit, commitment: VerificationRecord, *, adjudicator: str, verdict: str,
                 rationale_sha256: str, labels: Sequence[VerificationRecord]) -> VerificationRecord:
    """Record an actual adjudication of the named human labels by an independent person.

    Abstaining labels carry no verdict to adjudicate and are left out of the record.
    """
    binding = _binding(unit, commitment)
    labels = _bound(labels, binding, LABEL_FORMAT, "human")
    _require(_id(adjudicator) and verdict in VERDICTS and _hash(rationale_sha256), "invalid-adjudication")
    _require(adjudicator not in {l.data["annotator"] for l in labels}, "adjudicator-not-independent")
    return _record({"format": ADJUDICATION_FORMAT, **binding, "adjudicator": adjudicator,
                    "verdict": verdict, "rationaleSha256": rationale_sha256,
                    "labelSha256s": sorted(l.sha256 for l in labels
                                           if l.data["verdict"] != "abstain")})


# --- grading and adjudication --------------------------------------------------------


def _oracle_section(unit: Unit, commitment: Mapping[str, Any],
                    outputs: dict[str, bytes] | None, missing: list) -> dict:
    if not unit.oracles:
        return {"status": "not-used", "verdict": None, "labels": []}
    labels = []
    if outputs is None:
        missing += [{"source": "oracle", "kind": o.kind, "reason": "no-committed-output"}
                    for o in unit.oracles]
    else:
        request = VerifierRequest(commitment["attemptId"], commitment["manifestSha256"],
                                  commitment["observationSha256"], MappingProxyType(outputs))
        for oracle in unit.oracles:
            try:
                verdict = oracle.verify(request)
            except Exception:  # an oracle defect stays visible as a missing label
                verdict = "inconclusive"
            if verdict not in VERDICTS:
                missing.append({"source": "oracle", "kind": oracle.kind,
                                "reason": "oracle-inconclusive"})
                continue
            labels.append({"provenance": "oracle", "kind": oracle.kind,
                           "verifierSha256": oracle.sha256, "verdict": verdict})
    verdicts = {l["verdict"] for l in labels}
    status = "missing" if not verdicts else "agreed" if len(verdicts) == 1 else "disagreement"
    return {"status": status, "verdict": verdicts.pop() if status == "agreed" else None,
            "labels": labels}


def _human_section(unit: Unit, labels: list[VerificationRecord],
                   adjudications: list[VerificationRecord], missing: list) -> dict:
    annotators = [l.data["annotator"] for l in labels]
    _require(len(set(annotators)) == len(annotators), "duplicate-annotator")
    _require(len(adjudications) <= 1, "multiple-adjudications")
    rendered = [{**l.to_dict(), "labelSha256": l.sha256}
                for l in sorted(labels, key=lambda l: l.data["annotator"])]
    section = {"status": "not-used", "verdict": None, "labels": rendered,
               "disagreement": None, "adjudicationSha256": None}
    if not labels and not unit.human_required:
        _require(not adjudications, "adjudication-without-disagreement")
        return section
    for l in labels:
        if l.data["verdict"] == "abstain":
            missing.append({"source": "human", "annotator": l.data["annotator"], "reason": "abstained"})
    effective = [l for l in labels if l.data["verdict"] != "abstain"]
    by_verdict = {v: sorted(l.data["annotator"] for l in effective if l.data["verdict"] == v)
                  for v in VERDICTS}
    disagree = all(by_verdict.values())
    _require(disagree or not adjudications, "adjudication-without-disagreement")
    if len(effective) < MIN_ANNOTATORS:
        missing.append({"source": "human", "reason": "insufficient-annotators",
                        "have": len(effective), "need": MIN_ANNOTATORS})
        return {**section, "status": "insufficient-annotators"}
    if not disagree:
        return {**section, "status": "agreed", "verdict": effective[0].data["verdict"]}
    section["disagreement"] = by_verdict
    if not adjudications:
        missing.append({"source": "human", "reason": "unresolved-disagreement"})
        return {**section, "status": "unresolved-disagreement"}
    (record,) = adjudications
    _require(list(record.data["labelSha256s"]) == sorted(l.sha256 for l in effective),
             "adjudication-incomplete")
    # Re-checked here: labels may postdate the adjudication record.
    _require(record.data["adjudicator"] not in annotators, "adjudicator-not-independent")
    return {**section, "status": "adjudicated", "verdict": record.data["verdict"],
            "adjudicationSha256": record.sha256}


def verify_unit(unit: Unit, commitment: VerificationRecord, outputs: Mapping[str, bytes] | None,
                *, human: Sequence[VerificationRecord] = (),
                proxies: Sequence[VerificationRecord] = (),
                adjudications: Sequence[VerificationRecord] = ()) -> VerificationRecord:
    """Grade committed outputs with the unit's oracles and record every label source.

    The record keeps oracle, human and proxy results apart, with no combined verdict.
    """
    binding = _binding(unit, commitment)
    data = commitment.data
    if outputs is not None:
        outputs = _outputs(outputs, "uncommitted-output")
    _require((outputs is None) == (data["outputs"] is None), "uncommitted-output")
    _require(outputs is None or _hashes(outputs) == thaw(data["outputs"]), "uncommitted-output")
    human = _bound(human, binding, LABEL_FORMAT, "human")
    proxies = _bound(proxies, binding, LABEL_FORMAT, "proxy")
    adjudications = _bound(adjudications, binding, ADJUDICATION_FORMAT, wrong="invalid-adjudication")

    missing: list[dict] = []
    oracle = _oracle_section(unit, data, outputs, missing)
    human_section = _human_section(unit, human, adjudications, missing)
    cross = None not in (oracle["verdict"], human_section["verdict"]) \
        and oracle["verdict"] != human_section["verdict"]
    return _record({
        "format": UNIT_FORMAT, **binding, "rubricSha256": unit.rubric_sha256,
        "terminal": data["terminal"], "oracle": oracle, "human": human_section,
        "proxy": {"labels": [{**p.to_dict(), "labelSha256": p.sha256} for p in proxies],
                  "countsAsCorrectness": False},
        "crossProvenanceDisagreement": cross, "missingLabels": missing,
        "executionAuthorization": False})


# --- holdout sealing ------------------------------------------------------------------


def _units(units: Any) -> list[Unit]:
    _require(type(units) in (list, tuple) and all(isinstance(u, Unit) for u in units), "invalid-unit")
    return list(units)


def selection_view(records: Sequence[VerificationRecord], *,
                   units: Sequence[Unit]) -> tuple[VerificationRecord, ...]:
    """Records a proposer or selector may see; any held-out or unregistered one is refused.

    The partition comes from the registered unit a record binds, never from the record.
    """
    discovery = {u.sha256 for u in _units(units) if u.partition == "discovery"}
    _require(type(records) in (list, tuple), "invalid-record")
    for r in records:
        _require(_shape(r)["unitSha256"] in discovery, "holdout-sealed")
    return tuple(records)


def check_context(context: Mapping[str, bytes], units: Sequence[Unit]) -> None:
    """Refuse an improver/solver context carrying held-out grader material or its hashes.

    Keys and values are scanned. Visible discovery acceptance material stays allowed
    as normal work input.
    """
    _require(isinstance(context, Mapping) and all(
        type(k) is str and type(v) is bytes for k, v in context.items()), "invalid-context")
    sealed = [o for u in _units(units) if u.partition == "holdout" for o in u.oracles]
    values = [*(k.encode() for k in context), *context.values()]
    _require(not any(o._leaks_into(v) for o in sealed for v in values),
             "grader-material-in-context")
