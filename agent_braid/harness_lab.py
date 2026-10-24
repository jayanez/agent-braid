# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic laboratory fixture runner and containment qualification interface.

Runs one runner-owned Python fixture whose bytes are bound to the manifest's
``fixtureSha256`` in a bounded, killed-and-settled child process group with an
empty environment and a private working directory, and turns its JSON-lines events
plus the before/after working-directory files into a T012 observation.

Containment is labelled, never inherited: the built-in backend is ``simulated`` (it
limits and settles the child but does not confine filesystem, network or
credentials) and its label is carried on every result. Any other backend is
``native`` and refuses unless it carries an independently hash-verified
``Qualification`` that matches the manifest environment and enforces every effect
class. A result is evidence, never authorization: ``executionAuthorization`` stays
false and nothing here launches a host, model or paid route.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any

from .harness_manifest import HarnessManifest
from .harness_observation import (
    MAX_ARTIFACT_BYTES, MAX_ARTIFACTS, MAX_EVENTS, MAX_SEQ, ExportInventory, Observation,
    ObservationError, _is_relative, observe)
from .system_one import InvalidDecision, canonical, parse_json

QUALIFICATION_FORMAT = "braid-harness-containment-qualification/v0.1"
ENFORCED_EFFECTS = ("credential", "filesystem", "network", "process")
MAX_WALL_SECONDS = 60
MAX_FIXTURE_FILES = 32
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_CHILD_ENV = {"PYTHONHASHSEED": "0"}


class LabError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-lab-request"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-lab-request") -> None:
    if not condition:
        raise LabError(reason)


def _int(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


# --- containment qualification ------------------------------------------------------


@dataclass(frozen=True)
class Qualification:
    """Parsed native containment qualification; construction is not verification."""

    backend: str
    environment_sha256: str
    expires_at: int
    evidence_sha256: str
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()


def verify_qualification(raw: bytes, *, expected_sha256: str) -> Qualification:
    """Strictly parse a qualification and compare it with a trusted external hash.

    The record must declare that the backend enforces every effect class outside the
    prompt. Matching hashes prove byte identity only; the evidence it points at is
    judged by the T008 decision records, not here.
    """
    _require(type(expected_sha256) is str and _HASH.fullmatch(expected_sha256) is not None,
             "invalid-expected-hash")
    try:
        value = parse_json(raw)
    except InvalidDecision:
        raise LabError("invalid-qualification") from None
    ok = (set(value) == {"format", "backend", "kind", "environmentSha256", "enforced",
                         "expiresAt", "evidenceSha256"}
          and value["format"] == QUALIFICATION_FORMAT and value["kind"] == "native"
          and type(value["backend"]) is str and _ID.fullmatch(value["backend"]) is not None
          and value["enforced"] == list(ENFORCED_EFFECTS)
          and _int(value["expiresAt"], 0, 1 << 40)
          and all(type(value[k]) is str and _HASH.fullmatch(value[k]) is not None
                  for k in ("environmentSha256", "evidenceSha256")))
    _require(ok, "invalid-qualification")
    qualification = Qualification(value["backend"], value["environmentSha256"],
                                  value["expiresAt"], value["evidenceSha256"], canonical(value))
    _require(qualification.sha256 == expected_sha256, "qualification-drift")
    return qualification


@dataclass(frozen=True)
class FixtureLimits:
    """Trusted runner bounds for one fixture child; never read from the fixture."""

    wall_seconds: int = 10
    max_output_bytes: int = 65_536

    def __post_init__(self) -> None:
        _require(_int(self.wall_seconds, 1, MAX_WALL_SECONDS)
                 and _int(self.max_output_bytes, 1, 1_048_576), "invalid-limits")


@dataclass(frozen=True)
class ChildResult:
    """What a backend reports about one supervised child."""

    stdout: bytes
    exit_code: int | None
    timed_out: bool
    output_truncated: bool
    settled: bool


class ContainmentBackend:
    """Interface: supervised execution of an owned fixture. Subclass kind is ``native``."""

    kind = "native"
    qualification: Qualification | None = None

    def run(self, source: bytes, workdir: Path, limits: FixtureLimits) -> ChildResult:
        raise NotImplementedError


def _limit_child(limits: FixtureLimits):
    cap = limits.max_output_bytes + 1

    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (limits.wall_seconds + 1, limits.wall_seconds + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (cap, cap))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    return apply


def _settle(pgid: int) -> bool:
    """Kill the whole group, then confirm no member remains."""
    for attempt in range(40):
        try:
            os.killpg(pgid, signal.SIGKILL if attempt == 0 else 0)
        except ProcessLookupError:
            return True
        except OSError:
            return False
        time.sleep(0.05)
    return False


class SimulatedContainment(ContainmentBackend):
    """Limits and settles the child but confines nothing; results say ``simulated``."""

    kind = "simulated"

    def run(self, source: bytes, workdir: Path, limits: FixtureLimits) -> ChildResult:
        out_dir = Path(tempfile.mkdtemp(prefix="braid-lab-out-"))
        try:
            out_path = out_dir / "stdout"
            with open(out_path, "wb") as sink:
                try:
                    child = subprocess.Popen(
                        [sys.executable, "-I", "-S", "-c", source.decode("utf-8")],
                        cwd=workdir, env=_CHILD_ENV, stdin=subprocess.DEVNULL, stdout=sink,
                        stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True,
                        preexec_fn=_limit_child(limits))
                except (OSError, ValueError, UnicodeDecodeError):
                    raise LabError("launch-failed") from None
                timed_out = False
                try:
                    exit_code = child.wait(timeout=limits.wall_seconds)
                except subprocess.TimeoutExpired:
                    timed_out, exit_code = True, None
                    child.kill()
                    child.wait()  # reap the leader so only live group members remain
                settled = _settle(child.pid)
            with open(out_path, "rb") as stream:
                data = stream.read(limits.max_output_bytes + 1)
            truncated = len(data) > limits.max_output_bytes
            return ChildResult(data[:limits.max_output_bytes], exit_code, timed_out,
                               truncated, settled)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)


