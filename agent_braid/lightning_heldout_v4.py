# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-079 (REQ-008, REQ-009): the held-out ``v4-test`` split for the SPEC-071 runner, gated by the v4 freeze.

``specs/079-kind-choice-tool-fix/prompts/FREEZE-v4.json`` (written by ``scripts/spec079_freeze.py``) binds the
protocol, the split, its builder, Gate 0, the scorer, the OD-1 analysis, the measured tool modules and the analyze
skill by sha256 at develop ``FREEZE_COMMIT``, and pins the closed SPEC-069 and SPEC-078 freeze records. A
``v4-test`` run refuses before anything else unless that freeze holds at that commit; the plugin it measures is
built from that commit (OD-D). The analysis and reference requests are the v2 ones (``lightning_heldout_v2``).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .lightning_heldout_v2 import FreezeError, WINDOW, normalize_words, sha256, window_sha256

SPEC = 'specs/079-kind-choice-tool-fix'
PROMPT_FILES = {'v4-test': f'{SPEC}/prompts/v4-test.json'}
PROTECTED = ('v4-test',)
FREEZE = f'{SPEC}/prompts/FREEZE-v4.json'
FREEZE_COMMIT = '331a384eeed0c52d39186ce64fc8344f4a23a759'  # the develop commit T007 froze (#1643)
SKILL = 'integrations/agent-braid/skills/agent-braid-analyze/SKILL.md'
TEST_MARKER = '.V4T-'  # rollout ids of the v4 test split


def _freeze_script():
    """The freeze definition lives with its writer (checkout only, like the rest of the laboratory)."""
    from scripts import spec079_freeze
    return spec079_freeze


def load_freeze(root: Path) -> dict:
    definition = _freeze_script()
    path = root / FREEZE
    if not path.is_file():
        raise FreezeError('The v4 split is not frozen; v4 runs are refused', 'protocol-not-frozen')
    record = json.loads(path.read_text())
    if (record.get('schema') != definition.SCHEMA or set(record.get('files') or {}) != set(definition.BOUND)
            or set(record.get('closedRecords') or {}) != set(definition.RECORDS)):
        raise FreezeError('Unknown v4 freeze record', 'protocol-not-frozen')
    if record.get('commit') != FREEZE_COMMIT or record.get('pluginCommit') != FREEZE_COMMIT:
        raise FreezeError(f'The v4 freeze is not the one made at develop {FREEZE_COMMIT[:8]}', 'protocol-not-frozen')
    return record


def check_freeze(root: Path, prompt_set: str) -> str:
    """Refuse a v4 run unless every bound file and closed record matches the freeze; return the split's hash."""
    if prompt_set not in PROMPT_FILES:
        raise FreezeError('Unknown v4 prompt set', 'config-enum')
    record = load_freeze(root)
    for path, digest in record['files'].items():
        if not (root / path).is_file() or sha256(root / path) != digest:
            code = ('skill-hash-mismatch' if path == SKILL else 'holdout-hash-mismatch'
                    if path == PROMPT_FILES['v4-test'] else 'protocol-hash-mismatch')
            raise FreezeError(f'{path} differs from the v4 freeze', code)
    problems = _freeze_script().boundary_problems(root, record['closedRecords'])
    if problems:
        raise FreezeError('; '.join(problems), 'protocol-hash-mismatch')
    return record['files'][PROMPT_FILES['v4-test']]


def check_skill(root: Path, skill_bytes: bytes) -> None:
    """The v4 arm measures exactly the frozen analyze skill."""
    if hashlib.sha256(skill_bytes).hexdigest() != load_freeze(root)['files'][SKILL]:
        raise FreezeError('The packaged skill differs from the frozen v4 skill', 'skill-hash-mismatch')


def fingerprints(root: Path) -> dict:
    """Case-id and 8-word-window hashes of the v4 split, for the optimizer contamination scan."""
    ids, windows = set(), set()
    for case in json.loads((root / PROMPT_FILES['v4-test']).read_text())['cases']:
        ids.add(hashlib.sha256(case['id'].encode()).hexdigest())
        words = normalize_words(case['prompt'])
        windows |= {window_sha256(words[i:i + WINDOW]) for i in range(len(words) - WINDOW + 1)}
    return {'idSha256': sorted(ids), 'windowSha256': sorted(windows)}


def load_fingerprints(root: Path) -> dict | None:
    """The v4 fingerprints whenever the split exists. They do not depend on the freeze, so a later edit of a bound
    tool file (after the v4 result) never blocks unrelated optimizer runs; it only refuses v4 runs."""
    if not (root / PROMPT_FILES['v4-test']).is_file():
        return None
    return fingerprints(root)
