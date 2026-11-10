# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 S1.5b T106: git-history replay labels (REQ-104), structural-only and fail-closed.

Pairs of diverged commits are taken from one admitted repository's history (the two parents of
first-parent merge commits, and unmerged local branch tips against the current branch). Each
pair is labelled by `git merge-tree --write-tree` (the oracle): exit 0 is `merge-clean`, exit 1
with a tree line is `merge-conflict`. That is textual cleanliness, not semantic independence.
SPEC-012's planner is reused for the System 2 report and records `plannerAgrees`; it never
changes a label. Anything the oracle cannot answer stays unlabelled with a closed reason and is
never imputed.

Gate: the repository must pass the W0 corpus gate (`s15b_corpus_gate.admit_path`, which verifies
the T101 consent and the plugin registry), then the source family `git-history-replay` must be
admitted by a digest-bound consent addendum. The T101 record does not list that family, so
without an addendum every real run is refused. Only commits authored by the owner (identity
given by the caller, matched in memory, never stored or echoed) are replayed; a pair that
contains any other author is skipped and only counted.

Safety: the oracle runs in an empty scratch bare repository whose object store has the real
repository as an alternate, with a sanitized environment (temporary HOME, no system or global
config, no hooks, no template), so no object is written into the repository and no merge driver
or attribute from it is read or executed. Every other Git call is read only and bounded by
`GitCommandBudget`. Records and evidence hold closed vocabularies and counts only: no commit id,
path, author, message or ref name. The shadow episode store is never written. No network.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import random
import re
import secrets
import stat
import tempfile
import uuid

from agent_braid import git_replay, system_one_shadow as shadow
from agent_braid.git_adapter import analyze_git_with_provenance
from agent_braid.git_process import GitCommandBudget, GitCommandFailure, GitInfrastructureFailure, run_git
from research import s15b_corpus_gate as gate

FAMILY = "git-history-replay"
SCHEMA = "agent-braid-s1-outcome/v0.1"
EVIDENCE_SCHEMA = "agent-braid-spec066-s15b-replay-evidence/v0.1"
SOURCE = "git-history-replay"  # the record source, kept apart from the consent family above
MIN_GIT = (2, 38)
MAX_PAIRS = 200
MAX_MERGES = 2000
MAX_SIDE_PATHS = git_replay.MAX_PATHS
MAX_AUTHOR_COMMITS = 1000
SAMPLE_SEED = 0x5115B106
MAX_RECORDS_FILE = 4096
MAX_STORE_BYTES = 4 * 1024 * 1024
STORE_NAME = "system-one-s15b"
ORIGINS = ("merge-commit", "branch-tip")
OUTCOME_KINDS = ("merge-clean", "merge-conflict")
UNLABELLED = ("oracle-error", "no-merge-base", "objects-missing", "too-many-paths", "git-too-old", "analysis-error")
SKIPPED = ("octopus", "not-diverged", "author-excluded", "author-unverifiable")
AGREEMENT = (True, False, "unavailable")
ERRORS = ("not-a-worktree", "owner-identity-missing", "no-default-branch", "git-unavailable", "analysis-failed",
          "store-unsafe")
RECORD_KEYS = frozenset({"schemaVersion", "joinKey", "day", "source", "outcomeKind", "joinStatus",
                         "unlabelledReason", "pair", "plannerAgrees", "executionAuthorization"})
LIMITS = [
    "merge-tree labels textual cleanliness of the pair, not semantic independence or test success.",
    "Pairs from existing merge commits are work the owner already merged and resolved, so merge-conflict is "
    "over-represented relative to live runs; report by source and never pool silently.",
    "plannerAgrees compares two procedures (patch application versus three-way merge); a disagreement is data "
    "about the proxy, not a reason to drop a pair.",
    "Only commits authored by the owner are replayed; one person's history is not a population.",
    "Records are anchored to the run date and kept 30 days; resource pseudonyms share the record's life.",
]
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_OID = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_VERSION = re.compile(r"(\d+)\.(\d+)")
_FILE = re.compile(r"^replay-(\d{4}-\d{2}-\d{2})\.jsonl$")
_ENV_KEYS = ("PATH", "HOME", "TMPDIR", "LC_ALL", "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL",
             "GIT_TERMINAL_PROMPT", "GIT_OPTIONAL_LOCKS", "GIT_ALLOW_PROTOCOL", "GIT_PROTOCOL_FROM_USER",
             "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0", "GIT_CONFIG_KEY_1", "GIT_CONFIG_VALUE_1",
             "GIT_CONFIG_KEY_2", "GIT_CONFIG_VALUE_2", "GIT_CONFIG_KEY_3", "GIT_CONFIG_VALUE_3")
