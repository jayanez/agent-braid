# SPDX-License-Identifier: AGPL-3.0-only
"""Native account-level quota acquisition, separate from runtime admission.

The private, reviewed transport is loaded only after verifying its pinned bytes.
No import starts a process. Reads require explicit operator serialization; this
component does not authenticate auto-recharge or a registered evaluation process.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import signal
import stat
import subprocess
import threading
from types import ModuleType
from typing import Any

TRANSPORT_SHA256 = "6464c0bc4fd2c000b5337c62c27fbcfbbe90df5e254106b964d5d8581365db1f"
EXECUTABLE = Path("/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex")
EXECUTABLE_SHA256 = "0d5ac7aae20c4eda6242428d5e218c55ba96d8763fda2a271088ff37104b9d28"


class CodexObserverError(RuntimeError):
    """Bounded, redacted acquisition failure; never includes provider bodies."""


@dataclass(frozen=True)
class CodexQuotaSample:
    """Account-level sample, not a source receipt, launch permit or cash proof."""

    observed_at: datetime
    valid_until: datetime
    account_namespace_sha256: str
    account_object_sha256: str
    ordinary_usage_allowed: bool | None
    spend_control_reached: bool | None
    has_credits: bool | None
    unlimited_credits: bool | None
    transport_sha256: str = TRANSPORT_SHA256
    executable_sha256: str = EXECUTABLE_SHA256
    email_binding_sha256: str | None = None
    key_fingerprint_sha256: str | None = None

    def native_profile_witness(self, binding):
        """Project a privately keyed account witness; no browser/process attestation."""
        from .tooling_interface_observer import NativeProfileWitness
        from .tooling_subscription import OperationalProcessRouteBinding
        if (not isinstance(binding, OperationalProcessRouteBinding) or binding.host != "codex"
                or binding.account_sha256 != self.account_object_sha256
                or binding.account_namespace_sha256 != self.account_namespace_sha256
                or self.email_binding_sha256 is None or self.key_fingerprint_sha256 is None):
            raise CodexObserverError("native profile witness is unavailable or differently bound")
        subject = {"accountSha256": self.account_object_sha256,
                   "namespaceSha256": self.account_namespace_sha256,
                   "emailBindingSha256": self.email_binding_sha256,
                   "keyFingerprintSha256": self.key_fingerprint_sha256,
                   "observedAt": self.observed_at.isoformat(),
                   "transportSha256": self.transport_sha256,
                   "executableSha256": self.executable_sha256}
        return NativeProfileWitness(self.account_object_sha256, self.account_namespace_sha256,
            self.email_binding_sha256, self.key_fingerprint_sha256, self.observed_at, _digest(subject))


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _verified_bytes(path: Path, expected: str, *, private: bool) -> bytes:
    # O_NOFOLLOW checks the final component; ancestors belong to the operator's
    # trusted installation. Hash the opened bytes, not a second pathname read.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022
                or (private and (info.st_uid != os.getuid() or info.st_mode & 0o077))
                or info.st_size > (1024 * 1024 if private else 256 * 1024 * 1024)):
            raise CodexObserverError("source file ownership, mode or size refused")
        data = stream.read(info.st_size + 1)
    if len(data) != info.st_size or hashlib.sha256(data).hexdigest() != expected:
        raise CodexObserverError("source bytes differ from the reviewed pin")
    return data


def _load_transport(path: Path) -> ModuleType:
    data = _verified_bytes(path, TRANSPORT_SHA256, private=True)
    module = ModuleType("_agent_braid_reviewed_codex_transport")
    module.__file__ = str(path)
    exec(compile(data, str(path), "exec"), module.__dict__)
    if module.EXE != EXECUTABLE or module.EXPECTED_EXE_SHA256 != EXECUTABLE_SHA256:
        raise CodexObserverError("transport executable pin mismatch")
    return module


def _environment() -> dict[str, str]:
    home = pwd.getpwuid(os.getuid()).pw_dir
    if os.environ.get("HOME") != home or os.environ.get("CODEX_HOME"):
        raise CodexObserverError("custom account context requires separate verification")
    # No inherited API/provider/helper settings. The native executable accesses
    # its existing default account; this adapter never reads credential files.
    return {key: os.environ[key] for key in
            ("HOME", "PATH", "USER", "LOGNAME", "TMPDIR", "LANG", "LC_ALL")
            if key in os.environ}


def _stop(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=3)
    finally:
        for stream in (process.stdin, process.stdout):
            if stream is not None:
                stream.close()


def _flag(value: Any) -> bool | None:
    return value if type(value) is bool else None


def _project(account_result: dict[str, Any], quota: dict[str, Any], *,
             expected_namespace: str, observed: datetime,
             completed: datetime, max_age_seconds: int, private_hmac_key: bytes | None = None) -> CodexQuotaSample:
    account = account_result.get("account")
    routing = account_result.get("workspaceRouting")
    if (not isinstance(account, dict) or account.get("type") != "chatgpt"
            or account_result.get("requiresOpenaiAuth") is not True):
        raise CodexObserverError("native ChatGPT account unavailable")
    namespace = routing.get("chatgptAccountId") if isinstance(routing, dict) else None
    fallback = account.get("accountId")
    if namespace is not None and fallback is not None and namespace != fallback:
        raise CodexObserverError("conflicting account namespaces")
    namespace = namespace if namespace is not None else fallback
    if (not isinstance(namespace, str) or not namespace.strip()
            or namespace != quota.get("accountId") or _digest(namespace) != expected_namespace):
        raise CodexObserverError("account and quota namespace mismatch")
    if not 0 <= (completed - observed).total_seconds() < max_age_seconds:
        raise CodexObserverError("quota acquisition expired or clock moved backwards")
    snapshot = quota.get("rateLimits")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    credits = snapshot.get("credits")
    credits = credits if isinstance(credits, dict) else {}
    email_binding = fingerprint = None
    if private_hmac_key is not None:
        from . import tooling_interface_observer as ui
        try:
            fingerprint = ui.key_fingerprint(private_hmac_key)
            email_binding = ui.private_email_binding(account.get("email"), private_hmac_key)
        except ui.InterfaceObserverError:
            # Quota metadata can remain available; absent/unusable email cannot
            # produce an account-bound interface witness.
            email_binding = None
    return CodexQuotaSample(
        observed, observed + timedelta(seconds=max_age_seconds), _digest(namespace),
        _digest(account), _flag(quota.get("ordinaryUsageAllowed")),
        _flag(snapshot.get("spendControlReached")), _flag(credits.get("hasCredits")),
        _flag(credits.get("unlimited")),
        email_binding_sha256=email_binding, key_fingerprint_sha256=fingerprint,
    )


class CodexQuotaObserver:
    """One serialized metadata pass; no inference, retry or auth refresh.

    The caller must serialize other host observers externally. This lock covers
    only this instance, not other processes. The default account namespace must
    already be independently frozen by the operator, rather than learned here.
    """

    def __init__(self, transport_path: Path, *, expected_namespace_sha256: str,
                 max_age_seconds: int = 60, private_hmac_key: bytes | None = None):
        if (not isinstance(expected_namespace_sha256, str)
                or len(expected_namespace_sha256) != 64
                or any(c not in "0123456789abcdef" for c in expected_namespace_sha256)):
            raise CodexObserverError("expected namespace must be a frozen SHA-256")
        if type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 60:
            raise CodexObserverError("sample age must be between 1 and 60 seconds")
        self._transport_path = Path(transport_path)
        self._namespace = expected_namespace_sha256
        self._max_age = max_age_seconds
        if private_hmac_key is not None:
            from .tooling_interface_observer import key_fingerprint, InterfaceObserverError
            try:
                key_fingerprint(private_hmac_key)
            except InterfaceObserverError as exc:
                raise CodexObserverError("private identity key is invalid") from exc
        self._private_key = private_hmac_key
        self._lock = threading.Lock()

    def read(self, *, serialized_read_only: bool = False) -> CodexQuotaSample:
        """Read native metadata only after the operator has serialized hosts.

        May take up to three reviewed 20-second RPC deadlines plus cleanup.
        Never use this blocking acquisition as the supervisor's dispatch check.
        """
        if serialized_read_only is not True or not self._lock.acquire(blocking=False):
            raise CodexObserverError("explicit serialized read-only pass required")
        process = None
        rpc = None
        try:
            environment = _environment()
            transport = _load_transport(self._transport_path)
            _verified_bytes(EXECUTABLE, EXECUTABLE_SHA256, private=False)
            process = subprocess.Popen(
                [str(EXECUTABLE), "app-server", "--listen", "stdio://"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                cwd=self._transport_path.parent, env=environment, start_new_session=True,
            )
            rpc = transport.RpcClient(process)
            call = transport.require_rpc_success
            call(rpc, "initialize", {"clientInfo": {"name": "agent_braid_quota_observer",
                                                  "version": "1"},
                                     "capabilities": {"experimentalApi": True}})
            call(rpc, "initialized", {}, notification=True)
            observed = datetime.now(timezone.utc)
            account = call(rpc, "account/read", {"refreshToken": False})
            quota = call(rpc, "account/rateLimits/read",
                         {"supportsLunaReserve": False, "excludeResetCreditDetails": True})
            completed = datetime.now(timezone.utc)
            return _project(account, quota, expected_namespace=self._namespace,
                            observed=observed, completed=completed, max_age_seconds=self._max_age,
                            private_hmac_key=self._private_key)
        except Exception:
            raise CodexObserverError("native quota acquisition refused; no retry or fallback") from None
        finally:
            try:
                if rpc is not None:
                    rpc.close()
            finally:
                try:
                    if process is not None:
                        _stop(process)
                finally:
                    self._lock.release()
