# SPDX-License-Identifier: AGPL-3.0-only
"""Reuse the reviewed private Claude collector; acquisition is never admission.

No import, archive verification or offline load acquires credentials. Live reads
are explicit, serialized private subprocesses with owned process-group cleanup.
The consumer must use a source cache, never this blocking acquisition directly.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import pwd
import re
import signal
import stat
import subprocess
import sys
import threading
import time
from types import ModuleType
from typing import Any
import unicodedata

COLLECTOR_SHA256 = "d2b98daaf1861e12b5d27d348081f3b0358f1b4c506fa5fb3655003a4590de13"
ROUTES_SHA256 = "3b50b92c21ef757caf7b22dabaae45b2afdb1ef20903416df8ff990cd753170b"
REVIEW_MANIFEST_SHA256 = "dde4dc0c4fe41bd31dbd511574a5650a377a704a8aabcc50e68326daac1fe97e"
CONTEXT_SHA256 = "d822f99d9837ccad65bd3d777e01c10eec32d22c4fd53a1449fe1975cd462baf"
NATIVE_BINARY_SHA256 = "6eab8333fe2121553100d8f40bfada384a3e989b94f947e18ba6677a6fcb41ea"
NATIVE_VERSION = "2.1.287"
RECEIPT_SCHEMA = "claude-personal-api-read-diagnostic/v4"
ARCHIVED_EMAIL_METHOD = "claude-account-email-v1"
_SHA = re.compile(r"[0-9a-f]{64}")
_SUFFIX = re.compile(r"[0-9a-f]{8}")
_FINGERPRINT = re.compile(r"[0-9a-f]{16}")


class ClaudeObserverError(RuntimeError):
    """Redacted refusal, without credentials, private identities or response bodies."""


def _hash(value):
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ClaudeObserverError("frozen source or identity digest required")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _time(value):
    try:
        if not isinstance(value, str):
            raise ValueError
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.utcoffset() is None:
            raise ValueError
        return result.astimezone(timezone.utc)
    except Exception:
        raise ClaudeObserverError("original timezone-aware source timestamp required") from None


def _read_file(path: Path, expected: str | None, *, private: bool = True,
               maximum: int = 2 * 1024 * 1024) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022 or info.st_size > maximum
                    or (private and (info.st_uid != os.getuid() or info.st_mode & 0o077))):
                raise ValueError
            raw = stream.read(info.st_size + 1)
        if len(raw) != info.st_size or (expected is not None and hashlib.sha256(raw).hexdigest() != expected):
            raise ValueError
        return raw
    except Exception:
        raise ClaudeObserverError("private source, mode or reviewed pin refused") from None


def _directory(path: Path, *, private: bool) -> Path:
    try:
        text = str(path)
        info = path.lstat()
        if (not path.is_absolute() or path.resolve(strict=True) != path
                or text != unicodedata.normalize("NFC", text) or text != os.path.normpath(text)
                or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & (0o077 if private else 0o022)):
            raise ValueError
        return path
    except Exception:
        raise ClaudeObserverError("canonical private directory required") from None


@dataclass(frozen=True)
class VerifiedClaudeArchive:
    collector_path: Path = field(repr=False)
    collector_sha256: str
    routes_sha256: str
    review_manifest_sha256: str
    context_sha256: str


def verify_private_archive(archive_root: Path, review_root: Path) -> VerifiedClaudeArchive:
    """Verify exact historical bytes/context, not review approval or current auth."""
    try:
        archive_root, review_root = _directory(Path(archive_root), private=True), _directory(Path(review_root), private=True)
        collector = archive_root / "claude/collector.py"
        raw = _read_file(collector, COLLECTOR_SHA256)
        routes = json.loads(_read_file(archive_root / "claude/routes.json", ROUTES_SHA256))
        _read_file(review_root / "candidate/collector.py", COLLECTOR_SHA256)
        _read_file(review_root / "candidate/routes.json", ROUTES_SHA256)
        manifest = json.loads(_read_file(review_root / "MANIFEST.private.json", REVIEW_MANIFEST_SHA256))
        files = manifest["files"]
        if not isinstance(files, list) or not 1 <= len(files) <= 100:
            raise ValueError
        for entry in files:
            relative = Path(entry["path"])
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise ValueError
            data = _read_file(review_root / relative, entry["sha256"])
            if len(data) != entry["bytes"]:
                raise ValueError
        context = json.loads(_read_file(archive_root / "run-record.private.json", CONTEXT_SHA256))
        if (context["collectorSha256"] != COLLECTOR_SHA256 or context["routesSha256"] != ROUTES_SHA256
                or type(context["exitCode"]) is not int or context["exitCode"] != 0
                or context["retry"] is not False or context["receiptPresent"] is not True
                or routes["candidate"]["version"] != NATIVE_VERSION
                or routes["candidate"]["binary_sha256"] != NATIVE_BINARY_SHA256):
            raise ValueError
        del raw
        return VerifiedClaudeArchive(collector, COLLECTOR_SHA256, ROUTES_SHA256,
                                     REVIEW_MANIFEST_SHA256, CONTEXT_SHA256)
    except Exception:
        raise ClaudeObserverError("reviewed private archive or historical context refused") from None


def load_collector_for_offline_checks(archive_root: Path, review_root: Path) -> ModuleType:
    """Explicit inert loading of the already-reviewed source, never a live read."""
    verified = verify_private_archive(archive_root, review_root)
    raw = _read_file(verified.collector_path, COLLECTOR_SHA256)
    module = ModuleType("_agent_braid_reviewed_claude_collector")
    module.__file__ = str(verified.collector_path)
    exec(compile(raw, str(verified.collector_path), "exec"), module.__dict__)
    return module


@dataclass(frozen=True)
class ClaudeQuotaSample:
    """Private account metadata, with no process, recharge or cash assertion."""

    observed_at: datetime
    profile_observed_at: datetime
    valid_until: datetime
    account_sha256: str = field(repr=False)
    organization_sha256: str = field(repr=False)
    account_namespace_sha256: str = field(repr=False)
    email_binding_sha256: str = field(repr=False)
    key_fingerprint: str = field(repr=False)
    quota_values: tuple[float, float] = field(repr=False)
    quota_resets: tuple[datetime, datetime] = field(repr=False)
    profile_receipt_sha256: str = field(repr=False)
    sample_sha256: str
    keychain_suffix: str = field(repr=False)
    extra_usage_enabled: bool = False
    email_binding_method: str = ARCHIVED_EMAIL_METHOD

    def evidence_claims(self):
        """The CLI artifact is inspected context; acquisition does not execute it."""
        return {"acquisitionMethod": "reviewed-collector-direct-tls-get", "nativeProcessObserved": False,
                "referenceArtifactSha256": NATIVE_BINARY_SHA256, "inspectedClaudeVersion": NATIVE_VERSION}

    def as_quota_payload(self):
        return {"extraUsageEnabled": self.extra_usage_enabled, "quotaWindows": {
            name: {"usedPct": value, "resetsAt": reset.isoformat()}
            for name, value, reset in zip(("fiveHour", "sevenDay"), self.quota_values, self.quota_resets)}}

    def as_native_profile_witness(self):
        """Preserve archived HMAC; identify the digest of its original short fingerprint."""
        from .tooling_interface_observer import NativeProfileWitness
        fingerprint_digest = hashlib.sha256(self.key_fingerprint.encode("ascii")).hexdigest()
        return NativeProfileWitness(self.account_sha256, self.account_namespace_sha256,
            self.email_binding_sha256, fingerprint_digest, self.profile_observed_at,
            self.profile_receipt_sha256, self.email_binding_method)


def project_quota_receipt(receipt: Mapping[str, Any], *, expected_account_sha256: str,
                         expected_organization_sha256: str, expected_namespace_sha256: str,
                         expected_keychain_suffix: str, expected_key_fingerprint: str,
                         namespace_verifier: Callable[..., None], now: datetime,
                         max_age_seconds: int = 60) -> ClaudeQuotaSample:
    """Validate private authenticated-collector output; hashes alone do not authenticate."""
    try:
        encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if len(encoded) > 2 * 1024 * 1024:
            raise ValueError
        receipt = json.loads(encoded)
        for value in (expected_account_sha256, expected_organization_sha256, expected_namespace_sha256):
            _hash(value)
        if (type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 60
                or not isinstance(now, datetime) or now.utcoffset() is None
                or not callable(namespace_verifier)
                or not isinstance(expected_key_fingerprint, str) or not _FINGERPRINT.fullmatch(expected_key_fingerprint)
                or not isinstance(expected_keychain_suffix, str) or not _SUFFIX.fullmatch(expected_keychain_suffix)):
            raise ValueError
        current = now.astimezone(timezone.utc)
        if (receipt["schema"] != RECEIPT_SCHEMA or receipt["adapter_sha256"] != COLLECTOR_SHA256
                or receipt["candidate"] != {"version": NATIVE_VERSION, "binary_sha256": NATIVE_BINARY_SHA256,
                                           "routes_manifest_sha256": ROUTES_SHA256}
                or type(receipt["provider_inference_requests"]) is not int or receipt["provider_inference_requests"] != 0
                or receipt["collection_status"] != "bounded_observation"
                or not isinstance(receipt["credential_acquisition"], str)
                or receipt["credential_acquisition"] in ("", "none")):
            raise ValueError
        routes = receipt["routes"]
        if (not isinstance(routes, list) or len(routes) not in (2, 3)
                or [item["route"] for item in routes] not in (["profile", "usage"], ["profile", "usage", "prepaid-credit-balance"])):
            raise ValueError
        profile, usage = routes[:2]
        times = []
        for route in (profile, usage):
            if (route["schema"] != "claude-bounded-native-read-receipt/v3" or route["method"] != "GET"
                    or type(route["status"]) is not int or not 200 <= route["status"] < 300
                    or route["response_body_capture"] != "captured" or route["controls_status"] != "present"
                    or route["controls"]["extra_usage_enabled"] is not False):
                raise ValueError
            _hash(route["response_sha256"])
            observed = _time(route["observed_at_utc"])
            if not 0 <= (current - observed).total_seconds() <= max_age_seconds:
                raise ValueError
            times.append(observed)
        if not _time(receipt["started_at_utc"]) <= times[0] <= times[1] <= _time(receipt["finished_at_utc"]) <= current:
            raise ValueError
        identities = profile["identity_sha256"]
        if identities != {"account": expected_account_sha256, "organization": expected_organization_sha256}:
            raise ValueError
        for name, value in usage["identity_sha256"].items():
            if name not in identities or value != identities[name]:
                raise ValueError
        if (profile.get("identity_hmac_status") not in (None, "present")
                or set(profile["identity_hmac_sha256"]) != {"account_email"}
                or profile["identity_key_fingerprint"] != expected_key_fingerprint):
            raise ValueError
        email_hmac = profile["identity_hmac_sha256"]["account_email"]
        _hash(email_hmac)
        store = receipt["process_store_binding"]
        if (store["mode"] != "isolated-config-dir" or store["status"] != "bound"
                or store["keychain_service_suffix"] != expected_keychain_suffix
                or any(store[name] is not True for name in ("config_account_present", "config_organization_present",
                    "config_account_matches_profile", "config_organization_matches_profile"))):
            raise ValueError
        values, resets = [], []
        for name in ("five_hour", "seven_day"):
            window = usage["controls"]["quota_windows"][name]
            value = window["quota_used_pct"]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value < 100:
                raise ValueError
            reset = _time(window["resets_at_utc"])
            if reset <= current:
                raise ValueError
            values.append(value)
            resets.append(reset)
        if namespace_verifier(expected_account_sha256, expected_organization_sha256, expected_namespace_sha256) is not None:
            raise ValueError
        expiry = min(*(observed + timedelta(seconds=max_age_seconds) for observed in times), *resets)
        return ClaudeQuotaSample(times[1], times[0], expiry, expected_account_sha256, expected_organization_sha256,
            expected_namespace_sha256, email_hmac, expected_key_fingerprint, tuple(values), tuple(resets),
            _digest(profile), _digest(receipt), expected_keychain_suffix)
    except Exception:
        raise ClaudeObserverError("private quota/profile receipt refused; no inferred controls or identity") from None


def collection_environment(config_dir: Path) -> dict[str, str]:
    home = pwd.getpwuid(os.getuid()).pw_dir
    if os.environ.get("HOME") != home:
        raise ClaudeObserverError("custom HOME requires separate account-context verification")
    # Do not inherit provider, proxy, TLS, Python loader or credential-helper settings.
    # The collector receives its canonical store explicitly by config_dir argv.
    # Its native-account guard rejects an ambient CLAUDE_CONFIG_DIR override.
    return {"HOME": home, "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "CLAUDE_CODE_ENTRYPOINT": "cli"}


def stop_owned_collector(process) -> None:
    """Reap before returning; unresolved cleanup keeps the caller's lock held."""
    pending = None
    def send(sig):
        nonlocal pending
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        except BaseException as exc:
            pending = pending or exc
    def group_exists():
        nonlocal pending
        try:
            os.killpg(process.pid, 0)
            return True
        except ProcessLookupError:
            return False
        except BaseException as exc:
            pending = pending or exc
            return True
    send(signal.SIGTERM)
    deadline, killed = time.monotonic() + 1, False
    while group_exists():
        try:
            if not killed and (pending is not None or time.monotonic() >= deadline):
                send(signal.SIGKILL)
                killed = True
            try:
                process.wait(timeout=.05)
            except subprocess.TimeoutExpired:
                pass
            time.sleep(.05)
        except BaseException as exc:
            pending = pending or exc
    # Reap the leader even when its group has already disappeared. An interrupted
    # wait is remembered, but cannot release serialization before actual cleanup.
    while True:
        try:
            process.wait()
            break
        except BaseException as exc:
            pending = pending or exc
    if pending is not None:
        raise pending


