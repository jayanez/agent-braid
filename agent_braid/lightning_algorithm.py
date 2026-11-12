# SPDX-License-Identifier: AGPL-3.0-only
# Algorithm interface and Baseline adapted from microsoft/agent-lightning agentlightning/algorithm/base.py and
# agentlightning/algorithm/fast.py (Baseline) at commit 6db3c73dc0af2e50fe80e56873a57c1703f1b2a7 (v0.x),
# Copyright (c) Microsoft Corporation, MIT License (LICENSES/Agent-Lightning-MIT.txt). Changes: no async trainer,
# adapter or LLM proxy; an algorithm runs over a prompt set through the SPEC-071 runner and records its candidates
# in the run store. See docs/development/THIRD_PARTY.md.
"""Optimization algorithms for Braid Lightning (SPEC-072 REQ-003)."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
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


QUOTA_STOPS = ('weekly-stop', 'five-hour-headroom')
NO_IMPROVEMENT_ROUNDS = 2  # SPEC-072 REQ-007


class Session:
    """One algorithm run's budgets, stop reason and replay journal (SPEC-072 REQ-007).

    Optimizer calls and evaluations go through here. Each is journaled with its result; a resumed run re-executes the
    algorithm with the same seed and takes recorded results in order instead of calling again, so it reaches the same
    state before it continues. A quota stop ends the run (resumable); any other refusal stops it.
    """

    def __init__(self, store, config: dict, optimizer, evaluator, *, resume: bool = False):
        self.store = store
        self.budget = config['budget']
        self.hosts = len(config['rollout']['hosts'])
        self.optimizer = optimizer
        self.evaluator = evaluator
        self.journal = [e for e in store.read_journal() if e['kind'] != 'stop'] if resume else []
        self.position = 0
        self.rollouts = 0
        self.calls = 0
        self.replayed = 0
        self.stop: str | None = None
        self.refusal: str | None = None

    def _replay(self, kind: str, key: str):
        if self.position >= len(self.journal):
            return None
        entry = self.journal[self.position]
        if entry['kind'] != kind or entry['inputSha256' if kind == 'call' else 'key'] != key:
            raise runner_mod.RunnerError('The resumed run diverged from its journal', 'resume-diverged')
        self.position += 1
        self.replayed += 1
        return entry

    def _halt(self, exc: runner_mod.RunnerError) -> None:
        if exc.code in QUOTA_STOPS:
            self.stop = exc.code
        else:
            self.stop, self.refusal = 'refused', exc.code

    def call(self, text: str):
        """(call id, output, check), or None once a cap or refusal has stopped the run."""
        if self.stop:
            return None
        if self.calls >= self.budget['maxOptimizerCalls']:
            self.stop = 'optimizer-cap'
            return None
        key = hashlib.sha256(text.encode('utf-8')).hexdigest()
        entry = self._replay('call', key)
        if entry is None:
            try:
                call_id, output, check = self.optimizer.call(text)
            except runner_mod.RunnerError as exc:
                self._halt(exc)
                return None
            entry = {'kind': 'call', 'inputSha256': key, 'callId': call_id, 'output': output, 'check': check}
            self.store.append_journal(entry)
        self.calls += 1
        return entry['callId'], entry['output'], entry['check']

    def evaluate(self, body: str, case_ids: list[str], repetitions: int):
        """Reward vectors for a candidate body, or None when the rollout cap or a refusal stops the run."""
        if self.stop:
            return None
        if self.rollouts + len(case_ids) * repetitions * self.hosts > self.budget['maxRollouts']:
            self.stop = 'unit-cap'
            return None
        key = hashlib.sha256(json.dumps([sha256_text(body), case_ids, repetitions]).encode()).hexdigest()
        entry = self._replay('eval', key)
        if entry is None:
            try:
                vectors = self.evaluator(body, case_ids, repetitions)
            except runner_mod.RunnerError as exc:
                self._halt(exc)
                return None
            entry = {'kind': 'eval', 'key': key, 'vectors': vectors}
            self.store.append_journal(entry)
        self.rollouts += len(entry['vectors'])
        return entry['vectors']

    def finish(self, run_id: str) -> dict:
        """Record the stop reason; return the summary fields every algorithm reports."""
        self.store.append_journal({'kind': 'stop', 'reason': self.stop, 'refusal': self.refusal})
        return {'stop': self.stop, 'refusal': self.refusal, 'rollouts': self.rollouts, 'optimizerCalls': self.calls,
                'replayed': self.replayed,
                'resume': f'agent-braid lightning run --resume {run_id}' if self.stop in QUOTA_STOPS else None}


class Stagnation:
    """Counts consecutive rounds without a better development score (SPEC-072 REQ-007)."""

    def __init__(self):
        self.best = (-1.0, -1.0)
        self.flat = 0

    def update(self, value: tuple[float, float]) -> bool:
        """Record a round's best score; True when the run must stop for lack of improvement."""
        if value > self.best:
            self.best, self.flat = value, 0
        else:
            self.flat += 1
        return self.flat >= NO_IMPROVEMENT_ROUNDS


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

    def start(self, home, config: dict, run_id: str, seed_vectors: list[dict], *, resume: bool = False):
        """Create (or reopen, on resume) the run store with the seed recorded; return (store, seed, body,
        frontMatterSha256)."""
        store = store_mod.RunStore(home, run_id)
        raw = self.skill_text(config)
        record, body = seed(raw, created_at=_now(), dev_score={'minibatch': None, 'full': score(seed_vectors)})
        if resume:
            if store.manifest()['configDigest'] != digest(config):
                raise runner_mod.RunnerError('The resumed run has a different configuration', 'resume-diverged')
            if record.sha256 not in candidates(home, run_id):
                raise runner_mod.RunnerError('The resumed run has a different seed', 'resume-diverged')
            self._known = {sha: c.value for sha, c in candidates(home, run_id).items()}
            return store, record, body, sha256_text(split_skill(raw)[0])
        store.create(config_digest=digest(config))
        store.write_candidate_text(record.sha256, body)
        store.append('candidate', record)
        self._known = {record.sha256: record.to_dict()}
        return store, record, body, sha256_text(split_skill(raw)[0])

    def record(self, store, record: Candidate) -> None:
        """Append a candidate record unless the run already holds it (a resumed run re-derives its records)."""
        value = record.to_dict()
        known = self._known.get(record.sha256)
        if known is not None and {k: v for k, v in known.items() if k != 'createdAt'} == \
                {k: v for k, v in value.items() if k != 'createdAt'}:
            return
        store.append('candidate', record)
        self._known[record.sha256] = value

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
