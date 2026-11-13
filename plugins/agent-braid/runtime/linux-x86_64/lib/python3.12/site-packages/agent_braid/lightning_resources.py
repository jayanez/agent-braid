# SPDX-License-Identifier: AGPL-3.0-only
# Candidate role adapted from microsoft/agent-lightning agentlightning/types/resources.py (PromptTemplate) at commit
# 6db3c73dc0af2e50fe80e56873a57c1703f1b2a7 (v0.x), Copyright (c) Microsoft Corporation, MIT License
# (LICENSES/Agent-Lightning-MIT.txt). Changes: Pydantic resource replaced by an exact-key, content-addressed
# record (sha256, parent, origin, algorithm lineage, contamination checks); the template text is stored beside
# the record, never inside it; no template engine. See docs/development/THIRD_PARTY.md.
"""Versioned prompt candidates for Braid Lightning optimization (SPEC-072 REQ-002).

A candidate is the whole body of the analyze skill below its fixed front matter (SPEC-072 P3). The record
carries digests, lineage and scores only; the text lives in `candidates/<sha256>.md` beside the run.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .lightning_schema import (LightningSchemaError, _RFC3339, _boolean, _choice, _digest, _exact, _identifier,
                               _integer, _number)

CANDIDATE_SCHEMA = 'braid-lightning-candidate/v0.1'
ORIGIN_PATH = 'integrations/agent-braid/skills/agent-braid-analyze/SKILL.md'
ALGORITHMS = ('baseline', 'apo', 'gepa')
MAX_TEXT = 64 * 1024
MAX_CALLS = 64
# Fields a later record for the same sha256 may change; every other field identifies the candidate.
EVALUATIVE = frozenset({'devScore', 'paretoMember', 'createdAt'})


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def split_skill(raw: str) -> tuple[str, str]:
    """Split a skill file into its front matter (with both fences) and the candidate body."""
    if not isinstance(raw, str) or not raw.startswith('---\n'):
        raise LightningSchemaError('Skill file lacks front matter', 'candidate-front-matter')
    end = raw.find('\n---\n', 4)
    if end < 0:
        raise LightningSchemaError('Skill front matter is not closed', 'candidate-front-matter')
    return raw[:end + 5], raw[end + 5:]


def check_text(text: str, sha256: str) -> str:
    """Return `text` if it is the candidate body named by `sha256`; refuse otherwise."""
    if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > MAX_TEXT:
        raise LightningSchemaError('Candidate text must be non-empty and at most 64 KiB', 'candidate-text')
    if sha256_text(text) != sha256:
        raise LightningSchemaError('Candidate text does not match its sha256', 'candidate-hash-mismatch')
    return text


def _score(value, where: str):
    if value is None:
        return None
    value = _exact(value, {'d4FirstAttempt', 'schemaValid', 'rollouts'}, where)
    _number(value['d4FirstAttempt'], f'{where}.d4FirstAttempt', low=0, high=1)
    _number(value['schemaValid'], f'{where}.schemaValid', low=0, high=1)
    _integer(value['rollouts'], f'{where}.rollouts', low=1, high=10_000)
    return value


@dataclass(frozen=True)
class Candidate:
    """One `braid-lightning-candidate/v0.1` record (SPEC-072 contracts/candidate.md)."""
    value: dict

    KEYS = frozenset({'schema', 'sha256', 'parentSha256', 'originPath', 'frontMatterSha256', 'algorithm', 'round',
                      'optimizerCalls', 'optimizerTemplateSha256', 'contaminationCheck', 'devScore', 'paretoMember',
                      'createdAt', 'promotion', 'executionAuthorization'})

    @classmethod
    def parse(cls, value) -> 'Candidate':
        value = _exact(value, set(cls.KEYS), 'candidate')
        if value['schema'] != CANDIDATE_SCHEMA:
            raise LightningSchemaError('Unknown candidate schema', 'record-schema')
        if value['promotion'] != 'none' or value['executionAuthorization'] is not False:
            raise LightningSchemaError('Candidates carry no promotion or execution authority', 'record-shape')
        _digest(value['sha256'], 'candidate.sha256')
        parent = _digest(value['parentSha256'], 'candidate.parentSha256', optional=True)
        if value['originPath'] != ORIGIN_PATH:
            raise LightningSchemaError('candidate.originPath must be the analyze skill', 'candidate-origin')
        _digest(value['frontMatterSha256'], 'candidate.frontMatterSha256')
        algorithm = _choice(value['algorithm'], ALGORITHMS, 'candidate.algorithm')
        round_ = _integer(value['round'], 'candidate.round', high=100)
        calls = value['optimizerCalls']
        if not isinstance(calls, list) or len(calls) > MAX_CALLS or len(set(calls)) != len(calls):
            raise LightningSchemaError('candidate.optimizerCalls must be a list of distinct call ids', 'record-shape')
        for index, call in enumerate(calls):
            _identifier(call, f'candidate.optimizerCalls[{index}]')
        template = _digest(value['optimizerTemplateSha256'], 'candidate.optimizerTemplateSha256', optional=True)
        checks = value['contaminationCheck']
        if not isinstance(checks, list) or len(checks) != len(calls):
            raise LightningSchemaError('candidate.contaminationCheck needs one entry per optimizer call', 'record-shape')
        for index, check in enumerate(checks):
            where = f'candidate.contaminationCheck[{index}]'
            check = _exact(check, {'inputSha256', 'passed'}, where)
            _digest(check['inputSha256'], f'{where}.inputSha256')
            if _boolean(check['passed'], f'{where}.passed') is not True:
                raise LightningSchemaError('A candidate cannot come from a refused optimizer call',
                                           'holdout-contamination')
        if parent is None and (round_ != 0 or calls or algorithm != 'baseline'):
            raise LightningSchemaError('Only the round-0 baseline seed has no parent', 'candidate-lineage')
        if parent is not None and (round_ == 0 or not calls or algorithm == 'baseline'):
            raise LightningSchemaError('An optimized candidate needs a parent, a round and optimizer calls',
                                       'candidate-lineage')
        if parent == value['sha256']:
            raise LightningSchemaError('A candidate cannot be its own parent', 'candidate-lineage')
        if (template is None) != (not calls):
            raise LightningSchemaError('optimizerTemplateSha256 is set exactly when optimizer calls exist',
                                       'candidate-lineage')
        score = value['devScore']
        if score is not None:
            score = _exact(score, {'minibatch', 'full'}, 'candidate.devScore')
            _score(score['minibatch'], 'candidate.devScore.minibatch')
            _score(score['full'], 'candidate.devScore.full')
        if _boolean(value['paretoMember'], 'candidate.paretoMember') and algorithm != 'gepa':
            raise LightningSchemaError('paretoMember is GEPA only', 'record-shape')
        if not isinstance(value['createdAt'], str) or not _RFC3339.fullmatch(value['createdAt']):
            raise LightningSchemaError('candidate.createdAt must be UTC RFC 3339', 'record-type')
        return cls(json.loads(json.dumps(value)))

    @property
    def sha256(self) -> str:
        return self.value['sha256']

    def to_dict(self) -> dict:
        return json.loads(json.dumps(self.value))


def seed(skill_raw: str, *, created_at: str, dev_score: dict | None = None) -> tuple[Candidate, str]:
    """The round-0 baseline candidate and its body from the analyze skill bytes (contracts/candidate.md)."""
    front, body = split_skill(skill_raw)
    record = Candidate.parse({
        'schema': CANDIDATE_SCHEMA, 'sha256': sha256_text(body), 'parentSha256': None, 'originPath': ORIGIN_PATH,
        'frontMatterSha256': sha256_text(front), 'algorithm': 'baseline', 'round': 0, 'optimizerCalls': [],
        'optimizerTemplateSha256': None, 'contaminationCheck': [], 'devScore': dev_score, 'paretoMember': False,
        'createdAt': created_at, 'promotion': 'none', 'executionAuthorization': False})
    return record, check_text(body, record.sha256)


def latest(records: list[Candidate]) -> dict[str, Candidate]:
    """Latest record per sha256; later records may change only devScore, paretoMember and createdAt."""
    found: dict[str, Candidate] = {}
    for record in records:
        previous = found.get(record.sha256)
        if previous is not None:
            identity = {k: v for k, v in previous.value.items() if k not in EVALUATIVE}
            if identity != {k: v for k, v in record.value.items() if k not in EVALUATIVE}:
                raise LightningSchemaError('A later candidate record changed identifying fields',
                                           'candidate-immutable')
        found[record.sha256] = record
    for record in found.values():
        parent = record.value['parentSha256']
        if parent is not None and parent not in found:
            raise LightningSchemaError('Candidate parent is not recorded in this run', 'candidate-lineage')
    return found
