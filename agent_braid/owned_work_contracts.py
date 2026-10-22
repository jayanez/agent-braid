# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-051 pure event admission against caller-owned immutable registrations.

No capture, source discovery, store, observer, model, telemetry projection or grants.
All trusted artifacts below are host attestations, not evidence verified by this
module. A secure host adapter and actual source admission are separate work.
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from agent_braid.owned_work_authority import (
    OperatorRegistry, _check, _require, canonical_bytes, digest,
    parse_json, resolve_authority, utc,
)


def event_schema() -> dict:
    return json.loads(_EVENT_SCHEMA_BYTES)


def parse_event(raw: bytes) -> dict:
    """Return a detached structurally checked record, without admitting a source."""
    result = parse_json(raw)
    _check(result, _EVENT_SCHEMA, _EVENT_SCHEMA)
    expected = digest({k: v for k, v in result.items() if k != "recordDigest"})
    _require(result["recordDigest"] == expected, "record-digest")
    return result


_PIN_KEYS = frozenset({"sourceRevision", "sourceState", "dirtyDiffDigest",
                       "configDigest", "policyDigest", "toolchainDigest", "modelDigest"})


@dataclass(frozen=True, slots=True)
class AttemptRegistration:
    """Prospectively registered attempt, including known unavailable capabilities.

    JSON bytes in pins/capabilities are copied and canonicalized. No root paths,
    commands, logs, source bodies or arbitrary wire metadata are retained here.
    """

    attempt_id: str
    task_id: str
    family_id: str
    family_partition: str
    clock_domain_id: str
    pins: bytes
    capabilities: bytes
    recommendation_digest: str | None = None

    def __post_init__(self):
        for key in ("attempt_id", "task_id", "family_id", "clock_domain_id"):
            _check(getattr(self, key), {"type": "string", "pattern": "^[0-9a-f]{32}$"}, {})
        _require(self.family_partition in ("development", "evaluation"), "registration-partition")
        pins = parse_json(self.pins)
        _require(set(pins) == _PIN_KEYS, "registration-pins")
        schema = event_schema()
        for key, value in pins.items():
            _check(value, schema["properties"][key], schema)
        _require((pins["sourceState"] == "clean") == (pins["dirtyDiffDigest"] is None),
                 "registration-source-state")
        caps = parse_json(self.capabilities)
        _require(set(caps) == {"capabilities"}, "registration-capabilities")
        _check(caps["capabilities"], schema["$defs"]["origin"]["properties"]["capabilities"], schema)
        _unique(caps["capabilities"], "name", "registration-capabilities")
        object.__setattr__(self, "pins", canonical_bytes(pins))
        object.__setattr__(self, "capabilities", canonical_bytes(caps))
        _check(self.recommendation_digest, schema["$defs"]["origin"]["properties"]
               ["recommendationArtifactDigest"], schema)


@dataclass(frozen=True, slots=True)
class OracleAttestation:
    """Trusted operational command/log binding; no semantic or human gold label."""

    attempt_id: str
    artifact_digest: str
    clock_domain_id: str
    started_ns: int
    terminal_ns: int
    available_at_ns: int
    maturity_ns: int
    exit_code: int

    def __post_init__(self):
        for field, length in (("attempt_id", 32), ("artifact_digest", 64), ("clock_domain_id", 32)):
            _check(getattr(self, field), {"type": "string", "pattern": f"^[0-9a-f]{{{length}}}$"}, {})
        times = (self.started_ns, self.terminal_ns, self.available_at_ns, self.maturity_ns)
        _require(all(type(x) is int and 0 <= x <= 2**63 - 1 for x in times)
                 and tuple(sorted(times)) == times, "oracle-times")
        _require(type(self.exit_code) is int and -255 <= self.exit_code <= 255, "oracle-exit")


@dataclass(frozen=True, slots=True)
class DiagnosticAttestation:
    attempt_id: str
    evidence_digest: str
    layer: str
    cause_code: str

    def __post_init__(self):
        schema = event_schema()["$defs"]["outcome"]["properties"]["diagnosis"]["properties"]
        _check(self.attempt_id, {"type": "string", "pattern": "^[0-9a-f]{32}$"}, {})
        _check(self.evidence_digest, {"type": "string", "pattern": "^[0-9a-f]{64}$"}, {})
        _check(self.layer, schema["layer"], {})
        _check(self.cause_code, schema["causeCode"], {})
        _require(self.layer != "unknown" and self.cause_code != "unassigned", "diagnosis-attestation")


@dataclass(frozen=True, slots=True)
class FrozenRegistration:
    """Trusted pre-observation lot snapshot; completeness is external, not inferred."""

    source_root_digest: str
    scope_digest: str
    authority_pins: bytes
    lot_digest: str
    population_digest: str
    partition_digest: str
    attempts: tuple[AttemptRegistration, ...]
    oracle_attestations: tuple[OracleAttestation, ...] = ()
    diagnostic_attestations: tuple[DiagnosticAttestation, ...] = ()
    method_digests: frozenset[str] = frozenset()

    def __post_init__(self):
        for name in ("source_root_digest", "scope_digest", "lot_digest", "population_digest", "partition_digest"):
            _check(getattr(self, name), {"type": "string", "pattern": "^[0-9a-f]{64}$"}, {})
        pins = parse_json(self.authority_pins)
        _require(set(pins) == {"featureAllowlistDigest", "oracleContractDigest", "splitProtocolDigest"},
                 "registration-authority-pins")
        for value in pins.values():
            _check(value, {"type": "string", "pattern": "^[0-9a-f]{64}$"}, {})
        object.__setattr__(self, "authority_pins", canonical_bytes(pins))
        for name, cls in (("attempts", AttemptRegistration), ("oracle_attestations", OracleAttestation),
                          ("diagnostic_attestations", DiagnosticAttestation)):
            values = tuple(getattr(self, name))
            _require(all(type(x) is cls for x in values), "registration-type")
            object.__setattr__(self, name, values)
        object.__setattr__(self, "method_digests", frozenset(self.method_digests))
        for value in self.method_digests:
            _check(value, {"type": "string", "pattern": "^[0-9a-f]{64}$"}, {})
        _require(0 < len(self.attempts) <= 1000, "registration-attempt-limit")
        ids = [x.attempt_id for x in self.attempts]
        _require(len(set(ids)) == len(ids), "registration-duplicate")
        for field in ("family_id", "task_id"):
            groups = {}
            for attempt in self.attempts:
                key = getattr(attempt, field)
                value = (attempt.family_id, attempt.family_partition)
                _require(key not in groups or groups[key] == value, "registration-partition")
                groups[key] = value
        # One operational oracle per attempt: a correction cannot rebind the
        # attempt to a later passing run and so prefer a success over a failure.
        for name, key in (("oracle_attestations", lambda x: x.attempt_id),
                          ("diagnostic_attestations", lambda x: (x.attempt_id, x.evidence_digest))):
            values = getattr(self, name)
            _require(all(x.attempt_id in ids for x in values), "unregistered-attestation")
            keys = [key(x) for x in values]
            _require(len(set(keys)) == len(keys), "conflicting-attestation")


