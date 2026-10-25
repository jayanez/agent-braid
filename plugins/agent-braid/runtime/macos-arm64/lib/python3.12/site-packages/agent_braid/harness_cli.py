# SPDX-License-Identifier: AGPL-3.0-only
"""Experimental `harness` command group for the offline laboratory.

Exit codes follow forecast_cli: 0 success, 2 refusal (a single JSON object with ``status``, a
fixed ``reason`` code and ``executionAuthorization: false`` on stdout). Argument-usage errors
also exit 2 (argparse) but print usage text on stderr and nothing on stdout; callers tell the
two apart by the stream. Anything else is an internal bug and is not converted into a
refusal. Only ``prepare`` has effects (one new private candidate directory); admission,
reservation, dispatch and reconciliation stay with the separately reviewed operator contract.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import time

from .harness_journal import JournalError, inspect_attempt
from .harness_manifest import BINDING_NAMES, ManifestError, verify_manifest
from .harness_records import MAX_RECORD_BYTES, Record, RecordError, attempt_status_record, compare, decode
from .harness_surface import SurfaceError, import_candidate
from .system_one import InvalidDecision, parse_json, thaw

HELP = "experimental offline harness laboratory inspection (no execution authority)"
COMMANDS = ("inspect", "validate", "prepare", "status", "recover-inspect", "compare")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_LIMITS = {
    "manifest": ["offline-foundations profile only: no native host, model, provider or route",
                 "hashes bind bytes; they do not prove authenticity, rights or containment"],
    "decision": ["advisory selection record: candidate labels are not blinding and the decision "
                 "grants no promotion or execution"],
    "attempt-status": ["reports what the journal durably says; it never renews permission or "
                       "allows redispatch"],
    "comparison": ["compares a fixed subset of fields (bindings, outcome, scores, losses); differing records with no listed row carry unlistedChange=true"],
}


class CliRefusal(ValueError):
    """Sanitized refusal; ``reason`` is a fixed code and ``extra`` fixed-shape receipts only."""

    def __init__(self, reason: str, extra: dict | None = None):
        self.reason, self.extra = reason, extra or {}
        super().__init__(reason)


_COMMAND_HELP = {
    "inspect": "show a record's identity, base/candidate diff, losses and limits (read-only)",
    "validate": "strictly decode a record and optionally compare trusted identities (read-only)",
    "prepare": "import one verified candidate into a new private directory (the only effect)",
    "status": "report an attempt's durable journal state (read-only)",
    "recover-inspect": "report what recovery an attempt needs without performing it (read-only)",
    "compare": "field-level comparison of two records of the same kind (read-only)",
}


def add_parser(subparsers):
    parser = subparsers.add_parser("harness", help=HELP)
    commands = parser.add_subparsers(dest="harness_command", required=True)
    for name in ("inspect", "validate"):
        child = commands.add_parser(name, help=_COMMAND_HELP[name])
        child.add_argument("input", type=Path)
        if name == "validate":
            child.add_argument("--sha256", help="trusted full SHA-256 from outside the record")
            child.add_argument("--binding", action="append", default=[], metavar="NAME=SHA256",
                               help="trusted named manifest binding (manifest records only)")
    prepare = commands.add_parser("prepare", help=_COMMAND_HELP["prepare"])
    prepare.add_argument("manifest", type=Path)
    prepare.add_argument("--sha256", required=True, help="trusted full manifest SHA-256")
    prepare.add_argument("--bindings", required=True, type=Path,
                         help="JSON object of the thirteen trusted named bindings")
    for root in ("source", "base", "candidate", "context"):
        prepare.add_argument(f"--{root}-root", required=True, type=Path)
    prepare.add_argument("--destination", required=True, type=Path, help="new directory to claim")
    for name in ("status", "recover-inspect"):
        child = commands.add_parser(name, help=_COMMAND_HELP[name])
        child.add_argument("journal", type=Path)
        child.add_argument("manifest", type=Path)
        child.add_argument("--sha256", required=True, help="trusted full manifest SHA-256")
        child.add_argument("--attempt-id", required=True)
        child.add_argument("--now", type=int, default=None, help="trusted clock; default: system time")
    compare_parser = commands.add_parser("compare", help=_COMMAND_HELP["compare"])
    compare_parser.add_argument("input", type=Path)
    compare_parser.add_argument("other", type=Path)




def _hash(value: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise CliRefusal("invalid-hash")
    return value


def _read(path: Path) -> bytes:
    """Bounded read of one regular, non-symlink file."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise CliRefusal("input-unreadable") from None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise CliRefusal("input-unreadable")
        chunks, size = [], 0
        while size <= MAX_RECORD_BYTES:  # a read may return fewer bytes than asked
            chunk = os.read(descriptor, MAX_RECORD_BYTES + 1 - size)
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        data = b"".join(chunks)
    except OSError:
        raise CliRefusal("input-unreadable") from None
    finally:
        os.close(descriptor)
    if len(data) > MAX_RECORD_BYTES:
        raise CliRefusal("input-too-large")
    return data


def _record(path: Path) -> Record:
    return decode(_read(path))


