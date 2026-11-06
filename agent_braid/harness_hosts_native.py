# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-048/T008 native wiring: the Claude cohort unit over the qualified containment.

Glue between the host-profile gate (``harness_hosts.HostQualificationRun``) and the SPEC-065
native stack (``NativeClaudeTransport`` over a ``ContainmentBackend``). It adds only what the
pieces cannot know about each other:

* ``issued_records`` turns the founder's SPEC-065/T010 issuance record into the canonical
  containment and host record bytes, each checked against a trusted hash the caller supplies;
* ``qualified_policy`` builds the ``ContainmentPolicy`` from exactly the qualified pins and
  refuses on any difference from the qualified environment document (profile bytes included);
* ``guard_unhashed`` is the MDRV-04 guard: the four modules the environment hash omits must
  keep the bytes they had when the containment was qualified, unless the founder approved a
  specific new hash;
* ``run_native_unit`` admits one unit, runs it through the native transport and always
  settles it against the D2 caps, whatever the run did.

Nothing here starts a process, opens an account or reads a quota: the backend, the readings
and the clock are injected by the trusted driver running in the lab account. Every result
keeps ``executionAuthorization`` false.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from . import harness_containment_macos as mac
from . import harness_context as ctx
from . import harness_manifest as manifests
from . import harness_host_claude as hc
from . import harness_hosts as hh
from . import harness_lab as lab
from . import harness_quota
from .harness_transport_claude import NativeClaudeTransport
from .system_one import InvalidDecision, canonical, digest, parse_json, thaw

ISSUANCE_FORMAT = "spec065-issuance-v1"
# sha256 of the modules the environment hash omits (MDRV-04), at the qualified commit 320b00c4.
UNHASHED = {
    "harness_manifest.py": "6624d79de56e702062ba02cefb5cab3d6ec7a58b310c3520d7bdbe024df7fe61",
    "harness_context.py": "026a29c21b3d52afad4c8fb1f11730fd410d8f17d5d437cecfaf409732dd657e",
    "harness_observation.py": "053075bad3ac4f18da28569f4c60f4d32923a5a4f1ac8c183cd5941f41cd2a2a",
    "system_one.py": "8a52a047bc72ba4f1099df60c1051178fbcb7735ee4d6e615d9b8052bbb31f44",
}


class NativeWiringError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-native-wiring"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-native-wiring") -> None:
    if not condition:
        raise NativeWiringError(reason)


# --- issued records ------------------------------------------------------------------------


@dataclass(frozen=True)
class IssuedRecords:
    """Canonical qualification bytes, verified by the backend's own parsers."""

    containment: bytes
    containment_sha256: str
    host: bytes
    host_sha256: str
    environment_sha256: str
    expires_at: int

    @property
    def executionAuthorization(self) -> bool:
        return False


def issued_records(raw: bytes, *, containment_sha256: str, host_sha256: str) -> IssuedRecords:
    """Records of a founder-issued SPEC-065 record, bound to hashes the caller trusts."""
    try:
        value = parse_json(raw)
    except InvalidDecision:
        raise NativeWiringError("invalid-issuance") from None
    decision = value.get("decision") if type(value) is dict else None
    records = value.get("records") if type(value) is dict else None
    _require(type(decision) is dict and type(records) is dict
             and value.get("recordVersion") == ISSUANCE_FORMAT
             and value.get("executionAuthorization") is False
             and decision.get("disposition") == "issued", "invalid-issuance")
    containment, host = canonical(records.get("containment")), canonical(records.get("host"))
    _require(sha256(containment).hexdigest() == containment_sha256
             and sha256(host).hexdigest() == host_sha256, "qualification-drift")
    try:
        verified = lab.verify_qualification(containment, expected_sha256=containment_sha256)
        verified_host = hc.verify_host_qualification(host, expected_sha256=host_sha256)
    except (lab.LabError, hc.ClaudeHostError) as exc:
        raise NativeWiringError(exc.reason) from None
    _require(verified.environment_sha256 == verified_host.environment_sha256, "qualification-drift")
    return IssuedRecords(containment, containment_sha256, host, host_sha256,
                         verified.environment_sha256, min(verified.expires_at, verified_host.expires_at))


# --- policy from exactly the qualified inputs ----------------------------------------------


def probe_catalog_sha256() -> str:
    return mac._probe_catalog_sha256()


