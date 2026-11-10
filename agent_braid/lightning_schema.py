# SPDX-License-Identifier: AGPL-3.0-only
# Adapted from microsoft/agent-lightning agentlightning/schemas.py at commit
# bc3a9e80417d731744040df5d37117f9cc48005f (v1.0.3), Copyright (c) Microsoft
# Corporation, MIT License (LICENSES/Agent-Lightning-MIT.txt). Changes: Pydantic
# models replaced by frozen standard-library dataclasses with exact-key parsing;
# camelCase wire names; task and group identifiers added for rollout-level
# statistics; content-bearing payloads replaced by digests; Kubernetes fields
# removed. See docs/development/THIRD_PARTY.md.
"""Braid Lightning records: rollouts, attempts, events, rewards and models (SPEC-070 REQ-003).

Records carry identifiers, closed vocabularies, numbers and SHA-256 digests only. Prompt and response
text never appear here; content-bearing traces are a separate, consented contract (SPEC-074).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
import math
import re

ROLLOUT_SCHEMA = 'braid-lightning-rollout/v0.1'
EVENT_SCHEMA = 'braid-lightning-event/v0.1'
RESULT_SCHEMA = 'braid-lightning-attempt-result/v0.1'  # SPEC-071

QUEUING, RUNNING, SUCCEEDED, FAILED = 'queuing', 'running', 'succeeded', 'failed'
ROLLOUT_STATES = (QUEUING, RUNNING, SUCCEEDED, FAILED)
# Upstream VALID_TRANSITIONS: terminal states are final.
VALID_TRANSITIONS = {
    QUEUING: frozenset({RUNNING, FAILED}),
    RUNNING: frozenset({SUCCEEDED, FAILED}),
    SUCCEEDED: frozenset(),
    FAILED: frozenset(),
}
TERMINAL_STATES = frozenset({SUCCEEDED, FAILED})
DEFAULT_ATTEMPT_ID = '0'

HOSTS = ('claude-code', 'opencode')
EVENT_TYPES = ('attempt_start', 'model_request', 'tool_call', 'reward', 'attempt_end')
REWARD_SOURCES = ('verifier', 'fallback')
REQUEST_STATUSES = ('ok', 'error')
ATTEMPT_OUTCOMES = ('completed', 'refused', 'timeout', 'budget-stop', 'error')
MAX_COMPONENTS = 16

_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}')
_CODE = re.compile(r'[a-z][a-z0-9-]{0,63}')
_SHA = re.compile(r'[0-9a-f]{64}')


class LightningSchemaError(ValueError):
    """A Braid Lightning record is refused; `code` is a closed refusal bucket."""

    def __init__(self, message: str, code: str = 'record-shape'):
        super().__init__(message)
        self.code = code


def _exact(value, keys: set[str], where: str) -> dict:
    if not isinstance(value, dict):
        raise LightningSchemaError(f'{where} must be an object', 'record-type')
    unknown, missing = set(value) - keys, keys - set(value)
    if unknown:
        raise LightningSchemaError(f'{where} has unknown key(s): {", ".join(sorted(unknown))}', 'record-unknown-key')
    if missing:
        raise LightningSchemaError(f'{where} lacks key(s): {", ".join(sorted(missing))}', 'record-missing-key')
    return value


def _identifier(value, where: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise LightningSchemaError(f'{where} must be an identifier of 1-64 safe characters', 'record-identifier')
    return value


def _digest(value, where: str, *, optional: bool = False):
    if optional and value is None:
        return None
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise LightningSchemaError(f'{where} must be a lowercase SHA-256 digest', 'record-digest')
    return value


def _choice(value, options, where: str) -> str:
    if not isinstance(value, str) or value not in options:
        raise LightningSchemaError(f'{where} must be one of {", ".join(options)}', 'record-enum')
    return value


def _number(value, where: str, *, low: float | None = None, high: float | None = None) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise LightningSchemaError(f'{where} must be a finite number', 'record-type')
    if (low is not None and value < low) or (high is not None and value > high):
        raise LightningSchemaError(f'{where} is out of range', 'record-range')
    return float(value)


def _integer(value, where: str, *, low: int = 0, high: int = 2**31) -> int:
    if type(value) is not int or not low <= value <= high:
        raise LightningSchemaError(f'{where} must be an integer in [{low}, {high}]', 'record-range')
    return value


def _boolean(value, where: str) -> bool:
    if type(value) is not bool:
        raise LightningSchemaError(f'{where} must be a boolean', 'record-type')
    return value


def _code(value, where: str, *, optional: bool = False):
    if optional and value is None:
        return None
    if not isinstance(value, str) or not _CODE.fullmatch(value):
        raise LightningSchemaError(f'{where} must be a lowercase refusal code', 'record-code')
    return value


def canonical_bytes(value) -> bytes:
    """One JSON line: sorted keys, no whitespace, no NaN; the replay and hashing form."""
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False) + '\n').encode()


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise LightningSchemaError(f'Duplicate key {key}', 'record-duplicate')
        value[key] = item
    return value


def loads(raw: bytes | str):
    """Parse one record line, refusing duplicate keys and non-finite constants."""
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=lambda name: (_ for _ in ()).throw(
                              LightningSchemaError(f'Non-finite constant {name}', 'record-type')))
    except json.JSONDecodeError as exc:
        raise LightningSchemaError('Record is not valid JSON', 'record-json') from exc


@dataclass(frozen=True)
class ModelRef:
    """The host and model identity that served a call (upstream `Model`, keyed by host instead of endpoint)."""
    host: str
    model_id: str
    version: int = 0

    @classmethod
    def parse(cls, value, where: str = 'model') -> 'ModelRef':
        value = _exact(value, {'host', 'modelId', 'version'}, where)
        model_id = value['modelId']
        if not isinstance(model_id, str) or not 1 <= len(model_id) <= 128 or not model_id.isprintable():
            raise LightningSchemaError(f'{where}.modelId must be 1-128 printable characters', 'record-identifier')
        return cls(_choice(value['host'], HOSTS, f'{where}.host'), model_id,
                   _integer(value['version'], f'{where}.version'))

    def to_dict(self) -> dict:
        return {'host': self.host, 'modelId': self.model_id, 'version': self.version}


@dataclass(frozen=True)
class RolloutStatus:
    state: str = QUEUING
    last_attempt_id: str | None = None
    error_code: str | None = None
    version: int = 1
    created_at: float = 0.0
    updated_at: float = 0.0

    @classmethod
    def parse(cls, value, where: str = 'status') -> 'RolloutStatus':
        value = _exact(value, {'state', 'lastAttemptId', 'errorCode', 'version', 'createdAt', 'updatedAt'}, where)
        last = value['lastAttemptId']
        status = cls(_choice(value['state'], ROLLOUT_STATES, f'{where}.state'),
                     None if last is None else _identifier(last, f'{where}.lastAttemptId'),
                     _code(value['errorCode'], f'{where}.errorCode', optional=True),
                     _integer(value['version'], f'{where}.version', low=1),
                     _number(value['createdAt'], f'{where}.createdAt', low=0),
                     _number(value['updatedAt'], f'{where}.updatedAt', low=0))
        if status.updated_at < status.created_at:
            raise LightningSchemaError(f'{where}.updatedAt precedes createdAt', 'record-range')
        if status.error_code is not None and status.state != FAILED:
            raise LightningSchemaError(f'{where}.errorCode is only valid for failed rollouts', 'record-shape')
        return status

    def to_dict(self) -> dict:
        return {'state': self.state, 'lastAttemptId': self.last_attempt_id, 'errorCode': self.error_code,
                'version': self.version, 'createdAt': self.created_at, 'updatedAt': self.updated_at}


@dataclass(frozen=True)
class Rollout:
    """One unit of work: a candidate guidance evaluated on one task by one host (upstream `Rollout`)."""
    rollout_id: str
    task_id: str
    group_id: str
    candidate_sha256: str
    input_sha256: str
    host: str
    is_train: bool = True
    timeout_seconds: int = 300
    status: RolloutStatus = field(default_factory=RolloutStatus)

    @classmethod
    def parse(cls, value) -> 'Rollout':
        value = _exact(value, {'schema', 'rolloutId', 'taskId', 'groupId', 'candidateSha256', 'inputSha256',
                               'host', 'isTrain', 'timeoutSeconds', 'status'}, 'rollout')
        if value['schema'] != ROLLOUT_SCHEMA:
            raise LightningSchemaError('Unknown rollout schema', 'record-schema')
        return cls(_identifier(value['rolloutId'], 'rollout.rolloutId'), _identifier(value['taskId'], 'rollout.taskId'),
                   _identifier(value['groupId'], 'rollout.groupId'),
                   _digest(value['candidateSha256'], 'rollout.candidateSha256'),
                   _digest(value['inputSha256'], 'rollout.inputSha256'),
                   _choice(value['host'], HOSTS, 'rollout.host'), _boolean(value['isTrain'], 'rollout.isTrain'),
                   _integer(value['timeoutSeconds'], 'rollout.timeoutSeconds', low=1, high=86400),
                   RolloutStatus.parse(value['status'], 'rollout.status'))

    def to_dict(self) -> dict:
        return {'schema': ROLLOUT_SCHEMA, 'rolloutId': self.rollout_id, 'taskId': self.task_id,
                'groupId': self.group_id, 'candidateSha256': self.candidate_sha256,
                'inputSha256': self.input_sha256, 'host': self.host, 'isTrain': self.is_train,
                'timeoutSeconds': self.timeout_seconds, 'status': self.status.to_dict()}

    def transition(self, state: str, at: float, *, attempt_id: str | None = None,
                   error_code: str | None = None) -> 'Rollout':
        """Return the rollout in `state`; refuses transitions outside upstream VALID_TRANSITIONS."""
        _choice(state, ROLLOUT_STATES, 'state')
        if state not in VALID_TRANSITIONS[self.status.state]:
            raise LightningSchemaError(f'Invalid rollout transition {self.status.state} -> {state}', 'record-transition')
        if error_code is not None and state != FAILED:
            raise LightningSchemaError('errorCode is only valid for failed rollouts', 'record-shape')
        at = _number(at, 'at', low=self.status.updated_at)
        status = replace(self.status, state=state, version=self.status.version + 1, updated_at=at,
                         last_attempt_id=attempt_id if attempt_id is not None else self.status.last_attempt_id,
                         error_code=_code(error_code, 'errorCode', optional=True))
        if status.last_attempt_id is not None:
            _identifier(status.last_attempt_id, 'lastAttemptId')
        return replace(self, status=status)


def new_rollout(rollout_id: str, task_id: str, group_id: str, candidate_sha256: str, input_sha256: str,
                host: str, *, at: float, is_train: bool = True, timeout_seconds: int = 300) -> Rollout:
    value = {'schema': ROLLOUT_SCHEMA, 'rolloutId': rollout_id, 'taskId': task_id, 'groupId': group_id,
             'candidateSha256': candidate_sha256, 'inputSha256': input_sha256, 'host': host, 'isTrain': is_train,
             'timeoutSeconds': timeout_seconds,
             'status': {'state': QUEUING, 'lastAttemptId': None, 'errorCode': None, 'version': 1,
                        'createdAt': at, 'updatedAt': at}}
    return Rollout.parse(value)


@dataclass(frozen=True)
class Reward:
    """Verifiable reward (upstream `RewardData`): a scalar plus named components, never a judge opinion."""
    value: float
    components: tuple[tuple[str, float], ...]
    source: str
    reason: str | None = None

    @classmethod
    def parse(cls, value, where: str = 'reward') -> 'Reward':
        value = _exact(value, {'value', 'components', 'source', 'reason'}, where)
        components = value['components']
        if not isinstance(components, dict) or len(components) > MAX_COMPONENTS:
            raise LightningSchemaError(f'{where}.components must be an object of at most {MAX_COMPONENTS} entries', 'record-shape')
        parsed = tuple(sorted((_code(name, f'{where}.components key'),
                               _number(score, f'{where}.components.{name}', low=0, high=1))
                              for name, score in components.items()))
        return cls(_number(value['value'], f'{where}.value', low=0, high=1), parsed,
                   _choice(value['source'], REWARD_SOURCES, f'{where}.source'),
                   _code(value['reason'], f'{where}.reason', optional=True))

    def to_dict(self) -> dict:
        return {'value': self.value, 'components': dict(self.components), 'source': self.source, 'reason': self.reason}


_EVENT_DATA = {
    'attempt_start': {'host', 'model'},
    'model_request': {'requestSha256', 'responseSha256', 'latencyMs', 'status', 'retryCount', 'finishReason'},
    'tool_call': {'tool', 'argumentsSha256', 'resultSha256', 'status'},
    'reward': {'reward'},
    'attempt_end': {'outcome', 'turns'},
}


def _event_data(event_type: str, data) -> dict:
    data = _exact(data, _EVENT_DATA[event_type], f'{event_type}.data')
    if event_type == 'attempt_start':
        return {'host': _choice(data['host'], HOSTS, 'attempt_start.data.host'),
                'model': ModelRef.parse(data['model'], 'attempt_start.data.model').to_dict()}
    if event_type == 'model_request':
        return {'requestSha256': _digest(data['requestSha256'], 'model_request.data.requestSha256'),
                'responseSha256': _digest(data['responseSha256'], 'model_request.data.responseSha256', optional=True),
                'latencyMs': _number(data['latencyMs'], 'model_request.data.latencyMs', low=0),
                'status': _choice(data['status'], REQUEST_STATUSES, 'model_request.data.status'),
                'retryCount': _integer(data['retryCount'], 'model_request.data.retryCount', high=100),
                'finishReason': _code(data['finishReason'], 'model_request.data.finishReason', optional=True)}
    if event_type == 'tool_call':
        return {'tool': _identifier(data['tool'], 'tool_call.data.tool'),
                'argumentsSha256': _digest(data['argumentsSha256'], 'tool_call.data.argumentsSha256'),
                'resultSha256': _digest(data['resultSha256'], 'tool_call.data.resultSha256', optional=True),
                'status': _choice(data['status'], REQUEST_STATUSES, 'tool_call.data.status')}
    if event_type == 'reward':
        return {'reward': Reward.parse(data['reward'], 'reward.data.reward').to_dict()}
    return {'outcome': _choice(data['outcome'], ATTEMPT_OUTCOMES, 'attempt_end.data.outcome'),
            'turns': _integer(data['turns'], 'attempt_end.data.turns', high=1000)}


@dataclass(frozen=True)
class Event:
    """One event in an attempt, ordered by `sequence` (upstream `Event`, with a closed type vocabulary)."""
    rollout_id: str
    attempt_id: str
    sequence: int
    event_type: str
    timestamp: float
    data: dict

    @classmethod
    def parse(cls, value) -> 'Event':
        value = _exact(value, {'schema', 'rolloutId', 'attemptId', 'sequence', 'eventType', 'timestamp', 'data'}, 'event')
        if value['schema'] != EVENT_SCHEMA:
            raise LightningSchemaError('Unknown event schema', 'record-schema')
        event_type = _choice(value['eventType'], EVENT_TYPES, 'event.eventType')
        return cls(_identifier(value['rolloutId'], 'event.rolloutId'), _identifier(value['attemptId'], 'event.attemptId'),
                   _integer(value['sequence'], 'event.sequence'), event_type,
                   _number(value['timestamp'], 'event.timestamp', low=0), _event_data(event_type, value['data']))

    def to_dict(self) -> dict:
        return {'schema': EVENT_SCHEMA, 'rolloutId': self.rollout_id, 'attemptId': self.attempt_id,
                'sequence': self.sequence, 'eventType': self.event_type, 'timestamp': self.timestamp,
                'data': json.loads(json.dumps(self.data))}


PROMPT_SETS = ('development', 'held-out')
LABELS = ('pipeline-only', 'host-run')
BUDGET_STOPS = ('unit-cap', 'five-hour-headroom', 'weekly-stop', 'window-reset', 'window-reset-imminent')
REFUSALS = ('route-unverified', 'credential-leak', 'canary-hit', 'rollout-timeout', 'hook-failed', 'host-failed',
            'straggler-process')
_RFC3339 = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z')
_ATTEMPT_KEYS = {'kind', 'requestSha256', 'accepted', 'refusalSummary', 'request', 'report'}


def _text(value, where: str, *, optional: bool = True, limit: int = 128):
    if optional and value is None:
        return None
    if not isinstance(value, str) or not 1 <= len(value) <= limit or not value.isprintable():
        raise LightningSchemaError(f'{where} must be 1-{limit} printable characters', 'record-type')
    return value


def _parsed_attempt(value, where: str) -> dict:
    value = _exact(value, _ATTEMPT_KEYS, where)
    if value['kind'] is not None:
        _text(value['kind'], f'{where}.kind', limit=32)
    _digest(value['requestSha256'], f'{where}.requestSha256')
    _boolean(value['accepted'], f'{where}.accepted')
    _text(value['refusalSummary'], f'{where}.refusalSummary', limit=300)
    for key in ('request', 'report'):
        if value[key] is not None and not isinstance(value[key], (dict, list)):
            raise LightningSchemaError(f'{where}.{key} must be an object, a list or null', 'record-type')
    return json.loads(json.dumps(value))


@dataclass(frozen=True)
class AttemptResult:
    """Everything BL.1 records about one attempt of a rollout (SPEC-071 contracts/rollout-record.md)."""
    value: dict

    KEYS = frozenset({'schema', 'runId', 'rolloutId', 'attemptId', 'promptSet', 'promptSetSha256', 'hostVersion', 'model',
                      'repetition', 'keySource', 'credentialPresent', 'stop', 'refusal', 'startedAt', 'endedAt',
                      'durationSeconds', 'parsedAttempts', 'transcriptSha256', 'rewardSha256', 'label',
                      'executionAuthorization'})

    @classmethod
    def parse(cls, value) -> 'AttemptResult':
        value = _exact(value, set(cls.KEYS), 'result')
        if value['schema'] != RESULT_SCHEMA:
            raise LightningSchemaError('Unknown result schema', 'record-schema')
        if value['executionAuthorization'] is not False:
            raise LightningSchemaError('result.executionAuthorization is fixed to false', 'record-shape')
        for key in ('runId', 'rolloutId', 'attemptId'):
            _identifier(value[key], f'result.{key}')
        _choice(value['promptSet'], PROMPT_SETS, 'result.promptSet')
        _digest(value['promptSetSha256'], 'result.promptSetSha256')
        _text(value['hostVersion'], 'result.hostVersion')
        _text(value['model'], 'result.model')
        _integer(value['repetition'], 'result.repetition', low=1, high=100)
        _text(value['keySource'], 'result.keySource', limit=32)
        _boolean(value['credentialPresent'], 'result.credentialPresent')
        if value['stop'] is not None:
            _choice(value['stop'], BUDGET_STOPS, 'result.stop')
        if value['refusal'] is not None:
            _choice(value['refusal'], REFUSALS, 'result.refusal')
        for key in ('startedAt', 'endedAt'):
            if not isinstance(value[key], str) or not _RFC3339.fullmatch(value[key]):
                raise LightningSchemaError(f'result.{key} must be UTC RFC 3339', 'record-type')
        _number(value['durationSeconds'], 'result.durationSeconds', low=0)
        attempts = value['parsedAttempts']
        if not isinstance(attempts, list) or len(attempts) > 32:
            raise LightningSchemaError('result.parsedAttempts must be a list of at most 32 attempts', 'record-shape')
        parsed = [_parsed_attempt(item, f'result.parsedAttempts[{i}]') for i, item in enumerate(attempts)]
        _digest(value['transcriptSha256'], 'result.transcriptSha256')
        _digest(value['rewardSha256'], 'result.rewardSha256', optional=True)
        _choice(value['label'], LABELS, 'result.label')
        return cls(json.loads(json.dumps(dict(value, parsedAttempts=parsed))))

    def to_dict(self) -> dict:
        return json.loads(json.dumps(self.value))


def parse_record(value) -> Rollout | Event | AttemptResult:
    """Dispatch on the record's `schema`; anything else is refused."""
    if isinstance(value, dict) and value.get('schema') == ROLLOUT_SCHEMA:
        return Rollout.parse(value)
    if isinstance(value, dict) and value.get('schema') == EVENT_SCHEMA:
        return Event.parse(value)
    if isinstance(value, dict) and value.get('schema') == RESULT_SCHEMA:
        return AttemptResult.parse(value)
    raise LightningSchemaError('Unknown record kind', 'record-schema')
