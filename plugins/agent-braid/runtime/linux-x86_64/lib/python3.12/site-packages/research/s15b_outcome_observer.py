# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 S1.5b T102: outcome observer (REQ-102).

Joins System One shadow episode pairs with a later observed outcome (runtime conflict,
merge conflict, verify result) under a random join key. It emits outcome *kinds*, never
labels (T103's rubric maps kinds to labels). Nothing here is a scientific result and
nothing grants execution or training authority.

Privacy and safety rules (plan section 4):

* Structural only. A record holds closed vocabularies, counts and the episode pair's
  already-structural v0.2 object. No episode id, path, resource name, commit or run
  identifier, and no hash input is ever stored, logged or placed in an exception.
* Every outcome source passes the W0 corpus gate (`admit_path`) before any read.
* The host-global shadow store is read only. The store secret is read without creating
  it (the shadow module's own secret helper creates `salt.key` and is never called).
  Episodes of excluded workspaces are matched in memory at most and never persisted or
  purged (owner decision Q8). An episode without resource pseudonyms is never joined.
* Own store: `system-one-s15b/` beside the shadow store, private, bounded, retention
  anchored to the episode day, purged on write and on read, and removed by `purge()`
  (owner decision Q4: `python -m scripts.spec066_s15b_observe --purge` is the
  revocation path for this store). Nothing is written inside any repository.
* No network, no subprocess, no model call.

Private names of `agent_braid.system_one_shadow` used here (pinned by test T102-9):
`_store_root`, `_read_secret`, `_repo_salt`, `_pseudonym`.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Protocol
import uuid

from agent_braid import plugin_registry, system_one_shadow as shadow
from research import s15b_corpus_gate as gate

SCHEMA = "agent-braid-s1-outcome/v0.1"
OUTCOME_KINDS = ("runtime-conflict", "merge-conflict", "merge-clean", "verify-pass", "verify-fail")
SOURCE = "real-run"
MATCH_WINDOW_DAYS = 7
STORE_NAME = "system-one-s15b"
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_INVENTORY_ENTRIES = 10_000
RULE_ANSWER_FIELD = "ruleAnswer"
RECORD_FIELDS = frozenset({"schemaVersion", "joinKey", "day", "source", "outcomeKind", "joinStatus", "pair",
                           "executionAuthorization", RULE_ANSWER_FIELD})
INDEPENDENT = "likely-independent"
COUNTERS = ("outcomes-seen", "outcomes-invalid", "joined", "no-episode", "salt-unmatched", "ambiguous",
            "duplicate", "written", "episodes-read", "episodes-invalid", "episodes-unattributable",
            "episode-files-refused", "secret-absent", "secret-unsafe", "roots-unavailable", "no-salt",
            "truncated", "source-error", "advised-pairs", "rule-answered-pairs")
_UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
_EPISODE_FILE = re.compile(r"^episodes-(\d{4}-\d{2}-\d{2})\.jsonl$")
_OUTCOME_FILE = re.compile(r"^outcomes-(\d{4}-\d{2}-\d{2})\.jsonl$")
_LOCK = "store.lock"


class ObserverRefused(Exception):
    """A fixed, input-free refusal message for the store and record rules."""


def _need(condition: bool, message: str = "refused") -> None:
    if not condition:
        raise ObserverRefused(message)


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


# --- Outcomes and sources ---------------------------------------------------------

@dataclass(frozen=True)
class Outcome:
    """One observed outcome for a pair; resources stay in memory only."""

    kind: str
    day: date
    admission: dict
    left: frozenset
    right: frozenset
    variants: tuple | None = None  # pre-hashed sides: ((sorted sides, shared) hash lists per candidate salt)


@dataclass(frozen=True)
class HashedRow:
    """A source row that already holds salted pseudonyms (never resources): `variants` is a tuple of
    `{"left": [...], "right": [...], "shared": [...]}`, one per candidate repository salt."""

    kind: str
    day: date
    variants: tuple


class OutcomeSource(Protocol):
    """A source of pair-level outcomes. `root` is the path the gate must admit before any read.

    `outcomes(window)` yields `(outcomeKind, day, left_resources, right_resources)`; the
    observer adds the gate verdict. `window` is `(first_day, last_day)`, inclusive.
    """

    root: Path

    def outcomes(self, window: tuple) -> Iterable[tuple]: ...


def _valid_outcome(kind, day, left, right) -> bool:
    return (isinstance(kind, str) and kind in OUTCOME_KINDS and type(day) is date
            and all(isinstance(side, (set, frozenset, list, tuple)) and side
                    and all(isinstance(item, str) and item for item in side) for side in (left, right)))


def _valid_hashed(row) -> bool:
    good = lambda side: (isinstance(side, list) and len(side) <= shadow.MAX_HASHES
                         and all(isinstance(item, str) and re.fullmatch(r"[0-9a-f]{16}", item) for item in side))
    return (isinstance(row.kind, str) and row.kind in OUTCOME_KINDS and type(row.day) is date
            and isinstance(row.variants, tuple) and 0 < len(row.variants) <= 64
            and all(isinstance(v, dict) and set(v) == {"left", "right", "shared"} and all(good(x) for x in v.values())
                    and v["left"] and v["right"] for v in row.variants))


def collect_outcomes(sources, today: date, counts: Counter, *, home: Path | None = None,
                     consent_path: Path | None = None) -> list:
    """Admit each source through the gate, then read it; a refused source is never read."""
    window = (gate.retention_cutoff(today), today)
    found = []
    for source in sources:
        try:
            admission = gate.admit_path(source.root, home=home, consent_path=consent_path)
        except gate.GateRefusal as refusal:
            counts["refused:" + refusal.code] += 1
            continue
        try:
            for row in source.outcomes(window):
                counts["outcomes-seen"] += 1
                if isinstance(row, HashedRow):
                    if not _valid_hashed(row) or row.day > today:
                        counts["outcomes-invalid"] += 1
                        continue
                    found.append(Outcome(row.kind, row.day, admission, frozenset(), frozenset(), tuple(
                        (sorted((sorted(v["left"]), sorted(v["right"]))), sorted(v["shared"])) for v in row.variants)))
                    continue
                kind, day, left, right = row
                if not _valid_outcome(kind, day, left, right) or day > today:
                    counts["outcomes-invalid"] += 1
                    continue
                found.append(Outcome(kind, day, admission, frozenset(left), frozenset(right)))
        except Exception:  # a source's error text may hold paths: count it, never echo it
            counts["source-error"] += 1
    return found


# --- Read-only episode reader -------------------------------------------------------

def _read_private(path: Path, limit: int) -> bytes:
    """Bounded read of a regular, single-link, private file owned by this user; no symlink."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and not info.st_mode & 0o077
              and info.st_uid == os.getuid() and info.st_size <= limit)
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            return stream.read(limit + 1)
    finally:
        os.close(descriptor)


def read_secret(counts: Counter | None = None) -> bytes | None:
    """The shadow store secret, or None. Never creates the store, the secret or any file.

    A missing secret counts `secret-absent`; an unreadable or unsafe one `secret-unsafe`.
    """
    counts = Counter() if counts is None else counts
    try:
        root = shadow._store_root(create=False)
        if root is not None:
            return shadow._read_secret(root / shadow.SALT_FILE)
    except FileNotFoundError:
        pass
    except (OSError, ValueError):
        counts["secret-unsafe"] += 1
        return None
    counts["secret-absent"] += 1
    return None


def read_episodes(today: date, counts: Counter, answers: dict | None = None) -> list:
    """Retained v0.2 episode pairs with resource pseudonyms, as `(day, pair)`; reads only.

    Pairs without pseudonyms cannot be attributed to the admitted workspace and are never
    returned (fail closed). No episode id is kept. When `answers` is a dict it receives
    `id(pair) -> the DP-1 rule's choice` for each returned pair (None when the episode has no answer);
    the pair objects stay alive in the returned list, so the ids stay valid for the caller.
    """
    cutoff = gate.retention_cutoff(today)
    try:
        root = shadow._store_root(create=False)
        names = sorted(entry.name for entry in root.iterdir()) if root is not None else []
    except (OSError, ValueError):
        counts["episode-files-refused"] += 1
        return []
    pairs = []
    for name in names:
        matched = _EPISODE_FILE.fullmatch(name)
        if matched is None:
            continue
        try:
            file_day = date.fromisoformat(matched.group(1))
        except ValueError:
            continue
        if file_day < cutoff:
            continue
        try:
            data = _read_private(root / name, shadow.MAX_FILE_BYTES)
        except (OSError, ObserverRefused):
            counts["episode-files-refused"] += 1
            continue
        for line in data.split(b"\n"):
            if not line:
                continue
            try:
                episode = shadow.validate_episode(json.loads(line))
                day = date.fromisoformat(episode["day"])
            except (ValueError, RecursionError, UnicodeError):
                counts["episodes-invalid"] += 1
                continue
            if day < cutoff:
                continue
            counts["episodes-read"] += 1
            if episode["schemaVersion"] != shadow.SCHEMA:
                counts["episodes-unattributable"] += 1
                continue
            given = episode["systemOne"]["answers"]
            for index, pair in enumerate(episode["pairs"]):
                choice = given[index]["choice"] if given is not None and index < len(given) else None
                if choice is not None:
                    counts["rule-answered-pairs"] += 1
                    counts["advised-pairs"] += choice == INDEPENDENT
                if pair["resourceHashes"] is None:
                    counts["episodes-unattributable"] += 1
                else:
                    pairs.append((day, pair))
                    if answers is not None:
                        answers[id(pair)] = choice
    return pairs


# --- Matcher -----------------------------------------------------------------------

def candidate_roots(*, home: Path | None = None) -> list:
    """Raw and resolved `source_root` strings the adapter may have been configured with.

    Only the admitted workspace's registered source root and worktree roots count: the
    repo salt is the HMAC of the exact configured string, not of a realpath.
    """
    try:
        rows = plugin_registry.inspect_registry(home)["value"]["workspaces"]
        row = next(item for item in rows if item["workspaceId"] == gate.ADMITTED_WORKSPACE_ID)
        raw = [row["sourceRoot"], *row["worktreeRoots"]]
    except (plugin_registry.RegistryError, OSError, KeyError, TypeError, ValueError, StopIteration):
        return []  # the caller counts `roots-unavailable`
    found = set()
    for item in raw:
        for variant in (item, os.path.realpath(item)):
            found.update((variant, variant.rstrip("/"), variant.rstrip("/") + "/"))
    return sorted(found)


def candidate_salts(secret: bytes | None, roots) -> list:
    salts = {shadow._repo_salt(secret, root) for root in roots}
    return sorted(salt for salt in salts if salt is not None)


def _hashes(salt: bytes, resources) -> list:
    return sorted({shadow._pseudonym(salt, resource) for resource in resources})[:shadow.MAX_HASHES]


def _expected(salt: bytes, outcome: Outcome) -> tuple:
    shared = outcome.left & outcome.right
    return (sorted((_hashes(salt, outcome.left), _hashes(salt, outcome.right))), _hashes(salt, shared))


def match(outcome: Outcome, pairs, salts) -> tuple:
    """`(status, day, pair, reason)`; joins only when exactly one episode pair matches.

    The pair must lie within `MATCH_WINDOW_DAYS` before the outcome day and its
    left/right/shared pseudonym lists must equal those computed from the outcome's
    resources under some candidate salt (side order is not significant).
    """
    window = [(day, pair) for day, pair in pairs
              if outcome.day - timedelta(days=MATCH_WINDOW_DAYS) <= day <= outcome.day]
    if not window:
        return "no-match", None, None, "no-episode"
    expected = list(outcome.variants) if outcome.variants is not None else [_expected(salt, outcome) for salt in salts]
    if any(len(hashes) >= shadow.MAX_HASHES for sides, shared in expected for hashes in (*sides, shared)):
        return "no-match", None, None, "truncated"  # the 32-lowest lists cannot prove equality
    hits = []
    for day, pair in window:
        hashes = pair["resourceHashes"]
        actual = (sorted((hashes["left"], hashes["right"])), hashes["shared"])
        if actual in expected:
            hits.append((day, pair))
    if not hits:
        return "no-match", None, None, "salt-unmatched"
    if len(hits) > 1:
        return "ambiguous", None, None, "ambiguous"
    return "joined", hits[0][0], hits[0][1], "joined"


# --- Record ------------------------------------------------------------------------

def _validate_pair(pair) -> None:
    """Validate a v0.2 pair with pseudonyms by the shadow contract, wrapped in a shell episode."""
    _need(type(pair) is dict and type(pair.get("system2")) is str and pair["system2"] in shadow.CLASSIFICATIONS)
    shell = {"schemaVersion": shadow.SCHEMA, "episodeId": str(uuid.uuid4()), "day": "2000-01-01",
             "surface": "mcp", "operation": "analyze", "analysisKind": "aim",
             "analyzer": {"version": "0", "ruleSet": "r"}, "operationCount": 2, "pairCount": 1,
             "classificationCounts": {name: int(name == pair["system2"]) for name in shadow.CLASSIFICATIONS},
             "pairsRecorded": 1, "pairs": [pair],
             "systemOne": {"status": "abstained", "reason": "calibration-absent", "backendId": "b",
                           "manifestDigest": "0" * 64, "decisionPoint": shadow.DECISION_POINT,
                           "answers": None, "elapsedMicros": 0},
             "executionAuthorization": False}
    try:
        shadow.validate_episode(shell)
    except ValueError:
        raise ObserverRefused("refused") from None
    _need(pair["resourceHashes"] is not None)


def validate_record(record) -> dict:
    """Enforce the closed `agent-braid-s1-outcome/v0.1` field set.

    `ruleAnswer` (the DP-1 rule's choice on the pair, or null) is part of the set; a record stored
    before it existed, without the field, is still valid and counts as having no rule answer.
    """
    _need(type(record) is dict and set(record) in (RECORD_FIELDS, RECORD_FIELDS - {RULE_ANSWER_FIELD})
          and record["schemaVersion"] == SCHEMA)
    answer = record.get(RULE_ANSWER_FIELD)
    _need(answer is None or (type(answer) is str and answer in shadow.CHOICES))
    _need(type(record["joinKey"]) is str and _UUID4.fullmatch(record["joinKey"]))
    _need(type(record["day"]) is str and date.fromisoformat(record["day"]).isoformat() == record["day"])
    _need(record["source"] == SOURCE and record["joinStatus"] == "joined"
          and type(record["outcomeKind"]) is str and record["outcomeKind"] in OUTCOME_KINDS)
    _need(record["executionAuthorization"] is False)
    _validate_pair(record["pair"])
    return record


def make_record(kind: str, day: date, pair: dict, rule_answer: str | None = None) -> dict:
    """A joined record with a random join key, never derived from any input."""
    return validate_record({
        "schemaVersion": SCHEMA, "joinKey": str(uuid.UUID(bytes=secrets.token_bytes(16), version=4)),
        "day": day.isoformat(), "source": SOURCE, "outcomeKind": kind, "joinStatus": "joined",
        "pair": json.loads(json.dumps(pair)), RULE_ANSWER_FIELD: rule_answer, "executionAuthorization": False})


def _body(record: dict) -> bytes:
    return json.dumps({key: value for key, value in record.items() if key != "joinKey"},
                      sort_keys=True, separators=(",", ":")).encode()


def _line(record: dict) -> bytes:
    return (json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


@dataclass
class Result:
    records: list
    counts: Counter


def observe(sources, today: date, *, home: Path | None = None, consent_path: Path | None = None) -> Result:
    """Read, admit and match; writes nothing. Unmatched or ambiguous outcomes leave no record."""
    counts = Counter()
    outcomes = collect_outcomes(sources, today, counts, home=home, consent_path=consent_path)
    secret = read_secret(counts)
    rule_answers = {}
    pairs = read_episodes(today, counts, rule_answers)
    roots = candidate_roots(home=home)
    if not roots:
        counts["roots-unavailable"] += 1
    salts = candidate_salts(secret, roots)
    records = []
    for outcome in outcomes:
        if not salts:
            counts["no-salt"] += 1
            continue
        status, day, pair, reason = match(outcome, pairs, salts)
        counts[reason] += 1
        if status == "joined":
            records.append(make_record(outcome.kind, day, pair, rule_answers.get(id(pair))))
    return Result(records, counts)


# --- False independence of the DP-1 rule (REQ-402 (f)) and the D7 rollback -------------------

WILSON_Z = 1.959963984540054  # two-sided 95%
DECISION_POINT = "DP-1"


def wilson_upper(failures: int, trials: int, z: float = WILSON_Z) -> float | None:
    """Upper limit of the Wilson score interval for `failures` of `trials`; None without trials."""
    if trials <= 0:
        return None
    p = failures / trials
    denominator = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    margin = z * ((p * (1 - p) / trials + z * z / (4 * trials * trials)) ** 0.5)
    return min(1.0, (centre + margin) / denominator)


def merged_records(*groups) -> list:
    """Records from several groups with identical bodies collapsed (stored plus newly joined)."""
    seen, merged = set(), []
    for group in groups:
        for record in group:
            body = _body(record)
            if body not in seen:
                seen.add(body)
                merged.append(record)
    return merged


def false_independence(records, advised_pairs: int) -> dict:
    """Counts by closed key. A false independent is a joined `merge-conflict` on a pair whose rule
    answer was `likely-independent`; `undetermined` and unanswered pairs never count."""
    independent = [r for r in records if r.get(RULE_ANSWER_FIELD) == INDEPENDENT]
    conflicts = sum(r["outcomeKind"] == "merge-conflict" for r in independent)
    clean = sum(r["outcomeKind"] == "merge-clean" for r in independent)
    trials = conflicts + clean  # only a textual verdict on an advised pair is a trial
    upper = wilson_upper(conflicts, trials)
    return {"advisedPairsInEpisodes": advised_pairs, "joinedOutcomes": len(records),
            "joinedOnAdvisedPairs": len(independent), "advisedMergeClean": clean,
            "falseIndependent": conflicts,
            "falseIndependenceRate": None if not trials else round(conflicts / trials, 6),
            "wilson95Upper": None if upper is None else round(upper, 6)}


def false_independent_days(records) -> list:
    return sorted(r["day"] for r in records
                  if r["outcomeKind"] == "merge-conflict" and r.get(RULE_ANSWER_FIELD) == INDEPENDENT)


def apply_auto_rollback(records, today: date, *, home: Path | None = None) -> bool:
    """D7: roll DP-1 back (reason `auto-rollback-false-independence`) on a joined false independent.

    One atomic, idempotent promotion-registry append; it acts only while the latest DP-1 record is an
    owner go and the conflict is not older than that go. Returns whether this call recorded the rollback.
    """
    days = false_independent_days(records)
    if not days:
        return False
    from agent_braid import system_one_promotion as promotion
    return promotion.auto_rollback_false_independence(
        home, DECISION_POINT, false_independent_days=days, decided_on=today.isoformat()) is not None


# --- Own private store --------------------------------------------------------------

def store_directory() -> Path:
    """Beside, not inside, the shadow store."""
    return shadow.default_directory().parent / STORE_NAME


def _check_directory(path: Path) -> None:
    _need(path == Path(os.path.realpath(path)), "unsafe store path")
    for part in (path, *path.parents):
        _need(not part.is_symlink() and not (part / ".git").exists(), "unsafe store path")
    info = path.stat()
    _need(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077,
          "unsafe store path")


def _open_store(create: bool) -> Path | None:
    path = store_directory()
    if not path.exists():
        if not create:
            return None
        path.mkdir(parents=True, mode=0o700, exist_ok=True)
    _check_directory(path)
    return path


def _day_files(root: Path) -> list:
    found = []
    for entry in root.iterdir():
        if _OUTCOME_FILE.fullmatch(entry.name):
            try:
                _file_day(entry)
            except ValueError:
                continue  # not a date: not ours to read, purge or trust
            found.append(entry)
    return sorted(found)


def _file_day(path: Path) -> date:
    return date.fromisoformat(_OUTCOME_FILE.fullmatch(path.name).group(1))


def _lock(root: Path) -> int:
    descriptor = os.open(root / _LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(descriptor)
        raise ObserverRefused("store busy") from None
    return descriptor


def _purge_expired(root: Path, today: date) -> None:
    cutoff = gate.retention_cutoff(today)
    for entry in _day_files(root):
        if _file_day(entry) < cutoff:
            entry.unlink()


def _read_store(root: Path) -> list:
    records = []
    for entry in _day_files(root):
        for line in _read_private(entry, MAX_FILE_BYTES).split(b"\n"):
            if line:
                try:
                    records.append(validate_record(json.loads(line)))
                except (ValueError, RecursionError, UnicodeError, ObserverRefused):
                    raise ObserverRefused("invalid store") from None
    return records


def load_records(today: date) -> list:
    """Retained records; expired day files are purged first. Reads create nothing."""
    root = _open_store(create=False)
    if root is None:
        return []
    descriptor = _lock(root)
    try:
        _purge_expired(root, today)
        return _read_store(root)
    finally:
        os.close(descriptor)


def write_records(records, today: date) -> Counter:
    """Append new joined records; an identical record body already stored counts as duplicate."""
    counts = Counter()
    root = _open_store(create=True)
    descriptor = _lock(root)
    try:
        _purge_expired(root, today)
        known = {_body(record) for record in _read_store(root)}
        for record in records:
            validate_record(record)
            day = date.fromisoformat(record["day"])
            try:
                gate.require_retained(day, today)
            except gate.GateRefusal as refusal:
                counts["refused:" + refusal.code] += 1
                continue
            if _body(record) in known:
                counts["duplicate"] += 1
                continue
            target = root / f"outcomes-{record['day']}.jsonl"
            line = _line(record)
            handle = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
            try:
                info = os.fstat(handle)
                _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and not info.st_mode & 0o077
                      and info.st_uid == os.getuid())
                _need(info.st_size + len(line) <= MAX_FILE_BYTES, "store full")
                _need(os.write(handle, line) == len(line), "short write")
            finally:
                os.close(handle)
            known.add(_body(record))
            counts["written"] += 1
    finally:
        os.close(descriptor)
    return counts


def purge() -> dict:
    """Remove this store only (the revocation path for S1.5b); the shadow store is untouched."""
    root = _open_store(create=False)
    if root is None:
        return {"status": "empty", "externalCopies": "not-removed"}
    descriptor = _lock(root)
    removed = 0
    try:
        for entry in _day_files(root):
            entry.unlink()
            removed += 1
        (root / _LOCK).unlink()
        removed += 1
    finally:
        os.close(descriptor)
    result = {"status": "purged", "filesRemoved": removed, "externalCopies": "not-removed"}
    leftover = sum(1 for _ in root.iterdir())
    if leftover:
        result["leftoverEntries"] = leftover
    else:
        root.rmdir()
    return result


# --- Step 0: structural inventory of real-run sources ----------------------------------

def inventory(*, home: Path | None = None, consent_path: Path | None = None, locations=None) -> dict:
    """Counts of readable run records by day, per closed location name; no content, no names.

    A location is read only when the gate admits it; otherwise the refusal code is counted.
    Expected result today: zero (plan assumption A1 unverified), because the runtime state
    and plugin result roots lie outside every workspace root the gate can admit.
    """
    if locations is None:
        locations = {"runtime-state": Path.home() / ".local" / "state" / "agent-braid"}
    report = {}
    for name in sorted(locations):
        try:
            admission = gate.admit_path(locations[name], home=home, consent_path=consent_path)
        except gate.GateRefusal as refusal:
            report[name] = {"status": "refused", "code": refusal.code, "recordsByDay": {}}
            continue
        days = Counter()
        seen, truncated = 0, False
        for current, directories, files in os.walk(os.path.realpath(locations[name]), followlinks=False):
            directories[:] = [d for d in directories if not (Path(current) / d).is_symlink()]
            for item in files:
                seen += 1
                if seen > MAX_INVENTORY_ENTRIES:
                    truncated = True
                    break
                path = Path(current) / item
                try:
                    info = os.lstat(path)
                except OSError:
                    continue
                if stat.S_ISREG(info.st_mode) and path.suffix in (".json", ".jsonl"):
                    days[datetime.fromtimestamp(info.st_mtime, timezone.utc).date().isoformat()] += 1
            if truncated:
                break
        report[name] = {"status": "read", "rootKind": admission["rootKind"], "truncated": truncated,
                        "recordsByDay": dict(sorted(days.items()))}
    return report


# --- Positive control ------------------------------------------------------------------

_DISJOINT = "Complete exact-resource footprints are disjoint."
_SHARED_WRITE = "At least one exact shared resource has a write-like effect."


def synthetic_episode(secret: bytes, root: str, left, right, day: date) -> dict:
    """A `build_episode` v0.2 episode for synthetic resources under the repo salt of `root`."""
    shared = sorted(set(left) & set(right))
    classification = "conflicting" if shared else "independent-candidate"
    counts = {name: int(name == classification) for name in shadow.CLASSIFICATIONS}
    report = {
        "summary": {"operationCount": 2, "pairCount": 1, "classifications": counts},
        "analyzer": {"version": "0.0.0", "ruleSet": "synthetic"},
        "operations": [{"instanceId": "a", "resources": sorted(left)}, {"instanceId": "b", "resources": sorted(right)}],
        "interactions": [{"left": "a", "right": "b", "classification": classification,
                          "reasons": [_SHARED_WRITE if shared else _DISJOINT],
                          "constraints": ["serialize-or-isolate"] if shared else [],
                          "evidence": {"coverage": ["complete"]}, "sharedResources": shared}]}
    episode = shadow.build_episode(report, "analyze-work", "aim", salt=shadow._repo_salt(secret, root))
    episode["day"] = day.isoformat()
    return episode


def positive_control() -> dict:
    """Join a synthetic episode end to end; a worktree string must not join a source-root episode.

    Run in every evidence so a string mismatch (which looks like honest absence) is detectable.
    """
    secret, source, worktree, day = bytes(range(32)), "/synthetic/source-root", "/synthetic/worktree", date(2000, 1, 10)
    left, right = ["src/a.py", "src/shared.py"], ["src/b.py", "src/shared.py"]
    episode = synthetic_episode(secret, source, left, right, day)
    pairs = [(date.fromisoformat(episode["day"]), episode["pairs"][0])]
    outcome = Outcome("merge-conflict", day, {}, frozenset(left), frozenset(right))
    joined = match(outcome, pairs, candidate_salts(secret, [source, worktree]))[0]
    wrong = match(outcome, pairs, candidate_salts(secret, [worktree]))[0]
    return {"sourceRootStringJoins": joined == "joined", "worktreeStringDoesNotJoin": wrong == "no-match"}