def qualified_policy(environment: Mapping[str, Any], *, account: str, run_root: str, config_dir: str,
                     claude: str, interpreter: str, interpreter_sha256: str, interpreter_root: str,
                     proxy_port: int) -> mac.ContainmentPolicy:
    """Policy from the qualified pins; any difference from ``environment`` refuses.

    ``environment`` is the qualified bundle's ``environment.json``. The pins (``claude`` and
    ``sandbox-exec`` hashes, version, catalog) come from it; no helper or refresh endpoint is
    added, and the rendered launch profile must hash to the qualified ``profileSha256``.
    """
    keys = ("claudeSha256", "claudeVersion", "sandboxExecSha256", "probeCatalogSha256", "profileSha256")
    _require(isinstance(environment, Mapping)
             and all(type(environment.get(k)) is str for k in keys), "invalid-environment")
    _require(environment["claudeVersion"] == mac.CLAUDE_VERSION
             and environment["probeCatalogSha256"] == probe_catalog_sha256(), "environment-drift")
    try:
        policy = mac.ContainmentPolicy(
            account=account, run_root=run_root, config_dir=config_dir, claude=claude,
            claude_sha256=environment["claudeSha256"], claude_version=environment["claudeVersion"],
            interpreter=interpreter, interpreter_sha256=interpreter_sha256,
            interpreter_root=interpreter_root, sandbox_exec_sha256=environment["sandboxExecSha256"],
            proxy_port=proxy_port)
    except lab.LabError as exc:
        raise NativeWiringError(exc.reason) from None
    _require(sha256(policy.render("launch")).hexdigest() == environment["profileSha256"],
             "environment-drift")
    return policy


# --- MDRV-04 guard -------------------------------------------------------------------------


def guard_unhashed(directory: Path | str, approved: Mapping[str, str] | None = None) -> None:
    """Refuse unless each omitted module has its qualified bytes or a founder-approved hash."""
    approved = approved or {}
    for name, qualified in UNHASHED.items():
        try:
            actual = sha256((Path(directory) / name).read_bytes()).hexdigest()
        except OSError:
            raise NativeWiringError("unhashed-file-changed") from None
        _require(actual in (qualified, approved.get(name)), "unhashed-file-changed")


# --- readings and the unit -----------------------------------------------------------------


def reading_of(observation: hh.QuotaObservation) -> dict:
    """The ``harness_quota`` reading form of a host-gate observation."""
    stamp = datetime.fromtimestamp(observation.observed_at, timezone.utc)
    return {"source": harness_quota.SOURCE, "observedAt": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fiveHourPercent": int(observation.five_hour_percent),
            "weeklyPercent": int(observation.weekly_percent),
            "extraUsageEnabled": observation.extra_usage_enabled}


@dataclass(frozen=True)
class UnitOutcome:
    """A settled unit and the host result, if the run produced one."""

    record: hh.UnitRecord
    result: hc.ClaudeHostResult | None

    @property
    def executionAuthorization(self) -> bool:
        return False


def run_native_unit(*, run: hh.HostQualificationRun, backend: lab.ContainmentBackend,
                    workdir: Path | str, containment: bytes, containment_sha256: str,
                    manifest: Any, context: Any, request: hc.ClaudeRequest,
                    compatibility: hc.CompatibilityWindow, inventory: Any, attempt_id: str,
                    before: hh.QuotaObservation,
                    read_after: Callable[[], hh.QuotaObservation | None],
                    now: Callable[[], datetime], retention_seconds: int,
                    settle_now: Callable[[], int], environ: Mapping[str, str] | None = None) -> UnitOutcome:
    """Admit, run and settle one serial unit; settlement happens even when the run raises.

    The cohort state handed to the T004 quota gate is derived from the run (units settled and
    weekly consumption since the baseline), never from the caller. Admission refusals raise
    before anything launches; a host error is re-raised after the unit is settled
    not-completed.
    """
    started = now()
    ticket = run.admit_unit(before, containment=containment, containment_sha256=containment_sha256,
                            now=int(started.timestamp()))
    cohort = {"unitsUsed": len(run.verdict().units),
              "cohortWeeklyPercent": int(before.weekly_percent - run.baseline.weekly_percent)}
    result = error = None
    try:
        transport = NativeClaudeTransport(backend, workdir=workdir, pre_reading=reading_of(before),
                                          quota=("cohort", cohort), clock=now,
                                          environ=environ)
        result = hc.run_claude(manifest, context, transport=transport, request=request,
                               compatibility=compatibility, attempt_id=attempt_id,
                               inventory=inventory, now=ticket.admitted_at,
                               retention_seconds=retention_seconds,
                               limits=hc.HostLimits(wall_seconds=run.caps.unit_wall_seconds),
                               qualification=backend.host_qualification)
    except Exception as exc:  # settle first, then surface the original refusal
        error = exc
    try:
        after = read_after()
    except Exception:
        after = None  # a lost reading is a breach, not a crash
    completed = result is not None and result.observation.to_dict()["terminal"] == "completed"
    record = run.settle_unit(ticket, after, completed=completed, now=settle_now())
    if error is not None:
        raise error
    return UnitOutcome(record, result)