_CHILD_LOADER = r"""
import hashlib,os,stat,sys,types
path,output,config,key_path,expected,manifest_expected,key_expected=sys.argv[1:]
def read_checked(name,digest,maximum=2097152):
 fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as f:
  s=os.fstat(f.fileno())
  if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077 or s.st_size>maximum: raise RuntimeError('private pin refused')
  data=f.read(s.st_size+1)
 if len(data)!=s.st_size or hashlib.sha256(data).hexdigest()!=digest: raise RuntimeError('pin refused')
 return data
source=read_checked(path,expected)
read_checked(os.path.join(os.path.dirname(path),'routes.json'),manifest_expected)
module=types.ModuleType('_reviewed_private_claude_collector');module.__file__=path
exec(compile(source,path,'exec'),module.__dict__)
def load_pinned_identity_key(requested_path):
 if requested_path!=key_path: raise RuntimeError('key reference refused')
 raw=read_checked(key_path,key_expected,4096)
 text=raw.decode('ascii')
 if text.endswith('\n'): text=text[:-1]
 if not module._KEY_FILE_RE.fullmatch(text) or len(text)%2: raise RuntimeError('key format refused')
 identity_key=bytes.fromhex(text)
 if not any(identity_key): raise RuntimeError('key format refused')
 return identity_key
# The archived file remains unchanged. This reviewed loader replaces only its
# key-file acquisition with the same validation over exact pin-checked bytes.
# OAuth acquisition, profile/usage transport and HMAC algorithms remain original.
module.load_identity_key=load_pinned_identity_key
module.run_personal_diagnostic(__import__('pathlib').Path(output),config_dir=config,identity_key_file=key_path)
"""


