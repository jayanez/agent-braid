# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T011 offline, opt-in operational lifecycle with drift checks and reversible migration.

Experimental and disabled by default: nothing exists until a human installs it, and ordinary use
stays unreachable (``activate`` always refuses; the SPEC-049 T008 disposition is deferred and the
T009 production policy abstains with ``pending-endpoints``). Every result carries
``executionAuthorization`` false. The module starts no process, opens no network connection,
reads no clock, host or model, and writes only inside ``<root>/.braid-harness-lifecycle`` and
two kinds of sibling working directories it names itself (staging and removal); the caller
supplies ``root`` and every tick.

Reused, not re-implemented: staged profiles are T002 ``ComponentProfile`` records re-verified
with ``verify_profile``; promotion state is a T013 ``ProfileRegistry`` persisted with
``harness_promotion.save``/``load``; canaries and stops run the T009 ``PolicyRun``; revocation
calls ``ProfileRegistry.revoke_evidence`` and, for a caller-held store, T008
``propagate_revocation``. T009 refusals (``AutoPromotionError``) propagate unchanged.

* ``install`` needs ``opt_in=True``, a human operator, a supported host (only ``claude`` has an
  observed build; ``codex`` and anything else refuse) and an exact identity. It builds the
  layout in a staging directory and renames it into place, so an interrupted install leaves
  nothing installed. Directories are 0700 and files 0600; nothing is exported.
* ``migrate`` stages a verified, admitted (``implemented``) profile only as the next linked
  version of the current one; ``rollback`` (downgrade) restores the newest prior profile only if
  its stored bytes still hash to the recorded identity, and refuses otherwise. Prior profiles are
  kept; the withdrawn profile's bytes become unreferenced and ``recover`` deletes them, so
  migrating to it again needs its bytes. Every profile has a caller-fixed expiry tick; an expired
  profile gates the canary but is never deleted.
* ``check_drift`` compares the current source/host/model/tool/policy identity with the installed
  one and records a requalification requirement; only a human ``requalify`` with an evidence
  hash clears it. Requalifying the installation does not requalify a promotion decision: the
  registry still refuses to serve a profile decided under another identity.
* ``begin_canary``/``observe_canary`` run a T009 canary against the persisted registry; a drift
  stop also requires requalification, and an observation on a halted or drifted installation
  stops the run instead. ``incident_stop`` halts the installation (and the run, if given) and
  rolls the registry back; only a human ``clear_incident`` lifts the halt. The last
  ``STOP_RESERVE`` journal entries are reserved for stops; if even those are used up, the halt
  is still written without a journal entry.
* ``retain`` stores a private record with a caller-fixed retention tick (no default duration);
  only an explicit human ``purge`` deletes records whose tick has passed. Nothing is
  auto-deleted or auto-exported. Purge and uninstall keep hashes in their journal or receipt.
* ``uninstall`` refuses unknown or linked content, renames the installation to a removal
  directory (from then on it is not installed) and deletes it; ``recover`` finishes interrupted
  installs, uninstalls, temporary files and unreferenced blobs. ``residue`` lists what is left.

State changes are serialized by an exclusive POSIX lock (``recover`` takes it too) and written by
temp-file, fsync and rename. The state is written before the registry and records the registry
hash it expects, so a crash between the two leaves the halt or journal entry durable and shows
``registryConsistent: false``; registry-dependent calls then refuse until a stop is repeated or a
human ``save_registry`` writes a registry extending the stored journal. Subdirectories are
checked to be real directories under the lock; a same-user process swapping them between that
check and a write is outside the threat model (contract section 7). Records prove binding, not
authenticity: operators, identities, retention ticks and evidence hashes are caller-asserted.
Two installs racing for one root, or ``recover`` racing an install, are not handled. Human
workflow usability, native hosts and any activation are not covered.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
from hashlib import sha256
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Any, NoReturn

from . import harness_components as hc
from .harness_auto_promotion import AutoPromotionError, PolicyRun
from .harness_curation import CurationError, RevocationResult, propagate_revocation
from .harness_experience import ExperienceError
from .harness_promotion import (IDENTITY, MAX_TICK, ProfileRegistry, PromotionError,
                                _check_identity, load as load_registry_file, save as save_registry_file)
from .system_one import MAX_BYTES, InvalidDecision, canonical, parse_json