# Command-line config overrides repository-local config: these keys can make a read-only Git command run
# a program named by the repository (signature verification, fsmonitor, external diff, hooks).
_FORCED_CONFIG = (("log.showSignature", "false"), ("core.fsmonitor", "false"), ("diff.external", ""),
                  ("core.hooksPath", os.devnull))


class ReplayError(Exception):
    """A fixed code from `ERRORS`; the message is the code and carries nothing else."""

    def __init__(self, code: str) -> None:
        if code not in ERRORS:
            raise ValueError("unknown replay error code")
        self.code = code
        super().__init__(code)


class _Unlabelled(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def today() -> date:
    return datetime.now(timezone.utc).date()


def sanitized_environment(home: Path) -> dict:
    """Bounded Git environment without inherited config, hooks or remotes (SPEC-012's, plus forced overrides)."""
    home.mkdir(parents=True, exist_ok=True)
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home), "TMPDIR": str(home),
            "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "GIT_ALLOW_PROTOCOL": "file",
            "GIT_PROTOCOL_FROM_USER": "0", "GIT_CONFIG_COUNT": str(len(_FORCED_CONFIG)),
            **{f"GIT_CONFIG_{part}_{index}": value for index, pair in enumerate(_FORCED_CONFIG)
               for part, value in zip(("KEY", "VALUE"), pair)}}


class _Context:
    def __init__(self, tmp: Path) -> None:
        self.tmp = tmp
        self.env = sanitized_environment(tmp / "home")
        self.scratch = 0

    def budget(self, *, commands: int = 512, seconds: float = 120.0) -> GitCommandBudget:
        return GitCommandBudget(temp_root=self.tmp, wall_seconds=seconds, max_commands=commands)

    def git(self, cwd: Path, *args: str, budget: GitCommandBudget, allow_failure: bool = True):
        return run_git(cwd, args, env=self.env, budget=budget, allow_failure=allow_failure)


def _text(output: bytes) -> str:
    return output.decode("utf-8", "replace").strip()


def git_version(ctx: _Context) -> tuple | None:
    try:
        result = ctx.git(ctx.tmp, "--version", budget=ctx.budget(commands=4))
    except (GitCommandFailure, GitInfrastructureFailure):
        return None
    match = _VERSION.search(_text(result.stdout)) if result.returncode == 0 else None
    return (int(match.group(1)), int(match.group(2))) if match else None


class _Pair:
    __slots__ = ("origin", "left", "right", "merge", "base")

    def __init__(self, origin: str, left: str, right: str, merge: str | None = None) -> None:
        self.origin, self.left, self.right, self.merge, self.base = origin, left, right, merge, None


def _need_oid(value: str) -> str:
    if not _OID.fullmatch(value):
        raise ReplayError("git-unavailable")
    return value


def _enumerate(ctx: _Context, root: Path) -> tuple[list, Counter, bool]:
    """Candidate pairs in deterministic order, octopus merges counted; never reads file content."""
    budget = ctx.budget(commands=64, seconds=120.0)
    skipped: Counter = Counter()
    head = ctx.git(root, "rev-parse", "--verify", "-q", "HEAD^{commit}", budget=budget)
    name = ctx.git(root, "symbolic-ref", "-q", "--short", "HEAD", budget=budget)
    if head.returncode or name.returncode:
        raise ReplayError("no-default-branch")
    tip = _need_oid(_text(head.stdout))
    branch = _text(name.stdout)
    merges = ctx.git(root, "rev-list", "--first-parent", "--min-parents=2", "--parents",
                     f"--max-count={MAX_MERGES + 1}", "HEAD", budget=budget, allow_failure=False)
    lines = _text(merges.stdout).splitlines()
    capped = len(lines) > MAX_MERGES
    pairs, seen = [], set()
    for line in lines[:MAX_MERGES]:
        parts = line.split()
        if len(parts) > 3:
            skipped["octopus"] += 1
        elif len(parts) == 3:
            if (parts[1], parts[2]) not in seen:
                seen.add((parts[1], parts[2]))
                pairs.append(_Pair("merge-commit", _need_oid(parts[1]), _need_oid(parts[2]), _need_oid(parts[0])))
    refs = ctx.git(root, "for-each-ref", "--format=%(objectname) %(refname)", "--sort=refname",
                   "refs/heads", budget=budget, allow_failure=False)
    for line in _text(refs.stdout).splitlines():
        oid, _, ref = line.partition(" ")
        if ref == f"refs/heads/{branch}" or not _OID.fullmatch(oid):
            continue
        merged = ctx.git(root, "merge-base", "--is-ancestor", oid, tip, budget=budget)
        if merged.returncode not in (0, 1):
            raise ReplayError("git-unavailable")
        if merged.returncode == 1 and (tip, oid) not in seen:
            seen.add((tip, oid))
            pairs.append(_Pair("branch-tip", tip, oid))
    return pairs, skipped, capped


