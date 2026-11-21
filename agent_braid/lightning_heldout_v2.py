# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 (BL.2b) held-out set v2: prompt sets, protocol freeze and the preregistered analysis.

The freeze record (``specs/078-lightning-heldout-v2/prompts/FREEZE.json``) binds the protocol, the three splits,
the Gate 0 script and the A0 skill by sha256 at a ``develop`` commit. Every ``v2-*`` run refuses before anything
else when the record is missing or any bound file differs, and an A0 run (no explicit candidate text) refuses when
the packaged skill differs from the frozen one. The analysis implements OD-1 of ``evaluation-protocol.md``; it is
an empirical summary of one host, model and set, not a guarantee.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

SPEC = 'specs/078-lightning-heldout-v2'
PROMPT_FILES = {'v2-feedback': f'{SPEC}/prompts/feedback.json',
                'v2-validation': f'{SPEC}/prompts/validation.json',
                'v2-test': f'{SPEC}/prompts/test.json'}
PROTECTED = ('v2-validation', 'v2-test')  # never readable by, or quoted to, an optimizer call
FREEZE = f'{SPEC}/prompts/FREEZE.json'
FINGERPRINTS = f'{SPEC}/prompts/fingerprints.json'
FREEZE_SCHEMA = 'braid-lightning-v2-freeze/v0.1'
FINGERPRINT_SCHEMA = 'braid-lightning-v2-fingerprints/v0.1'
PROTOCOL = f'{SPEC}/evaluation-protocol.md'
GATE0 = 'scripts/spec078_gate0.py'
SKILL = 'integrations/agent-braid/skills/agent-braid-analyze/SKILL.md'
ANALYSIS = 'agent_braid/lightning_heldout_v2.py'  # Gate 0's OD-1 and references live here too
BOUND = (PROTOCOL, *PROMPT_FILES.values(), GATE0, ANALYSIS, SKILL)
PASS_MIN = 2           # OD-1: a prompt passes with at least 2 of its 3 repetitions valid
WILSON_LB_MIN = 0.80   # OD-1: Wilson 95 % lower bound of the passing share
WINDOW = 8
_WORD = re.compile(r'[a-z0-9]+')


class FreezeError(ValueError):
    """A v2 run is refused; ``code`` is listed in SPEC-078 contracts/refusals.md."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ----------------------------------------------------------------------------
# Freeze
# ----------------------------------------------------------------------------
def freeze_record(root: Path, commit: str) -> dict:
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise FreezeError('The freeze names a full develop commit', 'protocol-not-frozen')
    return {'schema': FREEZE_SCHEMA, 'commit': commit, 'files': {p: sha256(root / p) for p in BOUND}}


def load_freeze(root: Path) -> dict:
    path = root / FREEZE
    if not path.is_file():
        raise FreezeError('The SPEC-078 protocol is not frozen; v2 runs are refused', 'protocol-not-frozen')
    record = json.loads(path.read_text())
    if record.get('schema') != FREEZE_SCHEMA or set(record.get('files') or {}) != set(BOUND):
        raise FreezeError('Unknown SPEC-078 freeze record', 'protocol-not-frozen')
    return record


def check_freeze(root: Path, prompt_set: str) -> str:
    """Refuse a v2 run unless every bound file matches the freeze; return the prompt set's frozen hash."""
    if prompt_set not in PROMPT_FILES:
        raise FreezeError('Unknown v2 prompt set', 'config-enum')
    files = load_freeze(root)['files']
    for path in BOUND:
        if sha256(root / path) != files[path]:
            code = ('protocol-hash-mismatch' if path in (PROTOCOL, GATE0, ANALYSIS)
                    else 'skill-hash-mismatch' if path == SKILL else 'holdout-hash-mismatch')
            raise FreezeError(f'{path} differs from the SPEC-078 freeze', code)
    return files[PROMPT_FILES[prompt_set]]


def check_skill(root: Path, skill_bytes: bytes) -> None:
    """An A0 run measures exactly the frozen skill bytes."""
    if hashlib.sha256(skill_bytes).hexdigest() != load_freeze(root)['files'][SKILL]:
        raise FreezeError('The packaged skill differs from the frozen A0 skill', 'skill-hash-mismatch')


# ----------------------------------------------------------------------------
# Contamination fingerprints (SPEC-072 REQ-006 extended to v2 validation and test)
# ----------------------------------------------------------------------------
def normalize_words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def window_sha256(words: list[str]) -> str:
    return hashlib.sha256(' '.join(words).encode()).hexdigest()


def fingerprints(root: Path) -> dict:
    ids, windows = set(), set()
    for name in PROTECTED:
        for case in json.loads((root / PROMPT_FILES[name]).read_text())['cases']:
            ids.add(hashlib.sha256(case['id'].encode()).hexdigest())
            words = normalize_words(case['prompt'])
            windows |= {window_sha256(words[i:i + WINDOW]) for i in range(len(words) - WINDOW + 1)}
    return {'schema': FINGERPRINT_SCHEMA, 'window': WINDOW,
            'sources': {PROMPT_FILES[n]: sha256(root / PROMPT_FILES[n]) for n in PROTECTED},
            'idSha256': sorted(ids), 'windowSha256': sorted(windows)}