FORMAT = "braid-harness-lifecycle/v0.1"
OWNED = ".braid-harness-lifecycle"
STAGING_PREFIX = OWNED + ".installing-"
REMOVING_PREFIX = OWNED + ".removing-"
SUPPORTED_HOSTS = tuple(h for h, row in hc.HOST_SUPPORT.items() if row["observedBuild"] is not None)
KINDS = ("lesson", "trace", "trial")
EVENTS = ("installed", "migrated", "rolled-back", "drift-detected", "requalified",
          "registry-updated", "canary-begun", "canary-refused", "canary-observed",
          "canary-stopped", "incident-stop", "incident-cleared", "evidence-revoked", "retained",
          "purged")
ACTIVATION = "requires-separate-adr-and-operator-decision"
# Module-local provisional bounds; the contract leaves retention and disk caps open.
MAX_PRIVATE = 64
MAX_PRIVATE_BYTES = 65_536
MAX_PREVIOUS = 16
MAX_JOURNAL = 256
STOP_RESERVE = 8
MAX_DETAIL = 64
STATE, STATE_LOCK, REGISTRY = "state.json", "state.lock", "registry.json"
REGISTRY_LOCK = REGISTRY + ".lock"
PROFILES, PRIVATE = "profiles", "private"
_FILES = (STATE, STATE_LOCK, REGISTRY, REGISTRY_LOCK)
_BLOB = {PROFILES: re.compile(r"[0-9a-f]{64}\.json\Z"), PRIVATE: re.compile(r"[0-9a-f]{64}\Z")}
_TEMP = re.compile(r"\.[^/]+\.tmp-[0-9a-f]{16}\Z")
_WORKDIR = re.compile(re.escape(OWNED) + r"\.(installing|removing)-[0-9a-f]{16}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_STATE_KEYS = {"format", "scope", "host", "identity", "installedAt", "current", "previous",
               "requalification", "halted", "private", "registrySha256", "journal",
               "executionAuthorization"}
_ENTRY_KEYS = {"sha256", "version", "expiresAt", "migratedAt"}
_PRIVATE_KEYS = {"sha256", "kind", "sizeBytes", "retainUntil", "storedAt"}
_EVENT_KEYS = {"seq", "event", "at", "actor", "subject", "detail"}

# Indirections so interruption tests can fail one filesystem step.
_replace, _rename, _unlink = os.replace, os.rename, os.unlink


class LifecycleError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-input"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-input") -> None:
    if not condition:
        raise LifecycleError(reason)


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _id(value: Any) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _tick(value: Any) -> bool:
    return type(value) is int and 0 <= value < MAX_TICK


def _operator(value: Any) -> str:
    _require(type(value) is dict and set(value) == {"kind", "id"}
             and value["kind"] in ("human", "automatic-policy") and _id(value["id"]),
             "invalid-operator")
    _require(value["kind"] == "human", "automatic-promotion-disabled")
    return value["id"]


def _identity(value: Any, reason: str = "invalid-identity") -> dict:
    try:
        _check_identity(value, reason)
    except PromotionError:
        raise LifecycleError(reason) from None
    return dict(value)


def _drift(installed: dict, current: dict) -> list[str]:
    return [reason for key, reason in IDENTITY if installed[key] != current[key]]


# --- filesystem ---------------------------------------------------------------------


def _root(root: Any) -> Path:
    try:
        path = Path(root)
        mode = os.lstat(path).st_mode
    except (OSError, TypeError, ValueError):
        raise LifecycleError("invalid-root") from None
    _require(stat.S_ISDIR(mode), "invalid-root")
    return path


def _owned(root: Path) -> Path:
    owned = root / OWNED
    try:
        mode = os.lstat(owned).st_mode
    except FileNotFoundError:
        raise LifecycleError("not-installed") from None
    except OSError:
        raise LifecycleError("io-error") from None
    _require(stat.S_ISDIR(mode), "foreign-content")
    return owned


def _read(path: Path, limit: int, reason: str) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise LifecycleError(reason) from None
    try:
        with os.fdopen(fd, "rb") as handle:
            _require(stat.S_ISREG(os.fstat(handle.fileno()).st_mode), reason)
            raw = handle.read(limit + 1)
    except OSError:
        raise LifecycleError(reason) from None
    _require(len(raw) <= limit, reason)
    return raw


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_atomic(path: Path, data: bytes) -> None:
    """Replace ``path`` with ``data`` via an exclusive temp file, fsync and rename."""
    temp = path.with_name(f".{path.name}.tmp-{secrets.token_hex(8)}")
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        _replace(temp, path)
        _fsync_dir(path.parent)
    except OSError:
        try:
            _unlink(temp)
        except OSError:
            pass
        raise LifecycleError("write-failed") from None