@dataclass(frozen=True, slots=True)
class ValidatedState:
    """Immutable supplied history; every append revalidates all bytes, not a grant."""

    records: tuple[bytes, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "records", tuple(self.records))
        _require(all(type(x) is bytes for x in self.records), "state-record-type")

    @property
    def head_digest(self) -> str | None:
        return json.loads(self.records[-1])["recordDigest"] if self.records else None


@dataclass(frozen=True, slots=True)
class ValidationResult:
    state: ValidatedState
    duplicate: bool
    eligible_outcome_digests: tuple[str, ...]
    # attempt ID -> origin missing / outcome missing / latest operational label.
    population_status: tuple[tuple[str, str], ...]
    execution_authorization: bool = False
    training_admission: bool = False


def _unique(rows, key, code):
    _require(len({r[key] for r in rows}) == len(rows), code)


def _origin(event, attempt, registration):
    p = event["payload"]
    _require(p["clockDomainId"] == attempt.clock_domain_id, "clock-domain")
    _require(p["familyPartition"] == attempt.family_partition and
             p["partitionDigest"] == registration.partition_digest, "family-partition")
    _require(p["lotDigest"] == registration.lot_digest and
             p["populationDigest"] == registration.population_digest, "population-binding")
    _require(p["originNs"] == p["cutoffNs"], "origin-cutoff")
    _unique(p["features"], "name", "duplicate-feature")
    _unique(p["capabilities"], "name", "duplicate-capability")
    for feature in p["features"]:
        if feature["value"] is not None:
            _require(feature["eventNs"] <= feature["availableAtNs"] <= p["cutoffNs"], "future-feature")
            # The closed v1 features are attempt-level predictors, not process outcomes.
        _require(feature["scope"] == "attempt", "feature-scope")
    _require(p["capabilities"] == json.loads(attempt.capabilities)["capabilities"], "unobserved-capability")
    for cap in p["capabilities"]:
        if cap["status"] == "not-probed":
            _require(cap["availableAtNs"] is None and cap["evidenceDigest"] is None
                     and cap["reason"] == "not-probed", "unobserved-capability")
        else:
            _require(cap["evidenceDigest"] is not None and cap["availableAtNs"] is not None
                     and cap["availableAtNs"] <= p["cutoffNs"], "future-capability")
            _require((cap["status"] == "available") == (cap["reason"] == "observed-pass"),
                     "capability-status")
    _require(p["recommendationArtifactDigest"] == attempt.recommendation_digest, "recommendation-binding")
    _require((p["recommendation"] in ("not-produced", "unavailable")) ==
             (p["recommendationArtifactDigest"] is None), "recommendation-evidence")
    f = p["forecast"]
    if f["status"] == "produced":
        _require(p["originNs"] + f["horizonNs"] <= 2**63 - 1, "horizon-overflow")
        _require(f["methodDigest"] in registration.method_digests, "unregistered-method")
        if f["lower"] is not None:
            _require(f["lower"] <= f["point"] <= f["upper"], "forecast-interval")


def _spans(spans, clock):
    _unique(spans, "spanId", "duplicate-span")
    by_id = {s["spanId"]: s for s in spans}
    for span in spans:
        _require(span["clockDomainId"] == clock, "span-clock")
        start, end = span["startedNs"], span["finishedNs"]
        _require(end is None or start is not None and start <= end, "span-time")
        parent_id = span["parentSpanId"]
        seen = {span["spanId"]}
        while parent_id is not None:
            _require(parent_id in by_id and parent_id not in seen, "span-parent")
            seen.add(parent_id)
            parent = by_id[parent_id]
            if start is not None and end is not None and parent["status"] == "complete":
                _require(parent["startedNs"] <= start <= end <= parent["finishedNs"], "span-containment")
            parent_id = parent["parentSpanId"]


def _outcome(event, origin, attempt, registration, previous):
    p, op = event["payload"], origin["payload"]
    _require(p["originRecordDigest"] == origin["recordDigest"], "origin-reference")
    _require(p["clockDomainId"] == op["clockDomainId"], "clock-domain")
    if previous is None:
        _require(event["supersedesRecordDigest"] is None and p["amendmentReason"] == "initial",
                 "outcome-supersession")
    else:
        _require(event["supersedesRecordDigest"] == previous["recordDigest"] and
                 p["amendmentReason"] != "initial", "outcome-supersession")
    _unique(p["metrics"], "name", "duplicate-metric")
    oracle = p["oracle"]
    pins = json.loads(registration.authority_pins)
    _require(oracle["contractDigest"] == pins["oracleContractDigest"], "oracle-contract")
    observation = next((a for a in registration.oracle_attestations
                        if a.attempt_id == attempt.attempt_id and
                        a.artifact_digest == oracle["artifactDigest"]), None)
    if oracle["status"] in ("verified", "failed"):
        _require(observation is not None, "unbound-oracle")
        _require(observation.clock_domain_id == p["clockDomainId"] and
                 (p["terminalNs"], p["availableAtNs"], p["maturityNs"]) ==
                 (observation.terminal_ns, observation.available_at_ns, observation.maturity_ns), "oracle-times")
        _require(op["originNs"] <= observation.started_ns, "pre-origin-validation")
    else:
        _require(oracle["artifactDigest"] is None, "unbound-oracle")
    times = [op["originNs"]] + [p[k] for k in ("terminalNs", "availableAtNs", "maturityNs") if p[k] is not None]
    _require(times == sorted(times), "outcome-time")
    horizon = op["forecast"]["horizonNs"]
    end = op["originNs"] + horizon if horizon is not None else None
    late = end is not None and p["terminalNs"] is not None and p["terminalNs"] > end
    observed = p["censoring"]["observedUntilNs"]
    if late or (end is not None and p["terminalNs"] is None and observed is not None and observed >= end):
        _require(p["labelState"] == "censored" and p["censoring"]["state"] == "right-censored",
                 "original-horizon-censored")
    if previous is not None and previous["payload"]["censoring"]["state"] == "right-censored":
        # Once recorded at the fixed follow-up boundary, later evidence cannot
        # retry-select a mature original-lot observation.
        _require(p["labelState"] == "censored" and p["censoring"]["state"] == "right-censored",
                 "original-horizon-censored")
    metrics = {m["name"]: m for m in p["metrics"]}
    wall = metrics.get("validation_wall_ns")
    exit_metric = metrics.get("validation_exit_code")
    if p["labelState"] == "mature":
        _require(observation is not None and oracle["status"] == "verified" and
                 p["workflowTerminal"] in ("completed", "error") and
                 p["verificationDisposition"] in ("verified", "failed"), "maturity-evidence")
        _require(wall is not None and wall["scope"] == "validation-process" and
                 wall["value"] == observation.terminal_ns - observation.started_ns, "mature-target")
    if wall is not None and wall["value"] is not None:
        _require(observation is not None and wall["scope"] == "validation-process" and
                 wall["value"] == observation.terminal_ns - observation.started_ns, "unbound-target")
    if exit_metric is not None and exit_metric["value"] is not None:
        _require(observation is not None and exit_metric["scope"] == "validation-process" and
                 exit_metric["value"] == observation.exit_code, "unbound-exit")
    if p["verificationDisposition"] in ("verified", "failed"):
        _require(observation is not None and oracle["status"] == "verified", "verification-evidence")
        _require((p["verificationDisposition"] == "verified") == (observation.exit_code == 0),
                 "verification-disposition")
    c = p["censoring"]
    if c["observedUntilNs"] is not None:
        _require(c["observedUntilNs"] >= op["originNs"], "censor-time")
    if c["state"] == "right-censored":
        _require(end is not None and c["observedUntilNs"] is not None and
                 c["observedUntilNs"] >= end, "censor-horizon")
    if p["labelState"] != "mature" and not late:
        _require(wall is None or wall["value"] is None, "ineligible-target")
    diagnosis = p["diagnosis"]
    _require(diagnosis["boundedDiagnosticAnnexDigest"] is None, "annex-not-admitted")
    if diagnosis["claimLevel"] == "observed-mechanism":
        key = DiagnosticAttestation(attempt.attempt_id, diagnosis["evidenceDigest"],
                                    diagnosis["layer"], diagnosis["causeCode"])
        _require(key in registration.diagnostic_attestations, "unbound-diagnosis")
    _spans(p["spans"], p["clockDomainId"])
    bound = p["maturityNs"] if p["maturityNs"] is not None else p["availableAtNs"]
    for span in p["spans"]:
        if span["finishedNs"] is not None:
            _require(bound is not None and span["finishedNs"] <= bound, "future-span")


