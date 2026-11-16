# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 dataset export (BL.5): consented, redacted Braid Lightning traces to local datasets.

T003 (REQ-002): the input boundary. Content is read only through the SPEC-074 adapter
(`lightning_adapter.rollout_triplets`); content-free rollout records name each attempt's task and group. Every
model call either survives the consent and redaction filter or is counted under one exclusion reason, never
dropped silently (E1). Raw attempt ids stay in memory: records carry the adapter's `attempt-<hmac16>` pseudonym,
and refusals carry fixed texts and codes with no chained cause. Standard library only; no network or process.

T004 (REQ-003): the `supervised` writer. Each attempt's outcome comes from its content-free reward event (component
`d4`: 1.0 success, 0.0 failure, otherwise `unknown`) and its source from its attempt results (`fixture` only when
every result is labelled `pipeline-only`; otherwise, or with no result, `host-model`). OD-1 is deferred, so the
writer refuses any host-model unit with `terms-gate-missing` before writing anything; T008 replaces that refusal
with the owner terms-decision check. Lines are `trace_adapter.canonical_bytes(record)` plus a newline (E3).

T005 (REQ-004): the `rollout` writer. A record carries the attempt's turns (redacted prompt, response and tool
calls), its SPEC-071 reward vector unchanged and the rollout's latest status. `transition` writes one record per
model call; `trajectory` one per attempt (a rollout has one attempt: VALID_TRANSITIONS allows no retry, and
`read_runs` refuses a rollout with two), merged by token-ID prefix only when every turn carries token IDs that
chain (never for hosted Claude Code or OpenCode, whose triplets carry none), else at text level with the limit
`text-level-merge` (E2). Token IDs never enter a record. The T004 input and terms checks apply unchanged.

