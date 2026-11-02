# SPDX-License-Identifier: AGPL-3.0-only
"""Experimental `harness` command group for the offline laboratory.

Exit codes follow forecast_cli: 0 success, 2 refusal (a single JSON object with ``status``, a
fixed ``reason`` code and ``executionAuthorization: false`` on stdout). Argument-usage errors
also exit 2 (argparse) but print usage text on stderr and nothing on stdout; callers tell the
two apart by the stream. Anything else is an internal bug and is not converted into a
refusal. Only ``prepare`` has effects (one new private candidate directory); admission,
reservation, dispatch and reconciliation stay with the separately reviewed operator contract.

The SPEC-049 T009 advisory views (``capabilities``, ``registry-status``,
``evaluation-summary``, ``evidence``) are read-only and experimental: they report what the
T003/T013 records and a spec's evidence directory say, never promote, activate or grant,
and add no plugin or MCP surface. Ordinary-use activation awaits the SPEC-049 T007 human
decisions; a plugin/MCP extension needs its own versioned contract and review.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import time

from .harness_evaluation import COHORTS, REPORT_FORMAT
from .harness_journal import JournalError, inspect_attempt
from .harness_manifest import BINDING_NAMES, ManifestError, verify_manifest
from .harness_promotion import AUTOMATIC_PROMOTION, PromotionError, ProfileRegistry
from .harness_records import MAX_RECORD_BYTES, Record, RecordError, attempt_status_record, compare, decode
from .harness_surface import SurfaceError, import_candidate
from .system_one import InvalidDecision, canonical, parse_json, thaw

HELP = "experimental offline harness laboratory inspection (no execution authority)"
COMMANDS = ("inspect", "validate", "prepare", "status", "recover-inspect", "compare",
            "capabilities", "registry-status", "evaluation-summary", "evidence")
MAX_EVIDENCE_FILES = 256
MAX_EVIDENCE_ENTRIES = 1024  # files and directories listed in one walk
MAX_EVIDENCE_DEPTH = 4
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_TASK = re.compile(r"^- \[([ x])\] (T[0-9]{3})\b", re.MULTILINE)
_EVALUATION_LIMITS = [
    "summarizes a self-asserted T003 report: canonical bytes, format, cohort, identity hashes, "
    "summary keys and counts are checked; nested values are copied as decoded, and strata, rows "
    "and verdicts are not re-derived from a registration, verdict records or costs",
    "a matched --sha256 binds bytes; it does not prove authenticity or independent review",
    "no promotion, activation or grant follows from any verdict; human decisions are SPEC-049 T007",
]
_EVIDENCE_LIMITS = [
    "inventory only: file hashes bind bytes; contents, claims and checkbox state are not verified",
    "task evidence matches only evidence/<task>.json",
]
_ARM_KEYS = ("registered", "started", "outcomes", "correctPerRegistered", "correctPerStarted",
             "missingSensitivity")
_COMPARISON_KEYS = ("pairs", "lineages", "worseUpperBound", "noninferiority")
_EFFECTS = {"prepare": "new-private-candidate-directory"}
_ACTIVATION = "experimental only; ordinary-use activation awaits the SPEC-049 T007 human decisions"
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
    "capabilities": "list these commands, their effects and the activation status (read-only)",
    "registry-status": "report a T013 profile registry's active, pending and audit state (read-only)",
    "evaluation-summary": "summarize a T003 evaluation report per stratum (read-only)",
    "evidence": "inventory a spec directory's evidence files against its tasks (read-only)",
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
    commands.add_parser("capabilities", help=_COMMAND_HELP["capabilities"])
    registry_parser = commands.add_parser("registry-status", help=_COMMAND_HELP["registry-status"])
    registry_parser.add_argument("registry", type=Path)
    summary_parser = commands.add_parser("evaluation-summary",
                                         help=_COMMAND_HELP["evaluation-summary"])
    summary_parser.add_argument("report", type=Path)
    summary_parser.add_argument("--sha256", help="trusted full report SHA-256 from outside the record")
    evidence_parser = commands.add_parser("evidence", help=_COMMAND_HELP["evidence"])
    evidence_parser.add_argument("spec_dir", type=Path)


def _hash(value: str) -> str:
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise CliRefusal("invalid-hash")
    return value


def _read(path, dir_fd: int | None = None) -> bytes:
    """Bounded read of one regular, non-symlink file (relative to ``dir_fd`` when given)."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
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