class ClaudeQuotaObserver:
    """Explicit serialized metadata pass through the unchanged reviewed collector."""

    def __init__(self, archive_root: Path, review_root: Path, *, native_reference_artifact: Path,
                 python_executable: Path, expected_python_sha256: str, canonical_config_dir: Path,
                 expected_keychain_suffix: str, expected_account_sha256: str,
                 expected_organization_sha256: str, expected_namespace_sha256: str,
                 identity_key_path: Path, expected_identity_key_sha256: str,
                 expected_key_fingerprint: str, namespace_verifier: Callable[..., None],
                 max_age_seconds: int = 60, timeout_seconds: float = 90):
        for digest in (expected_python_sha256, expected_account_sha256, expected_organization_sha256,
                       expected_namespace_sha256, expected_identity_key_sha256):
            _hash(digest)
        config = _directory(Path(canonical_config_dir), private=False)
        if any(not Path(path).is_absolute() for path in (native_reference_artifact, python_executable, identity_key_path)):
            raise ClaudeObserverError("explicit absolute static reference, interpreter and private key paths required")
        if (not isinstance(expected_keychain_suffix, str) or not _SUFFIX.fullmatch(expected_keychain_suffix)
                or hashlib.sha256(str(config).encode()).hexdigest()[:8] != expected_keychain_suffix
                or not isinstance(expected_key_fingerprint, str) or not _FINGERPRINT.fullmatch(expected_key_fingerprint)
                or not callable(namespace_verifier) or type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 60
                or type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
                or not 0 < timeout_seconds <= 100):
            raise ClaudeObserverError("frozen canonical store, namespace and bounded observer required")
        self._archive, self._review = Path(archive_root), Path(review_root)
        self._reference, self._python = Path(native_reference_artifact), Path(python_executable)
        self._python_sha, self._config = expected_python_sha256, config
        self._key_path, self._key_sha = Path(identity_key_path), expected_identity_key_sha256
        self._timeout = timeout_seconds
        self._projection = {"expected_account_sha256": expected_account_sha256,
            "expected_organization_sha256": expected_organization_sha256, "expected_namespace_sha256": expected_namespace_sha256,
            "expected_keychain_suffix": expected_keychain_suffix, "expected_key_fingerprint": expected_key_fingerprint,
            "namespace_verifier": namespace_verifier, "max_age_seconds": max_age_seconds}
        self._lock = threading.Lock()

    def _recheck_installation(self) -> None:
        """Point-in-time path observations, under a trusted stable installation."""
        _directory(self._config, private=False)
        if os.path.lexists(self._config / ".credentials.json"):
            raise ClaudeObserverError("ambiguous isolated credential source")
        _read_file(self._reference, NATIVE_BINARY_SHA256, private=False, maximum=512 * 1024 * 1024)
        _read_file(self._python, self._python_sha, private=False, maximum=64 * 1024 * 1024)
        _read_file(self._key_path, self._key_sha, maximum=4096)

    def read(self, output_path: Path, *, serialized_read_only: bool = False,
             cancel_event: threading.Event | None = None) -> ClaudeQuotaSample:
        """Producer-only I/O. Caller must hold shared serialization through cleanup."""
        if serialized_read_only is not True or not self._lock.acquire(blocking=False):
            raise ClaudeObserverError("explicit serialized read-only pass required")
        process = None
        try:
            if sys.platform != "darwin" or (cancel_event is not None and cancel_event.is_set()):
                raise ClaudeObserverError("unsupported or cancelled acquisition")
            archive = verify_private_archive(self._archive, self._review)
            self._recheck_installation()
            output_path = Path(output_path)
            if (output_path.parent != archive.collector_path.parent or os.path.lexists(output_path)
                    or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.json", output_path.name)):
                raise ClaudeObserverError("new private collector output required")
            started = datetime.now(timezone.utc)
            environment = collection_environment(self._config)
            argv = [str(self._python), "-I", "-S", "-c", _CHILD_LOADER, str(archive.collector_path),
                str(output_path), str(self._config), str(self._key_path), COLLECTOR_SHA256, ROUTES_SHA256, self._key_sha]
            self._recheck_installation()
            if cancel_event is not None and cancel_event.is_set():
                raise ClaudeObserverError("cancelled before acquisition")
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, cwd=archive.collector_path.parent, env=environment, start_new_session=True)
            deadline = time.monotonic() + self._timeout
            while process.poll() is None:
                if (cancel_event is not None and cancel_event.is_set()) or time.monotonic() >= deadline:
                    raise ClaudeObserverError("collector cancelled or deadline exceeded")
                time.sleep(.05)
            if process.returncode != 0 or (cancel_event is not None and cancel_event.is_set()):
                raise ClaudeObserverError("collector failed or cancellation arrived at completion")
            raw = _read_file(output_path, None)
            completed = datetime.now(timezone.utc)
            if completed < started:
                raise ClaudeObserverError("collector clock moved backwards")
            sample = project_quota_receipt(json.loads(raw), now=completed, **self._projection)
            # Finish acquisition cleanup before rechecking eligibility and making
            # any sample available. The referenced CLI artifact was never run.
            stop_owned_collector(process)
            process = None
            verify_private_archive(self._archive, self._review)
            self._recheck_installation()
            final_time = datetime.now(timezone.utc)
            if (final_time < completed or final_time > sample.valid_until or time.monotonic() >= deadline
                    or (cancel_event is not None and cancel_event.is_set())):
                raise ClaudeObserverError("collector cancelled before return")
            return sample
        except Exception:
            raise ClaudeObserverError("private quota/profile acquisition refused; no retry or fallback") from None
        finally:
            try:
                if process is not None:
                    stop_owned_collector(process)
            finally:
                self._lock.release()
