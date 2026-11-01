# SPDX-License-Identifier: AGPL-3.0-only
"""Native Claude transport behind the contained launcher (SPEC-065 T006).

``NativeClaudeTransport`` is the ``kind = "native"`` ``ClaudeTransport``. It never starts a
process itself: every launch, the version probe included, goes through the T005 backend's
``launch`` entry point, which applies the NC-11 pre-session (F4) check, the deny-default
profile and the NC-8 limits. This module adds what only the transport can know:

* K2: ``verify_containment`` (called by ``run_claude`` before anything launches) refuses
  unless the backend passes ``harness_lab._check_backend`` and the manifest's
  ``containment.qualificationSha256``, ``hostQualificationSha256``, ``host.executableSha256``
  and ``host.build`` equal the backend's verified records and pinned policy.
* K4: ``argv[0]`` is the backend's absolute pinned executable, hash-checked at every launch;
  a bare ``claude`` is never resolved through ``PATH``. ``NATIVE_ENV_ALLOW`` is the typed
  environment policy the backend renders (NC-5, NC-7).
* K1: the launcher streams stdout to ``on_output`` while the child runs; the first ``init``
  event with an ``apiKeySource`` outside the subscription set kills the group at once and
  the output is cut at that line, so no ``assistant``/``result`` event is ever accepted.
  A launcher without ``on_output`` is refused: the check is never deferred to the end.
* the quota gate (T004) before the launch, one attempt per transport instance, no retry and
  no alternative route.

Results are evidence, never authorization; the stream, route and drift checks stay in
``run_claude``. Nothing here reads a quota source or a clock beyond the injected ones.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from hashlib import sha256
import inspect
import os
from pathlib import Path
import stat
import threading
from typing import Any

from . import harness_quota
from .harness_host_claude import (
    ENV_DENY, SUBSCRIPTION_KEY_SOURCES, ClaudeHostError, ClaudeTransport, HostLimits,
    HostQualification, HostRun, LaunchPlan, parse_version)
from .harness_lab import ContainmentBackend, LabError, Qualification, _check_backend
from .harness_manifest import NATIVE_BUILD, NATIVE_PROFILE, HarnessManifest
from .system_one import InvalidDecision, parse_json

# NC-5 (dedicated user's own login) and NC-7 (config and temp locations): the variables the
# contained launcher sets; no token variable exists.
NATIVE_ENV_ALLOW = ("CLAUDE_CONFIG_DIR", "HOME", "PATH", "TMPDIR")
VERSION_WALL_SECONDS = 10
VERSION_MAX_OUTPUT_BYTES = 4096
MAX_INIT_BYTES = 65_536  # an init line longer than this is not an init line
_RELAY_SECONDS = 0.05


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ClaudeHostError(reason)


def _file_sha256(path: str) -> str | None:
    """Hash of a regular, non-symlinked file, or ``None``; the backend re-checks trust."""
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            return None
        return sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


class _InitWatch:
    """Live K1 watcher fed with stdout chunks; decides at the first complete event line.

    ``violation`` is ``"route"`` when ``init`` reports a key source outside the
    subscription set, ``"no-init"`` when an ``assistant``/``result`` event or an oversized
    line comes first. ``keep`` is how many stdout bytes may reach ``run_claude``.
    """

    def __init__(self, stop: threading.Event):
        self._stop = stop
        self._buffer = b""
        self._seen = 0  # bytes of complete lines consumed
        self.received = 0
        self.done = False
        self.violation: str | None = None
        self.keep = 0

    def feed(self, data: bytes) -> None:
        self.received += len(data)
        if self.done:
            return
        self._buffer += data
        while not self.done:
            end = self._buffer.find(b"\n")
            if end < 0:
                if len(self._buffer) > MAX_INIT_BYTES:
                    self._reject("no-init", 0)
                return
            line, start = self._buffer[:end], self._seen
            self._seen += end + 1
            self._buffer = self._buffer[end + 1:]
            self._line(line, start, self._seen)

    def _line(self, line: bytes, start: int, end: int) -> None:
        try:
            event = parse_json(line) if line.strip() else None
        except InvalidDecision:
            event = None  # malformed lines are classified by run_claude
        kind = event.get("type") if type(event) is dict else None
        if kind == "system" and event.get("subtype") == "init":
            if event.get("apiKeySource") in SUBSCRIPTION_KEY_SOURCES:
                self.done = True
            else:
                self._reject("route", end)
        elif kind in ("assistant", "result"):
            self._reject("no-init", start)

    def _reject(self, violation: str, keep: int) -> None:
        self.done, self.violation, self.keep = True, violation, keep
        self._stop.set()  # the launcher kills and settles the group on this event


class NativeClaudeTransport(ClaudeTransport):
    """Single-attempt native transport over a verified ``ContainmentBackend``.

    ``backend`` must expose ``policy`` (pinned ``claude`` path and hash, ``claude_version``),
    ``qualification``, ``host_qualification`` and ``launch`` with an ``on_output`` hook.
    ``quota`` selects the T004 gate: ``("cohort", state)`` or ``("probe", sessions_started)``;
    ``pre_reading`` is the fresh NC-6 reading and ``clock`` returns a timezone-aware datetime.
    """

    kind = "native"

    def __init__(self, backend: ContainmentBackend, *, workdir: Path | str, pre_reading: Any,
                 quota: tuple[str, Any], clock: Callable[[], datetime],
                 environ: Any = None):
        _require(isinstance(backend, ContainmentBackend) and backend.kind == "native"
                 and hasattr(backend, "policy") and hasattr(backend, "launch"), "invalid-backend")
        _require(isinstance(backend.qualification, Qualification)
                 and isinstance(backend.host_qualification, HostQualification), "invalid-backend")
        _require("on_output" in inspect.signature(backend.launch).parameters, "live-init-unsupported")
        _require(type(quota) is tuple and len(quota) == 2 and quota[0] in ("cohort", "probe")
                 and callable(clock), "invalid-quota")
        self.backend = backend
        self._workdir = workdir
        self._pre_reading = pre_reading
        self._quota = quota
        self._clock = clock
        self._environ = os.environ if environ is None else environ
        self._attempted = False
        self.run_evidence: list[dict] = []

    # -- K2 -------------------------------------------------------------------------------

    def verify_containment(self, manifest: HarnessManifest, qualification: Any, now: int) -> None:
        backend, policy = self.backend, self.backend.policy
        try:
            _check_backend(backend, manifest, now)
        except LabError as exc:
            raise ClaudeHostError(exc.reason) from None
        data = manifest.data
        _require(data["profile"] == NATIVE_PROFILE, "native-host-unqualified")
        _require(isinstance(qualification, HostQualification)
                 and qualification.sha256 == backend.host_qualification.sha256
                 and data["hostQualificationSha256"] == qualification.sha256
                 and data["containment"]["qualificationSha256"] == backend.qualification.sha256
                 and data["containment"]["backend"] == backend.qualification.backend,
                 "qualification-mismatch")
        _require(data["host"]["executableSha256"] == policy.claude_sha256, "executable-mismatch")
        _require(data["host"]["build"] == policy.claude_version == NATIVE_BUILD, "build-mismatch")

    # -- launches -------------------------------------------------------------------------

    def _pinned(self) -> str:
        """K4: the absolute pinned path, hash-checked now; never a ``PATH`` lookup."""
        policy = self.backend.policy
        _require(os.path.isabs(policy.claude), "executable-unavailable")
        digest = _file_sha256(policy.claude)
        _require(digest is not None, "executable-unavailable")
        _require(digest == policy.claude_sha256, "executable-drift")
        return policy.claude

    def _no_deny_variables(self) -> None:
        _require(not any(name in self._environ for name in ENV_DENY), "env-deny-present")

    def _launch(self, argv: tuple[str, ...], stdin: bytes, *, wall: int, max_output: int,
                cancel: threading.Event, on_output: Callable[[bytes], None] | None = None) -> HostRun:
        try:
            return self.backend.launch(argv, stdin, cwd=self._workdir, wall_seconds=wall,
                                       max_output_bytes=max_output, cancel=cancel,
                                       on_output=on_output)
        except LabError as exc:
            raise ClaudeHostError(exc.reason) from None

    def version(self) -> str:
        self._no_deny_variables()
        run = self._launch((self._pinned(), "--version"), b"", wall=VERSION_WALL_SECONDS,
                           max_output=VERSION_MAX_OUTPUT_BYTES, cancel=threading.Event())
        _require(isinstance(run, HostRun) and run.exit_code == 0 and run.settled
                 and not (run.timed_out or run.cancelled or run.output_truncated), "version-unavailable")
        try:
            text = run.stdout.decode("ascii").strip()
        except UnicodeDecodeError:
            raise ClaudeHostError("invalid-version") from None
        _require(".".join(map(str, parse_version(text))) == self.backend.policy.claude_version,
                 "version-drift")  # NC-4: the exact pinned build, no window
        return text

    def _admit(self) -> None:
        mode, state = self._quota
        now = self._clock()
        if mode == "cohort":
            decision = harness_quota.admit(self._pre_reading, now, state)
        else:
            decision = harness_quota.admit_probe(self._pre_reading, now, state)
        self.run_evidence.append({
            "qualificationSha256": self.backend.qualification.sha256,
            "hostQualificationSha256": self.backend.host_qualification.sha256,
            "executableSha256": self.backend.policy.claude_sha256,
            "quotaProceed": decision.proceed, "quotaReason": decision.reason,
            "quota": dict(decision.evidence), "executionAuthorization": False})
        _require(decision.proceed, "quota-stop")

    def run(self, plan: LaunchPlan, prompt: bytes, limits: HostLimits,
            cancel: threading.Event) -> HostRun:
        _require(not self._attempted, "attempt-exhausted")  # no retry, no second route
        self._attempted = True
        _require(isinstance(plan, LaunchPlan) and isinstance(limits, HostLimits)
                 and isinstance(cancel, threading.Event) and type(prompt) is bytes
                 and plan.argv[:1] == ("claude",) and plan.env_deny == ENV_DENY
                 and plan.prompt_sha256 == sha256(prompt).hexdigest(), "invalid-launch-plan")
        self._no_deny_variables()
        self._admit()  # T004 gate; the F4 check (NC-11) runs inside the backend's launch
        argv = (self._pinned(), *plan.argv[1:])
        plan = replace(plan, argv=argv, env_allow=NATIVE_ENV_ALLOW)
        stop, finished = threading.Event(), threading.Event()
        watch = _InitWatch(stop)

        def relay() -> None:  # the caller's cancel also stops the launcher
            while not finished.wait(_RELAY_SECONDS):
                if cancel.is_set():
                    stop.set()
                    return

        relayer = threading.Thread(target=relay, daemon=True)
        relayer.start()
        try:
            run = self._launch(plan.argv, prompt, wall=limits.wall_seconds,
                               max_output=limits.max_output_bytes, cancel=stop,
                               on_output=watch.feed)
        finally:
            finished.set()
            relayer.join()
        _require(isinstance(run, HostRun) and type(run.stdout) is bytes, "invalid-transport-result")
        watch.feed(run.stdout[watch.received:])  # bytes a launcher did not stream live
        return self._finish(run, watch)

    def _finish(self, run: HostRun, watch: _InitWatch) -> HostRun:
        if watch.violation == "no-init":
            self.run_evidence.append({"initKill": "no-init-before-output"})
            raise ClaudeHostError("init-missing")
        if watch.violation == "route":
            self.run_evidence.append({"initKill": "route-unverified"})
            return HostRun(run.stdout[:watch.keep], None, cancelled=True,
                           output_truncated=run.output_truncated, settled=run.settled)
        return run