def load_fingerprints(root: Path) -> dict | None:
    """The v2 fingerprints, or None before the freeze; refused when they do not match the frozen splits."""
    path = root / FINGERPRINTS
    if not path.is_file():
        return None
    value = json.loads(path.read_text())
    files = load_freeze(root)['files']
    if value.get('schema') != FINGERPRINT_SCHEMA or value.get('window') != WINDOW or \
            value.get('sources') != {PROMPT_FILES[n]: files[PROMPT_FILES[n]] for n in PROTECTED}:
        raise FreezeError('v2 fingerprints do not match the SPEC-078 freeze', 'holdout-fingerprint-stale')
    return value


# ----------------------------------------------------------------------------
# Reference requests (Gate 0 and the fake-host pipeline)
# ----------------------------------------------------------------------------
def reference_request(case: dict, scoring, repository: str = '<repository>', *, honour_partial: bool = True) -> dict:
    """The SPEC-069 reference request for the expectation, with the coverage the case's facts give."""
    request = scoring.reference_request(case, repository)
    if case['expect']['kind'] == 'aim' and honour_partial:
        for op, unit in zip(request['operations'], case['facts']['units']):
            if unit['partial']:
                op['effects']['coverage']['status'] = 'partial'
    return request


# ----------------------------------------------------------------------------
# Analysis (evaluation-protocol.md, OD-1 and H-G2)
# ----------------------------------------------------------------------------
def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0 or not 0 <= successes <= n:
        raise ValueError('need n > 0 and 0 <= successes <= n')
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def meets_share_and_classes(passes: list[tuple[str, bool]]) -> tuple[bool, float]:
    """OD-1 items 1-2 over ``(class, passed)`` per prompt: Wilson lower bound at least 0.80 and every class with at
    least half its prompts passing."""
    if not passes:
        return False, 0.0
    low = wilson_interval(sum(ok for _, ok in passes), len(passes))[0]
    by_class: dict[str, list[bool]] = {}
    for cls, ok in passes:
        by_class.setdefault(cls, []).append(ok)
    return low >= WILSON_LB_MIN and all(2 * sum(v) >= len(v) for v in by_class.values()), low


def sign_test_one_sided(better: int, worse: int) -> float:
    """P(X >= better) for X ~ Binomial(better + worse, 1/2): exact McNemar on the discordant prompts."""
    n = better + worse
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(better, n + 1)) / 2 ** n


def clustered_se(rates: list[float]) -> float:
    """Prompt-clustered standard error of the trial-level rate: sd of per-prompt rates / sqrt(n)."""
    n = len(rates)
    if n < 2:
        return 0.0
    mean = sum(rates) / n
    return math.sqrt(sum((r - mean) ** 2 for r in rates) / (n - 1)) / math.sqrt(n)


def analyse(cases: list[dict], trials: dict[str, list[bool]], review: dict[str, str] | None = None,
            repetitions: int = 3) -> dict:
    """The Gate 1 report body for one arm on one split.

    ``trials`` maps a case id to its first-attempt validity per repetition; ``review`` maps a 0-of-n case id to
    ``model`` or ``instrument`` (REQ-006). The verdict is ``held`` while a zero prompt is unreviewed and
    ``invalidated`` after an ``instrument`` finding.
    """
    review = review or {}
    if set(trials) != {c['id'] for c in cases}:
        raise ValueError('trials must cover exactly the split')
    if any(len(v) != repetitions for v in trials.values()):
        raise ValueError(f'every prompt needs {repetitions} repetitions')
    per_prompt, passes, zero = [], [], []
    for case in cases:
        valid = trials[case['id']]
        ok = sum(valid) >= PASS_MIN
        per_prompt.append({'id': case['id'], 'class': case['class'], 'valid': sum(valid), 'of': len(valid),
                           'passes': ok})
        passes.append((case['class'], ok))
        if not any(valid):
            zero.append(case['id'])
    meets, low = meets_share_and_classes(passes)
    unknown = set(review) - set(zero)
    if unknown or set(review.values()) - {'model', 'instrument'}:
        raise ValueError('review names a prompt that is not 0/3 or an unknown class')
    if any(review.get(z) == 'instrument' for z in zero):
        verdict = 'invalidated'
    elif any(z not in review for z in zero):
        verdict = 'held'
    else:
        verdict = 'meets' if meets and not zero else 'misses'
    passing = sum(ok for _, ok in passes)
    classes: dict[str, list[int]] = {}
    for cls, ok in passes:
        tally = classes.setdefault(cls, [0, 0])
        tally[0] += ok
        tally[1] += 1
    rates = [row['valid'] / row['of'] for row in per_prompt]
    return {'prompts': len(cases), 'passing': passing, 'wilson95': list(wilson_interval(passing, len(cases))),
            'trialRate': sum(rates) / len(rates), 'trialRateClusteredSE': clustered_se(rates),
            'allRepetitionsValid': sum(row['valid'] == row['of'] for row in per_prompt),
            'perClass': {k: {'passing': v[0], 'of': v[1]} for k, v in sorted(classes.items())},
            'zeroPrompts': zero, 'review': dict(review), 'od1': verdict, 'perPrompt': per_prompt}


def compare(baseline: dict, candidate: dict) -> dict:
    """H-G2 primary: one-sided exact sign test on prompts whose pass status differs (candidate better)."""
    a = {r['id']: r['passes'] for r in baseline['perPrompt']}
    b = {r['id']: r['passes'] for r in candidate['perPrompt']}
    if set(a) != set(b):
        raise ValueError('the two results must cover the same prompts')
    better = sum(b[i] and not a[i] for i in a)
    worse = sum(a[i] and not b[i] for i in a)
    p = sign_test_one_sided(better, worse)
    return {'better': better, 'worse': worse, 'unchanged': len(a) - better - worse, 'pOneSided': p,
            'supported': p < 0.05}
