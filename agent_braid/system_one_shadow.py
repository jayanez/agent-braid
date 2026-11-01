# SPDX-License-Identifier: AGPL-3.0-only
"""System One shadow observer (SPEC-066 S1.5a); advisory records, never output.

After a successful System 2 analysis the observer derives one structural episode
(`agent-braid-s1-episode/v0.2`) from the report and the already-validated request,
and appends it to a private local store. It never changes a result, never raises
into its caller, and records only closed-vocabulary values, counts and per-repo
salted 16-hex pseudonyms: no resource names, identifiers, digests of input or text.
v0.1 lines written by earlier versions stay readable.
"""
from __future__ import annotations

import atexit
from collections import Counter
from datetime import date, timedelta
import hashlib
import hmac
import json
import os
from pathlib import Path
import queue
import re
import stat
import threading
import time
import uuid

# Shared canonical JSON, UTC day and private no-symlink path rules.
from .tooling_telemetry import _canonical, _path, today

SCHEMA = 'agent-braid-s1-episode/v0.2'
SCHEMA_V01 = 'agent-braid-s1-episode/v0.1'
SCHEMAS = (SCHEMA_V01, SCHEMA)
REPORT_SCHEMA = 'agent-braid-s1-report/v0.1'
DECISION_POINT = 'DP-1'
# Identity compiled into the shadow module (REQ-007). A different installed backend
# or manifest is refused, so recorded episodes always name the reviewed reference.
EXPECTED_BACKEND_ID = 'stdlib-rule-fixture-v1'
EXPECTED_MANIFEST_DIGEST = '49f9022082fd12eda9ae1e0cd86ff827ca0c41dded4a52c618357cc9e525a3ca'
BUDGET_NANOSECONDS = 50_000_000
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_REPORT_BYTES = 1024 * 1024  # artifact-backed reports above this are not observed
MAX_PAIRS = 64
RETENTION_DAYS = 30

OPERATIONS = ('analyze', 'analyze-work')
KINDS = ('aim', 'git')
CLASSIFICATIONS = ('independent-candidate', 'ordered', 'conflicting', 'unknown')
REASON_CODES = ('dependency-order', 'shared-write', 'partial-coverage', 'external-effect',
                'disjoint', 'shared-read-only', 'read-version')
CONSTRAINTS = ('preserve-dependency-order', 'serialize-or-isolate', 'serialize-unless-stronger-evidence',
               'requires-execution-contract-before-parallelism', 'validate-read-versions-at-use')
COVERAGE = ('complete', 'partial', 'unknown')
EFFECT_KINDS = ('read', 'write', 'call', 'transform', 'emit', 'delete', 'deploy', 'unknown')
STATUSES = ('answered', 'abstained', 'refused', 'skipped')
REASONS = ('calibration-absent', 'identity-mismatch', 'budget-exceeded', 'unmapped-reason',
           'store-unavailable', 'internal-error')
CHOICES = ('likely-independent', 'likely-conflicting', 'undetermined')
RESOURCE_CLASSES = ('src', 'test', 'docs', 'config', 'lockfile', 'generated', 'other')
MAX_DEPTH = 16
MAX_COUNT = 4096
MAX_HASHES = 32
SALT_FILE = 'salt.key'
SALT_BYTES = 32
SALT_DOMAIN = b'agent-braid-s1-repo\0'
SALT_TEMPORARY = SALT_FILE + '.tmp'
WORKER_LOCK_WAIT = 0.05  # seconds the off-request worker waits for a busy store
_POLL_SECONDS = 0.002
_OWN_FILES = frozenset({'store.lock', SALT_FILE, SALT_TEMPORARY})

# Exact, versioned mapping of agent_braid/analysis.py `_interaction` reason sentences
# (rule set exact-resource-footprints-v1). An unmapped sentence is never stored.
REASON_TABLE = {
    'An explicit dependency path orders the operations.': 'dependency-order',
    'At least one exact shared resource has a write-like effect.': 'shared-write',
    'At least one effect footprint is partial or unknown.': 'partial-coverage',
    'External, transforming, destructive, or unknown effects require adapter semantics.': 'external-effect',
    'Complete exact-resource footprints are disjoint.': 'disjoint',
    'Complete exact-resource footprints have no write conflict.': 'shared-read-only',
    'Read-version preconditions remain point-of-use obligations.': 'read-version',
}

_UUID4 = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
_DAY = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_HEX64 = re.compile(r'^[0-9a-f]{64}$')
_HEX16 = re.compile(r'^[0-9a-f]{16}$')
_URI = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*://')
_IDENT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')
_FILE = re.compile(r'^episodes-(\d{4}-\d{2}-\d{2})\.jsonl$')

