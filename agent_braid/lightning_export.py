# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 dataset export (BL.5): consented, redacted Braid Lightning traces to local datasets.

T003 (REQ-002): the input boundary. Content is read only through the SPEC-074 adapter
(`lightning_adapter.rollout_triplets`); content-free rollout records name each attempt's task and group. Every
model call either survives the consent and redaction filter or is counted under one exclusion reason, never
dropped silently (E1). Raw attempt ids stay in memory: records carry the adapter's `attempt-<hmac16>` pseudonym,
and refusals carry fixed texts and codes with no chained cause. Standard library only; no network or process.

T004 (REQ-003): the `supervised` writer. Each attempt's outcome comes from its content-free reward event (component
`d4`: 1.0 success, 0.0 failure, otherwise `unknown`) and its source from its attempt result (`pipeline-only` is a
`fixture`; anything else, or no result, is `host-model`, failing closed for the terms gate).
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

from . import lightning_adapter as adapter
from . import lightning_store as store
from .lightning_schema import canonical_bytes

LEVELS = ('transition', 'trajectory')
ROLES = ('system', 'user', 'assistant', 'tool')
ORDERING_KEY = ('taskId', 'groupId', 'rolloutId', 'attemptId', 'turnIndex')
_RECORD_ID = re.compile(r'r-[0-9a-f]{16}')
EXCLUSION_REASONS = ('no-consent', 'consent-none', 'unredacted', 'content-missing', 'balance', 'overlong',
                     'retention-expired')


