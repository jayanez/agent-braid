# SPDX-License-Identifier: AGPL-3.0-only
# Algorithm interface and Baseline adapted from microsoft/agent-lightning agentlightning/algorithm/base.py and
# agentlightning/algorithm/fast.py (Baseline) at commit 6db3c73dc0af2e50fe80e56873a57c1703f1b2a7 (v0.x),
# Copyright (c) Microsoft Corporation, MIT License (LICENSES/Agent-Lightning-MIT.txt). Changes: no async trainer,
# adapter or LLM proxy; an algorithm runs over a prompt set through the SPEC-071 runner and records its candidates
# in the run store. See docs/development/THIRD_PARTY.md.
"""Optimization algorithms for Braid Lightning (SPEC-072 REQ-003)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from . import lightning_runner as runner_mod
from . import lightning_store as store_mod
from .lightning_config import digest
from .lightning_resources import Candidate, latest, seed, sha256_text, split_skill


def _now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


PROMPTS = Path(__file__).resolve().parent / 'lightning_prompts'
_PLACEHOLDER = re.compile(r'\{(prompt_template|experiments|critique)\}')
_HEADER = re.compile(r'\A(?:<!--.*?-->\s*)+', re.S)


def render(path: Path, **values: str) -> str:
    """Fill a Markdown template in one pass, so placeholder-like text inside a value is never expanded."""
    text = _HEADER.sub('', path.read_text(encoding='utf-8'))
    return _PLACEHOLDER.sub(lambda m: values[m.group(1)], text)


def experiments(vectors: list[dict]) -> str:
    """Content-free reward vectors as optimizer input lines (SPEC-072 P1: no transcripts)."""
    return '\n'.join(
        f"- {v['caseId']} on {v['host']}: first attempt {'passed' if v['d4FirstAttempt'] else 'failed'} D4; "
        f"request {'schema-valid' if v['schemaValid'] else 'schema-invalid'}; "
        f"reasons: {', '.join(v.get('reasons') or []) or 'none'}; refusal: {v.get('refusal') or 'none'}"
        for v in vectors)


def score(vectors: list[dict]) -> dict | None:
    if not vectors:
        return None
    n = len(vectors)
    return {'d4FirstAttempt': round(sum(bool(v['d4FirstAttempt']) for v in vectors) / n, 6),
            'schemaValid': round(sum(bool(v['schemaValid']) for v in vectors) / n, 6), 'rollouts': n}


def rank(value: dict | None) -> tuple[float, float]:
    """Selection key (SPEC-072 P2): mean d4FirstAttempt, then mean schemaValid as tie-breaker."""
    return (value['d4FirstAttempt'], value['schemaValid']) if value else (-1.0, -1.0)


def dev_score(store: store_mod.RunStore) -> dict | None:
    """Mean schema and D4 first-attempt components over the run's verifier reward events."""
    rewards = [e.data['reward']['components'] for e in store.read('event') if e.event_type == 'reward']
    if not rewards:
        return None
    n = len(rewards)
    return {'d4FirstAttempt': round(sum(r['d4'] for r in rewards) / n, 6),
            'schemaValid': round(sum(r['schema'] for r in rewards) / n, 6), 'rollouts': n}


class Algorithm:
    """Run over a prompt set with the run store and the SPEC-071 runner; return a content-free summary."""
    name = ''

    def skill_text(self, config: dict) -> str:
        return (runner_mod.checkout_root() / config['target']['path']).read_text(encoding='utf-8')

    def start(self, home, config: dict, run_id: str, seed_vectors: list[dict]):
        """Create the run store and record the seed with its full development score; return (store, seed, body,
        frontMatterSha256)."""
        store = store_mod.RunStore(home, run_id)
        store.create(config_digest=digest(config))
        raw = self.skill_text(config)
        record, body = seed(raw, created_at=_now(), dev_score={'minibatch': None, 'full': score(seed_vectors)})
        store.write_candidate_text(record.sha256, body)
        store.append('candidate', record)
        return store, record, body, sha256_text(split_skill(raw)[0])

    def run(self, home, config: dict, **runner_kwargs) -> dict:
        raise NotImplementedError


class Baseline(Algorithm):
    """Evaluate the seed candidate unchanged (round 0, no optimizer calls)."""
    name = 'baseline'

    def run(self, home, config: dict, **runner_kwargs) -> dict:
        raw = self.skill_text(config)
        status = runner_mod.run(home, config, **runner_kwargs)
        store = store_mod.RunStore(home, status['runId'])
        score = dev_score(store)
        record, body = seed(raw, created_at=_now(), dev_score=score and {'minibatch': None, 'full': score})
        store.write_candidate_text(record.sha256, body)
        store.append('candidate', record)
        return {'algorithm': self.name, 'runId': status['runId'], 'candidateSha256': record.sha256,
                'status': status, 'report': runner_mod.report(home, status['runId']),
                'executionAuthorization': False}


ALGORITHMS: dict[str, type[Algorithm]] = {'baseline': Baseline}


def candidates(home, run_id: str) -> dict[str, Candidate]:
    """Latest candidate record per sha256 in a run, with lineage checked."""
    return latest(store_mod.RunStore(home, run_id).read('candidate'))