def _bindings(pairs: list[str]) -> dict[str, str]:
    result = {}
    for pair in pairs:
        name, separator, value = pair.partition("=")
        if not separator or name not in BINDING_NAMES or name in result:
            raise CliRefusal("invalid-binding")
        result[name] = _hash(value)
    return result


def _manifest(path: Path, sha256: str):
    return verify_manifest(_read(path), expected_sha256=_hash(sha256), expected_bindings={})


# --- views ----------------------------------------------------------------------------


def _file_diff(base: list[dict], candidate: list[dict]) -> dict:
    before, after = {r["path"]: r["sha256"] for r in base}, {r["path"]: r["sha256"] for r in candidate}
    return {"added": sorted(set(after) - set(before)), "removed": sorted(set(before) - set(after)),
            "modified": sorted(p for p in set(before) & set(after) if before[p] != after[p])}


def _inspect(record: Record) -> dict:
    data = record.data
    view = {"kind": record.kind, "sha256": record.sha256,
            "profileLimits": list(_LIMITS[record.kind])}
    if record.kind == "manifest":
        view.update(profile=data["profile"], taskId=data["task"]["id"],
                    baseSha256=data["base"]["sha256"], candidateSha256=data["candidate"]["sha256"],
                    candidateVsBase=_file_diff(thaw(data["base"]["files"]), thaw(data["candidate"]["files"])),
                    contextEntries=len(data["context"]), host=thaw(data["host"]["requested"]),
                    evidenceLosses=[])
    elif record.kind == "decision":
        view.update(decision=data["decision"], reasons=list(data["reasons"]),
                    chosenCandidateSha256=data["chosenCandidateSha256"],
                    evidenceLosses=list(data["losses"]), probes=data["counts"]["probes"],
                    attempts=[{"scope": a["scope"], "status": a["status"], "score": a["score"]}
                              for a in data["attempts"]])
    elif record.kind == "attempt-status":
        view.update({k: v for k, v in thaw(data).items() if k != "format"})
    else:
        view.update(identical=data["identical"], differences=thaw(data["differences"]))
    return view


def _recovery(record: Record) -> dict:
    ended = record.data["phase"] == "ended"
    return {"action": "none" if ended else "reconcile-required",
            "redispatchAllowed": False, "cliEffect": False,
            "note": "reconciliation and any new attempt need the operator contract and a fresh admission"}


# --- commands -------------------------------------------------------------------------


def _validate(args) -> dict:
    record = _record(args.input)
    bindings = _bindings(args.binding)
    result = {"kind": record.kind, "sha256": record.sha256, "authenticity": "unverified"}
    if bindings and record.kind != "manifest":
        raise CliRefusal("binding-not-applicable")
    if args.sha256 is None:
        if bindings:
            raise CliRefusal("invalid-binding")
        return result
    trusted = _hash(args.sha256)
    if record.kind == "manifest":
        verify_manifest(record.canonical_bytes, expected_sha256=trusted, expected_bindings=bindings)
    elif record.sha256 != trusted:
        raise CliRefusal("record-drift")
    return result | {"authenticity": "hash-matched"}


def _prepare(args) -> dict:
    raw = _read(args.manifest)
    try:
        bindings = parse_json(_read(args.bindings))
    except InvalidDecision:
        raise CliRefusal("invalid-bindings") from None
    try:
        receipt = import_candidate(
            raw, expected_sha256=_hash(args.sha256), expected_bindings=bindings,
            source_root=args.source_root, base_root=args.base_root,
            candidate_root=args.candidate_root, context_root=args.context_root,
            destination=args.destination)
    except SurfaceError as exc:
        raise CliRefusal(exc.reason, {"receipt": thaw(exc.receipt)} if exc.receipt else None) from None
    return {"receipt": thaw(receipt)}


def _journal(args) -> dict:
    manifest = _manifest(args.manifest, args.sha256)
    now = int(time.time()) if args.now is None else args.now
    status = inspect_attempt(args.journal.absolute(), manifest, attempt_id=args.attempt_id, now=now)
    record = attempt_status_record(status)
    result = {"record": record.to_dict()}
    if args.harness_command == "recover-inspect":
        result["recovery"] = _recovery(record)
    return result


def _dispatch(args) -> dict:
    command = args.harness_command
    if command == "inspect":
        return _inspect(_record(args.input))
    if command == "validate":
        return _validate(args)
    if command == "compare":
        return {"record": compare(_record(args.input), _record(args.other)).to_dict()}
    if command == "prepare":
        return _prepare(args)
    return _journal(args)


def _emit(value: dict) -> None:
    print(json.dumps(value, sort_keys=True, allow_nan=False))


def run(args) -> int:
    try:
        result = _dispatch(args)
    except (CliRefusal, RecordError, ManifestError, JournalError, SurfaceError) as exc:
        extra = exc.extra if isinstance(exc, CliRefusal) else {}
        _emit({"status": "refused", "reason": exc.reason, "executionAuthorization": False, **extra})
        return 2
    _emit({"status": "ok", "executionAuthorization": False, **result})
    return 0