_refusals = Counter()
_refusal_lock = threading.Lock()


class StoreRefused(ValueError):
    """The private store declined an episode; the caller is never affected."""


def _note_refusal(reason: str) -> None:
    with _refusal_lock:
        _refusals[reason] += 1


def refusal_counts() -> dict:
    """In-memory refusal counts for this process only."""
    with _refusal_lock:
        return dict(_refusals)


def default_directory() -> Path:
    """Fixed user-local location, independent of repository and host configuration."""
    return Path.home() / '.local' / 'share' / 'agent-braid' / 'system-one'


def display_location() -> str:
    """The store location with the home directory shown as `~`, so no user name is exposed."""
    directory = default_directory()
    try:
        return '~/' + directory.relative_to(Path.home()).as_posix()
    except ValueError:
        return str(directory)


def _safe(path: Path, *, directory=False) -> Path:
    """The shared path rules, with their errors worded for this store."""
    try:
        return _path(path, directory=directory)
    except ValueError as exc:
        raise ValueError(str(exc).replace('telemetry', 'System One store')) from None


# --- System One identity and answer ------------------------------------------

def _system_one_answer() -> dict:
    """Identity and strict-policy outcome of the installed reference backend.

    The strict policy ignores the question set, so a request-shaped stand-in carrying
    only its policy identifier obtains the real outcome without building a request.
    """
    from types import SimpleNamespace
    from . import system_one, system_one_policy
    answer = {'backendId': system_one.BACKEND_ID,
              'manifestDigest': system_one.digest(system_one.MODEL_MANIFEST)}
    if (answer['backendId'], answer['manifestDigest']) != (EXPECTED_BACKEND_ID, EXPECTED_MANIFEST_DIGEST):
        return dict(answer, status='refused', reason='identity-mismatch')
    outcome, reasons = system_one_policy.outcome(
        SimpleNamespace(envelope={'policyId': system_one.STRICT_POLICY}))
    if outcome == 'abstain' and reasons == ['calibration-absent']:
        return dict(answer, status='abstained', reason='calibration-absent')
    return dict(answer, status='skipped', reason='internal-error')


# --- Structural resource features ---------------------------------------------
# Deterministic path rules (contract episode-v0.2). Resource strings are used only
# here, in memory; the episode keeps classes, counts and salted 16-hex pseudonyms.

LOCKFILES = frozenset({'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock', 'uv.lock',
                       'pipfile.lock', 'cargo.lock', 'go.sum', 'gemfile.lock', 'composer.lock'})
GENERATED_SEGMENTS = frozenset({'dist', 'build', 'out', 'target', 'node_modules', '__pycache__', 'generated'})
TEST_SEGMENTS = frozenset({'test', 'tests', '__tests__', 'spec'})
DOC_EXTENSIONS = frozenset({'.md', '.rst', '.txt', '.adoc'})
CONFIG_EXTENSIONS = frozenset({'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.env'})
SOURCE_EXTENSIONS = frozenset({'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', '.kt', '.c', '.h',
                               '.cpp', '.cs', '.rb', '.php', '.swift', '.m', '.scala', '.sh'})


# `generated` as a whole word of the stem (foo.generated.ts, generated_ids.py), not a substring.
_GENERATED_NAME = re.compile(r'(^|[._-])generated([._-]|$)')
# Dependency manifests that use a documentation extension.
_MANIFEST_NAME = re.compile(r'^(requirements|constraints)([._-][\w.-]*)?\.(txt|in)$')


def _segments(resource: str) -> list[str] | None:
    """Path segments of a resource, or None for a non-path resource.

    A `scheme://authority/` prefix is removed (so `git://<repo>/a/b.py` is `a/b.py`),
    then any `?query` or `#fragment`; empty and `.` segments are dropped. A resource
    whose remaining text has neither `/` nor `.` is not a path.
    """
    text = resource
    match = _URI.match(text)
    if match:
        text = text[match.end():].partition('/')[2]
    text = text.split('?', 1)[0].split('#', 1)[0]
    if '/' not in text and '.' not in text:
        return None
    segments = [segment for segment in text.split('/') if segment not in ('', '.')]
    return segments or None