class ExportError(ValueError):
    """An export is refused; `code` is a closed refusal code and the text names no source value."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def empty_exclusions() -> dict[str, int]:
    return {reason: 0 for reason in EXCLUSION_REASONS}


# SPEC-074 gate refusal (or the same loss note on a triplet) -> exclusion reason, checked in this order. A missing
# or unreadable profile reads as consent none, so it is `consent-none`; `no-consent` is a source not listed.
_GATE_REASONS = {adapter.CONTENT_REFUSAL: 'consent-none', adapter.SOURCE_REFUSAL: 'no-consent'}
_CODE = re.compile(r'[a-z][a-z0-9-]{0,63}')


def exclusion_reason(triplet, gate_refusal: str | None = None) -> str | None:
    """Why an adapter triplet cannot be exported, or None. Consent reasons come first (E1).

    `gate_refusal` is the SPEC-074 gate's refusal for the triplet's source when it was read. It is needed because
    the rollout reader notes `content-consent-required` both without consent and for an unlisted source.
    """
    if gate_refusal is not None:
        return _GATE_REASONS.get(gate_refusal, 'no-consent')
    if not isinstance(triplet, dict):
        return 'unredacted'
    losses = triplet.get('losses') if isinstance(triplet.get('losses'), list) else []
    for loss, reason in _GATE_REASONS.items():
        if loss in losses:
            return reason
    redaction = triplet.get('redaction')
    if triplet.get('schema') != adapter.TRIPLET_SCHEMA or not isinstance(redaction, dict) \
            or redaction.get('scanClean') is not True or not isinstance(redaction.get('classes'), dict):
        return 'unredacted'
    if not isinstance(triplet.get('prompt'), dict) or not isinstance(triplet.get('response'), dict):
        return 'content-missing'
    return None


def select(items: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """Keep the exportable items, in order, and count each excluded one by reason."""
    kept, exclusions = [], empty_exclusions()
    for item in items:
        reason = exclusion_reason(item.get('triplet'), item.get('gateRefusal'))
        if reason is None:
            kept.append(item)
        else:
            exclusions[reason] += 1
    return kept, exclusions


def _tasks(run: store.RunStore) -> dict[str, tuple[str, str]]:
    return {r.rollout_id: (r.task_id, r.group_id) for r in run.read('rollout')}


def _code(exc: Exception, fallback: str) -> str:
    code = getattr(exc, 'code', None)
    return code if isinstance(code, str) and _CODE.fullmatch(code) else fallback


def read_runs(home: Path | None, run_ids: list[str]) -> list[dict]:
    """One item per model call of every attempt in the runs: source ids, its turn index and the adapter triplet.

    Any failure to read a run becomes an ExportError with a fixed text and code, without a chained cause, so no
    path, id or parser message leaves this function.
    """
    if len(set(run_ids)) != len(run_ids):
        raise ExportError('A run is named more than once', 'invalid-argument')
    # Read once here to name the reason. The adapter re-reads the gate for every attempt and fails closed: if the
    # profile changes mid-export, its triplets carry the refusal loss and are excluded all the same.
    refusal = adapter.gate(home, 'rollout')['refusal']
    items = []
    for run_id in run_ids:
        try:
            items += _read_run(home, run_id, refusal)
        except ExportError:
            raise
        except adapter.AdapterError as exc:
            raise ExportError('Adapter refused a source', _code(exc, 'source-invalid')) from None
        except OSError:
            raise ExportError('Run refused', 'store-unreadable') from None
        except (ValueError, TypeError, AttributeError, KeyError) as exc:  # StoreError and RegistryError included
            raise ExportError('Run refused', _code(exc, 'store-shape')) from None
    return items


def _outcome(reward) -> str:
    d4 = reward['components'].get('d4') if reward else None
    return 'success' if d4 == 1.0 else 'failure' if d4 == 0.0 else 'unknown'


def _read_run(home: Path | None, run_id: str, refusal: str | None) -> list[dict]:
    run = store.RunStore(home, run_id)
    tasks = _tasks(run)
    attempts: dict[str, set[str]] = {}
    rewards: dict[str, tuple] = {}
    for event in run.read('event'):
        attempts.setdefault(event.attempt_id, set()).add(event.rollout_id)
        if event.event_type == 'reward' and event.sequence >= rewards.get(event.attempt_id, (-1,))[0]:
            rewards[event.attempt_id] = (event.sequence, event.data['reward'])  # the attempt's last reward
    labels = {(r.value['rolloutId'], r.value['attemptId']): r.value['label'] for r in run.read('result')}
    items = []
    for attempt_id in sorted(attempts):
        rollouts = attempts[attempt_id]
        if len(rollouts) != 1:  # the adapter reads by attempt, so a shared attempt id would mix two rollouts
            raise ExportError('An attempt spans more than one rollout', 'source-invalid')
        rollout_id = next(iter(rollouts))
        if rollout_id not in tasks:
            raise ExportError('A rollout has events but no rollout record', 'source-invalid')
        task_id, group_id = tasks[rollout_id]
        reward = rewards.get(attempt_id, (None, None))[1]
        source = 'fixture' if labels.get((rollout_id, attempt_id)) == 'pipeline-only' else 'host-model'
        for index, triplet in enumerate(adapter.rollout_triplets(home, run_id, attempt_id)):
            items.append({'runId': run_id, 'taskId': task_id, 'groupId': group_id, 'rolloutId': rollout_id,
                          'attemptId': triplet['attemptId'], 'turnIndex': index, 'gateRefusal': refusal,
                          'outcome': _outcome(reward), 'reward': reward, 'source': source, 'triplet': triplet})
    return items


def _sort_key(item: dict) -> tuple:
    return tuple(item[key] for key in ORDERING_KEY)


def _units(items: list[dict], level: str) -> list[list[dict]]:
    """Export units in E3 order: one model call each (`transition`) or the kept calls of an attempt (`trajectory`)."""
    if level not in LEVELS:
        raise ExportError(f"Level is one of {', '.join(LEVELS)}", 'invalid-argument')
    ordered = sorted(items, key=_sort_key)
    if level == 'transition':
        return [[item] for item in ordered]
    units: dict[tuple, list[dict]] = {}
    for item in ordered:
        units.setdefault((item['runId'], *_sort_key(item)[:4]), []).append(item)
    return sorted(units.values(), key=lambda unit: _sort_key(unit[0]))


def _messages(unit: list[dict]) -> list[dict]:
    messages = []
    for item in unit:
        triplet = item['triplet']
        messages.append({'role': 'user', 'content': triplet['prompt']['text']})
        turn = {'role': 'assistant', 'content': triplet['response']['text']}
        if triplet['response'].get('toolCalls'):
            turn['toolCalls'] = triplet['response']['toolCalls']
        messages.append(turn)
    return messages


def _record_id(record: dict, first: dict, turn_range: list[int]) -> str:
    """`r-` plus 16 hex of the record without its id and its source position, so equal texts get distinct ids."""
    body = {'record': record, 'source': [first['runId'], first['rolloutId'], first['attemptId'], turn_range]}
    return 'r-' + hashlib.sha256(canonical_bytes(body)).hexdigest()[:16]


def _entry(unit: list[dict], record_id: str, line: bytes, turn_range: list[int], limits: list[str]) -> dict:
    first = unit[0]
    return {'recordId': record_id, 'sha256': hashlib.sha256(line).hexdigest(), 'runId': first['runId'],
            'taskId': first['taskId'], 'groupId': first['groupId'], 'rolloutId': first['rolloutId'],
            'attemptId': first['attemptId'], 'turnRange': turn_range, 'consentLevel': 'redacted',
            'source': first['source'], 'outcome': first['outcome'], 'limits': limits}


def check_supervised(record, *, outcome_field: bool = False) -> None:
    """Refuse a supervised record that does not have the contract shape (`invalid-record`)."""
    keys = {'recordId', 'messages', 'outcome'} if outcome_field else {'recordId', 'messages'}
    ok = isinstance(record, dict) and set(record) == keys and isinstance(record.get('recordId'), str) \
        and _RECORD_ID.fullmatch(record['recordId']) is not None and isinstance(record.get('messages'), list) \
        and len(record['messages']) > 0 and (not outcome_field or record['outcome'] in ('success', 'failure', 'unknown'))
    for message in record.get('messages', []) if ok else []:
        allowed = {'role', 'content', 'toolCalls', 'toolCallId'}
        ok = ok and isinstance(message, dict) and message.get('role') in ROLES \
            and isinstance(message.get('content'), str) and set(message) <= allowed \
            and (message['role'] == 'tool') == ('toolCallId' in message) \
            and ('toolCalls' not in message or message['role'] == 'assistant')
    if not ok:
        raise ExportError('A supervised record does not have the contract shape', 'invalid-record')


def supervised(items: list[dict], *, level: str, outcome_field: bool = False) -> tuple[list[bytes], list[dict], int]:
    """`supervised` lines and manifest record entries, in E3 order, plus how many units the d4 filter left out.

    Without `outcome_field` only units whose attempt passed D4 on the first attempt (`success`) are written;
    with it every unit is written and carries its `outcome`. Supervised exports are never balanced (E4).
    """
    if type(outcome_field) is not bool:
        raise ExportError('outcome_field is true or false', 'invalid-argument')
    lines, entries, left_out = [], [], 0
    for unit in _units(items, level):
        if not outcome_field and unit[0]['outcome'] != 'success':
            left_out += 1
            continue
        turn_range = [unit[0]['turnIndex'], unit[-1]['turnIndex']]
        record = {'messages': _messages(unit)}
        if outcome_field:
            record['outcome'] = unit[0]['outcome']
        record = {'recordId': _record_id(record, unit[0], turn_range), **record}
        check_supervised(record, outcome_field=outcome_field)
        line = canonical_bytes(record)
        lines.append(line)
        entries.append(_entry(unit, record['recordId'], line, turn_range,
                              ['text-level-merge'] if len(unit) > 1 else []))
    return lines, entries, left_out