# --- advisory views (SPEC-049 T009) ---------------------------------------------------


def _capabilities() -> dict:
    return {"experimental": True, "ordinaryUseActivation": _ACTIVATION,
            "automaticPromotion": AUTOMATIC_PROMOTION, "pluginOrMcpSurface": "none",
            "globalHostInstructions": "untouched",
            "commands": {name: {"help": _COMMAND_HELP[name], "effect": _EFFECTS.get(name, "none")}
                         for name in COMMANDS}}


def _registry_status(path: Path) -> dict:
    registry = ProfileRegistry.from_bytes(_read(path))
    decisions = registry.decisions
    last = registry.journal[-1] if registry.journal else None
    active = registry.active
    return {"sha256": registry.sha256, "scope": registry.scope,
            "automaticPromotion": AUTOMATIC_PROMOTION, "ordinaryUseActivation": _ACTIVATION,
            "active": None if active is None else {
                "decisionSha256": active, "profile": thaw(decisions[active]["profile"])},
            "pending": registry.pending, "previous": list(registry.previous),
            "revokedEvidence": sorted(registry.revoked),
            "decisions": [{"sha256": key, "decision": d["decision"], "actor": thaw(d["actor"]),
                           "cohort": d["cohort"], "decidedAt": d["decidedAt"]}
                          for key, d in sorted(decisions.items())],
            "journal": {"entries": len(registry.journal),
                        "lastEvent": None if last is None else last["event"],
                        "lastAt": None if last is None else last["at"]}}


def _pick(value, keys: tuple[str, ...], counts: tuple[str, ...] = ()) -> dict:
    """The named keys of a mapping; listed counts must be non-negative integers."""
    if type(value) is not dict or not set(keys) <= set(value) or not all(
            type(value[key]) is int and value[key] >= 0 for key in counts):
        raise CliRefusal("invalid-evaluation")
    return {key: value[key] for key in keys}


def _pick_each(value, keys: tuple[str, ...], counts: tuple[str, ...]) -> dict:
    if type(value) is not dict:
        raise CliRefusal("invalid-evaluation")
    return {name: _pick(item, keys, counts) for name, item in value.items()}


def _stratum(value) -> dict:
    data = _pick(value, ("units", "lineages", "arms", "comparisons"), ("units", "lineages"))
    data["arms"] = _pick_each(data["arms"], _ARM_KEYS, ("registered", "started"))
    data["comparisons"] = _pick_each(data["comparisons"], _COMPARISON_KEYS,
                                     ("pairs", "lineages", "worseUpperBound"))
    return data


def _evaluation_summary(args) -> dict:
    trusted = None if args.sha256 is None else _hash(args.sha256)
    raw = _read(args.report)
    digest = sha256(raw).hexdigest()
    if trusted is not None and trusted != digest:
        raise CliRefusal("record-drift")
    try:
        value = parse_json(raw)
    except InvalidDecision:
        raise CliRefusal("invalid-json") from None
    if canonical(value) != raw:
        raise CliRefusal("non-canonical")
    data = _pick(value, ("format", "registrationSha256", "cohort", "strata", "rows",
                         "costReportSha256", "pendingEndpoints", "executionAuthorization"))
    if (data["format"] != REPORT_FORMAT or data["executionAuthorization"] is not False
            or data["cohort"] not in COHORTS or type(data["strata"]) is not dict
            or type(data["rows"]) is not list or type(data["pendingEndpoints"]) is not list
            or not all(type(data[k]) is str and _HASH.fullmatch(data[k])
                       for k in ("registrationSha256", "costReportSha256"))):
        raise CliRefusal("invalid-evaluation")
    return {"sha256": digest, "authenticity": "unverified" if trusted is None else "hash-matched",
            "format": data["format"], "registrationSha256": data["registrationSha256"],
            "cohort": data["cohort"], "costReportSha256": data["costReportSha256"],
            "pendingEndpoints": data["pendingEndpoints"], "rows": len(data["rows"]),
            "strata": {name: _stratum(s) for name, s in sorted(data["strata"].items())},
            "limits": list(_EVALUATION_LIMITS), "ordinaryUseActivation": _ACTIVATION}


def _open_directory(name, dir_fd: int | None = None) -> int:
    """Descriptor of a real directory; a link or any other file type refuses."""
    try:
        return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)
    except OSError:
        raise CliRefusal("input-unreadable") from None