T006 (REQ-005, REQ-006): the manifest and the export. `export_dataset` reads, filters and writes the records, scans
the dataset bytes with the SPEC-074 post-redaction scan, builds `braid-lightning-dataset-manifest/v0.1`, checks
it (`check_manifest`: the rules the schema cannot express) and writes `records.jsonl` then `manifest.json` into a
private temporary directory that is renamed into place, so a refusal leaves no output. `redactionVersion` names the
SPEC-074 redactor by a digest of its pattern sources and salt size (SPEC-074 records carry no version; the digest
does not cover the redactor's code). `generatedAt` is outside the digest; nothing else depends on the clock or the
working directory. The SPEC-074 redactor replaces the current `$HOME` with `~` when the adapter reads content, so the
bytes are reproducible for the same `$HOME` at ingest and export, not across different ones. A crash between the
temporary directory and the rename can leave a `.export-*` directory beside the output; it holds only that export's
files and is the owner's to delete.

T007 (REQ-007): `balance equal`, the default for `rollout` exports (E4, OD-2): per task, keep `min(successes,
failures)` attempts of each outcome, chosen by a seeded hash rank of [seed, taskId, runId, rolloutId], so the same
data and seed keep the same attempts, also after a re-ingest with a new salt. Attempts are kept or dropped whole;
dropped model calls count as `balance` exclusions. Tasks with one outcome keep nothing and are reported, never
padded; attempts without a reward (`unknown`) cannot be paired and are dropped and reported. `supervised` exports are never balanced.

T008 (REQ-008): the terms gate (E5, OD-1). Every non-fixture unit needs an owner terms decision record under
`<plugin home>/lightning/terms/`, named by its relative path; the record binds a host and the exact model ids it
covers, names the provider, the terms version or URL, the review date, a `validUntil` date and the outcome. Only
`permits-training`, on the export day inside the record's dates, for a unit whose host and model the record lists,
lets the unit through; anything else refuses with `terms-gate-missing` before anything is written, and the manifest
cites the record's relative path and SHA-256. No record ships with Agent Braid: OD-1 is deferred.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

from . import lightning_adapter as adapter
from . import lightning_config as config
from . import plugin_registry as registry
from . import lightning_redact as redact
from . import lightning_store as store
from .trace_adapter import canonical_bytes as _canonical

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


def _tasks(run: store.RunStore) -> dict[str, tuple[str, str, str, str]]:
    """Task, group, latest state and host per rollout id (the record with the highest status version)."""
    latest: dict[str, object] = {}
    for record in run.read('rollout'):
        if record.rollout_id not in latest or record.status.version >= latest[record.rollout_id].status.version:
            latest[record.rollout_id] = record
    return {rid: (r.task_id, r.group_id, r.status.state, r.host) for rid, r in latest.items()}


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
    models: dict[str, set] = {}
    for event in run.read('event'):
        if event.event_type == 'attempt_start':
            models.setdefault(event.attempt_id, set()).add(event.data['model']['modelId'])
        attempts.setdefault(event.attempt_id, set()).add(event.rollout_id)
        if event.event_type == 'reward' and event.sequence >= rewards.get(event.attempt_id, (-1,))[0]:
            rewards[event.attempt_id] = (event.sequence, event.data['reward'])  # the attempt's last reward
    labels: dict[tuple, set] = {}
    for result in run.read('result'):
        labels.setdefault((result.value['rolloutId'], result.value['attemptId']), set()).add(result.value['label'])
    per_rollout: dict[str, int] = {}
    for rollouts in attempts.values():
        for rollout_id in rollouts:
            per_rollout[rollout_id] = per_rollout.get(rollout_id, 0) + 1
    if any(count > 1 for count in per_rollout.values()):  # VALID_TRANSITIONS allows no retry: one attempt each
        raise ExportError('A rollout has more than one attempt', 'source-invalid')
    items = []
    for attempt_id in sorted(attempts):
        rollouts = attempts[attempt_id]
        if len(rollouts) != 1:  # the adapter reads by attempt, so a shared attempt id would mix two rollouts
            raise ExportError('An attempt spans more than one rollout', 'source-invalid')
        rollout_id = next(iter(rollouts))
        if rollout_id not in tasks:
            raise ExportError('A rollout has events but no rollout record', 'source-invalid')
        task_id, group_id, status, host = tasks[rollout_id]
        model = next(iter(models[attempt_id])) if len(models.get(attempt_id, ())) == 1 else None
        reward = rewards.get(attempt_id, (None, None))[1]
        # fail closed: one host-run result (or none at all) makes the attempt host-model output
        source = 'fixture' if labels.get((rollout_id, attempt_id)) == {'pipeline-only'} else 'host-model'
        for index, triplet in enumerate(adapter.rollout_triplets(home, run_id, attempt_id)):
            items.append({'runId': run_id, 'taskId': task_id, 'groupId': group_id, 'rolloutId': rollout_id,
                          'attemptId': triplet['attemptId'], 'turnIndex': index, 'gateRefusal': refusal,
                          'outcome': _outcome(reward), 'reward': reward, 'status': status, 'source': source,
                          'host': host, 'model': model, 'triplet': triplet})
    return items


def line_bytes(record) -> bytes:
    """One dataset line: the contract's `trace_adapter.canonical_bytes(record)` followed by a newline."""
    return _canonical(record) + b'\n'


def _sort_key(item: dict) -> tuple:
    return (*(item[key] for key in ORDERING_KEY), item['runId'])  # runId breaks ties across runs


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
    return 'r-' + hashlib.sha256(_canonical(body)).hexdigest()[:16]


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
            and ('toolCalls' not in message or (message['role'] == 'assistant' and isinstance(message['toolCalls'], list)))
    if not ok:
        raise ExportError('A supervised record does not have the contract shape', 'invalid-record')


_ITEM_KEYS = frozenset({'runId', 'taskId', 'groupId', 'rolloutId', 'attemptId', 'turnIndex', 'outcome', 'reward',
                        'status', 'source', 'host', 'model', 'triplet'})


def _check_items(items, terms: dict | None = None) -> None:
    """Writers accept only selected items (E1) and non-fixture content only under a covering terms decision (E5)."""
    if not isinstance(items, list) or not all(isinstance(i, dict) and _ITEM_KEYS <= set(i) for i in items):
        raise ExportError('Export items come from read_runs', 'invalid-argument')
    if any(exclusion_reason(i['triplet'], i.get('gateRefusal')) is not None for i in items):
        raise ExportError('Export items must pass the consent and redaction filter first', 'invalid-argument')
    if any(i['source'] != 'fixture' and not _covered(terms, i) for i in items):
        raise ExportError('Host-model output needs an owner terms decision', 'terms-gate-missing')


def _covered(terms: dict | None, item: dict) -> bool:
    """A non-fixture unit passes only when the validated record permits training for its host and exact model."""
    return terms is not None and terms['outcome'] == 'permits-training' and item['host'] == terms['host'] \
        and item['model'] is not None and item['model'] in terms['models']


def supervised(items: list[dict], *, level: str, outcome_field: bool = False,
               terms: dict | None = None) -> tuple[list[bytes], list[dict], int]:
    """`supervised` lines and manifest record entries, in E3 order, plus how many units the d4 filter left out.

    Without `outcome_field` only units whose attempt passed D4 on the first attempt (`success`) are written;
    with it every unit is written and carries its `outcome`. Supervised exports are never balanced (E4).
    """
    if type(outcome_field) is not bool:
        raise ExportError('outcome_field is true or false', 'invalid-argument')
    _check_items(items, terms)
    units, left_out = [], 0
    for unit in _units(items, level):
        if outcome_field or unit[0]['outcome'] == 'success':
            units.append(unit)
        else:
            left_out += 1

    def build(unit):
        record = {'messages': _messages(unit)}
        if outcome_field:
            record['outcome'] = unit[0]['outcome']
        return record

    lines, entries = _write(units, build, lambda record: check_supervised(record, outcome_field=outcome_field))
    return lines, entries, left_out


def _limits(unit: list[dict]) -> list[str]:
    """`text-level-merge` when a unit merges more than one call without a token-ID prefix chain (E2)."""
    return [] if len(unit) == 1 or _token_prefix_merge(unit) else ['text-level-merge']


def _write(units: list[list[dict]], build, check) -> tuple[list[bytes], list[dict]]:
    """Lines and manifest entries for units: `build` makes the record body, `check` refuses a wrong shape."""
    lines, entries = [], []
    for unit in units:
        first = unit[0]
        turn_range = [first['turnIndex'], unit[-1]['turnIndex']]
        record = build(unit)
        record = {'recordId': _record_id(record, first, turn_range), **record}
        check(record)
        line = line_bytes(record)
        lines.append(line)
        entries.append(_entry(unit, record['recordId'], line, turn_range, _limits(unit)))
    return lines, entries


_ATTEMPT_ID = re.compile(r'(attempt|turn|strand|episode)-[0-9a-f]{16}')
_STATES = ('queuing', 'running', 'succeeded', 'failed')
_REWARD_KEYS = {'value', 'components', 'source', 'reason'}


def check_rollout(record) -> None:
    """Refuse a rollout record that does not have the contract shape (`invalid-record`)."""
    keys = {'recordId', 'rolloutId', 'attemptId', 'turns', 'reward', 'status'}
    ok = isinstance(record, dict) and set(record) == keys and isinstance(record['recordId'], str) \
        and _RECORD_ID.fullmatch(record['recordId']) is not None and isinstance(record['rolloutId'], str) \
        and isinstance(record['attemptId'], str) and _ATTEMPT_ID.fullmatch(record['attemptId']) is not None \
        and record['status'] in _STATES and isinstance(record['turns'], list) and len(record['turns']) > 0 \
        and (record['reward'] is None or (isinstance(record['reward'], dict) and set(record['reward']) == _REWARD_KEYS))
    for turn in record['turns'] if ok else []:
        ok = ok and isinstance(turn, dict) and set(turn) == {'prompt', 'response', 'toolCalls'} \
            and isinstance(turn['prompt'], str) and isinstance(turn['response'], str) \
            and isinstance(turn['toolCalls'], list)
    if not ok:
        raise ExportError('A rollout record does not have the contract shape', 'invalid-record')


def _tokens(part) -> list | None:
    value = part.get('tokenIds') if isinstance(part, dict) else None
    return value if isinstance(value, list) and value and all(type(t) is int for t in value) else None


def _token_prefix_merge(unit: list[dict]) -> bool:
    """True when the unit's calls are consecutive, every one carries token IDs and each prompt extends the previous
    prompt and response (E2). A call excluded from the middle breaks the chain even if the tokens still line up."""
    previous, index = None, None
    for item in unit:
        prompt, response = _tokens(item['triplet']['prompt']), _tokens(item['triplet']['response'])
        if prompt is None or response is None or (previous is not None and (
                item['turnIndex'] != index + 1 or prompt[:len(previous)] != previous)):
            return False
        previous, index = prompt + response, item['turnIndex']
    return True


def rollout_records(items: list[dict], *, level: str, terms: dict | None = None) -> tuple[list[bytes], list[dict]]:
    """`rollout` lines and manifest record entries, in E3 order. Balance is applied separately (T007)."""
    _check_items(items, terms)

    def build(unit):
        first = unit[0]
        turns = [{'prompt': i['triplet']['prompt']['text'], 'response': i['triplet']['response']['text'],
                  'toolCalls': i['triplet']['response'].get('toolCalls', [])} for i in unit]
        return {'rolloutId': first['rolloutId'], 'attemptId': first['attemptId'], 'turns': turns,
                'reward': first['reward'], 'status': first['status']}

    return _write(_units(items, level), build, check_rollout)


MANIFEST_VERSION = 'braid-lightning-dataset-manifest/v0.1'
KINDS = ('supervised', 'rollout')
BALANCES = ('equal', 'none')
RECORDS_FILE, MANIFEST_FILE = 'records.jsonl', 'manifest.json'
LIMITS = ('text-level-merge', 'truncated')


def redaction_version() -> str:
    """`spec074-redact/` plus 16 hex of the SPEC-074 redactor's pattern sources and salt size (no secret in it)."""
    patterns = [redact.PRIVATE_KEY, redact.BEARER, *redact.TOKENS, redact.B64_RUN, redact.ESCAPED, redact.WORD,
                redact.EMAIL, *redact.SECRET_PATTERNS]
    source = '\n'.join([f'{p.flags}:{p.pattern}' for p in patterns] + [f'salt:{redact.SALT_BYTES}'])
    return 'spec074-redact/' + hashlib.sha256(source.encode()).hexdigest()[:16]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_digest(manifest: dict) -> str:
    """SHA-256 of the canonical manifest without `generatedAt` and `digest`."""
    return _sha(_canonical({k: v for k, v in manifest.items() if k not in ('generatedAt', 'digest')}))


def _utc(now: float) -> str:
    return datetime.fromtimestamp(now, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _day(when: float) -> str:
    return datetime.fromtimestamp(when, timezone.utc).strftime('%Y-%m-%d')


def check_manifest(manifest: dict, records: bytes, sources: dict, terms: dict | None = None) -> None:
    """The builder checks the schema cannot express; `sources` maps (runId, rolloutId, attemptId) to the source
    read from the store. Refuses with `invalid-manifest`."""
    def fail(why: str):
        raise ExportError(f'Manifest refused: {why}', 'invalid-manifest')

    lines = records.splitlines(keepends=True)
    entries = manifest['records']
    if manifest['recordsSha256'] != _sha(records) or len(lines) != len(entries):
        fail('records hash')
    for line, entry in zip(lines, entries):
        try:
            line_id = json.loads(line)['recordId']
        except (ValueError, TypeError, KeyError):
            line_id = None
        if entry['sha256'] != _sha(line) or line_id != entry['recordId']:
            fail('record hash')
        if entry['turnRange'][0] > entry['turnRange'][1]:
            fail('turn range')
        if entry['limits'] != sorted(set(entry['limits'])):
            fail('limits')
        key = (entry['runId'], entry['rolloutId'], entry['attemptId'])
        if sources.get(key) != entry['source']:
            fail('source')  # never a host-model record labelled fixture (or the other way)
        if entry['source'] == 'host-model' and manifest['termsDecision'] is None:
            fail('terms decision')
    if set(manifest['retention']) != {entry['runId'] for entry in entries}:
        fail('retention')
    _check_balance(manifest, fail)
    cited = manifest['termsDecision']
    if cited is not None and (terms is None or cited != {'path': terms['path'], 'sha256': terms['sha256']}):
        fail('terms decision')  # the cited record must be the one the gate read and verified
    if manifest['kind'] == 'supervised' and (manifest['balance'] != 'none' or manifest['exclusions']['balance']):
        fail('supervised balance')
    if manifest['canaryScan'] != 'clean' or manifest['digest'] != manifest_digest(manifest):
        fail('digest')


def _check_balance(manifest: dict, fail) -> None:
    """The E4 arithmetic: each report row is consistent and the dataset holds exactly the attempts it says it kept."""
    report = manifest['balanceReport']
    tasks = [row['taskId'] for row in report]
    if len(tasks) != len(set(tasks)):
        fail('balance report')
    if manifest['kind'] == 'rollout' and (manifest['balance'] == 'equal') != bool(report):
        fail('balance report')  # equal reports every task; none reports nothing
    kept: dict[str, dict[str, set]] = {}
    for entry in manifest['records']:
        kept.setdefault(entry['taskId'], {}).setdefault(entry['outcome'], set()).add(
            (entry['runId'], entry['rolloutId'], entry['attemptId']))
    for row in report:
        least = min(row['successes'], row['failures'])
        single = (row['successes'] == 0) != (row['failures'] == 0)
        attempts = kept.get(row['taskId'], {})
        if row['keptPerOutcome'] != least or row['singleOutcome'] != single \
                or row['dropped'] != row['successes'] + row['failures'] + row['unknown'] - 2 * least \
                or len(attempts.get('success', ())) != least or len(attempts.get('failure', ())) != least \
                or attempts.get('unknown'):
            fail('balance report')
    if report and set(kept) - set(tasks):
        fail('balance report')


def build_manifest(entries: list[dict], records: bytes, *, kind: str, level: str, seed: int, balance: str,
                   exclusions: dict, balance_report: list, retention: dict, generated_at: str,
                   sources: dict, terms_decision: dict | None = None, terms: dict | None = None) -> dict:
    manifest = {
        'manifestVersion': MANIFEST_VERSION, 'kind': kind, 'level': level, 'generatedAt': generated_at,
        'seed': seed, 'balance': balance, 'orderingKey': list(ORDERING_KEY), 'redactionVersion': redaction_version(),
        # canaryScan is 'clean' by construction: scan() runs on these bytes before any write and refuses on a hit
        'termsDecision': terms_decision, 'canaryScan': 'clean', 'exclusions': dict(exclusions),
        'balanceReport': balance_report, 'retention': retention, 'records': entries,
        'recordsSha256': _sha(records),
    }
    manifest['digest'] = manifest_digest(manifest)
    check_manifest(manifest, records, sources, terms)
    return manifest


# OD-3 Q1 A: another user's home directory (the SPEC-074 redactor knows only the current one, which it turns into ~).
# Anywhere in the bytes, inside longer paths too, any case (macOS paths are case-insensitive), any name segment;
# fail closed: `/srv/home/x` and URL paths such as `/api/users/42` block as well (OD-3 Q1 A).
OTHER_HOME = re.compile(r'/(?:users|home)/[^\s/\\"\'<>,;:|]+', re.IGNORECASE)


def _decoded(text: str) -> list[str]:
    """A text and the decoded views SPEC-074 scans: URL, \\u escapes and base64 runs."""
    return [text, redact.unquote(text), redact._unescape(text),
            *(redact._b64(match.group(0)) for match in redact.B64_RUN.finditer(text))]


def _views(text: str) -> list[str]:
    """The bytes as text, each field alone and each two neighbouring fields joined (a value split across two
    fields is seen whole), every one with its decoded views."""
    pieces = [text]
    for line in text.splitlines():
        leaves = redact._leaves(json.loads(line))
        pieces += leaves + [left + right for left, right in zip(leaves, leaves[1:])]
    return [view for piece in pieces for view in _decoded(piece)]


def scan(data: bytes) -> None:
    """REQ-010: refuse with `canary-detected` when the final bytes (dataset and manifest) hold a SPEC-074 class
    (token, bearer, private key, e-mail, the current `$HOME`) or another user's home path, in any decoded view.

    Literal secrets the ingest was not given and secrets of unknown shape are not detected (OD-3 Q2 A). The scan
    uses `Path.home()`: a hit on the current home means it escaped the redaction SPEC-074 applied on read.
    """
    scanner = redact.Redactor(b'\0' * redact.SALT_BYTES, home=Path.home())
    try:
        views = _views(data.decode('ascii'))
    except (UnicodeDecodeError, ValueError):
        raise ExportError('The dataset bytes are not canonical', 'canary-detected') from None
    if any(scanner.scan(view) or OTHER_HOME.search(view) for view in views):
        raise ExportError('The dataset holds a value the canary scan flags', 'canary-detected')


def _retention_days(home: Path | None) -> int:
    """The profile's `traces.retentionDays` (1-90); no readable bound refuses fail-closed (`retention-expired`)."""
    try:
        value = config.load(home)
        days = value['traces']['retentionDays'] if value is not None else None
    except (OSError, ValueError, TypeError, KeyError):
        days = None
    if type(days) is not int or not 1 <= days <= 90:
        raise ExportError('No retention bound for the source runs', 'retention-expired')
    return days


def _run_expiry(home: Path | None, run_ids, days: int) -> dict[str, float]:
    """Epoch second each run expires: its `createdAt` plus the retention, the same cutoff SPEC-074's sweep uses."""
    out = {}
    for run_id in sorted(run_ids):
        try:
            created = store.RunStore(home, run_id).manifest()['createdAt']
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise ExportError('Run refused', _code(exc, 'store-shape')) from None
        out[run_id] = created + days * 86400
    return out


def drop_expired(items: list[dict], expiry: dict[str, float], now: float) -> tuple[list[dict], int]:
    """REQ-013: keep the items whose source run has not expired at `now` (epoch seconds, so no time zone enters);
    a run expires at the instant `createdAt + retentionDays` days, inclusive, as SPEC-074's sweep removes it."""
    kept = [item for item in items if now < expiry[item['runId']]]
    return kept, len(items) - len(kept)


def _retention(expiry: dict[str, float], days: int, run_ids) -> dict:
    return {run_id: {'retentionDays': days, 'expiresAt': _day(expiry[run_id])} for run_id in sorted(run_ids)}


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def check_output(out: Path) -> Path:
    """The output must be a canonical path (no symbolic link in any component, no traversal) whose parent is an
    existing directory, and must not exist or be an empty directory."""
    out = Path(out)
    try:
        out = registry._safe(out)
        parent_ok = out.parent.is_dir()
    except (OSError, ValueError):
        parent_ok = None
    if parent_ok is None:
        raise ExportError('The output path must be canonical, without symbolic links', 'path-refused')
    if not parent_ok:
        raise ExportError('The output directory must be inside an existing directory', 'path-refused')
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ExportError('The output directory must not exist or must be empty', 'output-not-empty')
    return out


def write_export(out: Path, records: bytes, manifest: dict) -> None:
    """Write `records.jsonl`, then `manifest.json`, into a private temporary directory renamed onto `out`."""
    out = check_output(out)
    try:
        temporary = Path(tempfile.mkdtemp(prefix='.export-', dir=out.parent))
    except OSError:
        raise ExportError('The output directory cannot be created', 'path-refused') from None
    try:
        for name, data in ((RECORDS_FILE, records), (MANIFEST_FILE, line_bytes(manifest))):
            fd = os.open(temporary / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        os.rename(temporary, out)  # POSIX: replaces an empty directory, never a non-empty one
    except OSError:
        shutil.rmtree(temporary, ignore_errors=True)
        raise ExportError('The export could not be written', 'path-refused') from None
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    try:
        _fsync_dir(out.parent)  # make the rename durable; the export is complete either way
    except OSError:
        pass


def _check_seed(seed) -> None:
    if type(seed) is not int or seed < 0:
        raise ExportError('The seed is an integer of at least 0', 'invalid-argument')


def _rank(seed: int, task_id: str, item: dict) -> str:
    """The draw key: no attempt pseudonym (it changes with each ingest's salt). A rollout has one attempt, so
    [runId, rolloutId] names the attempt; the same data and seed give the same selection across re-ingests."""
    key = [seed, task_id, item['runId'], item['rolloutId']]
    return hashlib.sha256(_canonical(key)).hexdigest()


def balance_equal(items: list[dict], *, seed: int) -> tuple[list[dict], list[dict], int]:
    """Equal 1:1 balance per task (E4, OD-2): the kept items, the balance report and the dropped model calls."""
    _check_seed(seed)
    attempts: dict[str, dict[tuple, list[dict]]] = {}
    for item in items:
        attempts.setdefault(item['taskId'], {}).setdefault(
            (item['runId'], item['rolloutId'], item['attemptId']), []).append(item)
    kept, report = [], []
    for task_id in sorted(attempts):
        by_outcome: dict[str, list[list[dict]]] = {'success': [], 'failure': [], 'unknown': []}
        for calls in attempts[task_id].values():
            by_outcome[calls[0]['outcome']].append(calls)
        keep = min(len(by_outcome['success']), len(by_outcome['failure']))
        for outcome in ('success', 'failure'):
            chosen = sorted(by_outcome[outcome], key=lambda calls: _rank(seed, task_id, calls[0]))[:keep]
            kept += [item for calls in chosen for item in calls]
        total = sum(len(v) for v in by_outcome.values())
        report.append({'taskId': task_id, 'successes': len(by_outcome['success']),
                       'failures': len(by_outcome['failure']), 'unknown': len(by_outcome['unknown']),
                       'keptPerOutcome': keep, 'dropped': total - 2 * keep,
                       'singleOutcome': (len(by_outcome['success']) == 0) != (len(by_outcome['failure']) == 0)})
    return kept, report, len(items) - len(kept)


def export_dataset(home: Path | None, run_ids: list[str], *, kind: str, level: str, out: Path, seed: int = 0,
                   balance: str | None = None, outcome_field: bool = False, now: float | None = None,
                   terms_decision: str | None = None, dry_run: bool = False) -> dict:
    """Export the runs as one dataset and return its manifest (nothing is written on any refusal).

    `balance` defaults to `equal` for `rollout` and is always `none` for `supervised` (E4).
    """
    balancing = balance
    if balancing is None and kind in KINDS:
        balancing = 'equal' if kind == 'rollout' else 'none'
    if kind not in KINDS or balancing not in BALANCES or (kind == 'supervised' and balancing != 'none') \
            or (kind == 'rollout' and outcome_field):
        raise ExportError('Invalid export arguments', 'invalid-argument')
    _check_seed(seed)
    check_output(out)  # before any read, so a bad output path refuses at once (and in a dry run)
    now = datetime.now(timezone.utc).timestamp() if now is None else now
    terms = None if terms_decision is None else load_terms_decision(home, terms_decision, today=_day(now))
    days = _retention_days(home)
    kept, exclusions = select(read_runs(home, run_ids))
    _check_items(kept, terms)  # the terms gate sees every candidate, before retention or balance can drop any
    expiry = _run_expiry(home, {item['runId'] for item in kept}, days)
    kept, expired = drop_expired(kept, expiry, now)
    exclusions['retention-expired'] += expired
    if expired and not kept:
        raise ExportError('Every record is past its source retention', 'retention-expired')
    report = []
    if balancing == 'equal':
        kept, report, dropped = balance_equal(kept, seed=seed)
        exclusions['balance'] += dropped
    if kind == 'supervised':
        lines, entries, _ = supervised(kept, level=level, outcome_field=outcome_field, terms=terms)
    else:
        lines, entries = rollout_records(kept, level=level, terms=terms)
    if not lines:
        raise ExportError('Nothing to export', 'no-records')
    records = b''.join(lines)
    sources = {(i['runId'], i['rolloutId'], i['attemptId']): i['source'] for i in kept}
    manifest = build_manifest(entries, records, kind=kind, level=level, seed=seed, balance=balancing,
                              exclusions=exclusions, balance_report=report,
                              retention=_retention(expiry, days, {e['runId'] for e in entries}),
                              generated_at=_utc(now), sources=sources,
                              terms_decision=None if terms is None or all(e['source'] == 'fixture' for e in entries)
                              else {'path': terms['path'], 'sha256': terms['sha256']}, terms=terms)
    scan(records + line_bytes(manifest))  # the final bytes, after balance and the manifest, before the rename
    if not dry_run:
        entry = _register(home, out, manifest)  # before the rename: an unregistered dataset is never written
        try:
            write_export(out, records, manifest)
        except BaseException:
            entry.unlink(missing_ok=True)
            raise
    return manifest


EXPORTS_DIRECTORY = 'exports'
EXPORT_ENTRY_SCHEMA = 'braid-lightning-export-entry/v0.1'


def _exports(home: Path | None) -> Path:
    return config.directory(home) / EXPORTS_DIRECTORY


def _register(home: Path | None, out: Path, manifest: dict) -> Path:
    """Record where a dataset was written, in the private `lightning/exports/` index, so `lightning purge` can list
    the datasets that cite a purged run (REQ-013). The entry holds the output path, the manifest digest and the cited
    run ids; no content."""
    directory = _exports(home)
    entry = {'schema': EXPORT_ENTRY_SCHEMA, 'out': str(check_output(out)), 'digest': manifest['digest'],
             'runIds': sorted(manifest['retention'])}
    try:
        registry._safe(directory, directory=True)
        directory.mkdir(mode=0o700, exist_ok=True)
        registry._private(directory, directory=True)
        path = directory / f"{manifest['digest']}-{hashlib.sha256(entry['out'].encode()).hexdigest()[:16]}.json"
        fd = os.open(registry._safe(path, directory=False), os.O_CREAT | os.O_TRUNC | os.O_WRONLY | os.O_NOFOLLOW,
                     0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(line_bytes(entry))
            stream.flush()
            os.fsync(stream.fileno())
    except (OSError, ValueError):
        raise ExportError('The export index cannot be written', 'path-refused') from None
    return path


def citing_manifests(home: Path | None, run_ids) -> list[dict]:
    """The exported datasets whose manifest still exists, still matches its digest and cites one of `run_ids`.

    Datasets are outside purge: the owner deletes them. Unreadable, moved or changed exports are left out.
    """
    wanted, found = set(run_ids), []
    directory = _exports(home)
    try:
        registry._safe(directory, directory=True)
        if not directory.is_dir():
            return []
        registry._private(directory, directory=True)
        names = sorted(p.name for p in directory.iterdir() if p.suffix == '.json')
    except (OSError, ValueError):
        return []
    for name in names:
        try:
            entry = json.loads((directory / name).read_bytes())
            out = Path(entry['out'])
            manifest = json.loads((out / MANIFEST_FILE).read_bytes())
            if entry.get('schema') != EXPORT_ENTRY_SCHEMA or manifest.get('digest') != entry['digest'] \
                    or manifest_digest(manifest) != entry['digest']:
                continue
            cited = sorted(wanted & set(manifest['retention']))
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            continue
        if cited:
            found.append({'manifest': str(out / MANIFEST_FILE), 'digest': entry['digest'], 'citesRuns': cited})
    return sorted(found, key=lambda item: item['manifest'])


TERMS_SCHEMA = 'braid-lightning-terms-decision/v0.1'
TERMS_DIRECTORY = 'terms'
TERMS_OUTCOMES = ('permits-training', 'forbids-training', 'undecided')  # only the first lets units through
_TERMS_PATH = re.compile(r'terms/[A-Za-z0-9][A-Za-z0-9._-]{0,127}\.json')
_DATE = re.compile(r'[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])')
_TEXT = re.compile(r'[^\x00-\x1f\x7f]{1,256}')
_MAX_TERMS_BYTES = 16 * 1024


def _valid_date(value) -> bool:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        return False
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        return False
    return True


def load_terms_decision(home: Path | None, relative: str, *, today: str) -> dict:
    """Read and validate an owner terms decision record; any defect refuses with `terms-gate-missing`.

    `relative` is `terms/<name>.json` under `<plugin home>/lightning/`. The record is
    `{schema, provider, host, models, terms: {version | url}, reviewedOn, validUntil, outcome}`; `today` (UTC,
    YYYY-MM-DD) must lie in `[reviewedOn, validUntil]`. The return value carries the path and SHA-256 the manifest
    cites. Refusal texts name no path or field value.
    """
    def refuse():
        raise ExportError('No valid owner terms decision record', 'terms-gate-missing')

    if not isinstance(relative, str) or not _TERMS_PATH.fullmatch(relative):
        refuse()
    raw = _read_private_record(config.directory(home), relative)
    if raw is None or len(raw) > _MAX_TERMS_BYTES:
        refuse()
    try:
        value = json.loads(raw, object_pairs_hook=_no_duplicates)
    except (ValueError, TypeError, RecursionError):
        value = None
    if value is None:
        refuse()  # outside the except, so the refusal carries no parser context
    keys = {'schema', 'provider', 'host', 'models', 'terms', 'reviewedOn', 'validUntil', 'outcome'}
    if not isinstance(value, dict) or set(value) != keys or value['schema'] != TERMS_SCHEMA:
        refuse()
    terms = value['terms']
    models = value['models']
    if not isinstance(value['provider'], str) or not _TEXT.fullmatch(value['provider']) \
            or value['host'] not in ('claude-code', 'opencode') \
            or not isinstance(models, list) or not models or len(models) > 64 or len(set(models)) != len(models) \
            or not all(isinstance(m, str) and _TEXT.fullmatch(m) and len(m) <= 128 for m in models) \
            or not isinstance(terms, dict) or len(terms) != 1 or not set(terms) <= {'version', 'url'} \
            or not isinstance(next(iter(terms.values())), str) or not _TEXT.fullmatch(next(iter(terms.values()))) \
            or ('url' in terms and not terms['url'].startswith('https://')) \
            or not _valid_date(value['reviewedOn']) or not _valid_date(value['validUntil']):
        refuse()
    if not value['reviewedOn'] <= today <= value['validUntil']:
        refuse()  # not reviewed yet, or stale
    if value['outcome'] != 'permits-training':  # forbids-training, undecided or anything else
        refuse()
    return {'path': relative, 'sha256': _sha(raw), 'host': value['host'], 'models': frozenset(models),
            'outcome': value['outcome']}


def _read_private_record(lightning: Path, relative: str) -> bytes | None:
    """The record's bytes, read without following a symbolic link and bounded to the limit plus one byte; None when
    a directory on the way (`lightning/`, `terms/`) or the file is missing, not private or not a regular file."""
    try:
        directory = registry._safe(lightning / TERMS_DIRECTORY, directory=True)
        for folder in (lightning, directory):
            registry._private(folder, directory=True)  # owner only: no other user can swap or plant the record
        fd = os.open(registry._safe(lightning / relative, directory=False), os.O_RDONLY | os.O_NOFOLLOW)
    except (OSError, ValueError):
        return None
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            return None
        return stream.read(_MAX_TERMS_BYTES + 1)


def _no_duplicates(pairs):
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate key')
    return dict(pairs)