def _precheck(ctx: _Context, root: Path, pair: _Pair, owner: str, shallow: bool, budget) -> str | None:
    """Return a skip reason, or None. Sets `pair.base` (None when there is no merge-base)."""
    present = all(ctx.git(root, "cat-file", "-e", f"{oid}^{{commit}}", budget=budget).returncode == 0
                  for oid in (pair.left, pair.right))
    if shallow or not present:
        return "objects-missing"
    base = ctx.git(root, "merge-base", pair.left, pair.right, budget=budget)
    pair.base = _text(base.stdout).splitlines()[0] if base.returncode == 0 and base.stdout.strip() else None
    revs = [pair.left, pair.right] + ([pair.merge] if pair.merge else [])
    if pair.base in (pair.left, pair.right):
        return "not-diverged"
    args = ["log", "--no-show-signature", "--format=%ae", f"--max-count={MAX_AUTHOR_COMMITS + 1}", "--no-mailmap", *revs]
    if pair.base:
        args += ["--not", pair.base]
    result = ctx.git(root, *args, budget=budget)
    if result.returncode:
        return "author-unverifiable"
    emails = _text(result.stdout).splitlines()
    if len(emails) > MAX_AUTHOR_COMMITS:
        return "author-unverifiable"
    if any(email.strip().casefold() != owner for email in emails):
        return "author-excluded"
    return None


def _changed_paths(ctx: _Context, root: Path, base: str, tip: str, budget) -> int:
    result = ctx.git(root, "diff", "--name-only", "-z", "--no-renames", "--no-ext-diff", "--no-textconv",
                     base, tip, "--", budget=budget)
    if result.returncode:
        raise _Unlabelled("oracle-error")
    return len([item for item in result.stdout.split(b"\0") if item])


def _oracle(ctx: _Context, root: Path, pair: _Pair, budget) -> str:
    """`git merge-tree --write-tree` in an empty scratch bare repository over the real objects."""
    ctx.scratch += 1
    scratch = ctx.tmp / f"scratch-{ctx.scratch}"
    made = ctx.git(ctx.tmp, "init", "--bare", "--template=", "-q", str(scratch), budget=budget)
    common = ctx.git(root, "rev-parse", "--git-common-dir", budget=budget)
    if made.returncode or common.returncode:
        raise _Unlabelled("oracle-error")
    objects = Path(os.path.realpath(root / _text(common.stdout))) / "objects"
    (scratch / "objects" / "info").mkdir(parents=True, exist_ok=True)
    (scratch / "objects" / "info" / "alternates").write_text(str(objects) + "\n", encoding="utf-8")
    result = ctx.git(scratch, "merge-tree", "--write-tree", "--no-messages", pair.left, pair.right, budget=budget)
    first = _text(result.stdout).splitlines()[:1]
    if result.returncode == 0 and first and _OID.fullmatch(first[0]):
        return "merge-clean"
    if result.returncode == 1 and first and _OID.fullmatch(first[0]):
        return "merge-conflict"
    raise _Unlabelled("oracle-error")


def _agreement(kind: str, request: dict, budget: GitCommandBudget) -> object:
    """Planner agreement, recorded only: equivalent orders with a clean merge, divergent with a conflict."""
    try:
        bundle, _ = git_replay.produce(request, budget=budget)
    except Exception:  # noqa: BLE001 - recorded only; any planner failure is "unavailable", never a label change
        return "unavailable"
    result = bundle.get("result")
    if result == "equivalent-observed":
        return kind == "merge-clean"
    if result == "divergent":
        return kind == "merge-conflict"
    return "unavailable"


def _request(root: Path, pair: _Pair) -> dict:
    return {"gitAnalysisRequestVersion": "0.1.0-alpha", "repository": str(root), "baseRevision": pair.base,
            "operations": [{"instanceId": side, "attemptId": side, "source": {"kind": "commit", "revision": oid},
                            "dependencies": [], "uncertainPaths": []}
                           for side, oid in (("left", pair.left), ("right", pair.right))]}


