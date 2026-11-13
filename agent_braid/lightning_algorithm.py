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

from . import lightning_reward as reward_mod
from . import lightning_runner as runner_mod
from . import lightning_store as store_mod
from .lightning_config import digest
from .lightning_resources import Candidate, latest, seed, sha256_text, split_skill
from .lightning_schema import AttemptResult, canonical_bytes


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
VECTOR_KEYS = frozenset({'caseId', 'host', 'd4FirstAttempt', 'schemaValid', 'reasons', 'refusal'})


def result_sha256(result: dict) -> str:
    return hashlib.sha256(canonical_bytes(result)).hexdigest()


def rescore(result: dict) -> dict:
    """The reward vector of one SPEC-071 attempt-result record, re-scored from its content-free parsed attempts."""
    host, case_id = result['rolloutId'].split('.')[:2]
    if result['promptSet'] != 'development':
        raise runner_mod.RunnerError('Optimization scores development attempts only', 'holdout-contamination')
    vector = {'caseId': case_id, 'host': host, 'd4FirstAttempt': False, 'schemaValid': False, 'reasons': [],
              'refusal': result['refusal']}
    if result['refusal'] is not None:
        return vector
    root = runner_mod.checkout_root()
    from scripts import spec069_scoring as scoring
    cases = json.loads((root / runner_mod.PROMPT_FILES['development']).read_text())['cases']
    case = next(c for c in cases if c['id'] == case_id)
    reward = reward_mod.replay(result['rolloutId'], case, result['parsedAttempts'], canary_hits=0,
                               components=['schema', 'd4', 'canary'], scoring=scoring,
                               scoring_sha256=reward_mod.check_scoring(root))
    return {**vector, 'd4FirstAttempt': reward['d4FirstAttempt'], 'schemaValid': reward['schemaValid'],
            'reasons': reward['reasons']}


