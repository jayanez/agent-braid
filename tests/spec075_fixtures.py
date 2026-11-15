# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 test fixtures: a temporary Braid Lightning home with consent and rollouts of synthetic content."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from unittest.mock import patch

from agent_braid import lightning_store as store
from agent_braid.cli import main
from agent_braid.lightning_schema import EVENT_SCHEMA, RESULT_SCHEMA, Event, new_rollout

DIGEST = 'c' * 64
T0 = 1_800_000_000.0


def cli(*args):
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), patch('sys.stderr', err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


def consent(home: Path, level: str = 'redacted', sources: str = 'rollout') -> None:
    flags = ['lightning', 'init', '--home', str(home), '--non-interactive', '--trace-consent', level]
    if level == 'redacted':
        flags += ['--trace-sources', sources]
    _, out, _ = cli(*flags)
    code, _, err = cli(*flags, '--apply', '--preview-digest', json.loads(out)['previewDigest'])
    if code:
        raise AssertionError(err)


def _event(rollout, attempt, sequence, event_type, data):
    return Event.parse({'schema': EVENT_SCHEMA, 'rolloutId': rollout, 'attemptId': attempt, 'sequence': sequence,
                        'eventType': event_type, 'timestamp': T0 + sequence, 'data': data})


def result(run_id, rollout, attempt, label):
    return {'schema': RESULT_SCHEMA, 'runId': run_id, 'rolloutId': rollout, 'attemptId': attempt,
            'promptSet': 'development', 'promptSetSha256': DIGEST, 'hostVersion': 'fake', 'model': 'fake',
            'repetition': 1, 'keySource': 'none', 'credentialPresent': False, 'stop': None, 'refusal': None,
            'startedAt': '2027-01-15T00:00:00Z', 'endedAt': '2027-01-15T00:00:00Z', 'durationSeconds': 0,
            'transcriptSha256': DIGEST, 'rewardSha256': None, 'label': label, 'executionAuthorization': False,
            'parsedAttempts': []}


def rollout(run: store.RunStore, rollout_id: str, attempt: str, turns, *, task='task-a', group='group-g', d4=True,
            label='pipeline-only', start=0, created=None, status=None) -> None:
    """One attempt: a model_request per turn (prompt, response[, toolCalls]) with stored content, then a reward with
    component d4 (None: no reward event), an attempt result with `label` (None: no result record) and, with
    `status`, the rollout moved through running to that terminal state."""
    record = new_rollout(rollout_id, task, group, DIGEST, DIGEST, 'claude-code', at=T0)
    run.append('rollout', record)
    if status is not None:
        record = record.transition('running', T0 + 1, attempt_id=attempt)
        run.append('rollout', record)
        run.append('rollout', record.transition(status, T0 + 2))
    sequence = start
    for turn in turns:
        sequence += 1
        run.append('event', _event(rollout_id, attempt, sequence, 'model_request', {
            'requestSha256': DIGEST, 'responseSha256': DIGEST, 'latencyMs': 5, 'status': 'ok', 'retryCount': 0,
            'finishReason': None}))
        if turn is not None:
            body = {'attemptId': attempt, 'sequence': sequence, 'prompt': turn[0], 'response': turn[1]}
            if len(turn) > 2:
                body['toolCalls'] = turn[2]
            run.append('trace', body, now=(T0 if created is None else created) + sequence)
    if d4 is not None:
        sequence += 1
        run.append('event', _event(rollout_id, attempt, sequence, 'reward', {'reward': {
            'value': 1.0 if d4 else 0.0, 'components': {'schema': 1.0, 'd4': 1.0 if d4 else 0.0, 'canary': 1.0},
            'source': 'verifier', 'reason': None}}))
    if label is not None:
        run.append('result', result(run.run_id, rollout_id, attempt, label))


def new_run(home: Path, run_id: str = 'run-1', *, created: float = T0) -> store.RunStore:
    run = store.RunStore(home, run_id, content_consent='redacted')
    run.create(config_digest=DIGEST, now=created)
    return run
