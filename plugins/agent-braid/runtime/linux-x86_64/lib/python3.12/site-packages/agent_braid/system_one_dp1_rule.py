# SPDX-License-Identifier: AGPL-3.0-only
"""DP-1 structural independence rule (SPEC-066): a simple, pure, auditable advisory rule.

For a pair System 2 could not decide (`unknown`) this rule says `likely-independent` only when
every clause below holds, and `undetermined` otherwise. It never says `likely-conflicting`, never
overrides System 2 and never grants authority. It is a rule, not a learned model: calibration is
absent and nothing here is verified. Standard library only; no I/O.
"""
from __future__ import annotations

import hashlib
import json
import re

BACKEND_KIND = 'rule'  # learned backends keep the T303/T402/T403 promotion gate
BACKEND_ID = 'dp1-structural-rule-v1'
RULE_ID = 'dp1-structural-independence'
RULE_VERSION = '1'
LABEL = 'not verified'
CHOICES = ('likely-independent', 'likely-conflicting', 'undetermined')
INDEPENDENT, UNDETERMINED = CHOICES[0], CHOICES[2]

ALLOWED_REASON_CODES = frozenset({'partial-coverage', 'read-version'})
ALLOWED_EFFECT_KINDS = frozenset({'read', 'write'})
BLOCKING_CLASSES = ('lockfile', 'config', 'generated')
CLAUSES = ('system2-unknown', 'reason-codes-subset', 'effect-kinds-read-write',
           'no-shared-canonical-resource', 'no-same-parent-dir', 'no-top-dir-overlap',
           'no-lockfile-config-generated-class')

# Identity of the installed backend; the shadow module compiles in its digest (REQ-007).
RULE_MANIFEST = {'backendId': BACKEND_ID, 'backendKind': BACKEND_KIND, 'ruleId': RULE_ID,
                 'version': RULE_VERSION, 'decisionPoint': 'DP-1', 'calibration': 'absent',
                 'clauses': list(CLAUSES), 'allowedReasonCodes': sorted(ALLOWED_REASON_CODES),
                 'allowedEffectKinds': sorted(ALLOWED_EFFECT_KINDS), 'blockingClasses': list(BLOCKING_CLASSES)}


def manifest_digest() -> str:
    raw = json.dumps(RULE_MANIFEST, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    return hashlib.sha256(raw).hexdigest()


_UNSUPPORTED = re.compile(r'^git-unsupported://')


def canonical_resource(resource: str) -> str:
    """The resource without its `?query` / `#fragment` and with the Git adapter's delete or
    unknown scheme folded into `git://`, so a modify and a delete of one path compare equal.

    The Git adapter ends delete and unknown resources with `?operation=<id>`; raw string
    comparison would call them disjoint from the same path's plain write resource.
    """
    text = resource.split('#', 1)[0].split('?', 1)[0]
    return _UNSUPPORTED.sub('git://', text)


def shared_canonical(left, right) -> set:
    """Canonical resources present on both sides."""
    return {canonical_resource(r) for r in left} & {canonical_resource(r) for r in right}


def _sides(value):
    return (value.get('left'), value.get('right')) if isinstance(value, dict) else (None, None)


def advise_pair(pair: dict, left_resources, right_resources) -> str:
    """One of CHOICES for a pair.

    `pair` holds the episode features (system2, reasonCodes, effectKinds, resourceClasses,
    sameParentDirCount, topDirOverlap); the resources are the live in-memory sides of the same
    System 2 report. Anything missing or malformed is `undetermined`.
    """
    try:
        if pair['system2'] != 'unknown':
            return UNDETERMINED
        if not set(pair['reasonCodes']) <= ALLOWED_REASON_CODES:
            return UNDETERMINED
        kinds = pair['effectKinds']
        if kinds is None or not all(set(side) <= ALLOWED_EFFECT_KINDS for side in _sides(kinds)):
            return UNDETERMINED
        if shared_canonical(left_resources, right_resources):
            return UNDETERMINED
        if pair['sameParentDirCount'] != 0 or pair['topDirOverlap'] is not False:
            return UNDETERMINED
        classes = pair['resourceClasses']
        if any(side[name] != 0 for side in _sides(classes) for name in BLOCKING_CLASSES):
            return UNDETERMINED
    except (KeyError, TypeError, AttributeError):
        return UNDETERMINED
    return INDEPENDENT
