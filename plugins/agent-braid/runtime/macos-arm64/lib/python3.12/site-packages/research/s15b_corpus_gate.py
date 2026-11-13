# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 S1.5b W0: enforce the T101 corpus consent on a path (REQ-101).

The T101 record is a scope, not a corpus. This module turns it into a fail-closed gate:
a path is admitted only inside the single admitted workspace (its registered source root
or a registered, existing worktree root), as the plugin registry says. Admitting a path
grants nothing else: no execution authority, no training admission, no SPEC-051 authority
descriptor (that needs the T103/T104 pins and a trusted operator registry).

The admitted and excluded workspace ids are literal constants here, so widening the corpus
needs a code change and review, not only an edit of the consent data. Refusals use a closed
set of codes and never echo a path, a workspace id or any input. The module reads only (the
consent record and the plugin registry) and writes nothing. No network, no subprocess.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import os
from pathlib import Path
import stat

from agent_braid import plugin_registry
from agent_braid.owned_work_authority import OwnedWorkError, digest, parse_json

ADMITTED_WORKSPACE_ID = "eedc05f71069fdb4af00c6b99932195b"
EXCLUDED_WORKSPACE_IDS = frozenset({"d3bbc34b44184e2d87966c8175c1a277", "d615578cfefe747d77cd4ae884525081"})
RETENTION_DAYS = 30
MAX_RECORD_BYTES = 65536
CONSENT_PATH = (Path(__file__).resolve().parents[1]
                / "specs/066-system-one-shadow/evidence/owner-consent-s15b-corpus-20261110.json")

CODES = ("consent-invalid", "registry-unavailable", "workspace-not-registered", "workspace-excluded",
         "path-outside-admitted", "source-family-not-admitted", "retention-expired")
ADDENDUM_SCHEMA = "agent-braid-spec066-s15b-source-family-addendum/v1"
_SCOPE = "agent-braid-spec066-s15b-corpus-scope/v1"
_CONSENT_REF = "agent-braid-spec066-s15b-corpus-consent-ref/v1"
_ROOT = "agent-braid-spec066-s15b-corpus-root/v1"


class GateRefusal(Exception):
    """A fixed refusal code from `CODES`; the message is the code and carries nothing else."""

    def __init__(self, code: str) -> None:
        if code not in CODES:
            raise ValueError("unknown refusal code")
        self.code = code
        super().__init__(code)


class RefusalCounter:
    """Counts refusals by closed code; evidence and logs use these counts, never inputs."""

    def __init__(self) -> None:
        self._counts = dict.fromkeys(CODES, 0)

    def record(self, refusal: GateRefusal) -> None:
        self._counts[refusal.code] += 1

    def counts(self) -> dict:
        return dict(self._counts)


@dataclass(frozen=True)
class Consent:
    """The verified parts of the T101 record that callers may use."""

    source_families: tuple
    retention_days: int
    scope_digest: str


def _need(condition: bool, code: str = "consent-invalid") -> None:
    if not condition:
        raise GateRefusal(code)


def _read_record(path: Path) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            _need(stat.S_ISREG(os.fstat(stream.fileno()).st_mode))
            return stream.read(MAX_RECORD_BYTES + 1)
    except OSError:
        raise GateRefusal("consent-invalid") from None


def load_consent(path: Path | None = None) -> Consent:
    """Read and verify the T101 record; any deviation is `consent-invalid`."""
    raw = _read_record(Path(CONSENT_PATH if path is None else path))
    try:
        record = parse_json(raw, limit=MAX_RECORD_BYTES)
        corpus, owner, digests = record["corpus"], record["ownerResponse"], record["digests"]
        admitted, excluded = corpus["admittedWorkspaces"], corpus["excludedWorkspaces"]
        _need(record["executionAuthorization"] is False and record["trainingAdmission"] is False)
        _need(record["schema"] == "agent-braid-spec066-s15b-corpus-consent/v0.1"
              and record["decision"] == "admitted-scope-only")
        _need(corpus["dataClass"] == "structural-only" and corpus["retentionDays"] == RETENTION_DAYS)
        _need(isinstance(admitted, list) and len(admitted) == 1 and isinstance(excluded, list))
        _need(admitted[0]["workspaceId"] == ADMITTED_WORKSPACE_ID
              and admitted[0]["sourceRootDigest"] == digest({"schema": _ROOT, "workspaceId": ADMITTED_WORKSPACE_ID}))
        excluded_ids = [entry["workspaceId"] for entry in excluded]
        _need(len(excluded_ids) == len(set(excluded_ids)) and set(excluded_ids) == EXCLUDED_WORKSPACE_IDS)
        families = corpus["sourceFamilies"]
        _need(isinstance(families, list) and all(isinstance(name, str) for name in families))
        scope = digest({"schema": _SCOPE, "corpus": corpus})
        _need(digests["scopeDigest"] == scope)
        _need(digests["consentReferenceDigest"] == digest(
            {"schema": _CONSENT_REF, "date": record["decisionDate"], "answer": owner["answer"],
             "decision": owner["decisionAsRecorded"]}))
        return Consent(tuple(families), RETENTION_DAYS, scope)
    except (OwnedWorkError, KeyError, TypeError, AttributeError):
        raise GateRefusal("consent-invalid") from None