def validate_append(raw: bytes, *, authority: bytes, registry: OperatorRegistry | None,
                    registration: FrozenRegistration, now_utc: str,
                    state: ValidatedState = ValidatedState()) -> ValidationResult:
    """Return a new immutable state or refusal; neither append nor capture occurs.

    Every call resolves the supplied fresh registry, replays bounded history and
    validates the candidate. Idempotence is semantic/canonical, not whitespace.
    No callback can replace operator-snapshot resolution. Complete registration
    and artifact truth remain trusted external obligations.
    """
    _require(type(registration) is FrozenRegistration and type(state) is ValidatedState,
             "trusted-state-required")
    candidate = parse_event(raw)
    _require(len(state.records) <= 4096 and sum(map(len, state.records)) <= 10485760,
             "state-limit")
    original = tuple(parse_event(x) for x in state.records)
    actions = tuple(sorted({"record-origin" if x["kind"] == "origin" else "append-outcome"
                            for x in original} |
                           {"record-origin" if candidate["kind"] == "origin" else "append-outcome"}))
    context = resolve_authority(authority, registry, source_root_digest=registration.source_root_digest,
                                scope_digest=registration.scope_digest,
                                expected_pins=json.loads(registration.authority_pins), actions=actions,
                                now_utc=now_utc)
    caps = context.descriptor["caps"]
    _require(len(raw) <= caps["maxRecordBytes"] and
             len(registration.attempts) <= caps["maxAttempts"], "authority-cap")
    duplicate = any(x == candidate for x in original)
    events = original if duplicate else original + (candidate,)
    encoded = tuple(canonical_bytes(x) for x in events)
    _require(len(events) <= caps["maxRecords"] and
             all(len(x) <= caps["maxRecordBytes"] for x in encoded) and
             sum(map(len, encoded)) <= caps["maxStoreBytes"], "authority-cap")
    by_attempt = {a.attempt_id: a for a in registration.attempts}
    origins, outcomes = {}, {}
    prior = None
    prior_utc = None
    for sequence, event in enumerate(events):
        _require(event["sequence"] == sequence and event["previousRecordDigest"] == prior, "record-chain")
        _require(event["authorityDigest"] == context.authority_digest, "authority-binding")
        recorded = utc(event["recordedAtUTC"])
        descriptor = context.descriptor
        _require(utc(descriptor["validFromUTC"]) <= recorded <= utc(now_utc) and
                 recorded < utc(descriptor["validUntilUTC"]), "record-date")
        _require(prior_utc is None or recorded >= prior_utc, "record-time-regression")
        _require((utc(now_utc).date() - recorded.date()).days < caps["retentionUTCDates"], "retention-expired")
        attempt = by_attempt.get(event["attemptId"])
        _require(attempt is not None, "unregistered-attempt")
        _require(event["taskId"] == attempt.task_id and event["familyId"] == attempt.family_id,
                 "attempt-identity")
        _require({k: event[k] for k in _PIN_KEYS} == json.loads(attempt.pins), "source-pins")
        if event["kind"] == "origin":
            _require(attempt.attempt_id not in origins and event["supersedesRecordDigest"] is None,
                     "conflicting-origin")
            _origin(event, attempt, registration)
            origins[attempt.attempt_id] = event
        else:
            origin = origins.get(attempt.attempt_id)
            _require(origin is not None, "missing-origin")
            _outcome(event, origin, attempt, registration, outcomes.get(attempt.attempt_id))
            outcomes[attempt.attempt_id] = event
        prior, prior_utc = event["recordDigest"], recorded
    eligible = tuple(x["recordDigest"] for aid, x in outcomes.items()
                     if x["payload"]["labelState"] == "mature" and
                     origins[aid]["payload"]["forecast"]["status"] == "produced")
    population = tuple((a.attempt_id, "origin-missing" if a.attempt_id not in origins else
                        outcomes[a.attempt_id]["payload"]["labelState"] if a.attempt_id in outcomes
                        else "outcome-missing") for a in registration.attempts)
    return ValidationResult(ValidatedState(encoded), duplicate, eligible, population)