def _scan(directory: Path) -> tuple[list[str], list[str], list[str]]:
    """(owned files, temporary debris, foreign entries) relative to an installation directory.

    Only the fixed layout counts as owned; links, special files and unknown names are foreign.
    """
    owned, debris, foreign = [], [], []
    try:
        for entry in os.scandir(directory):
            name, mode = entry.name, entry.stat(follow_symlinks=False).st_mode
            if name in _BLOB and stat.S_ISDIR(mode):
                for child in os.scandir(entry.path):
                    rel, cmode = f"{name}/{child.name}", child.stat(follow_symlinks=False).st_mode
                    if stat.S_ISREG(cmode) and _BLOB[name].fullmatch(child.name):
                        owned.append(rel)
                    elif stat.S_ISREG(cmode) and _TEMP.fullmatch(child.name):
                        debris.append(rel)
                    else:
                        foreign.append(rel)
            elif stat.S_ISREG(mode) and name in _FILES:
                owned.append(name)
            elif stat.S_ISREG(mode) and _TEMP.fullmatch(name):
                debris.append(name)
            else:
                foreign.append(name)
    except OSError:
        raise LifecycleError("io-error") from None
    return sorted(owned), sorted(debris), sorted(foreign)


def _layout(owned: Path) -> None:
    """Both blob directories are real directories, not links; checked under the lock."""
    for name in _BLOB:
        try:
            mode = os.lstat(owned / name).st_mode
        except OSError:
            raise LifecycleError("foreign-content") from None
        _require(stat.S_ISDIR(mode), "foreign-content")


def _remove_tree(directory: Path) -> list[str]:
    """Delete an installation-shaped directory; refuse before deleting if anything is foreign."""
    owned, debris, foreign = _scan(directory)
    _require(not foreign, "foreign-content")
    for rel in owned + debris:
        _unlink(directory / rel)
    for name in _BLOB:
        if os.path.lexists(directory / name):
            os.rmdir(directory / name)
    os.rmdir(directory)
    return owned + debris


# --- state --------------------------------------------------------------------------


def _check_entry(e: Any) -> bool:
    return (type(e) is dict and set(e) == _ENTRY_KEYS and _hash(e["sha256"])
            and type(e["version"]) is int and 1 <= e["version"] <= hc.MAX_VERSION
            and _tick(e["expiresAt"]) and _tick(e["migratedAt"]))


def _check_private(r: Any) -> bool:
    return (type(r) is dict and set(r) == _PRIVATE_KEYS and _hash(r["sha256"])
            and r["kind"] in KINDS and type(r["sizeBytes"]) is int
            and 0 <= r["sizeBytes"] <= MAX_PRIVATE_BYTES and _tick(r["retainUntil"])
            and _tick(r["storedAt"]))


def _check_state(v: Any) -> None:
    _require(type(v) is dict and set(v) == _STATE_KEYS, "invalid-state")
    stack = v["previous"]
    _require(v["format"] == FORMAT and v["executionAuthorization"] is False and _id(v["scope"])
             and v["host"] in SUPPORTED_HOSTS and _tick(v["installedAt"])
             and _hash(v["registrySha256"])
             and (v["current"] is None or _check_entry(v["current"]))
             and type(stack) is list and len(stack) <= MAX_PREVIOUS
             and all(map(_check_entry, stack))
             # Linked migrations from version 1 keep the stack at versions 1..n below current.
             and [e["version"] for e in stack] == list(range(1, len(stack) + 1))
             and (v["current"] is None and not stack
                  or v["current"] is not None and v["current"]["version"] == len(stack) + 1)
             and type(v["requalification"]) is list
             and v["requalification"] == sorted(set(v["requalification"]))
             and all(map(_id, v["requalification"])) and v["halted"] in (None, "incident-stop")
             and type(v["private"]) is list and len(v["private"]) <= MAX_PRIVATE
             and all(map(_check_private, v["private"]))
             and [r["sha256"] for r in v["private"]] == sorted({r["sha256"] for r in v["private"]})
             and type(v["journal"]) is list and 1 <= len(v["journal"]) <= MAX_JOURNAL,
             "invalid-state")
    _identity(v["identity"], "invalid-state")
    last = 0
    for index, e in enumerate(v["journal"]):
        _require(type(e) is dict and set(e) == _EVENT_KEYS and type(e["seq"]) is int
                 and e["seq"] == index and e["event"] in EVENTS and _tick(e["at"])
                 and e["at"] >= last and (e["actor"] is None or _id(e["actor"]))
                 and (e["subject"] is None or _hash(e["subject"]))
                 and type(e["detail"]) is list and len(e["detail"]) <= MAX_DETAIL
                 and all(map(_id, e["detail"])), "invalid-state")
        last = e["at"]