def _episode_pair(ctx: _Context, request: dict, salt: bytes | None) -> dict:
    try:
        report, _ = analyze_git_with_provenance(request, env=ctx.env, budget=ctx.budget())
        episode = shadow.build_episode(report, "analyze", "git", request=request, salt=salt)
        shadow.validate_episode(episode)
    except Exception:  # noqa: BLE001 - any analysis failure is the closed reason, never its text
        raise _Unlabelled("analysis-error") from None
    if len(episode["pairs"]) != 1:
        raise _Unlabelled("analysis-error")
    return episode["pairs"][0]


def _label(ctx: _Context, root: Path, pair: _Pair, old_git: bool, salt: bytes | None) -> tuple:
    """Return (outcomeKind|None, unlabelledReason|None, pairObject|None, plannerAgrees)."""
    budget = ctx.budget()
    try:
        if old_git:
            raise _Unlabelled("git-too-old")
        if pair.base is None:
            raise _Unlabelled("no-merge-base")
        for oid in (pair.left, pair.right):
            if _changed_paths(ctx, root, pair.base, oid, budget) > MAX_SIDE_PATHS:
                raise _Unlabelled("too-many-paths")
        kind = _oracle(ctx, root, pair, budget)
    except _Unlabelled as exc:
        return None, exc.reason, None, "unavailable"
    except (GitCommandFailure, GitInfrastructureFailure, OSError):
        return None, "oracle-error", None, "unavailable"
    request = _request(root, pair)
    try:
        episode_pair = _episode_pair(ctx, request, salt)
    except _Unlabelled as exc:
        return None, exc.reason, None, "unavailable"
    return kind, None, episode_pair, _agreement(kind, request, ctx.budget())


def _record(day: str, kind, reason, pair, agrees) -> dict:
    return {"schemaVersion": SCHEMA, "joinKey": str(uuid.UUID(bytes=secrets.token_bytes(16), version=4)),
            "day": day, "source": SOURCE, "outcomeKind": kind,
            "joinStatus": "labelled" if kind else "unlabelled", "unlabelledReason": reason,
            "pair": pair, "plannerAgrees": agrees, "executionAuthorization": False}


def validate_record(record: object) -> dict:
    ok = (type(record) is dict and set(record) == RECORD_KEYS and record["schemaVersion"] == SCHEMA
          and record["source"] == SOURCE and record["executionAuthorization"] is False
          and type(record["day"]) is str and bool(_DAY.fullmatch(record["day"]))
          and type(record["joinKey"]) is str and (type(record["plannerAgrees"]) is bool or record["plannerAgrees"] == "unavailable")
          and (record["outcomeKind"] in OUTCOME_KINDS) == (record["joinStatus"] == "labelled")
          and (record["unlabelledReason"] in UNLABELLED) == (record["joinStatus"] == "unlabelled")
          and (record["outcomeKind"] is None) == (record["unlabelledReason"] is not None)
          and (record["pair"] is None or type(record["pair"]) is dict))
    if not ok:
        raise ValueError("invalid replay record")
    if record["pair"] is not None:
        shadow._validate_v02_pair(record["pair"])
    return record


def read_salt(directory: Path | None = None) -> bytes | None:
    """The store secret if it exists and is safe; never created."""
    path = Path(shadow.default_directory() if directory is None else directory) / shadow.SALT_FILE
    try:
        return shadow._read_secret(path)
    except (OSError, ValueError):
        return None


