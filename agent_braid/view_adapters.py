# SPDX-License-Identifier: AGPL-3.0-only
"""Artifact adapters: Agent Braid artifacts to agent-braid-loom/v0.1 events (SPEC-061 REQ-002).

Each `events_from_<family>(data, *, path, seq_start=1)` is a pure function of the
artifact bytes. It parses them strictly, translates what the source already says
without recomputing or reinterpreting it, and returns validated events numbered from
`seq_start`. `path` is the artifact path relative to the root the user named; the
event `evidenceRef` is that path plus the SHA-256 of the bytes, so every event is
`rehashed`. A grant expiry the viewer observes after the recorded validity is the one
`derived` event. Every event is read-only: `executionAuthorization` is false.

Each adapter has a table of the source schema versions it supports (SUPPORTED_VERSIONS).
Another version, bytes that are not one strict JSON object, or content that does not
fit the contract yield a single `observation.gap` with reason `source-unsupported`
instead of a guess. A crossing whose lists or text exceed the contract caps is not
emitted; a `stream-truncated` gap with the same evidence reference takes its place.
Scheduler strand closes carry the outcome `ok` because the preparation evidence only
exists once every worker finished and verified.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any, Callable

from .view_loom import MAX_SEQ, LoomError, validate_event

MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
HOST = "braid"
_CAP_REASONS = ("too-many-items", "free-text")

# adapter -> (version field, supported versions)
SUPPORTED_VERSIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "analysis-report": ("reportVersion", ("0.1.0-alpha",)),
    "git-replay-plan": ("gitPlanVersion", ("0.1.0-alpha",)),
    "scheduler-preparation": ("runtimePreparationEvidenceVersion", ("0.1.0-alpha",)),
    "runtime-grant": ("runtimeOperatorGrantVersion", ("0.1.0-alpha",)),
    "runtime-state": ("gitRuntimeStateVersion", ("0.1.0-alpha",)),
}


class AdapterError(ValueError):
    """An artifact could not be read safely (a caller or file-system problem, not a content gap)."""


def read_artifact(root: str | Path, path: str, *, limit: int = MAX_ARTIFACT_BYTES) -> bytes:
    """Read one regular file under `root`: no `..`, no symbolic link, at most `limit` bytes."""
    parts = path.split("/") if isinstance(path, str) else []
    if not path or path.startswith("/") or ".." in parts or "\x00" in path:
        raise AdapterError("artifact path must be relative, without '..'")
    base = Path(root).resolve()
    try:
        target = (base / path).parent.resolve() / parts[-1]
        target.relative_to(base)
        descriptor = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    except (OSError, ValueError) as exc:
        raise AdapterError("artifact is outside the root, a link, or unreadable") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise AdapterError("artifact is not a regular file within the size limit")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
    finally:
        os.close(descriptor)
    if len(data) > limit:
        raise AdapterError("artifact grew beyond the size limit while being read")
    return data


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _constant(token: str) -> None:
    raise ValueError(f"non-finite JSON number: {token}")


def _load(data: bytes, adapter: str) -> dict[str, Any]:
    document = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    if not isinstance(document, dict):
        raise ValueError("artifact is not a JSON object")
    field, versions = SUPPORTED_VERSIONS[adapter]
    version = document.get(field)
    if not isinstance(version, str) or version not in versions:
        raise ValueError(f"{field} is not a supported version")
    return document


class _Source:
    """Event factory bound to one artifact: adapter, evidence reference and verification."""

    def __init__(self, adapter: str, data: bytes, path: str) -> None:
        self.adapter = adapter
        self.evidence = {"path": path, "sha256": hashlib.sha256(data).hexdigest()}

    def event(self, kind: str, data: dict[str, Any], *, rel_ms: int = 0, timed: bool = False,
              compatibility_class: int | None = None, derived: bool = False) -> dict[str, Any]:
        """A validated event with seq 1; `_number` assigns the real sequence numbers."""
        return validate_event({
            "schemaVersion": "agent-braid-loom/v0.1",
            "seq": 1,
            "kind": kind,
            "at": {"relMs": rel_ms, "basis": "artifact-relative" if timed else "sequence-only"},
            "source": {"adapter": self.adapter, "evidenceRef": dict(self.evidence), "host": HOST,
                       "verification": "derived" if derived else "rehashed"},
            "assurance": {"compatibilityClass": compatibility_class, "notAGuarantee": True},
            "executionAuthorization": False,
            "data": data,
        })

    def gap(self, reason: str) -> dict[str, Any]:
        return self.event("observation.gap", {"reason": reason, "strandId": None, "fromSeq": None, "toSeq": None})


def _number(events: list[dict[str, Any]], seq_start: int) -> list[dict[str, Any]]:
    if type(seq_start) is not int or seq_start < 1 or seq_start + len(events) - 1 > MAX_SEQ:
        raise LoomError("out-of-range", "seq_start leaves no room for the events in 1..MAX_SEQ")
    for offset, event in enumerate(events):
        event["seq"] = seq_start + offset
    return events


def _run(adapter: str, data: bytes, path: str, seq_start: int,
         build: Callable[[dict[str, Any], _Source], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    source = _Source(adapter, data, path)
    fallback = source.gap("source-unsupported")  # also refuses an invalid evidence path up front
    try:
        events = build(_load(data, adapter), source)
    except (ValueError, KeyError, TypeError):
        events = [fallback]
    return _number(events, seq_start)


def _ms(nanoseconds: Any) -> int:
    if type(nanoseconds) is not int:
        raise TypeError("a timestamp is an integer")
    return nanoseconds // 1_000_000


def _analysis(report: dict[str, Any], source: _Source) -> list[dict[str, Any]]:
    report_id = report["analysisId"]
    counts = report["summary"]["classifications"]
    events = [source.event("analysis.report", {
        "reportId": report_id,
        "operationCount": report["summary"]["operationCount"],
        "pairCount": report["summary"]["pairCount"],
        "summary": {"independentCandidate": counts["independent-candidate"], "ordered": counts["ordered"],
                    "conflicting": counts["conflicting"], "unknown": counts["unknown"]},
        "uncertainty": report["uncertainty"],
        "limits": report["limits"],
    })]
    for operation in report["operations"]:
        identifier = operation["instanceId"]
        events.append(source.event("strand.open", {
            "strandId": identifier, "host": HOST, "role": "operation", "label": identifier,
            "parentStrandId": None,
        }))
    for pair in report["interactions"]:
        evidence = pair["evidence"]
        try:
            events.append(source.event("crossing.classified", {
                "reportId": report_id, "left": pair["left"], "right": pair["right"],
                "classification": pair["classification"], "sharedResources": pair["sharedResources"],
                "reasons": pair["reasons"], "constraints": pair["constraints"],
                "evidence": {"method": evidence["method"], "coverage": evidence["coverage"],
                             "ruleSet": evidence["ruleSet"]},
            }, compatibility_class=evidence["assuranceClass"]))
        except LoomError as exc:
            if exc.reason not in _CAP_REASONS:
                raise
            events.append(source.gap("stream-truncated"))
    return events


def _git_plan(plan: dict[str, Any], source: _Source) -> list[dict[str, Any]]:
    order = plan["fallbackOrder"]
    return [source.event("wave.planned", {
        "planId": plan["planDigest"], "mode": plan["mode"], "waves": plan["waves"],
        "serialSlots": 0 if order is None else len(order),
    })]


# Same-time order inside a scheduler preparation: a wave starts before its strands open
# and finishes after they close.
_WAVE_STARTED, _STRAND_OPEN, _STRAND_CLOSE, _WAVE_FINISHED = range(4)


def _scheduler(evidence: dict[str, Any], source: _Source) -> list[dict[str, Any]]:
    schedule_id = evidence["scheduleDigest"]
    waves: dict[int, list[dict[str, Any]]] = {}
    timeline: list[tuple[int, int, int, str, dict[str, Any]]] = []
    for worker in evidence["workers"]:
        started, finished = worker["startedNs"], worker["finishedNs"]
        identifier = worker["operationId"]
        _ms(started), _ms(finished)
        waves.setdefault(worker["wave"], []).append(worker)
        number = worker["wave"]
        timeline.append((started, _STRAND_OPEN, number, "strand.open", {
            "strandId": identifier, "host": HOST, "role": "worker", "label": identifier,
            "parentStrandId": None}))
        timeline.append((finished, _STRAND_CLOSE, number, "strand.close",
                         {"strandId": identifier, "outcome": "ok"}))
    for number, members in waves.items():
        data = {"scheduleId": schedule_id, "wave": number, "strands": [w["operationId"] for w in members]}
        timeline.append((min(w["startedNs"] for w in members), _WAVE_STARTED, number, "wave.started", data))
        timeline.append((max(w["finishedNs"] for w in members), _WAVE_FINISHED, number, "wave.finished", data))
    timeline.sort(key=lambda item: item[:3])
    return [source.event(kind, data, rel_ms=_ms(at), timed=True) for at, _, _, kind, data in timeline]


def _grant_data(grant: dict[str, Any], derived: bool) -> dict[str, Any]:
    return {"grantId": grant["grantId"], "action": grant["action"], "derived": derived}


def _grant(grant: dict[str, Any], source: _Source, now: int | None) -> list[dict[str, Any]]:
    issued, expires, state = grant["issuedAt"], grant["expiresAt"], grant["state"]
    if type(issued) is not int or type(expires) is not int or expires <= issued:
        raise ValueError("a grant is valid from issuedAt to a later expiresAt")
    events = [source.event("grant.issued", _grant_data(grant, False), timed=True)]
    if state == "consumed":
        events.append(source.event("grant.consumed", _grant_data(grant, False)))
    elif state != "issued":
        raise ValueError("unknown grant state")
    elif now is not None and now >= expires:
        events.append(source.event("grant.expired", _grant_data(grant, True),
                                   rel_ms=(expires - issued) * 1000, timed=True, derived=True))
    return events


def _runtime_state(state: dict[str, Any], source: _Source) -> list[dict[str, Any]]:
    return [source.event("runtime.phase", {"manifestDigest": state["manifestDigest"], "phase": state["phase"]})]


def events_from_analysis(data: bytes, *, path: str, seq_start: int = 1) -> list[dict[str, Any]]:
    """`analysis.analyze()` report: one report event, one strand per operation, one crossing per pair."""
    return _run("analysis-report", data, path, seq_start, _analysis)


def events_from_git_plan(data: bytes, *, path: str, seq_start: int = 1) -> list[dict[str, Any]]:
    """Git replay plan: its mode, waves and fallback order as one `wave.planned`."""
    return _run("git-replay-plan", data, path, seq_start, _git_plan)


def events_from_scheduler(data: bytes, *, path: str, seq_start: int = 1) -> list[dict[str, Any]]:
    """Scheduler preparation evidence: worker strands and the start and finish of each wave."""
    return _run("scheduler-preparation", data, path, seq_start, _scheduler)


def events_from_grant(data: bytes, *, path: str, seq_start: int = 1, now: int | None = None) -> list[dict[str, Any]]:
    """Operator grant file. `now` (epoch seconds) is the viewer clock: at or after `expiresAt`
    an issued grant gets one derived `grant.expired`. Without it nothing is derived."""
    if now is not None and type(now) is not int:
        raise TypeError("now is an integer count of epoch seconds")
    return _run("runtime-grant", data, path, seq_start, lambda grant, source: _grant(grant, source, now))


def events_from_runtime_state(data: bytes, *, path: str, seq_start: int = 1) -> list[dict[str, Any]]:
    """Runtime `state.json`: its phase and manifest digest as one `runtime.phase`."""
    return _run("runtime-state", data, path, seq_start, _runtime_state)