def _read_state(owned: Path) -> dict:
    raw = _read(owned / STATE, MAX_BYTES, "invalid-state")
    try:
        value = parse_json(raw)
    except InvalidDecision:
        raise LifecycleError("invalid-state") from None
    fmt = value.get("format") if type(value) is dict else None
    _require(not (type(fmt) is str and fmt.startswith("braid-harness-lifecycle/")
                  and fmt != FORMAT), "unsupported-version")
    _require(canonical(value) == raw, "non-canonical")
    _check_state(value)
    return value


def _event(state: dict, name: str, at: Any, *, actor: str | None = None,
           subject: str | None = None, detail: Any = (), stop: bool = False) -> None:
    """Append one journal entry.

    A ``stop`` keeps the journal clock on a bad tick, may use the reserved entries and is
    skipped (its state change still persists) when even those are used up.
    """
    journal = state["journal"]
    last, detail = journal[-1]["at"], list(detail)
    if stop and not (_tick(at) and at >= last):
        at, detail = last, [*detail, "invalid-time"]
    _require(_tick(at), "invalid-time")
    _require(at >= last, "time-regression")
    if stop and len(journal) >= MAX_JOURNAL:
        return
    _require(len(journal) < MAX_JOURNAL - (0 if stop else STOP_RESERVE), "journal-full")
    journal.append({"seq": len(journal), "event": name, "at": at, "actor": actor,
                    "subject": subject, "detail": detail})


