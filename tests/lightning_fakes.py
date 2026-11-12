# SPDX-License-Identifier: AGPL-3.0-only
"""Test doubles for SPEC-072 algorithms: synthetic vectors carried by SPEC-071 attempt-result records."""
import hashlib
import json

from agent_braid.lightning_schema import RESULT_SCHEMA

ZERO = '0' * 64


def results(vector_fn):
    """Wrap ``vector_fn(body, case_ids, reps) -> [vector]`` into an evaluator returning attempt-result records whose
    first parsed attempt's report carries the vector (read back by ``scorer``)."""
    def evaluator(body, case_ids, reps):
        out = []
        for index, vector in enumerate(vector_fn(body, case_ids, reps)):
            key = json.dumps([body, case_ids, reps, index]).encode()
            attempt = 'a' + hashlib.sha256(key).hexdigest()[:20]
            out.append({
                'schema': RESULT_SCHEMA, 'runId': 'run', 'rolloutId': f"{vector['host']}.{vector['caseId']}.{index}",
                'attemptId': attempt, 'promptSet': 'development', 'promptSetSha256': ZERO, 'hostVersion': 'fake',
                'model': 'fake', 'repetition': 1, 'keySource': 'none', 'credentialPresent': False, 'stop': None,
                'refusal': None, 'startedAt': '2026-11-12T00:00:00Z', 'endedAt': '2026-11-12T00:00:00Z',
                'durationSeconds': 0, 'transcriptSha256': ZERO, 'rewardSha256': None, 'label': 'pipeline-only',
                'executionAuthorization': False,
                'parsedAttempts': [{'kind': 'analyze-work', 'requestSha256': ZERO, 'accepted': True,
                                    'refusalSummary': None, 'request': None, 'report': vector}]})
        return out
    return evaluator


def scorer(result):
    return dict(result['parsedAttempts'][0]['report'])
