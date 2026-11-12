# SPDX-License-Identifier: AGPL-3.0-only
# Beam search with textual gradients adapted from microsoft/agent-lightning agentlightning/algorithm/apo/apo.py at
# commit 6db3c73dc0af2e50fe80e56873a57c1703f1b2a7 (v0.x), Copyright (c) Microsoft Corporation, MIT License
# (LICENSES/Agent-Lightning-MIT.txt). Changes: synchronous; one critique per parent and `branchFactor` edits from
# it (SPEC-072 feasibility table) instead of one critique per branch; parents are the whole beam (never replicated
# or sampled) and each candidate is scored on its round's minibatch; critiques see content-free reward vectors,
# never traces; one template per role (variant01) instead of a random variant; every call goes through the runner's
# OptimizerChannel; budgets and the 3-round cap stop the run. See docs/development/THIRD_PARTY.md.
"""APO for Braid Lightning (SPEC-072 REQ-004): ProTeGi-style beam search over the analyze skill body."""
from __future__ import annotations

import hashlib
import json

from . import lightning_runner as runner_mod
from .lightning_algorithm import (PROMPTS, QUOTA_STOPS, Algorithm, Session, Stagnation, _now, experiments, rank,
                                  render, rescore, score)
from .lightning_resources import CANDIDATE_SCHEMA, ORIGIN_PATH, MAX_TEXT, Candidate, sha256_text

MAX_ROUNDS = 3  # ProTeGi-style optimization overfits after about 3 steps (SPEC-072 REQ-007)
TEMPLATES = {'gradient': PROMPTS / 'apo_text_gradient.md', 'edit': PROMPTS / 'apo_apply_edit.md'}


def template_hashes() -> dict[str, str]:
    return {role: hashlib.sha256(path.read_bytes()).hexdigest() for role, path in sorted(TEMPLATES.items())}


def template_set_sha256() -> str:
    """One digest for the critique and edit templates together (the candidate's optimizerTemplateSha256)."""
    return hashlib.sha256(json.dumps(template_hashes(), sort_keys=True).encode()).hexdigest()


def _key(node: dict) -> tuple[float, float]:
    return rank(node['score'])


