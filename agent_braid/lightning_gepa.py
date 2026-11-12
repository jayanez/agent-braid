# SPDX-License-Identifier: AGPL-3.0-only
"""GEPA for Braid Lightning (SPEC-072 REQ-005).

Implemented from the description in arXiv 2507.19457 (Agrawal et al., "GEPA: Reflective Prompt Evolution Can
Outperform Reinforcement Learning"): a Pareto front over per-prompt scores, parent sampling weighted by the number
of prompts on which a front member scores best, reflective mutation on a minibatch, acceptance only when the child's
minibatch score beats the parent's, then a full development evaluation. No GEPA or DSPy code is vendored. Until BL.4
the reflection sees content-free reward vectors, `score_case` reasons, refusal codes and the parent text only.
"""
from __future__ import annotations

import hashlib
import json
import random

from . import lightning_runner as runner_mod
from .lightning_algorithm import PROMPTS, Algorithm, _now, experiments, rank, render, score
from .lightning_resources import CANDIDATE_SCHEMA, MAX_TEXT, ORIGIN_PATH, Candidate, sha256_text

TEMPLATE = PROMPTS / 'gepa_reflection.md'


def template_sha256() -> str:
    return hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()


def per_case(vectors: list[dict]) -> dict[str, float]:
    """Mean first-attempt D4 per case over hosts and repetitions (the front's per-prompt score, SPEC-072 P2)."""
    totals: dict[str, list[int]] = {}
    for v in vectors:
        totals.setdefault(v['caseId'], []).append(bool(v['d4FirstAttempt']))
    return {case: sum(hits) / len(hits) for case, hits in totals.items()}


def dominates(a: dict[str, float], b: dict[str, float], cases: list[str]) -> bool:
    return all(a[c] >= b[c] for c in cases) and any(a[c] > b[c] for c in cases)


def pareto_front(scores: dict[str, dict[str, float]], cases: list[str]) -> list[str]:
    """Candidates no other candidate dominates over the per-case scores; equal score vectors keep the first."""
    front: list[str] = []
    for sha, own in scores.items():
        if any(dominates(other, own, cases) for key, other in scores.items() if key != sha):
            continue
        if any(all(scores[kept][c] == own[c] for c in cases) for kept in front):
            continue
        front.append(sha)
    return front


def weights(front: list[str], scores: dict[str, dict[str, float]], cases: list[str]) -> dict[str, int]:
    """For each front member, the number of prompts on which it reaches the best score among the front."""
    counts = {sha: 0 for sha in front}
    for case in cases:
        best = max(scores[sha][case] for sha in front)
        for sha in front:
            counts[sha] += scores[sha][case] == best
    return counts


def select_parent(front: list[str], scores: dict[str, dict[str, float]], cases: list[str],
                  rng: random.Random) -> str:
    counts = weights(front, scores, cases)
    candidates = [sha for sha in front if counts[sha] > 0]
    return rng.choices(candidates, weights=[counts[sha] for sha in candidates], k=1)[0]


