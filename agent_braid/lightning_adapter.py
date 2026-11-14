# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 trace adapter: the consent gate (REQ-002, T003) and triplets and messages (REQ-006, T007).

Without consent `redacted` (a missing or invalid profile reads as `none`), or for a source the owner did not
list, the adapter emits only content-free records and reports why. Rollout records and the Loom stream become
`braid-lightning-triplet/v0.1` and `braid-lightning-messages/v0.1` records (contracts/triplet.md); every text
is redacted with the run salt and post-scanned. Host transcripts and System One are T008. The record
shapes follow agent-lightning v0.x `TracerTraceToTriplet`, `RewardMatchPolicy` and `TraceToMessages` so
SPEC-075 can export them; no upstream code is copied.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from . import lightning_config as config
from . import lightning_redact as redact
from . import lightning_store as store
from . import view_loom
from .lightning_schema import canonical_bytes

CONTENT_REFUSAL = 'content-consent-required'
SOURCE_REFUSAL = 'source-not-consented'
SOURCE_INVALID = 'source-invalid'
TRIPLET_SCHEMA = 'braid-lightning-triplet/v0.1'
MESSAGES_SCHEMA = 'braid-lightning-messages/v0.1'
REWARD_MATCHES = ('first-occurrence', 'first-sibling')  # upstream RewardMatchPolicy subset
_PLACEHOLDER = re.compile(r'\[REDACTED:([a-z-]+)')


class AdapterError(ValueError):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def _sources(home: Path | None) -> list[str]:
    try:
        value = config.load(home)
    except (ValueError, OSError):
        return []
    return [] if value is None else value['traces']['sources']


def gate(home: Path | None, source: str | None = None) -> dict:
    """Whether content may be read (from `source`, when given); `refusal` names the reason when it may not."""
    consent = store.content_consent(home)
    refusal = None
    if consent != 'redacted':
        refusal = CONTENT_REFUSAL
    elif source is not None and source not in _sources(home):
        refusal = SOURCE_REFUSAL
    return {'contentConsent': consent, 'source': source, 'content': refusal is None, 'refusal': refusal}


def require_content(home: Path | None, source: str) -> None:
    decision = gate(home, source)
    if decision['refusal'] == CONTENT_REFUSAL:
        raise AdapterError('Trace content needs consent redacted: agent-braid lightning init --trace-consent redacted',
                           CONTENT_REFUSAL)
    if decision['refusal']:
        raise AdapterError(f'Source {source} is not in traces.sources', SOURCE_REFUSAL)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _redaction(value) -> dict:
    """Placeholder counts per class in a redacted value; `scanClean` holds because `Redactor.clean` passed."""
    classes: dict[str, int] = {}
    for name in _PLACEHOLDER.findall(canonical_bytes(value).decode()):
        classes[name] = classes.get(name, 0) + 1
    return {'classes': dict(sorted(classes.items())), 'scanClean': True}


def _clean(redactor: redact.Redactor, value):
    try:
        return redactor.clean(value)
    except redact.RedactionError as exc:
        raise AdapterError(str(exc), exc.code) from exc


def _triplet(rollout_id, attempt_id, source, digest, prompt, response, reward, match, losses, created_at) -> dict:
    body = {'prompt': prompt, 'response': response}
    return {'schema': TRIPLET_SCHEMA, 'rolloutId': rollout_id, 'attemptId': attempt_id, 'source': source,
            'sourceSha256': digest, **body, 'reward': reward, 'rewardMatch': match,
            'redaction': _redaction(body), 'losses': sorted(set(losses)), 'createdAt': created_at}


def _messages(rollout_id, source, digest, messages, losses, created_at) -> dict:
    return {'schema': MESSAGES_SCHEMA, 'rolloutId': rollout_id, 'source': source, 'sourceSha256': digest,
            'messages': messages, 'redaction': _redaction(messages), 'losses': sorted(set(losses)),
            'createdAt': created_at}


def _match_rewards(requests: list, rewards: list, policy: str) -> dict:
    """Reward per request sequence: first-occurrence gives each reward to the nearest unrewarded request before it;
    first-sibling gives the attempt's first reward to its first request."""
    if policy not in REWARD_MATCHES:
        raise AdapterError(f"Reward match is one of {', '.join(REWARD_MATCHES)}", 'reward-match')
    if policy == 'first-sibling':
        return {requests[0].sequence: rewards[0].data['reward']['value']} if requests and rewards else {}
    matched, pending = {}, []
    events = sorted([(e.sequence, 0, e) for e in requests] + [(e.sequence, 1, e) for e in rewards])
    for _, is_reward, event in events:
        if not is_reward:
            pending.append(event.sequence)
        elif pending:
            matched[pending.pop()] = event.data['reward']['value']
    return matched


def _rollout_source(home: Path | None, run_id: str, attempt_id: str):
    run = store.RunStore(home, run_id)
    events = sorted((e for e in run.read('event') if e.attempt_id == attempt_id), key=lambda e: e.sequence)
    if not events:
        raise AdapterError(f'No events for attempt {attempt_id}', SOURCE_INVALID)
    return run, events


def _content_by_sequence(run, attempt_id: str) -> tuple[dict, list]:
    content, losses = {}, []
    for line in run.read_content():
        record = line.get('record')
        if record is None:
            losses.append('content-refused')
        elif isinstance(record, dict) and record.get('attemptId') == attempt_id:
            if record.get('sequence') in content:
                losses.append('content-duplicate')  # the first record for a request is kept
            else:
                content[record.get('sequence')] = (line['createdAt'], record)
    return content, losses