class APO(Algorithm):
    """Beam search with textual gradients; the evaluator runs rollouts for a candidate body on development cases.

    ``evaluator(body, case_ids, repetitions) -> [attempt-result record]`` (SPEC-071, development cases only);
    ``scorer(record)`` re-scores a record into a vector ``{caseId, host, d4FirstAttempt, schemaValid, reasons,
    refusal}`` (default: ``rescore``); ``seed_vectors`` are the seed's full development vectors from the SPEC-071
    baseline run (not charged to the arm).
    """
    name = 'apo'

    def __init__(self, *, evaluator, optimizer: runner_mod.OptimizerChannel, seed_vectors: list[dict],
                 scorer=rescore):
        if not isinstance(optimizer, runner_mod.OptimizerChannel):
            raise runner_mod.RunnerError('Optimizer calls must go through the runner', 'optimizer-bypass')
        self.evaluator = evaluator
        self.optimizer = optimizer
        self.seed_vectors = list(seed_vectors)
        self.scorer = scorer

    def run(self, home, config: dict, *, run_id: str, resume: bool = False, replay: bool = False,
            **_ignored) -> dict:
        algo, rollout = config['algorithm'], config['rollout']
        cases = [c['id'] for c in json.loads(
            (runner_mod.checkout_root() / runner_mod.PROMPT_FILES['development']).read_text())['cases']]
        store, seed_record, seed_body, front_sha = self.start(home, config, run_id, self.seed_vectors, resume=resume)
        session = Session(store, config, self.optimizer, self.evaluator, resume=resume, scorer=self.scorer,
                          replay=replay)
        stagnation = Stagnation()
        template_sha = template_set_sha256()

        seen = {seed_record.sha256}
        beam = [{'sha': seed_record.sha256, 'body': seed_body, 'vectors': [], 'score': None}]
        history = []
        rounds = min(algo['rounds'], MAX_ROUNDS)
        size = min(algo['minibatch'], len(cases))
        failed_calls = 0
        for rnd in range(1, rounds + 1):
            parents = len(beam)
            start = ((rnd - 1) * size) % len(cases)
            batch = [cases[(start + i) % len(cases)] for i in range(size)]
            if beam[0]['sha'] == seed_record.sha256 and beam[0]['score'] is None:
                beam[0]['vectors'] = [v for v in self.seed_vectors if v['caseId'] in batch]
                beam[0]['score'] = score(beam[0]['vectors'])
            children = []
            for parent in list(beam):
                critique = session.call(render(TEMPLATES['gradient'], prompt_template=parent['body'],
                                               experiments=experiments(parent['vectors'])))
                if critique is None:
                    break
                critique_id, critique_text, critique_check = critique
                if not critique_text.strip():
                    failed_calls += 1
                    continue
                for _ in range(algo['branchFactor']):
                    edit = session.call(render(TEMPLATES['edit'], prompt_template=parent['body'],
                                               critique=critique_text))
                    if edit is None:
                        break
                    edit_id, body, edit_check = edit
                    sha = sha256_text(body)
                    if not body.strip() or len(body.encode('utf-8')) > MAX_TEXT or sha in seen:
                        failed_calls += 1  # not a usable skill body: a failed call, no candidate
                        continue
                    vectors = session.evaluate(body, batch, 1)
                    if vectors is None:
                        break
                    seen.add(sha)
                    node = {'sha': sha, 'body': body, 'vectors': vectors, 'score': score(vectors),
                            'parent': parent['sha'], 'round': rnd, 'calls': [critique_id, edit_id],
                            'checks': [critique_check, edit_check]}
                    store.write_candidate_text(sha, body)
                    self.record(store, self._record(node, front_sha, template_sha, None))
                    children.append(node)
                if session.stop:
                    break
            beam = sorted(beam + children, key=_key, reverse=True)[:algo['beamWidth']]
            history.append({'round': rnd, 'minibatch': batch, 'parents': parents,
                            'children': [c['sha'] for c in children], 'beam': [n['sha'] for n in beam]})
            if session.stop:
                break
            if stagnation.update(_key(beam[0])) and rnd < rounds:
                session.stop = 'no-improvement'
                break

        optimized = [n for n in beam if n['sha'] != seed_record.sha256]
        best = max(optimized, key=_key) if optimized else None
        if best is not None and session.refusal is None and session.stop not in (*QUOTA_STOPS, 'replay-diverged'):
            stop = session.stop
            session.stop = None  # a search stop still allows the final evaluation within budget
            full = session.evaluate(best['body'], cases, rollout['repetitions'])
            session.stop = session.stop or stop
            if full is not None:
                self.record(store, self._record(best, front_sha, template_sha, score(full)))
                best['full'] = score(full)
        return {'algorithm': self.name, 'runId': run_id, 'seedSha256': seed_record.sha256,
                'bestSha256': best['sha'] if best else None, 'bestFull': best.get('full') if best else None,
                'seedFull': score(self.seed_vectors), 'rounds': history, 'failedCalls': failed_calls,
                'templates': template_hashes(), 'templateSetSha256': template_sha, **session.finish(run_id),
                'executionAuthorization': False}

    def _record(self, node: dict, front_sha: str, template_sha: str, full: dict | None) -> Candidate:
        return Candidate.parse({
            'schema': CANDIDATE_SCHEMA, 'sha256': node['sha'], 'parentSha256': node['parent'], 'originPath': ORIGIN_PATH,
            'frontMatterSha256': front_sha, 'algorithm': 'apo', 'round': node['round'], 'optimizerCalls': node['calls'],
            'optimizerTemplateSha256': template_sha, 'contaminationCheck': node['checks'],
            'devScore': {'minibatch': node['score'], 'full': full}, 'paretoMember': False, 'createdAt': _now(),
            'promotion': 'none', 'executionAuthorization': False})