class Session:
    """One algorithm run's budgets, stop reason and replay journal (SPEC-072 REQ-007, REQ-010).

    Optimizer calls and evaluations go through here. A call is journaled with its output; an evaluation stores the
    evaluator's SPEC-071 attempt-result records in the run and journals their ids and hashes. Vectors are always
    ``scorer(result)``, so selection decisions are a function of the stored parsed attempts. A resumed run re-executes
    the algorithm with the same seed and takes journaled results in order instead of calling again. ``replay`` takes
    everything from the journal, writes nothing and notes stored results whose hash no longer matches. A quota stop
    ends the run (resumable); any other refusal stops it.
    """

    def __init__(self, store, config: dict, optimizer, evaluator, *, resume: bool = False, scorer=rescore,
                 replay: bool = False):
        self.store = store
        self.budget = config['budget']
        self.hosts = len(config['rollout']['hosts'])
        self.optimizer = optimizer
        self.evaluator = evaluator
        self.scorer = scorer
        self.replay = replay
        self.journal = [e for e in store.read_journal() if e['kind'] in ('call', 'eval')] if resume or replay else []
        self.results = {r.value['attemptId']: r.value for r in store.read('result')} if resume or replay else {}
        self.altered: list[str] = []
        self.position = 0
        self.rollouts = 0
        self.calls = 0
        self.replayed = 0
        self.stop: str | None = None
        self.refusal: str | None = None

    def _replay(self, kind: str, key: str):
        if self.position >= len(self.journal):
            if self.replay:
                raise runner_mod.RunnerError('The journal ends before the run does', 'replay-incomplete')
            return None
        entry = self.journal[self.position]
        if entry['kind'] != kind or entry['inputSha256' if kind == 'call' else 'key'] != key:
            if self.replay:
                self.stop = 'replay-diverged'  # the re-scored attempts lead to another decision: stop and report
                return False
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
        if entry is False:
            return None
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
        if entry is False:
            return None
        if entry is None:
            try:
                records = [AttemptResult.parse(r) for r in self.evaluator(body, case_ids, repetitions)]
            except runner_mod.RunnerError as exc:
                self._halt(exc)
                return None
            for record in records:
                if record.value['attemptId'] in self.results:
                    raise runner_mod.RunnerError('An attempt id was reused', 'resume-diverged')
                self.store.append('result', record)
                self.results[record.value['attemptId']] = record.value
            entry = {'kind': 'eval', 'key': key,
                     'results': [[r.value['attemptId'], result_sha256(r.value)] for r in records]}
            self.store.append_journal(entry)
        results = []
        for attempt_id, sha in entry['results']:
            if attempt_id not in self.results:
                raise runner_mod.RunnerError('A journaled attempt result is missing', 'replay-incomplete')
            if result_sha256(self.results[attempt_id]) != sha:
                self.altered.append(attempt_id)
            results.append(self.results[attempt_id])
        vectors = [self.scorer(r) for r in results]
        if any(set(v) != VECTOR_KEYS for v in vectors):
            raise runner_mod.RunnerError('The scorer returned an unknown vector shape', 'reward-shape')
        self.rollouts += len(vectors)
        return vectors

    def finish(self, run_id: str) -> dict:
        """Record the stop reason (not on replay); return the summary fields every algorithm reports."""
        if not self.replay:
            self.store.append_journal({'kind': 'stop', 'reason': self.stop, 'refusal': self.refusal})
        return {'stop': self.stop, 'refusal': self.refusal, 'rollouts': self.rollouts, 'optimizerCalls': self.calls,
                'replayed': self.replayed, 'alteredResults': list(self.altered),
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


def _same_start(journaled: dict | None, start: dict) -> bool:
    """A resume or replay matches the run's start: same algorithm and seed, and the same source arm and seed skill
    (the commit may differ when the source is the working tree, whose skill the seed record already pins)."""
    if journaled is None or {k: journaled[k] for k in ('algorithm', 'rngSeed')} != \
            {k: start[k] for k in ('algorithm', 'rngSeed')}:
        return False
    stored, given = journaled.get('source'), start.get('source')
    if stored is None or given is None:
        return given is None and (stored is None or stored['workingTree'])
    return all(stored[k] == given[k] for k in ('arm', 'seedSkillSha256', 'workingTree')) and \
        (stored['workingTree'] or stored['commit'] == given['commit'])

class Algorithm:
    """Run over a prompt set with the run store and the SPEC-071 runner; return a content-free summary."""
    name = ''

    def skill_text(self, config: dict) -> str:
        if self.seed_text is not None:
            return self.seed_text
        return (runner_mod.checkout_root() / config['target']['path']).read_text(encoding='utf-8')

    rng_seed: int | None = None
    seed_text: str | None = None  # a pinned seed skill (T009 exploratory arms: the T010 guidance)
    source: dict | None = None  # where the pinned seed came from; journaled with the start entry
    replaying = False

    def start(self, home, config: dict, run_id: str, seed_vectors: list[dict], *, resume: bool = False):
        """Create (or reopen, on resume or replay) the run store with the seed and the algorithm's seed recorded;
        return (store, seed, body, frontMatterSha256)."""
        store = store_mod.RunStore(home, run_id)
        raw = self.skill_text(config)
        record, body = seed(raw, created_at=_now(), dev_score={'minibatch': None, 'full': score(seed_vectors)})
        start = {'kind': 'start', 'algorithm': self.name, 'rngSeed': self.rng_seed}
        if self.source is not None:
            start['source'] = self.source
        self._derived = {}
        if resume or self.replaying:
            if store.manifest()['configDigest'] != digest(config):
                raise runner_mod.RunnerError('The resumed run has a different configuration', 'resume-diverged')
            stored = candidates(home, run_id)
            if record.sha256 not in stored:
                raise runner_mod.RunnerError('The resumed run has a different seed', 'resume-diverged')
            journaled = next((e for e in store.read_journal() if e['kind'] == 'start'), None)
            if not _same_start(journaled, start):
                raise runner_mod.RunnerError('The resumed run has another algorithm, seed or source', 'resume-diverged')
            self._known = {sha: c.value for sha, c in stored.items()}
            self._derived = {record.sha256: self._known[record.sha256]}
            return store, record, body, sha256_text(split_skill(raw)[0])
        store.create(config_digest=digest(config))
        store.append_journal(start)
        store.write_candidate_text(record.sha256, body)
        store.append('candidate', record)
        self._known = {record.sha256: record.to_dict()}
        return store, record, body, sha256_text(split_skill(raw)[0])

    def record(self, store, record: Candidate) -> None:
        """Append a candidate record unless the run already holds it (a resumed run re-derives its records); on
        replay only note what the run derives."""
        value = record.to_dict()
        if self.replaying:
            self._derived[record.sha256] = value
            return
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


def _decision(value: dict) -> dict:
    return {k: v for k, v in value.items() if k != 'createdAt'}


def replay(home, run_id: str, algorithm: Algorithm, config: dict) -> dict:
    """Re-run a finished algorithm from its journal and stored attempt results, writing nothing (SPEC-072 REQ-010).

    Every vector is re-scored from the stored parsed attempts, so the comparison shows whether those attempts still
    reproduce every candidate record (lineage, scores, Pareto membership) and the summary's choices.
    """
    stored = {sha: _decision(c.value) for sha, c in candidates(home, run_id).items()}
    algorithm.replaying = True
    try:
        summary = algorithm.run(home, config, run_id=run_id, resume=True, replay=True)
    finally:
        algorithm.replaying = False
    derived = {sha: _decision(value) for sha, value in algorithm._derived.items()}
    changed = sorted(sha for sha in stored.keys() | derived.keys() if stored.get(sha) != derived.get(sha))
    diverged = summary['stop'] == 'replay-diverged'
    return {'runId': run_id, 'algorithm': algorithm.name, 'selectionsMatch': not changed and not diverged,
            'changedCandidates': changed, 'diverged': diverged,
            'resultsMatch': not summary['alteredResults'], 'alteredResults': summary['alteredResults'],
            'bestSha256': summary['bestSha256'], 'executionAuthorization': False}