def span_union_ns(spans: tuple[dict, ...], *, stage: str, clock_domain_id: str) -> int | None:
    """Union inclusive completed spans of one stage; never sum nested durations.

    Missing/interrupted or exclusive rows refuse a numeric total (None). This is
    a pure descriptive helper, not a full observer accounting implementation.
    """
    schema = event_schema()
    rows = list(spans)
    definition = schema["$defs"]["outcome"]["properties"]["spans"]
    _check(rows, definition, schema)
    _spans(rows, clock_domain_id)
    selected = [s for s in rows if s["stage"] == stage]
    if not selected or any(s["status"] != "complete" or s["accounting"] != "inclusive" for s in selected):
        return None
    intervals = sorted((s["startedNs"], s["finishedNs"]) for s in selected)
    start, end = intervals[0]
    total = 0
    for left, right in intervals[1:]:
        if left > end:
            total += end - start
            start = left
        end = max(end, right)
    return total + end - start


# Embedded fixed schema, tied byte-semantically to SPEC-051 by parity tests.
_EVENT_SCHEMA_BYTES = (
    '{"type":"object","additionalProperties":false,"required":["schema","kind","sourceKind","se'
    'quence","attemptId","taskId","familyId","authorityDigest","sourceRevision","sourceState","'
    'dirtyDiffDigest","configDigest","policyDigest","toolchainDigest","modelDigest","recordedAt'
    'UTC","previousRecordDigest","supersedesRecordDigest","recordDigest","payload","executionAu'
    'thorization","trainingAdmission","collector047Projection"],"properties":{"schema":{"const"'
    ':"agent-braid-owned-work-evaluation/v1"},"kind":{"enum":["origin","outcome"]},"sourceKind"'
    ':{"const":"owned-deterministic-development"},"sequence":{"type":"integer","minimum":0,"max'
    'imum":9223372036854775807},"attemptId":{"type":"string","pattern":"^[0-9a-f]{32}$"},"taskI'
    'd":{"type":"string","pattern":"^[0-9a-f]{32}$"},"familyId":{"type":"string","pattern":"^[0'
    '-9a-f]{32}$"},"authorityDigest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"sourceRevisi'
    'on":{"type":"string","pattern":"^[0-9a-f]{40}$"},"sourceState":{"enum":["clean","dirty"]},'
    '"dirtyDiffDigest":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]}'
    ',"configDigest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"policyDigest":{"type":"strin'
    'g","pattern":"^[0-9a-f]{64}$"},"toolchainDigest":{"type":"string","pattern":"^[0-9a-f]{64}'
    '$"},"modelDigest":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]}'
    ',"recordedAtUTC":{"type":"string","format":"date-time","pattern":"Z$"},"previousRecordDige'
    'st":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"supersedesRe'
    'cordDigest":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"reco'
    'rdDigest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"payload":{},"executionAuthorizatio'
    'n":{"const":false},"trainingAdmission":{"const":false},"collector047Projection":{"const":"'
    'none"}},"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"urn:agent-braid:pr'
    'oposed:owned-work-evaluation:v1","title":"PROPOSED private evaluation ledger event; no '
    'capture admission","$defs":{"origin":{"type":"object","additionalProperties":false,"requir'
    'ed":["clockDomainId","originNs","cutoffNs","lotDigest","populationDigest","partitionDigest'
    '","familyPartition","features","capabilities","condition","recommendation","recommendation'
    'ArtifactDigest","chosenAction","forecast"],"properties":{"clockDomainId":{"type":"string",'
    '"pattern":"^[0-9a-f]{32}$"},"originNs":{"type":"integer","minimum":0,"maximum":92233720368'
    '54775807},"cutoffNs":{"type":"integer","minimum":0,"maximum":9223372036854775807},"lotDige'
    'st":{"type":"string","pattern":"^[0-9a-f]{64}$"},"populationDigest":{"type":"string","patt'
    'ern":"^[0-9a-f]{64}$"},"partitionDigest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"fam'
    'ilyPartition":{"enum":["development","evaluation"]},"features":{"type":"array","maxItems":'
    '6,"items":{"oneOf":[{"type":"object","additionalProperties":false,"required":["name","unit'
    '","value","missingReason","scope","eventNs","availableAtNs"],"properties":{"name":{"const"'
    ':"operation_count"},"unit":{"const":"count"},"value":{"anyOf":[{"type":"integer","minimum"'
    ':0,"maximum":9223372036854775807},{"type":"null"}]},"missingReason":{"anyOf":[{"enum":["no'
    't-measured","not-applicable","not-admitted","not-produced","not-probed","unavailable","cro'
    'ss-clock","censored","revoked","unknown"]},{"type":"null"}]},"scope":{"enum":["attempt","v'
    'alidation-process","observer-process"]},"eventNs":{"anyOf":[{"type":"integer","minimum":0,'
    '"maximum":9223372036854775807},{"type":"null"}]},"availableAtNs":{"anyOf":[{"type":"intege'
    'r","minimum":0,"maximum":9223372036854775807},{"type":"null"}]}},"allOf":[{"if":{"properti'
    'es":{"value":{"type":"null"}}},"then":{"properties":{"missingReason":{"enum":["not-measure'
    'd","not-applicable","not-admitted","not-produced","not-probed","unavailable","cross-clock"'
    ',"censored","revoked","unknown"]},"eventNs":{"type":"null"},"availableAtNs":{"type":"null"'
    '}}},"else":{"properties":{"missingReason":{"type":"null"},"eventNs":{"type":"integer","min'
    'imum":0,"maximum":9223372036854775807},"availableAtNs":{"type":"integer","minimum":0,"maxi'
    'mum":9223372036854775807}}}}]},{"type":"object","additionalProperties":false,"required":["'
    'name","unit","value","missingReason","scope","eventNs","availableAtNs"],"properties":{"nam'
    'e":{"const":"changed_file_count"},"unit":{"const":"count"},"value":{"anyOf":[{"type":"inte'
    'ger","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"missingReason":{"anyOf"'
    ':[{"enum":["not-measured","not-applicable","not-admitted","not-produced","not-probed","una'
    'vailable","cross-clock","censored","revoked","unknown"]},{"type":"null"}]},"scope":{"enum"'
    ':["attempt","validation-process","observer-process"]},"eventNs":{"anyOf":[{"type":"integer'
    '","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"availableAtNs":{"anyOf":[{'
    '"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]}},"allOf":[{"'
    'if":{"properties":{"value":{"type":"null"}}},"then":{"properties":{"missingReason":{"enum"'
    ':["not-measured","not-applicable","not-admitted","not-produced","not-probed","unavailable"'
    ',"cross-clock","censored","revoked","unknown"]},"eventNs":{"type":"null"},"availableAtNs":'
    '{"type":"null"}}},"else":{"properties":{"missingReason":{"type":"null"},"eventNs":{"type":'
    '"integer","minimum":0,"maximum":9223372036854775807},"availableAtNs":{"type":"integer","mi'
    'nimum":0,"maximum":9223372036854775807}}}}]},{"type":"object","additionalProperties":false'
    ',"required":["name","unit","value","missingReason","scope","eventNs","availableAtNs"],"pro'
    'perties":{"name":{"const":"declared_write_count"},"unit":{"const":"count"},"value":{"anyOf'
    '":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"missing'
    'Reason":{"anyOf":[{"enum":["not-measured","not-applicable","not-admitted","not-produced","'
    'not-probed","unavailable","cross-clock","censored","revoked","unknown"]},{"type":"null"}]}'
    ',"scope":{"enum":["attempt","validation-process","observer-process"]},"eventNs":{"anyOf":['
    '{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"availableA'
    'tNs":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"'
    '}]}},"allOf":[{"if":{"properties":{"value":{"type":"null"}}},"then":{"properties":{"missin'
    'gReason":{"enum":["not-measured","not-applicable","not-admitted","not-produced","not-probe'
    'd","unavailable","cross-clock","censored","revoked","unknown"]},"eventNs":{"type":"null"},'
    '"availableAtNs":{"type":"null"}}},"else":{"properties":{"missingReason":{"type":"null"},"e'
    'ventNs":{"type":"integer","minimum":0,"maximum":9223372036854775807},"availableAtNs":{"typ'
    'e":"integer","minimum":0,"maximum":9223372036854775807}}}}]},{"type":"object","additionalP'
    'roperties":false,"required":["name","unit","value","missingReason","scope","eventNs","avai'
    'lableAtNs"],"properties":{"name":{"const":"context_bytes"},"unit":{"const":"bytes"},"value'
    '":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]}'
    ',"missingReason":{"anyOf":[{"enum":["not-measured","not-applicable","not-admitted","not-pr'
    'oduced","not-probed","unavailable","cross-clock","censored","revoked","unknown"]},{"type":'
    '"null"}]},"scope":{"enum":["attempt","validation-process","observer-process"]},"eventNs":{'
    '"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"a'
    'vailableAtNs":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"typ'
    'e":"null"}]}},"allOf":[{"if":{"properties":{"value":{"type":"null"}}},"then":{"properties"'
    ':{"missingReason":{"enum":["not-measured","not-applicable","not-admitted","not-produced","'
    'not-probed","unavailable","cross-clock","censored","revoked","unknown"]},"eventNs":{"type"'
    ':"null"},"availableAtNs":{"type":"null"}}},"else":{"properties":{"missingReason":{"type":"'
    'null"},"eventNs":{"type":"integer","minimum":0,"maximum":9223372036854775807},"availableAt'
    'Ns":{"type":"integer","minimum":0,"maximum":9223372036854775807}}}}]},{"type":"object","ad'
    'ditionalProperties":false,"required":["name","unit","value","missingReason","scope","event'
    'Ns","availableAtNs"],"properties":{"name":{"const":"prior_queue_wait_ns"},"unit":{"const":'
    '"ns"},"value":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"typ'
    'e":"null"}]},"missingReason":{"anyOf":[{"enum":["not-measured","not-applicable","not-admit'
    'ted","not-produced","not-probed","unavailable","cross-clock","censored","revoked","unknown'
    '"]},{"type":"null"}]},"scope":{"enum":["attempt","validation-process","observer-process"]}'
    ',"eventNs":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":'
    '"null"}]},"availableAtNs":{"anyOf":[{"type":"integer","minimum":0,"maximum":92233720368547'
    '75807},{"type":"null"}]}},"allOf":[{"if":{"properties":{"value":{"type":"null"}}},"then":{'
    '"properties":{"missingReason":{"enum":["not-measured","not-applicable","not-admitted","not'
    '-produced","not-probed","unavailable","cross-clock","censored","revoked","unknown"]},"even'
    'tNs":{"type":"null"},"availableAtNs":{"type":"null"}}},"else":{"properties":{"missingReaso'
    'n":{"type":"null"},"eventNs":{"type":"integer","minimum":0,"maximum":9223372036854775807},'
    '"availableAtNs":{"type":"integer","minimum":0,"maximum":9223372036854775807}}}}]},{"type":'
    '"object","additionalProperties":false,"required":["name","unit","value","missingReason","s'
    'cope","eventNs","availableAtNs"],"properties":{"name":{"const":"required_validation_count"'
    '},"unit":{"const":"count"},"value":{"anyOf":[{"type":"integer","minimum":0,"maximum":92233'
    '72036854775807},{"type":"null"}]},"missingReason":{"anyOf":[{"enum":["not-measured","not-a'
    'pplicable","not-admitted","not-produced","not-probed","unavailable","cross-clock","censore'
    'd","revoked","unknown"]},{"type":"null"}]},"scope":{"enum":["attempt","validation-process"'
    ',"observer-process"]},"eventNs":{"anyOf":[{"type":"integer","minimum":0,"maximum":92233720'
    '36854775807},{"type":"null"}]},"availableAtNs":{"anyOf":[{"type":"integer","minimum":0,"ma'
    'ximum":9223372036854775807},{"type":"null"}]}},"allOf":[{"if":{"properties":{"value":{"typ'
    'e":"null"}}},"then":{"properties":{"missingReason":{"enum":["not-measured","not-applicable'
    '","not-admitted","not-produced","not-probed","unavailable","cross-clock","censored","revok'
    'ed","unknown"]},"eventNs":{"type":"null"},"availableAtNs":{"type":"null"}}},"else":{"prope'
    'rties":{"missingReason":{"type":"null"},"eventNs":{"type":"integer","minimum":0,"maximum":'
    '9223372036854775807},"availableAtNs":{"type":"integer","minimum":0,"maximum":9223372036854'
    '775807}}}}]}]}},"capabilities":{"type":"array","maxItems":3,"items":{"type":"object","addi'
    'tionalProperties":false,"required":["name","status","availableAtNs","evidenceDigest","reas'
    'on"],"properties":{"name":{"enum":["resolved-toolchain","process-supervision","native-stdi'
    'o-containment"]},"status":{"enum":["available","unavailable","not-probed"]},"availableAtNs'
    '":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]}'
    ',"evidenceDigest":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]}'
    ',"reason":{"enum":["observed-pass","permission-denied","missing-binary","unsupported-platf'
    'orm","not-probed","unknown"]}}}},"condition":{"enum":["cold","warm","unknown"]},"recommend'
    'ation":{"enum":["not-produced","answered","refused","semantic-defer","unavailable"]},"reco'
    'mmendationArtifactDigest":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"'
    'null"}]},"chosenAction":{"enum":["not-yet-chosen","keep-order","serial-development","aband'
    'on"]},"forecast":{"type":"object","additionalProperties":false,"required":["status","targe'
    't","horizonNs","point","lower","upper","unit","methodDigest","missingReason"],"properties"'
    ':{"status":{"enum":["not-produced","produced"]},"target":{"const":"validation_wall_ns"},"h'
    'orizonNs":{"anyOf":[{"type":"integer","minimum":1,"maximum":86400000000000},{"type":"null"'
    '}]},"point":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type"'
    ':"null"}]},"lower":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},'
    '{"type":"null"}]},"upper":{"anyOf":[{"type":"integer","minimum":0,"maximum":92233720368547'
    '75807},{"type":"null"}]},"unit":{"const":"ns"},"methodDigest":{"anyOf":[{"type":"string","'
    'pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"missingReason":{"anyOf":[{"enum":["not-measu'
    'red","not-applicable","not-admitted","not-produced","not-probed","unavailable","cross-cloc'
    'k","censored","revoked","unknown"]},{"type":"null"}]}},"allOf":[{"if":{"properties":{"stat'
    'us":{"const":"not-produced"}}},"then":{"properties":{"horizonNs":{"type":"null"},"point":{'
    '"type":"null"},"lower":{"type":"null"},"upper":{"type":"null"},"methodDigest":{"type":"nul'
    'l"},"missingReason":{"enum":["not-measured","not-applicable","not-admitted","not-produced"'
    ',"not-probed","unavailable","cross-clock","censored","revoked","unknown"]}}},"else":{"prop'
    'erties":{"horizonNs":{"type":"integer","minimum":1,"maximum":86400000000000},"point":{"typ'
    'e":"integer","minimum":0,"maximum":9223372036854775807},"methodDigest":{"type":"string","p'
    'attern":"^[0-9a-f]{64}$"},"missingReason":{"type":"null"}}}},{"oneOf":[{"properties":{"low'
    'er":{"type":"null"},"upper":{"type":"null"}}},{"properties":{"lower":{"type":"integer","mi'
    'nimum":0,"maximum":9223372036854775807},"upper":{"type":"integer","minimum":0,"maximum":92'
    '23372036854775807}}}]}]}}},"outcome":{"type":"object","additionalProperties":false,"requir'
    'ed":["originRecordDigest","clockDomainId","chosenAction","workflowTerminal","productDispos'
    'ition","verificationDisposition","terminalNs","availableAtNs","maturityNs","labelState","m'
    'etrics","oracle","censoring","diagnosis","spans","amendmentReason"],"properties":{"originR'
    'ecordDigest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"clockDomainId":{"type":"string"'
    ',"pattern":"^[0-9a-f]{32}$"},"chosenAction":{"enum":["keep-order","serial-development","ab'
    'andon","not-observed"]},"workflowTerminal":{"enum":["completed","refused","cancelled","err'
    'or","abandoned","missing","not-selected"]},"productDisposition":{"enum":["answered","refus'
    'ed","semantic-defer","error","not-run","unknown"]},"verificationDisposition":{"enum":["ver'
    'ified","failed","unavailable","not-run","unknown"]},"terminalNs":{"anyOf":[{"type":"intege'
    'r","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"availableAtNs":{"anyOf":['
    '{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"maturityNs'
    '":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]}'
    ',"labelState":{"enum":["unavailable","pending","mature","censored","invalid"]},"metrics":{'
    '"type":"array","maxItems":12,"items":{"oneOf":[{"type":"object","additionalProperties":fal'
    'se,"required":["name","unit","value","missingReason","scope"],"properties":{"name":{"const'
    '":"validation_wall_ns"},"unit":{"const":"ns"},"value":{"anyOf":[{"type":"integer","minimum'
    '":0,"maximum":9223372036854775807},{"type":"null"}]},"missingReason":{"anyOf":[{"enum":["n'
    'ot-measured","not-applicable","not-admitted","not-produced","not-probed","unavailable","cr'
    'oss-clock","censored","revoked","unknown"]},{"type":"null"}]},"scope":{"enum":["attempt","'
    'validation-process","observer-process"]}},"allOf":[{"if":{"properties":{"value":{"type":"n'
    'ull"}}},"then":{"properties":{"missingReason":{"enum":["not-measured","not-applicable","no'
    't-admitted","not-produced","not-probed","unavailable","cross-clock","censored","revoked","'
    'unknown"]}}},"else":{"properties":{"missingReason":{"type":"null"}}}}]},{"type":"object","'
    'additionalProperties":false,"required":["name","unit","value","missingReason","scope"],"pr'
    'operties":{"name":{"const":"queue_wait_ns"},"unit":{"const":"ns"},"value":{"anyOf":[{"type'
    '":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"missingReason":{'
    '"anyOf":[{"enum":["not-measured","not-applicable","not-admitted","not-produced","not-probe'
    'd","unavailable","cross-clock","censored","revoked","unknown"]},{"type":"null"}]},"scope":'
    '{"enum":["attempt","validation-process","observer-process"]}},"allOf":[{"if":{"properties"'
    ':{"value":{"type":"null"}}},"then":{"properties":{"missingReason":{"enum":["not-measured",'
    '"not-applicable","not-admitted","not-produced","not-probed","unavailable","cross-clock","c'
    'ensored","revoked","unknown"]}}},"else":{"properties":{"missingReason":{"type":"null"}}}}]'
    '},{"type":"object","additionalProperties":false,"required":["name","unit","value","missing'
    'Reason","scope"],"properties":{"name":{"const":"cpu_user_ns"},"unit":{"const":"ns"},"value'
    '":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]}'
    ',"missingReason":{"anyOf":[{"enum":["not-measured","not-applicable","not-admitted","not-pr'
    'oduced","not-probed","unavailable","cross-clock","censored","revoked","unknown"]},{"type":'
    '"null"}]},"scope":{"enum":["attempt","validation-process","observer-process"]}},"allOf":[{'
    '"if":{"properties":{"value":{"type":"null"}}},"then":{"properties":{"missingReason":{"enum'
    '":["not-measured","not-applicable","not-admitted","not-produced","not-probed","unavailable'
    '","cross-clock","censored","revoked","unknown"]}}},"else":{"properties":{"missingReason":{'
    '"type":"null"}}}}]},{"type":"object","additionalProperties":false,"required":["name","unit'
    '","value","missingReason","scope"],"properties":{"name":{"const":"cpu_system_ns"},"unit":{'
    '"const":"ns"},"value":{"anyOf":[{"type":"integer","minimum":0,"maximum":922337203685477580'
    '7},{"type":"null"}]},"missingReason":{"anyOf":[{"enum":["not-measured","not-applicable","n'
    'ot-admitted","not-produced","not-probed","unavailable","cross-clock","censored","revoked",'
    '"unknown"]},{"type":"null"}]},"scope":{"enum":["attempt","validation-process","observer-pr'
    'ocess"]}},"allOf":[{"if":{"properties":{"value":{"type":"null"}}},"then":{"properties":{"m'
    'issingReason":{"enum":["not-measured","not-applicable","not-admitted","not-produced","not-'
    'probed","unavailable","cross-clock","censored","revoked","unknown"]}}},"else":{"properties'
    '":{"missingReason":{"type":"null"}}}}]},{"type":"object","additionalProperties":false,"req'
    'uired":["name","unit","value","missingReason","scope"],"properties":{"name":{"const":"samp'
    'led_peak_rss_bytes"},"unit":{"const":"bytes"},"value":{"anyOf":[{"type":"integer","minimum'
    '":0,"maximum":9223372036854775807},{"type":"null"}]},"missingReason":{"anyOf":[{"enum":["n'
    'ot-measured","not-applicable","not-admitted","not-produced","not-probed","unavailable","cr'
    'oss-clock","censored","revoked","unknown"]},{"type":"null"}]},"scope":{"enum":["attempt","'
    'validation-process","observer-process"]}},"allOf":[{"if":{"properties":{"value":{"type":"n'
    'ull"}}},"then":{"properties":{"missingReason":{"enum":["not-measured","not-applicable","no'
    't-admitted","not-produced","not-probed","unavailable","cross-clock","censored","revoked","'
    'unknown"]}}},"else":{"properties":{"missingReason":{"type":"null"}}}}]},{"type":"object","'
    'additionalProperties":false,"required":["name","unit","value","missingReason","scope"],"pr'
    'operties":{"name":{"const":"git_calls"},"unit":{"const":"count"},"value":{"anyOf":[{"type"'
    ':"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}]},"missingReason":{"'
    'anyOf":[{"enum":["not-measured","not-applicable","not-admitted","not-produced","not-probed'
    '","unavailable","cross-clock","censored","revoked","unknown"]},{"type":"null"}]},"scope":{'
    '"enum":["attempt","validation-process","observer-process"]}},"allOf":[{"if":{"properties":'
    '{"value":{"type":"null"}}},"then":{"properties":{"missingReason":{"enum":["not-measured","'
    'not-applicable","not-admitted","not-produced","not-probed","unavailable","cross-clock","ce'
    'nsored","revoked","unknown"]}}},"else":{"properties":{"missingReason":{"type":"null"}}}}]}'
    ',{"type":"object","additionalProperties":false,"required":["name","unit","value","missingR'
    'eason","scope"],"properties":{"name":{"const":"retry_count"},"unit":{"const":"count"},"val'
    'ue":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}'
    ']},"missingReason":{"anyOf":[{"enum":["not-measured","not-applicable","not-admitted","not-'
    'produced","not-probed","unavailable","cross-clock","censored","revoked","unknown"]},{"type'
    '":"null"}]},"scope":{"enum":["attempt","validation-process","observer-process"]}},"allOf":'
    '[{"if":{"properties":{"value":{"type":"null"}}},"then":{"properties":{"missingReason":{"en'
    'um":["not-measured","not-applicable","not-admitted","not-produced","not-probed","unavailab'
    'le","cross-clock","censored","revoked","unknown"]}}},"else":{"properties":{"missingReason"'
    ':{"type":"null"}}}}]},{"type":"object","additionalProperties":false,"required":["name","un'
    'it","value","missingReason","scope"],"properties":{"name":{"const":"conflict_count"},"unit'
    '":{"const":"count"},"value":{"anyOf":[{"type":"integer","minimum":0,"maximum":922337203685'
    '4775807},{"type":"null"}]},"missingReason":{"anyOf":[{"enum":["not-measured","not-applicab'
    'le","not-admitted","not-produced","not-probed","unavailable","cross-clock","censored","rev'
    'oked","unknown"]},{"type":"null"}]},"scope":{"enum":["attempt","validation-process","obser'
    'ver-process"]}},"allOf":[{"if":{"properties":{"value":{"type":"null"}}},"then":{"propertie'
    's":{"missingReason":{"enum":["not-measured","not-applicable","not-admitted","not-produced"'
    ',"not-probed","unavailable","cross-clock","censored","revoked","unknown"]}}},"else":{"prop'
    'erties":{"missingReason":{"type":"null"}}}}]},{"type":"object","additionalProperties":fals'
    'e,"required":["name","unit","value","missingReason","scope"],"properties":{"name":{"const"'
    ':"rework_count"},"unit":{"const":"count"},"value":{"anyOf":[{"type":"integer","minimum":0,'
    '"maximum":9223372036854775807},{"type":"null"}]},"missingReason":{"anyOf":[{"enum":["not-m'
    'easured","not-applicable","not-admitted","not-produced","not-probed","unavailable","cross-'
    'clock","censored","revoked","unknown"]},{"type":"null"}]},"scope":{"enum":["attempt","vali'
    'dation-process","observer-process"]}},"allOf":[{"if":{"properties":{"value":{"type":"null"'
    '}}},"then":{"properties":{"missingReason":{"enum":["not-measured","not-applicable","not-ad'
    'mitted","not-produced","not-probed","unavailable","cross-clock","censored","revoked","unkn'
    'own"]}}},"else":{"properties":{"missingReason":{"type":"null"}}}}]},{"type":"object","addi'
    'tionalProperties":false,"required":["name","unit","value","missingReason","scope"],"proper'
    'ties":{"name":{"const":"validation_exit_code"},"unit":{"const":"exit-code"},"value":{"anyO'
    'f":[{"type":"integer","minimum":-255,"maximum":255},{"type":"null"}]},"missingReason":{"an'
    'yOf":[{"enum":["not-measured","not-applicable","not-admitted","not-produced","not-probed",'
    '"unavailable","cross-clock","censored","revoked","unknown"]},{"type":"null"}]},"scope":{"e'
    'num":["attempt","validation-process","observer-process"]}},"allOf":[{"if":{"properties":{"'
    'value":{"type":"null"}}},"then":{"properties":{"missingReason":{"enum":["not-measured","no'
    't-applicable","not-admitted","not-produced","not-probed","unavailable","cross-clock","cens'
    'ored","revoked","unknown"]}}},"else":{"properties":{"missingReason":{"type":"null"}}}}]},{'
    '"type":"object","additionalProperties":false,"required":["name","unit","value","missingRea'
    'son","scope"],"properties":{"name":{"const":"observer_wall_ns"},"unit":{"const":"ns"},"val'
    'ue":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"type":"null"}'
    ']},"missingReason":{"anyOf":[{"enum":["not-measured","not-applicable","not-admitted","not-'
    'produced","not-probed","unavailable","cross-clock","censored","revoked","unknown"]},{"type'
    '":"null"}]},"scope":{"enum":["attempt","validation-process","observer-process"]}},"allOf":'
    '[{"if":{"properties":{"value":{"type":"null"}}},"then":{"properties":{"missingReason":{"en'
    'um":["not-measured","not-applicable","not-admitted","not-produced","not-probed","unavailab'
    'le","cross-clock","censored","revoked","unknown"]}}},"else":{"properties":{"missingReason"'
    ':{"type":"null"}}}}]},{"type":"object","additionalProperties":false,"required":["name","un'
    'it","value","missingReason","scope"],"properties":{"name":{"const":"output_bytes"},"unit":'
    '{"const":"bytes"},"value":{"anyOf":[{"type":"integer","minimum":0,"maximum":92233720368547'
    '75807},{"type":"null"}]},"missingReason":{"anyOf":[{"enum":["not-measured","not-applicable'
    '","not-admitted","not-produced","not-probed","unavailable","cross-clock","censored","revok'
    'ed","unknown"]},{"type":"null"}]},"scope":{"enum":["attempt","validation-process","observe'
    'r-process"]}},"allOf":[{"if":{"properties":{"value":{"type":"null"}}},"then":{"properties"'
    ':{"missingReason":{"enum":["not-measured","not-applicable","not-admitted","not-produced","'
    'not-probed","unavailable","cross-clock","censored","revoked","unknown"]}}},"else":{"proper'
    'ties":{"missingReason":{"type":"null"}}}}]}]}},"oracle":{"type":"object","additionalProper'
    'ties":false,"required":["status","contractDigest","artifactDigest","check","semanticCorrec'
    'tness","humanLabel"],"properties":{"status":{"enum":["not-obtained","pending","verified","'
    'failed"]},"contractDigest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"artifactDigest":{'
    '"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"null"}]},"check":{"const":"'
    'validation-command-terminal-and-bound-log"},"semanticCorrectness":{"const":"unknown"},"hum'
    'anLabel":{"const":"unknown"}}},"censoring":{"type":"object","additionalProperties":false,"'
    'required":["state","reason","observedUntilNs"],"properties":{"state":{"enum":["not-censore'
    'd","right-censored","missing-outcome","revoked","invalid-oracle","not-applicable"]},"reaso'
    'n":{"anyOf":[{"enum":["not-measured","not-applicable","not-admitted","not-produced","not-p'
    'robed","unavailable","cross-clock","censored","revoked","unknown"]},{"type":"null"}]},"obs'
    'ervedUntilNs":{"anyOf":[{"type":"integer","minimum":0,"maximum":9223372036854775807},{"typ'
    'e":"null"}]}}},"diagnosis":{"type":"object","additionalProperties":false,"required":["clai'
    'mLevel","layer","causeCode","evidenceDigest","boundedDiagnosticAnnexDigest"],"properties":'
    '{"claimLevel":{"enum":["unknown","observed-mechanism","hypothesis"]},"layer":{"enum":["unk'
    'nown","product","verification","infrastructure"]},"causeCode":{"enum":["unassigned","os-ex'
    'ec-permission-denied","explicit-boundary-refusal","deadline-observed","cancellation-observ'
    'ed"]},"evidenceDigest":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"type":"nul'
    'l"}]},"boundedDiagnosticAnnexDigest":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"'
    '},{"type":"null"}]}},"allOf":[{"if":{"properties":{"claimLevel":{"const":"unknown"}}},"the'
    'n":{"properties":{"causeCode":{"const":"unassigned"}}}},{"if":{"properties":{"claimLevel":'
    '{"const":"observed-mechanism"}}},"then":{"properties":{"evidenceDigest":{"type":"string","'
    'pattern":"^[0-9a-f]{64}$"}}}}]},"spans":{"type":"array","maxItems":1024,"items":{"type":"o'
    'bject","additionalProperties":false,"required":["spanId","parentSpanId","clockDomainId","s'
    'tage","startedNs","finishedNs","status","accounting"],"properties":{"spanId":{"type":"stri'
    'ng","pattern":"^[0-9a-f]{32}$"},"parentSpanId":{"anyOf":[{"type":"string","pattern":"^[0-9'
    'a-f]{32}$"},{"type":"null"}]},"clockDomainId":{"type":"string","pattern":"^[0-9a-f]{32}$"}'
    ',"stage":{"enum":["queue","acquisition","decision","prepare","transport","validation","cle'
    'anup","observer"]},"startedNs":{"anyOf":[{"type":"integer","minimum":0,"maximum":922337203'
    '6854775807},{"type":"null"}]},"finishedNs":{"anyOf":[{"type":"integer","minimum":0,"maximu'
    'm":9223372036854775807},{"type":"null"}]},"status":{"enum":["complete","interrupted","unav'
    'ailable"]},"accounting":{"enum":["inclusive","exclusive"]}},"allOf":[{"if":{"properties":{'
    '"status":{"const":"complete"}}},"then":{"properties":{"startedNs":{"type":"integer","minim'
    'um":0,"maximum":9223372036854775807},"finishedNs":{"type":"integer","minimum":0,"maximum":'
    '9223372036854775807}}}},{"if":{"properties":{"status":{"const":"unavailable"}}},"then":{"p'
    'roperties":{"startedNs":{"type":"null"},"finishedNs":{"type":"null"}}}}]}},"amendmentReaso'
    'n":{"enum":["initial","late-maturity","correction"]}},"allOf":[{"if":{"properties":{"label'
    'State":{"const":"mature"}}},"then":{"properties":{"terminalNs":{"type":"integer","minimum"'
    ':0,"maximum":9223372036854775807},"availableAtNs":{"type":"integer","minimum":0,"maximum":'
    '9223372036854775807},"maturityNs":{"type":"integer","minimum":0,"maximum":9223372036854775'
    '807},"oracle":{"properties":{"status":{"const":"verified"},"artifactDigest":{"type":"strin'
    'g","pattern":"^[0-9a-f]{64}$"}}},"censoring":{"properties":{"state":{"const":"not-censored'
    '"},"reason":{"type":"null"}}}}}},{"if":{"properties":{"labelState":{"const":"censored"}}},'
    '"then":{"properties":{"censoring":{"properties":{"state":{"enum":["right-censored","missin'
    'g-outcome","revoked","invalid-oracle","not-applicable"]},"reason":{"enum":["not-measured",'
    '"not-applicable","not-admitted","not-produced","not-probed","unavailable","cross-clock","c'
    'ensored","revoked","unknown"]}}}}}}]}},"allOf":[{"if":{"properties":{"kind":{"const":"orig'
    'in"}}},"then":{"properties":{"payload":{"$ref":"#/$defs/origin"}}},"else":{"properties":{"'
    'payload":{"$ref":"#/$defs/outcome"}}}},{"if":{"properties":{"sourceState":{"const":"clean"'
    '}}},"then":{"properties":{"dirtyDiffDigest":{"type":"null"}}},"else":{"properties":{"dirty'
    'DiffDigest":{"type":"string","pattern":"^[0-9a-f]{64}$"}}}}]}'
)
_EVENT_SCHEMA = json.loads(_EVENT_SCHEMA_BYTES)