def replay(repository, *, owner_email: str, addendum: dict | None = None, home: Path | None = None,
           consent_path: Path | None = None, salt_dir: Path | None = None, run_day: date | None = None) -> dict:
    """Gate, enumerate, label. Returns `{records, evidence}`; writes nothing."""
    if type(owner_email) is not str or "@" not in owner_email.strip():
        raise ReplayError("owner-identity-missing")
    owner = owner_email.strip().casefold()
    consent = gate.load_consent(consent_path)
    gate.admit_path(repository, home=home, consent_path=consent_path)
    gate.require_source_family(FAMILY, consent=consent, addendum=addendum)
    day = (run_day or today()).isoformat()
    with tempfile.TemporaryDirectory(prefix="agent-braid-s15b-replay-") as directory:
        ctx = _Context(Path(directory).resolve())
        try:
            top = ctx.git(Path(os.path.realpath(repository)), "rev-parse", "--show-toplevel",
                          budget=ctx.budget(commands=4))
            if top.returncode or not _text(top.stdout):
                raise ReplayError("not-a-worktree")
            root = Path(os.path.realpath(_text(top.stdout)))
            gate.admit_path(root, home=home, consent_path=consent_path)
            version = git_version(ctx)
            old_git = version is None or version < MIN_GIT
            shallow_answer = ctx.git(root, "rev-parse", "--is-shallow-repository", budget=ctx.budget(commands=4))
            if shallow_answer.returncode or _text(shallow_answer.stdout) not in ("true", "false"):
                raise ReplayError("git-unavailable")
            shallow = _text(shallow_answer.stdout) == "true"
            pairs, skipped, capped = _enumerate(ctx, root)
            salt = shadow._repo_salt(read_salt(salt_dir), str(root))
            kept = []
            for pair in pairs:
                reason = _precheck(ctx, root, pair, owner, shallow, ctx.budget())
                if reason in SKIPPED:
                    skipped[reason] += 1
                else:
                    kept.append((pair, reason))
            sampled = len(kept) > MAX_PAIRS
            if sampled:
                chosen = sorted(random.Random(SAMPLE_SEED).sample(range(len(kept)), MAX_PAIRS))
                kept = [kept[index] for index in chosen]
            records, origins, agreement = [], Counter(), Counter()
            for pair, precheck in kept:
                origins[pair.origin] += 1
                if precheck:
                    result = (None, precheck, None, "unavailable")
                else:
                    result = _label(ctx, root, pair, old_git, salt)
                records.append(validate_record(_record(day, *result)))
                agreement[str(result[3]).lower()] += 1
        except (GitCommandFailure, GitInfrastructureFailure, OSError, ValueError):
            raise ReplayError("git-unavailable") from None
    attempted = [r for r in records if r["pair"] is not None or r["unlabelledReason"] == "analysis-error"]
    if attempted and all(r["unlabelledReason"] == "analysis-error" for r in attempted):
        raise ReplayError("analysis-failed")
    labelled = Counter(r["outcomeKind"] for r in records if r["outcomeKind"])
    unlabelled = Counter(r["unlabelledReason"] for r in records if r["unlabelledReason"])
    evidence = {
        "schema": EVIDENCE_SCHEMA, "date": day, "executionAuthorization": False,
        "pairs": {"enumerated": len(pairs), "recorded": len(records), "sampledToCap": sampled,
                  "enumerationCapped": capped, "byOrigin": {k: origins.get(k, 0) for k in ORIGINS},
                  "skipped": {k: skipped.get(k, 0) for k in SKIPPED},
                  "labelled": {k: labelled.get(k, 0) for k in OUTCOME_KINDS},
                  "unlabelled": {k: unlabelled.get(k, 0) for k in UNLABELLED}},
        "plannerAgrees": {"true": agreement.get("true", 0), "false": agreement.get("false", 0),
                          "unavailable": agreement.get("unavailable", 0)},
        "allPairsExcludedByAuthor": not kept and skipped.get("author-excluded", 0) > 0,
        "gitSupportsMergeTree": not old_git, "retentionDays": gate.RETENTION_DAYS, "limits": list(LIMITS)}
    return {"records": records, "evidence": evidence}


# --- Store: private directory beside, not inside, the shadow store ----------------------------

def default_store() -> Path:
    return shadow.default_directory().parent / STORE_NAME


def _open_store(directory: Path) -> None:
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = os.lstat(directory)
    except OSError:
        raise ReplayError("store-unsafe") from None
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ReplayError("store-unsafe")


def write_records(records: list, *, store: Path | None = None, run_day: date | None = None) -> int:
    """Replace the replay file atomically (0600); every earlier replay file is superseded and removed.

    Retention therefore counts from the latest run date and never keeps a second copy of a pair."""
    current = run_day or today()
    directory = Path(default_store() if store is None else store)
    _open_store(directory)
    payload = "".join(json.dumps(validate_record(r), sort_keys=True, separators=(",", ":")) + "\n"
                      for r in records).encode()
    if len(records) > MAX_RECORDS_FILE or len(payload) > MAX_STORE_BYTES:
        raise ReplayError("store-unsafe")
    gate.require_retained(current, today())
    for entry in sorted(os.listdir(directory)):
        match = _FILE.fullmatch(entry)
        if match and stat.S_ISREG(os.lstat(directory / entry).st_mode):
            (directory / entry).unlink()  # one logical file: every run recomputes, so older copies would double-count
    target, temporary = directory / f"replay-{current.isoformat()}.jsonl", directory / f"replay.{secrets.token_hex(8)}.tmp"
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, target)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise ReplayError("store-unsafe") from None
    return len(records)