def _inside(path: Path, root: Path) -> bool:
    return path.is_relative_to(root)


def _inside_folded(path: Path, root: Path) -> bool:
    """Case-insensitive containment, used for exclusion so a case variant on a case-insensitive
    filesystem cannot slip past an excluded root (over-refusing is the safe direction)."""
    return Path(str(path).casefold()).is_relative_to(Path(str(root).casefold()))


def _real(item) -> Path:
    return Path(os.path.realpath(item))


def _roots(row: dict) -> list:
    """Real source root and existing real worktree roots; a root that is the filesystem root,
    the user's home or one of its ancestors is too broad to be a workspace and is dropped."""
    home = _real(Path.home())
    found = [(_real(row["sourceRoot"]), "source-root")] + [
        (_real(item), "worktree") for item in row["worktreeRoots"] if Path(item).is_dir()]
    return [(root, kind) for root, kind in found if root != root.parent and not home.is_relative_to(root)]


def admit_path(path, *, home: Path | None = None, consent_path: Path | None = None) -> dict:
    """Admit `path` only inside the admitted workspace; returns `{workspaceId, rootKind}`.

    `home` is the plugin home (default: the plugin registry's own default). The consent is
    always verified here. A path containing `..` is refused, the rest is resolved through
    symlinks, and registry roots are resolved the same way. A path under an excluded
    workspace is refused even when it is also nested under an admitted root. The verdict
    is returned, not the resolved path: callers must not treat it as a handle (the path can
    change after the check) and re-check at use.
    """
    load_consent(consent_path)
    try:
        raw = os.fspath(path)
        _need(isinstance(raw, str) and "\0" not in raw and ".." not in Path(raw).parts, "path-outside-admitted")
        target = Path(os.path.realpath(raw))
    except (TypeError, ValueError, OSError):
        raise GateRefusal("path-outside-admitted") from None
    try:
        rows = plugin_registry.inspect_registry(home)["value"]["workspaces"]
    except (plugin_registry.RegistryError, OSError, KeyError, TypeError, ValueError):
        raise GateRefusal("registry-unavailable") from None

    try:
        by_id = {row["workspaceId"]: _roots(row) for row in rows}
    except (KeyError, TypeError, OSError, RuntimeError):
        raise GateRefusal("registry-unavailable") from None
    if ADMITTED_WORKSPACE_ID not in by_id:
        raise GateRefusal("workspace-not-registered")
    if any(_inside_folded(target, root) for identifier in EXCLUDED_WORKSPACE_IDS for root, _ in by_id.get(identifier, ())):
        raise GateRefusal("workspace-excluded")
    for root, kind in by_id[ADMITTED_WORKSPACE_ID]:
        if _inside(target, root):
            return {"workspaceId": ADMITTED_WORKSPACE_ID, "rootKind": kind}
    raise GateRefusal("path-outside-admitted")


def require_source_family(name: str, *, consent: Consent | None = None, addendum: dict | None = None) -> None:
    """Refuse a source family the consent does not list.

    An addendum may add families only when it is bound to this consent's scope digest and
    carries its own digest; it never changes the corpus or the workspace.
    """
    if consent is None:
        consent = load_consent()
    allowed = set(consent.source_families)
    if addendum is not None:
        try:
            body = {key: addendum[key] for key in ("schema", "consentScopeDigest", "sourceFamilies")}
            ok = (set(addendum) == {*body, "digest"} and body["schema"] == ADDENDUM_SCHEMA
                  and body["consentScopeDigest"] == consent.scope_digest
                  and isinstance(body["sourceFamilies"], list)
                  and all(isinstance(item, str) for item in body["sourceFamilies"])
                  and addendum["digest"] == digest(body))
        except (KeyError, TypeError, OwnedWorkError):
            ok = False
        _need(ok, "source-family-not-admitted")
        allowed |= set(body["sourceFamilies"])
    _need(isinstance(name, str) and name in allowed, "source-family-not-admitted")


def retention_cutoff(today: date) -> date:
    """First admitted day (the caller supplies today in UTC): older records must be purged."""
    return today - timedelta(days=RETENTION_DAYS)


def require_retained(record_day: date, today: date) -> None:
    """Refuse a record older than the retention cutoff."""
    _need(type(record_day) is date and type(today) is date, "retention-expired")
    _need(record_day >= retention_cutoff(today), "retention-expired")
