# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 Amendment 1 (REQ-014): the fresh ``v3-test`` split, its freeze and fingerprints.

The v3 freeze (``prompts/FREEZE-v3.json``) binds the v3 protocol, the split, its builder, Gate 0, the shared
analysis module, this module and the fixed analyze skill by sha256 at a ``develop`` commit. A ``v3-test`` run
refuses before anything else when a bound file differs; an A0' run refuses a packaged skill other than the frozen
one. The analysis, reference requests and refusal codes are the v2 ones (``lightning_heldout_v2``), which stays
unchanged because the v2 freeze binds it.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .lightning_heldout_v2 import (FreezeError, WINDOW, analyse, normalize_words, reference_request,  # noqa: F401
                                   sha256, window_sha256)

SPEC = 'specs/078-lightning-heldout-v2'
PROMPT_FILES = {'v3-test': f'{SPEC}/prompts/v3-test.json'}
PROTECTED = ('v3-test',)
FREEZE = f'{SPEC}/prompts/FREEZE-v3.json'
FINGERPRINTS = f'{SPEC}/prompts/fingerprints-v3.json'
FREEZE_SCHEMA = 'braid-lightning-v3-freeze/v0.1'
FINGERPRINT_SCHEMA = 'braid-lightning-v3-fingerprints/v0.1'
PROTOCOL = f'{SPEC}/evaluation-protocol-v3.md'
GATE0 = 'scripts/spec078_gate0.py'
BUILDER = 'scripts/spec078_build_v3.py'
FACTS = 'scripts/spec078_build_set.py'  # the shared fact generator, expectation rule and window checks
ANALYSIS = 'agent_braid/lightning_heldout_v2.py'
MODULE = 'agent_braid/lightning_heldout_v3.py'
SKILL = 'integrations/agent-braid/skills/agent-braid-analyze/SKILL.md'
BOUND = (PROTOCOL, PROMPT_FILES['v3-test'], BUILDER, FACTS, GATE0, ANALYSIS, MODULE, SKILL)
TEST_MARKER = '.V3T-'  # rollout ids of the v3 test split


def freeze_record(root: Path, commit: str) -> dict:
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise FreezeError('The freeze names a full develop commit', 'protocol-not-frozen')
    return {'schema': FREEZE_SCHEMA, 'commit': commit, 'files': {p: sha256(root / p) for p in BOUND}}


def load_freeze(root: Path) -> dict:
    path = root / FREEZE
    if not path.is_file():
        raise FreezeError('The v3 split is not frozen; v3 runs are refused', 'protocol-not-frozen')
    record = json.loads(path.read_text())
    if record.get('schema') != FREEZE_SCHEMA or set(record.get('files') or {}) != set(BOUND):
        raise FreezeError('Unknown v3 freeze record', 'protocol-not-frozen')
    return record


def check_freeze(root: Path, prompt_set: str) -> str:
    """Refuse a v3 run unless every bound file matches the freeze; return the split's frozen hash."""
    if prompt_set not in PROMPT_FILES:
        raise FreezeError('Unknown v3 prompt set', 'config-enum')
    files = load_freeze(root)['files']
    for path in BOUND:
        if sha256(root / path) != files[path]:
            code = ('skill-hash-mismatch' if path == SKILL else 'holdout-hash-mismatch'
                    if path == PROMPT_FILES['v3-test'] else 'protocol-hash-mismatch')
            raise FreezeError(f'{path} differs from the v3 freeze', code)
    return files[PROMPT_FILES[prompt_set]]


def check_skill(root: Path, skill_bytes: bytes) -> None:
    """An A0' run measures exactly the frozen fixed skill."""
    if hashlib.sha256(skill_bytes).hexdigest() != load_freeze(root)['files'][SKILL]:
        raise FreezeError("The packaged skill differs from the frozen A0' skill", 'skill-hash-mismatch')


def fingerprints(root: Path) -> dict:
    ids, windows = set(), set()
    for case in json.loads((root / PROMPT_FILES['v3-test']).read_text())['cases']:
        ids.add(hashlib.sha256(case['id'].encode()).hexdigest())
        words = normalize_words(case['prompt'])
        windows |= {window_sha256(words[i:i + WINDOW]) for i in range(len(words) - WINDOW + 1)}
    return {'schema': FINGERPRINT_SCHEMA, 'window': WINDOW,
            'sources': {PROMPT_FILES['v3-test']: sha256(root / PROMPT_FILES['v3-test'])},
            'idSha256': sorted(ids), 'windowSha256': sorted(windows)}


def load_fingerprints(root: Path) -> dict | None:
    """The v3 fingerprints, or None before the freeze; refused when they do not match the frozen split."""
    path = root / FINGERPRINTS
    if not path.is_file():
        return None
    value = json.loads(path.read_text())
    files = load_freeze(root)['files']
    if value.get('schema') != FINGERPRINT_SCHEMA or value.get('window') != WINDOW or \
            value.get('sources') != {PROMPT_FILES['v3-test']: files[PROMPT_FILES['v3-test']]}:
        raise FreezeError('v3 fingerprints do not match the v3 freeze', 'holdout-fingerprint-stale')
    return value