# --- the fixed unit workload ---------------------------------------------------------------

UNIT_TASK = b"Read the owned note and answer in one short sentence what it says.\n"
UNIT_NOTE = b"T008 unit note: the lab is a closed room.\n"
UNIT_MODEL, UNIT_EFFORT = "haiku", "low"


def unit_inputs(*, environment_sha256: str, claude_sha256: str, containment_sha256: str,
                host_qualification_sha256: str, backend_name: str = mac.BACKEND):
    """Manifest and context of the fixed read-only T008 unit; every pin is the backend's own.

    One owned note, read tools only, Haiku at low effort on the subscription route. The
    manifest declares exactly the values ``NativeClaudeTransport.verify_containment``
    compares, so a unit built from different pins is refused before it launches.
    """
    def file(path, content, **extra):
        return {"path": path, "sha256": sha256(content).hexdigest(), "sizeBytes": len(content), **extra}

    base = [file("guidance/main.md", b"Answer briefly.\n")]
    candidate = [file("guidance/main.md", b"Answer briefly and exactly.\n")]
    value = {
        "format": manifests.FORMAT, "profile": manifests.NATIVE_PROFILE,
        "source": {"commit": "1" * 40, "selectedInputs": [file("task.txt", UNIT_TASK, origin="committed")]},
        "base": {"sha256": digest(base), "files": base},
        "candidate": {"sha256": digest(candidate), "files": candidate},
        "task": {"id": "T008-UNIT", "inputSha256": digest({"task": "t008-unit"}),
                 "fixtureSha256": digest({"oracle": "none: containment and quota unit"})},
        "context": [{"id": "note", "path": "a/note.txt", "sha256": sha256(UNIT_NOTE).hexdigest(),
                     "sizeBytes": len(UNIT_NOTE), "trust": "untrusted-evidence", "selected": True}],
        "host": {"kind": "claude", "executableSha256": claude_sha256, "build": mac.CLAUDE_VERSION,
                 "requested": {"model": UNIT_MODEL, "effort": UNIT_EFFORT, "route": "subscription"},
                 "observed": {"provider": None, "model": None, "build": None, "route": None}},
        "containment": {"backend": backend_name, "qualificationSha256": containment_sha256},
        "hostQualificationSha256": host_qualification_sha256,
        "tools": [{"id": "fixture-contract", "sha256": "3" * 64}],
        "policy": {"version": "t008-v1", "sha256": "4" * 64},
        "verifier": {"version": "none-v1", "sha256": "5" * 64},
        "normalizer": {"version": "exact-v1", "sha256": "6" * 64},
        "environment": {"os": "Darwin", "architecture": "arm64", "sha256": environment_sha256,
                        "outputDestinationSha256": "8" * 64},
        "envelopeSha256": "9" * 64,
        "allowedComponentPaths": ["guidance/main.md"],
        "effects": {"read": ["base/guidance/main.md", "candidate/guidance/main.md",
                             "context/a/note.txt", "source/task.txt"],
                    "write": ["lab/guidance/main.md"], "delete": []},
        "limits": thaw(manifests.NATIVE_LIMITS), "executionAuthorization": False,
    }
    manifest = manifests.parse_manifest(canonical(value))
    budget = ctx.ContextBudget(max_entries=4, max_entry_bytes=1024, max_total_bytes=2048, excerpt_bytes=128)
    return manifest, ctx.assemble_context(manifest, {"a/note.txt": UNIT_NOTE}, budget=budget)