class GEPA(Algorithm):
    """Reflective prompt evolution with a Pareto front (see module docstring).

    ``evaluator(body, case_ids, repetitions) -> [vector]`` as for APO; ``seed_vectors`` are the seed's full
    development vectors from the SPEC-071 baseline run (not charged to the arm). ``rng_seed`` fixes parent and
    minibatch sampling so a resumed run repeats its choices.
    """
    name = 'gepa'

    def __init__(self, *, evaluator, optimizer: runner_mod.OptimizerChannel, seed_vectors: list[dict],
                 rng_seed: int = 0):
        if not isinstance(optimizer, runner_mod.OptimizerChannel):
            raise runner_mod.RunnerError('Optimizer calls must go through the runner', 'optimizer-bypass')
        self.evaluator = evaluator
        self.optimizer = optimizer
        self.seed_vectors = list(seed_vectors)
        self.rng_seed = rng_seed

    def run(self, home, config: dict, *, run_id: str, **_ignored) -> dict:
        algo, budget, rollout = config['algorithm'], config['budget'], config['rollout']
        cases = [c['id'] for c in json.loads(
            (runner_mod.checkout_root() / runner_mod.PROMPT_FILES['development']).read_text())['cases']]
        hosts = len(rollout['hosts'])
        store, seed_record, seed_body, front_sha = self.start(home, config, run_id, self.seed_vectors)
        rng = random.Random(self.rng_seed)
        size = min(algo['minibatch'], len(cases))
        template = template_sha256()

        pool = {seed_record.sha256: {'body': seed_body, 'full': self.seed_vectors, 'record': seed_record.to_dict()}}
        scores = {seed_record.sha256: per_case(self.seed_vectors)}
        front = pareto_front(scores, cases)
        state = {'rollouts': 0, 'stop': None, 'failedCalls': 0}
        history = []

        def charge(units: int) -> bool:
            if state['rollouts'] + units > budget['maxRollouts']:
                state['stop'] = 'unit-cap'
                return False
            return True

        def refresh_front() -> None:
            nonlocal front
            front = pareto_front(scores, cases)
            for sha, node in pool.items():
                record = node['record']
                member = sha in front
                if record['algorithm'] == 'gepa' and record['paretoMember'] != member:
                    record = {**record, 'paretoMember': member, 'createdAt': _now()}
                    store.append('candidate', Candidate.parse(record))
                    node['record'] = record

        seen = {seed_record.sha256}
        for rnd in range(1, algo['rounds'] + 1):
            if len(self.optimizer.calls) >= budget['maxOptimizerCalls']:
                state['stop'] = 'optimizer-cap'
                break
            parent = select_parent(front, scores, cases, rng)
            batch = sorted(rng.sample(cases, size))
            parent_vectors = [v for v in pool[parent]['full'] if v['caseId'] in batch]
            call_id, body, check = self.optimizer.call(render(
                TEMPLATE, prompt_template=pool[parent]['body'], experiments=experiments(parent_vectors)))
            entry = {'round': rnd, 'parent': parent, 'minibatch': batch, 'child': None, 'accepted': False}
            history.append(entry)
            sha = sha256_text(body)
            if not body.strip() or len(body.encode('utf-8')) > MAX_TEXT or sha in seen:
                state['failedCalls'] += 1  # not a usable skill body: a failed call, no candidate
                continue
            if not charge(size * hosts):
                break
            child_vectors = self.evaluator(body, batch, 1)
            state['rollouts'] += len(child_vectors)
            seen.add(sha)
            minibatch = score(child_vectors)
            entry.update(child=sha, accepted=rank(minibatch) > rank(score(parent_vectors)))
            record = Candidate.parse({
                'schema': CANDIDATE_SCHEMA, 'sha256': sha, 'parentSha256': parent, 'originPath': ORIGIN_PATH,
                'frontMatterSha256': front_sha, 'algorithm': 'gepa', 'round': rnd, 'optimizerCalls': [call_id],
                'optimizerTemplateSha256': template, 'contaminationCheck': [check],
                'devScore': {'minibatch': minibatch, 'full': None}, 'paretoMember': False, 'createdAt': _now(),
                'promotion': 'none', 'executionAuthorization': False}).to_dict()
            store.write_candidate_text(sha, body)
            store.append('candidate', Candidate.parse(record))
            if not entry['accepted']:
                continue
            if not charge(len(cases) * rollout['repetitions'] * hosts):
                break  # an accepted child whose full evaluation exceeds the budget is not evaluated
            full = self.evaluator(body, cases, rollout['repetitions'])
            state['rollouts'] += len(full)
            record = {**record, 'devScore': {'minibatch': minibatch, 'full': score(full)}, 'createdAt': _now()}
            store.append('candidate', Candidate.parse(record))
            pool[sha] = {'body': body, 'full': full, 'record': record}
            scores[sha] = per_case(full)
            refresh_front()

        best = max(pool, key=lambda sha: rank(score(pool[sha]['full'])))
        return {'algorithm': self.name, 'runId': run_id, 'seedSha256': seed_record.sha256, 'bestSha256': best,
                'bestFull': score(pool[best]['full']), 'seedFull': score(self.seed_vectors), 'front': list(front),
                'rounds': history, 'rollouts': state['rollouts'], 'optimizerCalls': len(self.optimizer.calls),
                'failedCalls': state['failedCalls'], 'stop': state['stop'], 'templateSha256': template,
                'rngSeed': self.rng_seed, 'executionAuthorization': False}
