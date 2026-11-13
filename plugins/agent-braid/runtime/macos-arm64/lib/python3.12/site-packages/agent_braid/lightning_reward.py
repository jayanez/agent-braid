# SPDX-License-Identifier: AGPL-3.0-only
# Reward record role adapted from microsoft/agent-lightning agentlightning/emitter/reward.py at commit
# 6db3c73dc0af2e50fe80e56873a57c1703f1b2a7 (v0.x), Copyright (c) Microsoft Corporation, MIT License
# (LICENSES/Agent-Lightning-MIT.txt). Changes: span emission replaced by a pure, deterministic reward vector
# computed by the frozen SPEC-069 scoring rules; no tracer, no model call, no LLM judge.
# See docs/development/THIRD_PARTY.md.
"""Verifiable reward vector for one Braid Lightning rollout (SPEC-071 REQ-008, contracts/reward-vector.md).

The reward is an empirical measurement (Article 13), never a guarantee. ``schemaValid`` is the runtime verdict of
the first ``analyze-work`` attempt; SPEC-069's differential corpus test keeps that runtime validator equivalent to
the declared per-kind schema in ``agent_braid/analyze_work_schema.py``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import ModuleType

REWARD_SCHEMA = 'braid-lightning-reward/v0.1'
FREEZE = 'specs/069-aim-request-authoring/prompts/FREEZE.json'
SCORING = 'scripts/spec069_scoring.py'
COMPONENTS = ('schema', 'd4', 'canary')
MAX_REASONS = 8


class RewardError(ValueError):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def frozen_hashes(root: Path) -> dict[str, str]:
    """The latest FREEZE record's file hashes."""
    records = json.loads((root / FREEZE).read_text())['records']
    return dict(records[-1]['files'])


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_scoring(root: Path) -> str:
    """Refuse when the scoring rules differ from the frozen ones (R2); return their hash."""
    actual = file_sha256(root / SCORING)
    if frozen_hashes(root).get(SCORING) != actual:
        raise RewardError('The SPEC-069 scoring rules differ from FREEZE.json', 'scoring-hash-mismatch')
    return actual


def check_prompt_set(root: Path, relative: str) -> str:
    """Refuse a held-out or development set whose bytes differ from FREEZE (REQ-009)."""
    actual = file_sha256(root / relative)
    if frozen_hashes(root).get(relative) != actual:
        raise RewardError('The prompt set differs from FREEZE.json', 'holdout-hash-mismatch')
    return actual


def compute(rollout_id: str, case: dict, attempts: list[dict], *, canary_hits: int, components: list[str],
            scoring: ModuleType, scoring_sha256: str) -> dict:
    """The reward vector. Deterministic for equal inputs; ``canaryHits > 0`` zeroes D4."""
    if type(canary_hits) is not int or canary_hits < 0:
        raise RewardError('canaryHits must be a non-negative integer', 'reward-shape')
    if not components or set(components) - set(COMPONENTS):
        raise RewardError('Unknown reward component', 'reward-shape')
    score = scoring.score_case(case, attempts)
    clean = canary_hits == 0
    return {
        'schema': REWARD_SCHEMA,
        'rolloutId': rollout_id,
        'schemaValid': bool(attempts) and bool(attempts[0].get('accepted')),
        'd4FirstAttempt': bool(score['validFirstAttempt']) and clean,
        'd4WithinRetry': bool(score['validWithinRetry']) and clean,
        'attempts': len(attempts),
        'reasons': [str(reason)[:200] for reason in score['reasons'][:MAX_REASONS]],
        'canaryHits': canary_hits,
        'scoringSha256': scoring_sha256,
        'components': [c for c in COMPONENTS if c in components],
        'claim': 'empirical-measurement',
    }


def canonical(reward: dict) -> bytes:
    return (json.dumps(reward, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()


def reward_sha256(reward: dict) -> str:
    return hashlib.sha256(canonical(reward)).hexdigest()


def scoring_attempts(parsed_attempts: list[dict]) -> list[dict]:
    """The ``score_case`` inputs from content-free parsed attempts (replay, REQ-011)."""
    return [{'kind': a['kind'], 'request': a['request'], 'accepted': a['accepted'],
             'refusalSummary': a['refusalSummary'], 'report': a['report']} for a in parsed_attempts]


def parsed_attempts(attempts: list[dict]) -> list[dict]:
    """Content-free attempt records: no prompt or response text, only declared fields and runtime verdicts."""
    out = []
    for attempt in attempts:
        request = attempt.get('request')
        out.append({'kind': attempt.get('kind') if isinstance(attempt.get('kind'), str) else None,
                    'requestSha256': hashlib.sha256(json.dumps(request, sort_keys=True, default=str).encode()).hexdigest(),
                    'accepted': bool(attempt.get('accepted')),
                    'refusalSummary': (str(attempt['refusalSummary'])[:300] or None) if attempt.get('refusalSummary') else None,
                    'request': request if isinstance(request, (dict, list)) else None,
                    'report': attempt.get('report') if isinstance(attempt.get('report'), (dict, list)) else None})
    return out


def replay(rollout_id: str, case: dict, parsed: list[dict], *, canary_hits: int, components: list[str],
           scoring: ModuleType, scoring_sha256: str) -> dict:
    return compute(rollout_id, case, scoring_attempts(parsed), canary_hits=canary_hits, components=components,
                   scoring=scoring, scoring_sha256=scoring_sha256)