def rollout_triplets(home: Path | None, run_id: str, attempt_id: str, *,
                     reward_match: str = 'first-occurrence') -> list[dict]:
    """One triplet per `model_request` of an attempt; text comes from the run's content records (same sequence)."""
    return _rollout(home, run_id, attempt_id, reward_match)[0]


def _rollout(home, run_id, attempt_id, reward_match):
    run, events = _rollout_source(home, run_id, attempt_id)
    requests = [e for e in events if e.event_type == 'model_request']
    rewards = _match_rewards(requests, [e for e in events if e.event_type == 'reward'], reward_match)
    allowed = gate(home, 'rollout')['content']
    content, losses = _content_by_sequence(run, attempt_id) if allowed else ({}, ['content-consent-required'])
    redactor = redact.Redactor(run._salt()) if content else None
    digest = _sha(b''.join(canonical_bytes(e.to_dict()) for e in events)
                  + b''.join(sorted(canonical_bytes(c) for c in content.values())))
    triplets = []
    for event in requests:
        created_at, record = content.get(event.sequence, (event.timestamp, None))
        lost = list(losses)
        prompt = response = None
        if allowed and record is None:
            lost.append('content-missing')
        elif record is not None:
            body = _clean(redactor, {'prompt': record.get('prompt'), 'response': record.get('response'),
                                     'toolCalls': record.get('toolCalls', [])})
            prompt = None if body['prompt'] is None else {'text': body['prompt']}
            response = None if body['response'] is None else {'text': body['response'], 'toolCalls': body['toolCalls']}
            lost += [f'{name}-missing' for name in ('prompt', 'response') if body[name] is None]
        if event.sequence not in rewards:
            lost.append('reward-unmatched')
        triplets.append(_triplet(event.rollout_id, attempt_id, 'rollout', digest, prompt, response,
                                 rewards.get(event.sequence), reward_match, lost, created_at))
    return triplets, events[0].rollout_id, digest, losses


def rollout_messages(home: Path | None, run_id: str, attempt_id: str) -> dict:
    """User and assistant turns of an attempt, in event order (upstream TraceToMessages)."""
    triplets, rollout_id, digest, run_losses = _rollout(home, run_id, attempt_id, 'first-occurrence')
    messages, losses = [], set(run_losses)
    for triplet in triplets:
        losses.update(loss for loss in triplet['losses'] if loss != 'reward-unmatched')
        if triplet['prompt'] is not None:
            messages.append({'role': 'user', 'content': triplet['prompt']['text']})
        if triplet['response'] is not None:
            turn = {'role': 'assistant', 'content': triplet['response']['text']}
            if triplet['response']['toolCalls']:
                turn['toolCalls'] = triplet['response']['toolCalls']
            messages.append(turn)
    created = min((t['createdAt'] for t in triplets), default=None)
    return _messages(rollout_id, 'rollout', digest, messages, losses, created)


def _loom(home: Path | None, data: bytes, salt: bytes):
    if not isinstance(data, bytes):
        raise AdapterError('The Loom stream is bytes', SOURCE_INVALID)
    try:
        events = view_loom.parse_stream(data)
    except view_loom.LoomError as exc:
        raise AdapterError(f'Loom stream refused: {exc.reason}', SOURCE_INVALID) from exc
    digest = _sha(data)
    allowed = gate(home, 'loom')['content']
    return events, digest, f'loom-{digest[:16]}', (redact.Redactor(salt) if allowed else None)


def loom_messages(home: Path | None, data: bytes, salt: bytes) -> dict:
    """One `system` message per Loom event (its kind and data); empty without consent."""
    events, digest, rollout_id, redactor = _loom(home, data, salt)
    if redactor is None:
        return _messages(rollout_id, 'loom', digest, [], ['content-consent-required'], None)
    messages = [{'role': 'system', 'content': _clean(redactor, canonical_bytes(
        {'kind': e['kind'], 'data': e['data']}).decode())} for e in events]
    return _messages(rollout_id, 'loom', digest, messages, [], None)


def loom_triplets(home: Path | None, data: bytes, salt: bytes) -> list[dict]:
    """One triplet per strand: its label as the prompt, its tools and outcome as the response; Loom has no reward."""
    events, digest, rollout_id, redactor = _loom(home, data, salt)
    strands: dict[str, dict] = {}
    for event in events:
        body = event['data']
        if not event['kind'].startswith('strand.'):
            continue
        strand = strands.setdefault(body['strandId'], {'label': None, 'tools': [], 'outcome': None})
        if event['kind'] == 'strand.open':
            strand['label'] = body['label']
        elif event['kind'] == 'strand.update' and body.get('toolName'):
            strand['tools'].append(body['toolName'])
        elif event['kind'] == 'strand.close':
            strand['outcome'] = body['outcome']
    triplets = []
    for strand_id, strand in strands.items():
        losses = ['reward-unavailable', 'model-text-unavailable']
        prompt = response = None
        if redactor is None:
            losses.append('content-consent-required')
        else:
            body = _clean(redactor, strand)
            prompt = None if body['label'] is None else {'text': body['label']}
            response = {'text': body['outcome'] or '', 'toolCalls': body['tools']}
            if body['outcome'] is None:
                losses.append('outcome-missing')
        triplets.append(_triplet(rollout_id, strand_id, 'loom', digest, prompt, response, None,
                                 None, losses, None))
    return triplets