def classify(resource: str) -> str:
    """One of RESOURCE_CLASSES by the first matching rule, in contract order."""
    segments = _segments(resource)
    if segments is None:
        return 'other'
    *directories, name = [segment.lower() for segment in segments]
    stem, extension = os.path.splitext(name)
    if name in LOCKFILES:
        return 'lockfile'
    if GENERATED_SEGMENTS.intersection(directories) or '.min.' in name or _GENERATED_NAME.search(stem):
        return 'generated'
    if (TEST_SEGMENTS.intersection(directories) or name.startswith('test_') or (extension and stem.endswith('_test'))
            or '.test.' in name or '.spec.' in name):
        return 'test'
    if _MANIFEST_NAME.match(name):
        return 'config'
    if extension in DOC_EXTENSIONS or 'docs' in directories:
        return 'docs'
    if extension in CONFIG_EXTENSIONS or name.startswith('.'):
        return 'config'
    if extension in SOURCE_EXTENSIONS:
        return 'src'
    return 'other'


def _class_counts(resources) -> dict:
    counts = Counter(classify(resource) for resource in resources)
    return {name: min(counts[name], MAX_COUNT) for name in RESOURCE_CLASSES}


def _parent(segments: list[str]) -> str:
    return '/'.join(segments[:-1])


def _repo_salt(secret: bytes | None, repository: str | None) -> bytes | None:
    if secret is None or type(repository) is not str or not repository:
        return None
    return hmac.new(secret, SALT_DOMAIN + os.fsencode(repository), hashlib.sha256).digest()


def _pseudonym(salt: bytes, resource: str) -> str:
    return hmac.new(salt, resource.encode('utf-8', 'surrogatepass'), hashlib.sha256).hexdigest()[:16]


def _hashes(salt: bytes, resources) -> list[str]:
    return sorted({_pseudonym(salt, resource) for resource in resources})[:MAX_HASHES]


def _aim_kinds(request) -> dict | None:
    """Per-operation effect kinds from the validated AIM records, or None when unavailable."""
    if request is None:
        return None
    from . import analysis
    records, _ = analysis._records(request)
    return {record['instanceId']: sorted({kind for kinds in analysis._effect_map(record).values()
                                           for kind in kinds}) for record in records}


# The Git adapter writes `git://` resources only with kind `write` and
# `git-unsupported://` resources only with kind `unknown` (git_adapter._record), so the
# report's resources fix each Git operation's kinds exactly without re-running Git.
GIT_SCHEME_KINDS = (('git://', 'write'), ('git-unsupported://', 'unknown'))


def _git_kinds(resources) -> list[str] | None:
    kinds = set()
    for resource in resources:
        kind = next((k for prefix, k in GIT_SCHEME_KINDS if resource.startswith(prefix)), None)
        if kind is None:
            return None
        kinds.add(kind)
    return sorted(kinds)


def _resource_features(item: dict, sides: dict, kinds: dict | None, salt: bytes | None) -> dict:
    left, right = sides[item['left']], sides[item['right']]
    shared = item['sharedResources']
    split = {resource: _segments(resource) for resource in {*left, *right}}
    paths = [segments for segments in split.values() if segments is not None]
    parents = [Counter(_parent(split[r]) for r in side if split[r] is not None) for side in (left, right)]
    same_parent = sum(count * parents[1][parent] for parent, count in parents[0].items())
    tops = [{split[r][0] for r in side if split[r] is not None and len(split[r]) > 1} for side in (left, right)]
    side_kinds = None
    if kinds is not None and item['left'] in kinds and item['right'] in kinds:
        side_kinds = {'left': kinds[item['left']], 'right': kinds[item['right']]}
    return {'effectKinds': side_kinds,
            'resourceClasses': {'left': _class_counts(left), 'right': _class_counts(right)},
            'sharedResourceClasses': _class_counts(shared),
            'maxDepth': min(max((len(segments) for segments in paths), default=0), MAX_DEPTH),
            'sameParentDirCount': min(same_parent, MAX_COUNT),
            'topDirOverlap': bool(tops[0] & tops[1]),
            'resourceHashes': None if salt is None else {
                'left': _hashes(salt, left), 'right': _hashes(salt, right), 'shared': _hashes(salt, shared)}}


# --- Episode construction -----------------------------------------------------

def _count(value, low, high) -> int:
    if not _int(value, low, high):
        raise ValueError('report count outside the episode contract')
    return value