@contextmanager
def _locked(root: Any) -> Iterator[tuple[Path, dict]]:
    """Hold the installation's exclusive lock and yield its validated state."""
    owned = _owned(_root(root))
    try:
        lock = os.open(owned / STATE_LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    except OSError:
        raise LifecycleError("foreign-content") from None
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = _read_state(owned)
        _layout(owned)
        yield owned, state
    finally:
        os.close(lock)


@dataclass
class _Txn:
    """Effects applied after the state is durable: a registry write, then blob deletions."""

    registry: ProfileRegistry | None = None
    delete: tuple[str, ...] = ()
    registryFailure: str | None = None
    deleteFailures: tuple[str, ...] = ()


def _mutate(root: Any, change: Callable[[Path, dict, _Txn], Any]) -> tuple[Any, _Txn]:
    """Run ``change`` on the locked state, persist it atomically if it changed, then the effects."""
    txn = _Txn()
    with _locked(root) as (owned, state):
        before = canonical(state)
        result = change(owned, state, txn)
        if txn.registry is not None:
            state["registrySha256"] = txn.registry.sha256
        after = canonical(state)
        if after != before:
            _check_state(state)
            _write_atomic(owned / STATE, after)
        if txn.registry is not None:
            try:
                save_registry_file(owned / REGISTRY, txn.registry)
            except PromotionError as exc:
                txn.registryFailure = exc.reason
        failures = []
        for rel in txn.delete:
            try:
                _unlink(owned / rel)
            except FileNotFoundError:
                pass
            except OSError:
                failures.append(rel)
        txn.deleteFailures = tuple(failures)
    return result, txn


def _gate(state: dict) -> None:
    _require(state["halted"] is None, "incident-stop")
    _require(not state["requalification"], "requalification-required")


def _registry(owned: Path, state: dict | None = None) -> ProfileRegistry:
    try:
        registry = load_registry_file(owned / REGISTRY)
    except PromotionError as exc:
        raise LifecycleError(exc.reason) from None
    _require(state is None or registry.sha256 == state["registrySha256"], "registry-inconsistent")
    return registry


def _store_blob(path: Path, raw: bytes) -> None:
    try:
        if _read(path, len(raw), "absent") == raw:
            return
    except LifecycleError:
        pass
    _write_atomic(path, raw)


def _profile_shas(state: dict) -> set[str]:
    return {e["sha256"] for e in [state["current"], *state["previous"]] if e}


def _orphans(state: dict, files: list[str]) -> list[str]:
    referenced = {f"{PROFILES}/{sha}.json" for sha in _profile_shas(state)}
    referenced |= {f"{PRIVATE}/{r['sha256']}" for r in state["private"]}
    return [f for f in files if "/" in f and f not in referenced]


# --- read-only views ----------------------------------------------------------------


def residue(root: Any) -> list[str]:
    """Lifecycle-owned names left directly under ``root`` (empty after a clean uninstall)."""
    root = _root(root)
    try:
        names = os.listdir(root)
    except OSError:
        raise LifecycleError("io-error") from None
    return sorted(n for n in names if n == OWNED or _WORKDIR.fullmatch(n))


def status(root: Any, *, now: Any = None) -> dict:
    """Read-only status; ``now`` (a tick) evaluates expiry. Writes and deletes nothing."""
    base = {"ordinaryUse": "unavailable", "activation": ACTIVATION, "export": "disabled",
            "executionAuthorization": False, "residue": residue(root)}
    _require(now is None or _tick(now), "invalid-time")
    try:
        owned = _owned(_root(root))
    except LifecycleError as exc:
        if exc.reason != "not-installed":
            raise
        return base | {"installed": False, "state": "not-installed"}
    state = _read_state(owned)
    files, debris, foreign = _scan(owned)
    try:
        consistent = _registry(owned).sha256 == state["registrySha256"]
    except LifecycleError:
        consistent = False
    current = state["current"]
    expired = bool(current and now is not None and now >= current["expiresAt"])
    if state["halted"]:
        label = "halted"
    elif state["requalification"]:
        label = "requalification-required"
    elif expired:
        label = "expired"
    else:
        label = "installed"
    journal = state["journal"]
    return base | {
        "installed": True, "state": label, "scope": state["scope"], "host": state["host"],
        "identity": state["identity"],
        "current": None if current is None else current | {"expired": expired},
        "previous": [e["sha256"] for e in reversed(state["previous"])],
        "requalification": state["requalification"], "halted": state["halted"],
        "registryConsistent": consistent, "private": state["private"],
        "debris": sorted(debris + _orphans(state, files)), "foreign": foreign,
        "events": journal, "journal": {"entries": len(journal), "last": journal[-1]["event"],
                                       "lastAt": journal[-1]["at"]}}


def _verified_profile(owned: Path, sha: str, reason: str) -> bytes:
    raw = _read(owned / PROFILES / f"{sha}.json", MAX_BYTES, reason)
    _require(sha256(raw).hexdigest() == sha, reason)
    try:
        hc.verify_profile(raw, expected_sha256=sha)
    except hc.ProfileError:
        raise LifecycleError(reason) from None
    return raw


def read_profile(root: Any, sha: Any) -> bytes:
    """Stored bytes of the current or a prior profile, verified against its recorded identity."""
    with _locked(root) as (owned, state):
        _require(_hash(sha) and sha in _profile_shas(state), "profile-unavailable")
        return _verified_profile(owned, sha, "profile-unavailable")


def load_registry(root: Any) -> ProfileRegistry:
    with _locked(root) as (owned, _):
        return _registry(owned)


def activate(root: Any = None) -> NoReturn:
    """Always refused: ordinary use needs a separately adopted policy, ADR and operator decision."""
    raise LifecycleError("activation-requires-adoption")


# --- installation -------------------------------------------------------------------


def install(root: Any, *, opt_in: Any, operator: Any, scope: Any, host: Any, identity: Any,
            at: Any) -> dict:
    """Opt-in installation of an empty, disabled lifecycle for one task-local scope."""
    root = _root(root)
    _require(opt_in is True, "opt-in-required")
    actor = _operator(operator)
    identity = _identity(identity)
    _require(_id(scope), "invalid-scope")
    _require(_tick(at), "invalid-time")
    _require(type(host) is str and host in SUPPORTED_HOSTS, "unsupported-host")
    _require(not os.path.lexists(root / OWNED), "already-installed")
    staging = root / f"{STAGING_PREFIX}{secrets.token_hex(8)}"
    registry = ProfileRegistry.empty(scope)
    state = {"format": FORMAT, "scope": scope, "host": host, "identity": identity,
             "installedAt": at, "current": None, "previous": [], "requalification": [],
             "halted": None, "private": [], "registrySha256": registry.sha256,
             "executionAuthorization": False,
             "journal": [{"seq": 0, "event": "installed", "at": at, "actor": actor,
                          "subject": None, "detail": [host]}]}
    _check_state(state)
    try:
        os.mkdir(staging, 0o700)
        for name in _BLOB:
            os.mkdir(staging / name, 0o700)
        os.close(os.open(staging / STATE_LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        save_registry_file(staging / REGISTRY, registry)
        _write_atomic(staging / STATE, canonical(state))
        _rename(staging, root / OWNED)
        _fsync_dir(root)
    except (OSError, LifecycleError, PromotionError):
        if os.path.isdir(staging):
            try:
                _remove_tree(staging)
            except (OSError, LifecycleError):
                pass  # left for recover(); not installed either way
        raise LifecycleError("write-failed") from None
    return status(root)


def migrate(root: Any, raw: Any, *, expected_sha256: Any, expires_at: Any, operator: Any,
            at: Any) -> dict:
    """Stage a verified profile as the next linked version; the prior one is retained."""
    actor = _operator(operator)
    _require(_tick(at), "invalid-time")
    _require(_tick(expires_at) and expires_at > at, "invalid-expiry")
    _require(type(raw) is bytes and _hash(expected_sha256)
             and sha256(raw).hexdigest() == expected_sha256, "profile-drift")
    try:
        profile = hc.verify_profile(raw, expected_sha256=expected_sha256)
    except hc.ProfileError as exc:
        raise LifecycleError(exc.reason) from None
    data = profile.data
    _require(data["admission"]["state"] == "implemented", "profile-blocked")

    def change(owned: Path, state: dict, txn: _Txn) -> None:
        _gate(state)
        _require(data["host"] == state["host"], "host-mismatch")
        current = state["current"]
        linked = (data["parentSha256"] is None and profile.version == 1 if current is None else
                  data["parentSha256"] == current["sha256"]
                  and profile.version == current["version"] + 1)
        _require(linked, "migration-not-linked")
        _require(current is None or len(state["previous"]) < MAX_PREVIOUS, "history-full")
        _event(state, "migrated", at, actor=actor, subject=profile.sha256,
               detail=[f"v{profile.version}"])
        if current is not None:
            state["previous"].append(current)
        state["current"] = {"sha256": profile.sha256, "version": profile.version,
                            "expiresAt": expires_at, "migratedAt": at}
        _store_blob(owned / PROFILES / f"{profile.sha256}.json", raw)

    _mutate(root, change)
    return status(root)


def rollback(root: Any, *, operator: Any, at: Any, reason: Any) -> dict:
    """Withdraw the current profile and restore the newest prior one, byte-for-byte or refuse."""
    actor = _operator(operator)
    _require(_id(reason), "invalid-reason")

    def change(owned: Path, state: dict, txn: _Txn) -> None:
        _require(bool(state["previous"]), "no-prior-profile")
        _verified_profile(owned, state["previous"][-1]["sha256"], "prior-profile-unavailable")
        _event(state, "rolled-back", at, actor=actor, subject=state["current"]["sha256"],
               detail=[reason])
        state["current"] = state["previous"].pop()

    _mutate(root, change)
    return status(root)


# --- drift --------------------------------------------------------------------------


def check_drift(root: Any, current: Any, *, at: Any) -> list[str]:
    """Drift reasons of ``current`` against the installed identity; drift requires requalifying."""
    current = _identity(current)
    _require(_tick(at), "invalid-time")

    def change(owned: Path, state: dict, txn: _Txn) -> list[str]:
        reasons = _drift(state["identity"], current)
        merged = sorted(set(state["requalification"]) | set(reasons))
        if merged != state["requalification"]:
            _event(state, "drift-detected", at, detail=reasons)
            state["requalification"] = merged
        return reasons

    return _mutate(root, change)[0]


def requalify(root: Any, current: Any, *, operator: Any, evidence: Any, at: Any) -> dict:
    """A human rebinds the installation to ``current`` citing a requalification evidence hash."""
    actor = _operator(operator)
    current = _identity(current)
    _require(_hash(evidence), "invalid-evidence")

    def change(owned: Path, state: dict, txn: _Txn) -> None:
        _event(state, "requalified", at, actor=actor, subject=evidence,
               detail=_drift(state["identity"], current))
        state["identity"], state["requalification"] = current, []

    _mutate(root, change)
    return status(root)


# --- registry, canary, incidents and revocation --------------------------------------


def _registry_written(txn: _Txn) -> None:
    _require(txn.registryFailure is None, txn.registryFailure or "registry-unavailable")


def save_registry(root: Any, registry: Any, *, at: Any) -> dict:
    """Persist a registry a human advanced with T013 calls; its journal must extend the stored one.

    This is also the human repair after an interrupted registry write.
    """
    _require(type(registry) is ProfileRegistry, "invalid-registry")

    def change(owned: Path, state: dict, txn: _Txn) -> None:
        _require(registry.scope == state["scope"], "scope-mismatch")
        stored = _registry(owned)
        _require(registry.journal[:len(stored.journal)] == stored.journal, "concurrent-update")
        _event(state, "registry-updated", at, subject=registry.sha256)
        txn.registry = registry

    _registry_written(_mutate(root, change)[1])
    return status(root)


def begin_canary(root: Any, run: Any, record: Any, *, at: Any, **inputs: Any) -> PolicyRun:
    """``shadow`` -> ``canary`` through T009 against the persisted registry; refusals are journaled."""
    _require(type(run) is PolicyRun and "registry" not in inputs, "invalid-input")
    _require(_tick(at), "invalid-time")

    def change(owned: Path, state: dict, txn: _Txn) -> Any:
        _gate(state)
        current = state["current"]
        _require(current is not None, "no-profile")
        _require(at < current["expiresAt"], "profile-expired")
        _require(inputs.get("identity") == state["identity"], "identity-drift")
        registry = _registry(owned, state)
        try:
            new = run.begin_canary(record, at=at, registry=registry, **inputs)
        except AutoPromotionError as exc:
            _event(state, "canary-refused", at, detail=[exc.reason])
            return exc
        _event(state, "canary-begun", at, subject=new.decisionSha256)
        return new

    result = _mutate(root, change)[0]
    if isinstance(result, AutoPromotionError):
        raise result
    return result


@dataclass(frozen=True)
class Halt:
    """A canary step or stop: the run (if any), the registry after rollback, a visible failure."""

    run: PolicyRun | None
    registry: ProfileRegistry | None
    registryFailure: str | None = None

    @property
    def executionAuthorization(self) -> bool:
        return False


def _stop_registry(owned: Path) -> tuple[ProfileRegistry | None, str | None]:
    try:
        return _registry(owned), None
    except LifecycleError as exc:
        return None, exc.reason


def observe_canary(root: Any, run: Any, seen: Any, *, current: Any, at: Any) -> Halt:
    """Record one T009 canary observation; a stop rolls the registry back and is journaled.

    On a halted installation the run is stopped as an incident, and on one awaiting
    requalification as drift, instead of observing.
    """
    _require(type(run) is PolicyRun, "invalid-input")

    def change(owned: Path, state: dict, txn: _Txn) -> Halt:
        registry, failure = _stop_registry(owned)
        if state["halted"]:
            step = run.stop("incident", at=at, registry=registry)
        elif state["requalification"]:
            step = run.stop("drift", at=at, registry=registry)
        else:
            step = run.observe(seen, current=current, at=at, registry=registry)
        failure = failure or step.registryFailure
        if step.registry is not None and step.registry is not registry:
            txn.registry = step.registry
        if step.run.state != "stopped":
            _event(state, "canary-observed", at, subject=run.decisionSha256,
                   detail=[step.run.observations[-1]])
            return Halt(step.run, step.registry, failure)
        reason = step.run.journal[-1]["reason"]
        if reason == "drift-stop" and not state["requalification"]:
            try:
                drift = _drift(state["identity"], _identity(current))
            except LifecycleError:
                drift = ["invalid-identity"]
            state["requalification"] = sorted(set(drift) or {"canary-drift"})
        _event(state, "canary-stopped", at, subject=run.decisionSha256,
               detail=[reason, *([failure] if failure else [])], stop=True)
        return Halt(step.run, step.registry, failure)

    halt, txn = _mutate(root, change)
    return Halt(halt.run, halt.registry, halt.registryFailure or txn.registryFailure)


def incident_stop(root: Any, *, at: Any, run: Any = None) -> Halt:
    """Halt the installation and any run and roll the registry back; the halt is written first."""
    _require(run is None or type(run) is PolicyRun, "invalid-input")

    def change(owned: Path, state: dict, txn: _Txn) -> Halt:
        registry, failure = _stop_registry(owned)
        stopped, after = None, registry
        if run is not None:
            step = run.stop("incident", at=at, registry=registry)
            stopped, after, failure = step.run, step.registry, failure or step.registryFailure
        elif registry is not None:
            try:
                after = registry.rollback(at=at, reason="incident-stop")
            except PromotionError as exc:
                failure = exc.reason
        if after is not None and after is not registry:
            txn.registry = after
        state["halted"] = "incident-stop"
        _event(state, "incident-stop", at, detail=[failure] if failure else [], stop=True)
        return Halt(stopped, after, failure)

    halt, txn = _mutate(root, change)
    return Halt(halt.run, halt.registry, halt.registryFailure or txn.registryFailure)


def clear_incident(root: Any, *, operator: Any, evidence: Any, at: Any) -> dict:
    actor = _operator(operator)
    _require(_hash(evidence), "invalid-evidence")

    def change(owned: Path, state: dict, txn: _Txn) -> None:
        _require(state["halted"] is not None, "not-halted")
        _event(state, "incident-cleared", at, actor=actor, subject=evidence)
        state["halted"] = None

    _mutate(root, change)
    return status(root)


def revoke(root: Any, evidence: Any, *, at: Any, reason: Any,
           store: Any = None) -> tuple[ProfileRegistry, RevocationResult | None]:
    """Revoke evidence in the persisted registry and, if given, a caller-held T008 store.

    The store result is returned, not persisted: the store is the caller's value.
    """
    _require(_hash(evidence), "invalid-evidence")
    _require(_id(reason), "invalid-reason")

    def change(owned: Path, state: dict, txn: _Txn) -> tuple:
        try:
            registry = _registry(owned, state).revoke_evidence(evidence, at=at, reason=reason)
            curated = None if store is None else propagate_revocation(store, [evidence], at, reason)
        except (PromotionError, CurationError, ExperienceError) as exc:
            raise LifecycleError(exc.reason) from None
        _event(state, "evidence-revoked", at, subject=evidence, detail=[reason])
        txn.registry = registry
        return registry, curated

    result, txn = _mutate(root, change)
    _registry_written(txn)
    return result


# --- private data, retention and purge -------------------------------------------------


def retain(root: Any, data: Any, *, kind: Any, retain_until: Any, at: Any) -> str:
    """Store one private record until a caller-fixed tick; nothing deletes it but ``purge``."""
    _require(type(data) is bytes, "invalid-record")
    _require(len(data) <= MAX_PRIVATE_BYTES, "record-too-large")
    _require(type(kind) is str and kind in KINDS, "invalid-kind")
    _require(_tick(at), "invalid-time")
    _require(_tick(retain_until) and retain_until > at, "invalid-retention")
    digest = sha256(data).hexdigest()

    def change(owned: Path, state: dict, txn: _Txn) -> str:
        _require(all(r["sha256"] != digest for r in state["private"]), "duplicate-record")
        _require(len(state["private"]) < MAX_PRIVATE, "private-full")
        _event(state, "retained", at, subject=digest, detail=[kind])
        state["private"] = sorted([*state["private"], {
            "sha256": digest, "kind": kind, "sizeBytes": len(data), "retainUntil": retain_until,
            "storedAt": at}], key=lambda r: r["sha256"])
        _store_blob(owned / PRIVATE / digest, data)
        return digest

    return _mutate(root, change)[0]


def purge(root: Any, *, now: Any, operator: Any, at: Any) -> dict:
    """A human deletes private records whose retention tick is at or before ``now`` (<= ``at``)."""
    actor = _operator(operator)
    _require(_tick(now) and _tick(at) and now <= at, "invalid-time")

    def change(owned: Path, state: dict, txn: _Txn) -> list[str]:
        gone = [r["sha256"] for r in state["private"] if r["retainUntil"] <= now]
        _event(state, "purged", at, actor=actor, detail=gone)
        state["private"] = [r for r in state["private"] if r["sha256"] not in gone]
        txn.delete = tuple(f"{PRIVATE}/{sha}" for sha in gone)  # after the state drops them
        return gone

    gone, txn = _mutate(root, change)
    return {"purged": gone, "failures": [rel.split("/")[1] for rel in txn.deleteFailures],
            "executionAuthorization": False}


# --- uninstall and recovery -------------------------------------------------------------


def uninstall(root: Any, *, operator: Any, at: Any) -> dict:
    """A human removes the whole installation; refused if it holds anything not owned."""
    actor = _operator(operator)
    _require(_tick(at), "invalid-time")
    root = _root(root)
    with _locked(root) as (owned, state):
        _require(at >= state["journal"][-1]["at"], "time-regression")
        files, debris, foreign = _scan(owned)
        _require(not foreign, "foreign-content")
        removed = []
        for rel in files + debris:
            raw = _read(owned / rel, MAX_BYTES, "io-error")
            removed.append({"path": rel, "sha256": sha256(raw).hexdigest(), "sizeBytes": len(raw)})
        tomb = root / f"{REMOVING_PREFIX}{secrets.token_hex(8)}"
        try:
            _rename(owned, tomb)
            _fsync_dir(root)
        except OSError:
            raise LifecycleError("write-failed") from None
    try:  # from here on nothing is installed; recover() finishes an interrupted removal
        _remove_tree(tomb)
    except OSError:
        raise LifecycleError("cleanup-incomplete") from None
    return {"removed": removed, "operator": actor, "uninstalledAt": at,
            "stateSha256": sha256(canonical(state)).hexdigest(), "executionAuthorization": False}


def recover(root: Any) -> dict:
    """Finish interrupted installs and uninstalls and delete temporary or unreferenced files."""
    root = _root(root)
    removed = []
    try:
        if os.path.lexists(root / OWNED):
            with _locked(root) as (owned, state):
                files, debris, foreign = _scan(owned)
                _require(not foreign, "foreign-content")
                for rel in sorted(debris + _orphans(state, files)):
                    _unlink(owned / rel)
                    removed.append(f"{OWNED}/{rel}")
        for name in sorted(os.listdir(root)):
            if _WORKDIR.fullmatch(name):
                _require(stat.S_ISDIR(os.lstat(root / name).st_mode), "foreign-content")
                _remove_tree(root / name)
                removed.append(name)
    except OSError:
        raise LifecycleError("io-error") from None
    return {"removed": removed, "executionAuthorization": False}
