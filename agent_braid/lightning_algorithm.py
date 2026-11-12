# SPDX-License-Identifier: AGPL-3.0-only
# Algorithm interface and Baseline adapted from microsoft/agent-lightning agentlightning/algorithm/base.py and
# agentlightning/algorithm/fast.py (Baseline) at commit 6db3c73dc0af2e50fe80e56873a57c1703f1b2a7 (v0.x),
# Copyright (c) Microsoft Corporation, MIT License (LICENSES/Agent-Lightning-MIT.txt). Changes: no async trainer,
# adapter or LLM proxy; an algorithm runs over a prompt set through the SPEC-071 runner and records its candidates
# in the run store. See docs/development/THIRD_PARTY.md.
"""Optimization algorithms for Braid Lightning (SPEC-072 REQ-003)."""
from __future__ import annotations

from datetime import datetime, timezone

from . import lightning_runner as runner_mod
from . import lightning_store as store_mod
from .lightning_resources import Candidate, latest, seed


def _now() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


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