# --- fixture workspace --------------------------------------------------------------


def _write_inputs(workdir: Path, inputs: Mapping[str, bytes]) -> None:
    for name, content in inputs.items():
        target = workdir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)


def _collect(workdir: Path) -> tuple[dict[str, bytes], bool]:
    """Read regular files below workdir; any unsafe or excess entry marks it lossy."""
    files: dict[str, bytes] = {}
    complete = True
    stack = [(workdir, 0)]
    while stack:
        directory, depth = stack.pop()
        for entry in os.scandir(directory):
            rel = Path(entry.path).relative_to(workdir).as_posix()
            if entry.is_symlink() or depth >= 7:
                complete = False
            elif entry.is_dir(follow_symlinks=False):
                stack.append((Path(entry.path), depth + 1))
            elif entry.is_file(follow_symlinks=False):
                fd = os.open(entry.path, os.O_RDONLY | os.O_NOFOLLOW)
                with os.fdopen(fd, "rb") as stream:
                    data = stream.read(MAX_ARTIFACT_BYTES + 1)
                if len(files) >= MAX_ARTIFACTS or len(data) > MAX_ARTIFACT_BYTES \
                        or not _is_relative(rel):
                    complete = False
                else:
                    files[rel] = data
            else:
                complete = False
    return files, complete


def _parse_events(stdout: bytes) -> tuple[list[dict], list[str]]:
    events: list[dict] = []
    errors: list[str] = []
    for line in stdout.split(b"\n"):
        if not line:
            continue
        if len(events) >= MAX_EVENTS:
            errors.append("event-overflow")
            break
        try:
            events.append(parse_json(line))
        except InvalidDecision:
            errors.append("malformed-line")
    return events, list(dict.fromkeys(errors))


def _supervisor_terminal(events: list[dict], child: ChildResult) -> None:
    """Record a termination the supervisor itself observed; never a completion."""
    if any(e.get("kind") == "terminal" for e in events):
        return
    state = "interrupted" if child.timed_out else "failed" if child.exit_code else None
    seqs = [e["seq"] for e in events if type(e.get("seq")) is int]
    if state and len(events) < MAX_EVENTS and max(seqs, default=-1) < MAX_SEQ:
        events.append({"seq": max(seqs, default=-1) + 1, "kind": "terminal", "state": state})