def _evidence_entry(name: str, raw: bytes) -> dict:
    entry = {"path": name, "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    try:
        value = parse_json(raw)  # objects only: any other top level is not a JSON object
    except InvalidDecision:
        return entry | {"jsonObject": False, "task": None, "executionAuthorization": None}
    task, authority = value.get("task"), value.get("executionAuthorization")
    return entry | {"jsonObject": True,
                    "task": task if type(task) is str and len(task) <= 64 else None,
                    "executionAuthorization": authority if type(authority) is bool else None}


def _evidence_files(root: int) -> list[dict]:
    """Entries for every regular file below the ``root`` descriptor, walked by descriptor so
    no path is looked up twice; links, special files and over-bound trees refuse."""
    found, pending, opened, seen = [], [(root, "", 0)], [], 0
    try:
        while pending:
            directory, prefix, depth = pending.pop()
            try:
                names = sorted(entry.name for entry in os.scandir(directory))
            except OSError:
                raise CliRefusal("input-unreadable") from None
            seen += len(names)
            if seen > MAX_EVIDENCE_ENTRIES:
                raise CliRefusal("too-many-entries")
            for name in names:
                try:
                    mode = os.lstat(name, dir_fd=directory).st_mode
                except OSError:
                    raise CliRefusal("input-unreadable") from None
                if stat.S_ISDIR(mode):
                    if depth + 1 >= MAX_EVIDENCE_DEPTH:
                        raise CliRefusal("too-deep")
                    opened.append(_open_directory(name, directory))
                    pending.append((opened[-1], f"{prefix}{name}/", depth + 1))
                elif len(found) >= MAX_EVIDENCE_FILES:
                    raise CliRefusal("too-many-entries")
                else:  # _read refuses a link or a descriptor that is not a regular file
                    found.append(_evidence_entry(prefix + name, _read(name, dir_fd=directory)))
            if directory != root:  # keep at most one open descriptor per pending directory
                opened.remove(directory)
                os.close(directory)
    finally:
        for descriptor in opened:
            os.close(descriptor)
    return sorted(found, key=lambda entry: entry["path"])


def _evidence(spec: Path) -> dict:
    spec_fd = _open_directory(spec)
    try:
        evidence_fd = _open_directory("evidence", spec_fd)
        try:
            files = _evidence_files(evidence_fd)
        finally:
            os.close(evidence_fd)
        try:
            tasks_text = _read("tasks.md", dir_fd=spec_fd).decode("utf-8")
        except UnicodeDecodeError:
            raise CliRefusal("invalid-tasks") from None
    finally:
        os.close(spec_fd)
    names = {f["path"] for f in files}
    tasks = [{"id": task, "checked": mark == "x", "evidence": f"{task.lower()}.json" in names}
             for mark, task in _TASK.findall(tasks_text)]
    if len(tasks) > MAX_EVIDENCE_FILES:
        raise CliRefusal("too-many-entries")
    anomalies = ([{"kind": "checked-without-evidence", "subject": t["id"]}
                  for t in tasks if t["checked"] and not t["evidence"]]
                 + [{"kind": "claims-execution-authorization", "subject": f["path"]}
                    for f in files if f["executionAuthorization"] is True])
    return {"specDirectory": spec.resolve().name, "files": files, "tasks": tasks,
            "anomalies": anomalies, "limits": list(_EVIDENCE_LIMITS),
            "ordinaryUseActivation": _ACTIVATION}


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
    if command == "capabilities":
        return _capabilities()
    if command == "registry-status":
        return _registry_status(args.registry)
    if command == "evaluation-summary":
        return _evaluation_summary(args)
    if command == "evidence":
        return _evidence(args.spec_dir)
    return _journal(args)


def _emit(value: dict) -> None:
    print(json.dumps(value, sort_keys=True, allow_nan=False))


def run(args) -> int:
    try:
        result = _dispatch(args)
    except (CliRefusal, RecordError, ManifestError, JournalError, SurfaceError,
            PromotionError) as exc:
        extra = exc.extra if isinstance(exc, CliRefusal) else {}
        _emit({"status": "refused", "reason": exc.reason, "executionAuthorization": False, **extra})
        return 2
    _emit({"status": "ok", "executionAuthorization": False, **result})
    return 0