def _pair(item: dict) -> dict | None:
    """Closed-vocabulary pair, or None when any sentence or token is not in the tables."""
    codes = set()
    for sentence in item['reasons']:
        code = REASON_TABLE.get(sentence) if type(sentence) is str else None
        if code is None:
            return None
        codes.add(code)
    constraints = item['constraints']
    coverage = item['evidence']['coverage']
    classification = item['classification']
    if (classification not in CLASSIFICATIONS
            or not all(type(c) is str and c in CONSTRAINTS for c in constraints)
            or not all(type(c) is str and c in COVERAGE for c in coverage)):
        return None
    return {'system2': classification,
            'system2Determinate': classification != 'unknown',
            'reasonCodes': sorted(codes),
            'constraints': sorted(set(constraints)),
            'coverage': sorted(set(coverage)),
            'sharedResourceCount': min(len(item['sharedResources']), MAX_COUNT),
            'effectKinds': None,
            'dependency': 'dependency-order' in codes,
            'observedOutcome': None}


def build_episode(report: dict, operation: str, kind: str, *, request=None, salt: bytes | None = None,
                  clock=None, started=None) -> dict:
    """Derive one contract-conformant v0.2 episode (never stores input).

    `request` is the already-validated analysis request (AIM records give per-side
    effect kinds; Git kinds come from the report's adapter resources). `salt` is the
    per-repo key for resource pseudonyms; without it `resourceHashes` is null.
    `started` lets the caller count work done before this call (artifact decoding)
    against the same 50 ms budget.
    """
    clock = clock or time.monotonic_ns
    started = clock() if started is None else started
    summary = report['summary']
    operation_count = _count(summary['operationCount'], 1, 64)
    pair_count = _count(summary['pairCount'], 0, 2016)
    analyzer = {'version': report['analyzer']['version'], 'ruleSet': report['analyzer']['ruleSet']}
    # Complete per-class counts survive the pair cap, so DP-1 shares cover every pair.
    counts = {name: _count(summary['classifications'][name], 0, 2016) for name in CLASSIFICATIONS}
    if sum(counts.values()) != pair_count:
        raise ValueError('report classifications do not sum to the pair count')
    interactions = report['interactions']
    pairs = []
    for item in interactions:
        pair = _pair(item)
        if pair is None:
            pairs, mapped = [], False
            break
        pairs.append(pair)
    else:
        mapped = True
    if pairs:
        pairs = pairs[:MAX_PAIRS]
        sides = {entry['instanceId']: entry['resources'] for entry in report['operations']}
        kinds = (_aim_kinds(request) if kind == 'aim'
                 else {name: _git_kinds(resources) for name, resources in sides.items()})
        if kinds is not None:
            kinds = {name: value for name, value in kinds.items() if value is not None}
        for pair, item in zip(pairs, interactions):
            pair.update(_resource_features(item, sides, kinds, salt))
    system_one_started = clock()
    answer = _system_one_answer()
    elapsed_micros = max(0, (clock() - system_one_started) // 1000)
    status, reason = answer['status'], answer['reason']
    if not mapped:
        status, reason = 'skipped', 'unmapped-reason'
    if clock() - started > BUDGET_NANOSECONDS and status != 'refused':
        status, reason = 'skipped', 'budget-exceeded'
    return {'schemaVersion': SCHEMA,
            'episodeId': str(uuid.uuid4()),
            'day': today().isoformat(),
            'surface': 'mcp',
            'operation': operation,
            'analysisKind': kind,
            'analyzer': analyzer,
            'operationCount': operation_count,
            'pairCount': pair_count,
            'classificationCounts': counts,
            'pairsRecorded': len(pairs),
            'pairs': pairs,
            'systemOne': {'status': status, 'reason': reason,
                          'backendId': answer['backendId'], 'manifestDigest': answer['manifestDigest'],
                          'decisionPoint': DECISION_POINT, 'answers': None,
                          'elapsedMicros': min(elapsed_micros, 50_000)},
            'executionAuthorization': False}


# --- Validation ---------------------------------------------------------------

def _need(condition, message='invalid System One episode'):
    if not condition:
        raise ValueError(message)


def _int(value, low, high) -> bool:
    return type(value) is int and low <= value <= high


def _strings(value, allowed) -> bool:
    return (type(value) is list and all(type(v) is str and v in allowed for v in value)
            and value == sorted(set(value)))


V01_PAIR_FIELDS = frozenset({'system2', 'system2Determinate', 'reasonCodes', 'constraints', 'coverage',
                             'sharedResourceCount', 'effectKinds', 'dependency', 'observedOutcome'})
V02_PAIR_FIELDS = V01_PAIR_FIELDS | {'resourceClasses', 'sharedResourceClasses', 'maxDepth',
                                     'sameParentDirCount', 'topDirOverlap', 'resourceHashes'}


def _classes(value) -> bool:
    return (type(value) is dict and set(value) == set(RESOURCE_CLASSES)
            and all(_int(count, 0, MAX_COUNT) for count in value.values()))


def _hash_list(value) -> bool:
    return (type(value) is list and len(value) <= MAX_HASHES and value == sorted(set(value))
            and all(type(h) is str and _HEX16.fullmatch(h) for h in value))


def _validate_v02_pair(pair: dict) -> None:
    sides = pair['resourceClasses']
    _need(type(sides) is dict and set(sides) == {'left', 'right'} and all(map(_classes, sides.values())))
    shared = pair['sharedResourceClasses']
    _need(_classes(shared))
    total, count = sum(shared.values()), pair['sharedResourceCount']
    _need(total == count if count < MAX_COUNT else total >= MAX_COUNT)
    _need(_int(pair['maxDepth'], 0, MAX_DEPTH) and _int(pair['sameParentDirCount'], 0, MAX_COUNT))
    _need(type(pair['topDirOverlap']) is bool)
    hashes = pair['resourceHashes']
    _need(hashes is None or (type(hashes) is dict and set(hashes) == {'left', 'right', 'shared'}
                             and all(map(_hash_list, hashes.values()))))


def validate_episode(value) -> dict:
    """Enforce the v0.2 (or legacy v0.1) contract, including the never-present rule.

    The only free strings allowed are episodeId, day, backendId, manifestDigest and,
    in v0.2, the 16-hex resource pseudonyms.
    """
    _need(type(value) is dict and set(value) == {
        'schemaVersion', 'episodeId', 'day', 'surface', 'operation', 'analysisKind', 'analyzer',
        'operationCount', 'pairCount', 'classificationCounts', 'pairsRecorded', 'pairs', 'systemOne',
        'executionAuthorization'})
    _need(type(value['schemaVersion']) is str and value['schemaVersion'] in SCHEMAS)
    _need(value['surface'] == 'mcp')
    pair_fields = V02_PAIR_FIELDS if value['schemaVersion'] == SCHEMA else V01_PAIR_FIELDS
    _need(type(value['episodeId']) is str and _UUID4.fullmatch(value['episodeId']))
    _need(type(value['day']) is str and _DAY.fullmatch(value['day']))
    try:
        _need(date.fromisoformat(value['day']).isoformat() == value['day'])
    except ValueError:
        raise ValueError('invalid System One episode') from None
    _need(type(value['operation']) is str and value['operation'] in OPERATIONS)
    _need(type(value['analysisKind']) is str and value['analysisKind'] in KINDS)
    analyzer = value['analyzer']
    _need(type(analyzer) is dict and set(analyzer) == {'version', 'ruleSet'}
          and all(type(v) is str and _IDENT.fullmatch(v) for v in analyzer.values()))
    _need(_int(value['operationCount'], 1, 64) and _int(value['pairCount'], 0, 2016))
    _need(_int(value['pairsRecorded'], 0, MAX_PAIRS) and value['executionAuthorization'] is False)
    counts = value['classificationCounts']
    _need(type(counts) is dict and set(counts) == set(CLASSIFICATIONS)
          and all(_int(c, 0, 2016) for c in counts.values()) and sum(counts.values()) == value['pairCount'])
    pairs = value['pairs']
    _need(type(pairs) is list and len(pairs) == value['pairsRecorded'] <= value['pairCount'])
    for pair in pairs:
        _need(type(pair) is dict and set(pair) == pair_fields)
        _need(type(pair['system2']) is str and pair['system2'] in CLASSIFICATIONS)
        _need(type(pair['system2Determinate']) is bool
              and pair['system2Determinate'] == (pair['system2'] != 'unknown'))
        _need(_strings(pair['reasonCodes'], REASON_CODES) and _strings(pair['constraints'], CONSTRAINTS))
        _need(_strings(pair['coverage'], COVERAGE) and _int(pair['sharedResourceCount'], 0, 4096))
        kinds = pair['effectKinds']
        _need(kinds is None or (type(kinds) is dict and set(kinds) == {'left', 'right'}
              and all(_strings(side, EFFECT_KINDS) for side in kinds.values())))
        _need(type(pair['dependency']) is bool and pair['observedOutcome'] is None)
        if pair_fields is V02_PAIR_FIELDS:
            _validate_v02_pair(pair)
    one = value['systemOne']
    _need(type(one) is dict and set(one) == {
        'status', 'reason', 'backendId', 'manifestDigest', 'decisionPoint', 'answers', 'elapsedMicros'})
    _need(type(one['status']) is str and one['status'] in STATUSES)
    _need(one['reason'] is None or (type(one['reason']) is str and one['reason'] in REASONS))
    _need(type(one['backendId']) is str and _IDENT.fullmatch(one['backendId']))
    _need(type(one['manifestDigest']) is str and _HEX64.fullmatch(one['manifestDigest']))
    _need(one['decisionPoint'] == DECISION_POINT and _int(one['elapsedMicros'], 0, 50_000))
    answers = one['answers']
    if one['status'] == 'answered':
        _need(type(answers) is list and len(answers) == len(pairs))
        for answer in answers:
            _need(type(answer) is dict and set(answer) == {'choice', 'probabilities'}
                  and type(answer['choice']) is str and answer['choice'] in CHOICES)
            probabilities = answer['probabilities']
            _need(type(probabilities) is dict and set(probabilities) == set(CHOICES)
                  and all(type(p) is float and 0.0 <= p <= 1.0 for p in probabilities.values()))
    else:
        _need(answers is None)
    return value


# --- Private store ------------------------------------------------------------

def _store_root(*, create: bool) -> Path | None:
    root = _safe(default_directory(), directory=True)
    if not root.exists():
        if not create:
            return None
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        _safe(root, directory=True)
    return root


def _listing(root: Path) -> tuple[list[Path], list[Path]]:
    """Day files and unrelated entries; the store's own files (`_OWN_FILES`) are listed in neither."""
    days, others = [], []
    for entry in sorted(root.iterdir()):
        if entry.name not in _OWN_FILES:
            (days if _FILE.fullmatch(entry.name) else others).append(entry)
    return days, others


def _entries(root: Path) -> list[Path]:
    """The store's day files; unrelated files (for example .DS_Store) are ignored."""
    return [_safe(entry) for entry in _listing(root)[0]]


def _unlink_own(path: Path) -> bool:
    """Remove a file or planted link at `path`; True when something was removed.

    unlink never follows a link, so a planted link is removed, not its target. A
    directory or other entry is not ours to remove and stays in place.
    """
    if path.is_symlink() or path.is_file():
        path.unlink()
        return True
    return False


def _retained(name: str, current: date) -> bool:
    """Older dates expire; future-dated files (clock skew) are kept, never deleted."""
    try:
        parsed = date.fromisoformat(_FILE.fullmatch(name).group(1))
    except ValueError:
        return False
    return parsed >= current - timedelta(days=RETENTION_DAYS - 1)


class _Lock:
    """Exclusive flock on the store's lock file, never blocking for long.

    The worker (`wait`) retries for a few milliseconds so that concurrent processes
    do not silently drop salts or episodes; interactive callers refuse at once.
    """

    def __init__(self, root: Path, *, wait: float = 0.0):
        self.path = _safe(root / 'store.lock')
        self.descriptor = None
        self.wait = wait

    def __enter__(self):
        import fcntl
        self.descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            _safe(self.path)
            deadline = time.monotonic() + self.wait
            while True:
                try:
                    fcntl.flock(self.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise StoreRefused('busy') from None
                    time.sleep(_POLL_SECONDS)
        except BaseException:
            os.close(self.descriptor)
            raise
        return self

    def __exit__(self, *exc):
        os.close(self.descriptor)


def append(episode: dict) -> None:
    """Append one validated episode; raise StoreRefused when the store cannot take it safely."""
    current = today()
    try:
        validate_episode(episode)
        line = _canonical(episode)
        _need(hasattr(os, 'O_NOFOLLOW'), 'secure store opening is unsupported')
        root = _store_root(create=True)
        with _Lock(root, wait=WORKER_LOCK_WAIT):
            for entry in _entries(root):
                if not _retained(entry.name, current):
                    entry.unlink()
            target = _safe(root / f"episodes-{episode['day']}.jsonl")
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
            try:
                info = os.fstat(descriptor)
                _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and not info.st_mode & 0o077
                      and info.st_uid == os.getuid(), 'unsafe System One day file')
                if info.st_size + len(line) > MAX_FILE_BYTES:
                    raise StoreRefused('oversize')
                written = os.write(descriptor, line)
                _need(written == len(line), 'short write')
            finally:
                os.close(descriptor)
    except StoreRefused:
        raise
    except (OSError, ValueError, ImportError) as exc:
        raise StoreRefused('unavailable') from exc


def _private_file(info) -> bool:
    """A regular, single-link file owned by this user with no group or other bits."""
    return (stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and not info.st_mode & 0o077
            and info.st_uid == os.getuid())


def _read_secret(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        _need(_private_file(info) and info.st_size == SALT_BYTES, 'unsafe System One salt')
        secret = os.read(descriptor, SALT_BYTES + 1)
    finally:
        os.close(descriptor)
    _need(len(secret) == SALT_BYTES, 'unsafe System One salt')
    return secret


def _secret() -> bytes | None:
    """The store's 32-byte local secret, created on first use; None when unavailable.

    Never returned outside this module, logged or written anywhere but `salt.key`.
    """
    try:
        _need(hasattr(os, 'O_NOFOLLOW'), 'secure store opening is unsupported')
        root = _store_root(create=True)
        with _Lock(root, wait=WORKER_LOCK_WAIT):
            path = _safe(root / SALT_FILE)
            try:
                return _read_secret(path)
            except FileNotFoundError:
                pass
            except ValueError:
                # A torn secret (killed mid-write) is our own regular private file of the
                # wrong size: replace it under the lock. Anything else stays refused.
                info = os.lstat(path)
                _need(_private_file(info) and info.st_size != SALT_BYTES, 'unsafe System One salt')
                path.unlink()
            # Publish atomically: a complete, synced temporary file is linked into place.
            temporary = _safe(root / SALT_TEMPORARY)
            if temporary.is_symlink() or temporary.exists():
                temporary.unlink()
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                _need(os.write(descriptor, os.urandom(SALT_BYTES)) == SALT_BYTES, 'short write')
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            try:
                os.link(temporary, path)
            finally:
                temporary.unlink()
            return _read_secret(path)
    except (OSError, ValueError, ImportError):
        _note_refusal('salt-unavailable')
        return None


def observe(operation: str, kind: str, source, request=None, repository: str | None = None) -> None:
    """Record one episode for a successful analysis; never raises, never alters the report.

    `source` is the report dict, or the encoded evidence artifact that holds it;
    `request` is the validated request (read only); `repository` is the configured
    source root, used only to derive the per-repo salt and never stored.
    """
    started = time.monotonic_ns()  # the 50 ms budget covers decoding as well as building
    try:
        if type(source) is bytes:
            source = json.loads(source)
            source = source.get('report') if type(source) is dict else None
            if type(source) is not dict:
                return
        salt = _repo_salt(_secret(), repository) if repository else None
        append(build_episode(source, operation, kind, request=request, salt=salt, started=started))
    except StoreRefused as exc:
        _note_refusal(str(exc))
    except Exception:
        _note_refusal('internal-error')


# --- Off-request worker ----------------------------------------------------------
# Episode building and the store write run on one daemon thread so they never add
# latency to a request or run while the plugin router's admission lock is held.

_jobs: queue.Queue = queue.Queue(maxsize=1)
_worker = None
_worker_guard = threading.Lock()


def _work() -> None:
    while True:
        job = _jobs.get()
        try:
            observe(*job)
        finally:
            _jobs.task_done()


def submit(operation: str, kind: str, source, request=None, repository: str | None = None) -> None:
    """Hand a final report (dict) or its evidence artifact (bytes) to the worker; never blocks or raises.

    `request` and `repository` are passed by reference only; all work on them happens
    on the worker thread.
    """
    global _worker
    try:
        if type(source) is bytes and len(source) > MAX_REPORT_BYTES:
            _note_refusal('oversize-report')
            return
        with _worker_guard:
            if _worker is None or not _worker.is_alive():
                if _worker is None:
                    atexit.register(flush, 1.0)  # give a queued episode a moment at shutdown
                _worker = threading.Thread(target=_work, name='system-one-shadow', daemon=True)
                _worker.start()
        _jobs.put_nowait((operation, kind, source, request, repository))
    except queue.Full:
        _note_refusal('busy')
    except Exception:
        _note_refusal('internal-error')


def flush(timeout: float = 5.0) -> bool:
    """Wait until submitted work is done (tests, shutdown); False when the timeout passed first."""
    deadline = time.monotonic() + timeout
    while _jobs.unfinished_tasks:
        if time.monotonic() >= deadline:
            return False
        time.sleep(_POLL_SECONDS)
    return True


def store_present() -> bool:
    """True when the store holds episode files; reads only, creates nothing."""
    try:
        root = _store_root(create=False)
        return root is not None and bool(_listing(root)[0])
    except (OSError, ValueError):
        return False


# --- Report and purge -----------------------------------------------------------

REPORT_LIMITS = [
    'Counts only; episode bodies and resource pseudonyms are never printed.',
    'DP-1 pairs only; no observed outcome is joined in S1.5a, so no accuracy or utility is measured.',
    'Thirty UTC dates retained on access; inactive files are not maintained by a daemon.',
    'Episodes skipped before storage (refused store, internal errors) are known only in this process.',
]


def _read_file(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        _need(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_FILE_BYTES, 'unsafe System One day file')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            return stream.read(MAX_FILE_BYTES + 1)
    finally:
        os.close(descriptor)


def report() -> dict:
    """Aggregate retained episodes; reads the store only and creates nothing."""
    current = today()
    days = {}
    invalid = 0
    root = _store_root(create=False)
    for entry in (_entries(root) if root is not None else []):
        if not _retained(entry.name, current):
            continue
        day = _FILE.fullmatch(entry.name).group(1)
        for line in _read_file(entry).split(b'\n'):
            if not line:
                continue
            try:
                episode = validate_episode(json.loads(line))
            except (ValueError, RecursionError, UnicodeError):
                invalid += 1
                continue
            bucket = days.setdefault(day, {'day': day, 'episodes': 0, 'operations': Counter(),
                                           'system2': Counter(), 'systemOne': Counter(),
                                           'allPairs': Counter(), 'schemas': Counter()})
            bucket['episodes'] += 1
            bucket['schemas'][episode['schemaVersion']] += 1
            bucket['operations'][episode['operation']] += 1
            bucket['systemOne'][episode['systemOne']['status']] += 1
            bucket['system2'].update(pair['system2'] for pair in episode['pairs'])
            bucket['allPairs'].update({name: count for name, count in episode['classificationCounts'].items()
                                       if count})
    totals = {'episodes': 0, 'operations': Counter(), 'system2': Counter(),
              'systemOne': Counter(), 'allPairs': Counter(), 'schemas': Counter()}
    for bucket in days.values():
        totals['episodes'] += bucket['episodes']
        for name in ('operations', 'system2', 'systemOne', 'allPairs', 'schemas'):
            totals[name].update(bucket[name])
    recorded = sum(totals['system2'].values())
    analysed = sum(totals['allPairs'].values())
    unknown = totals['allPairs']['unknown']
    plain = lambda bucket: {key: dict(value) if isinstance(value, Counter) else value
                            for key, value in bucket.items()}
    return {'schema': REPORT_SCHEMA,
            'retentionDays': RETENTION_DAYS,
            'days': [plain(days[key]) for key in sorted(days)],
            'totals': plain(totals),
            'pairsRecorded': recorded,
            'pairsAnalysed': analysed,
            'unknownPairs': unknown,
            'unknownShare': round(unknown / analysed, 6) if analysed else None,
            'invalidLines': invalid,
            'refusalsThisProcess': refusal_counts(),
            'limits': list(REPORT_LIMITS),
            'executionAuthorization': False}


def render_report(value: dict) -> str:
    lines = [f"System One shadow report ({value['schema']})",
             f"Episodes: {value['totals']['episodes']}  Pairs analysed: {value['pairsAnalysed']}"
             f"  Pairs recorded: {value['pairsRecorded']}",
             'Unknown-pair share (DP-1 opportunity): '
             + ('none recorded' if value['unknownShare'] is None
                else f"{value['unknownShare']:.1%} ({value['unknownPairs']} pairs)")]
    for bucket in value['days']:
        lines.append(f"{bucket['day']}: {bucket['episodes']} episodes; operations {bucket['operations']}; "
                     f"System 2 {bucket['system2']}; System One {bucket['systemOne']}")
    if value['invalidLines']:
        lines.append(f"Invalid lines ignored: {value['invalidLines']}")
    lines.extend(value['limits'])
    return '\n'.join(lines)


def purge() -> dict:
    """Delete the store's day files, salt and lock, then the directory when nothing else is in it."""
    root = _store_root(create=False)
    if root is None:
        return {'status': 'empty', 'externalCopies': 'not-removed'}
    try:
        with _Lock(root) as lock:
            days, others = _listing(root)
            for entry in days:
                _safe(entry).unlink()
            salt = root / SALT_FILE
            salted = _unlink_own(salt)
            if not salted and salt.exists():
                others = [*others, salt]  # not ours to remove (for example a directory)
            _unlink_own(root / SALT_TEMPORARY)
            lock.path.unlink()
    except OSError:
        raise StoreRefused('unavailable') from None
    result = {'status': 'purged', 'filesRemoved': len(days) + 1 + salted, 'externalCopies': 'not-removed'}
    if others:
        result['leftover'] = [entry.name for entry in others]
    else:
        root.rmdir()
    return result