@dataclass(frozen=True)
class LabResult:
    """Evidence about one fixture run; never an authorization."""

    observation: Observation
    containment: str
    exit_code: int | None
    timed_out: bool
    output_truncated: bool
    settled: bool
    cleaned: bool
    executionAuthorization: bool = False

    def to_dict(self) -> dict:
        return {"observationSha256": self.observation.sha256, "containment": self.containment,
                "exitCode": self.exit_code, "timedOut": self.timed_out,
                "outputTruncated": self.output_truncated, "settled": self.settled,
                "cleaned": self.cleaned, "executionAuthorization": False}


def _check_backend(backend: Any, manifest: HarnessManifest, now: int) -> str:
    if type(backend) is SimulatedContainment:
        return "simulated"
    _require(isinstance(backend, ContainmentBackend) and backend.kind == "native",
             "invalid-backend")
    qualification = backend.qualification
    _require(isinstance(qualification, Qualification)
             and qualification.environment_sha256 == manifest.data["environment"]["sha256"]
             and now < qualification.expires_at, "containment-unqualified")
    return "native"


def run_fixture(manifest: HarnessManifest, fixture: bytes, *, backend: ContainmentBackend,
                attempt_id: str, inventory: ExportInventory, now: int, retention_seconds: int,
                inputs: Mapping[str, bytes] | None = None,
                limits: FixtureLimits | None = None) -> LabResult:
    """Run an owned fixture under ``backend`` and observe it; refuse, never repair."""
    limits = limits or FixtureLimits()
    inputs = {} if inputs is None else inputs
    _require(isinstance(manifest, HarnessManifest) and isinstance(limits, FixtureLimits))
    label = _check_backend(backend, manifest, now)
    manifest_limits = manifest.data["limits"]
    _require(type(fixture) is bytes and 0 < len(fixture) <= manifest_limits["maxFileBytes"],
             "invalid-fixture")
    _require(sha256(fixture).hexdigest() == manifest.bindings["fixture"], "fixture-drift")
    _require(limits.max_output_bytes <= manifest_limits["maxStageOutputBytes"], "invalid-limits")
    _require(isinstance(inputs, Mapping) and len(inputs) <= min(MAX_FIXTURE_FILES, manifest_limits["maxFiles"])
             and len({str(k).casefold() for k in inputs}) == len(inputs)
             and all(_is_relative(k) and type(v) is bytes
                     and len(v) <= min(MAX_ARTIFACT_BYTES, manifest_limits["maxFileBytes"])
                     for k, v in inputs.items()), "invalid-inputs")
    source = "fixture" if label == "simulated" else "host"
    observe_args = dict(manifest_sha256=manifest.sha256, attempt_id=attempt_id, source=source,
                        inventory=inventory, now=now, retention_seconds=retention_seconds)
    try:
        observe([], **observe_args)  # validate arguments before anything executes
    except ObservationError as exc:
        raise LabError(exc.reason) from None

    try:
        workdir = Path(tempfile.mkdtemp(prefix="braid-lab-work-"))
    except OSError:
        raise LabError("workspace-unavailable") from None
    try:
        try:
            _write_inputs(workdir, inputs)
            try:
                child = backend.run(fixture, workdir, limits)
            except LabError:
                raise
            except Exception:  # untrusted backend: surface a fixed reason only
                raise LabError("backend-failed") from None
            after, complete = _collect(workdir)
        except OSError:
            raise LabError("workspace-unavailable") from None
        _require(isinstance(child, ChildResult), "invalid-backend-result")
        events, errors = _parse_events(child.stdout)
        _supervisor_terminal(events, child)
        if child.output_truncated:
            errors.append("output-truncated")
        if not child.settled:
            errors.append("unsettled-child")
        if not complete:
            errors.append("artifact-unobservable")
        try:
            observation = observe(events, before=dict(inputs), after=after,
                                  transport_errors=errors, **observe_args)
        except ObservationError as exc:
            raise LabError(exc.reason) from None
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return LabResult(observation, label, child.exit_code, child.timed_out,
                     child.output_truncated, child.settled, not workdir.exists())
