# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 dataset export (BL.5): consented, redacted Braid Lightning traces to local datasets.

T003 (REQ-002): the input boundary. Content is read only through the SPEC-074 adapter
(`lightning_adapter.rollout_triplets`); content-free rollout records name each attempt's task and group. Every
model call either survives the consent and redaction filter or is counted under one exclusion reason, never
dropped silently (E1). Raw attempt ids stay in memory: records carry the adapter's `attempt-<hmac16>` pseudonym,
and refusals carry fixed texts and codes with no chained cause. Standard library only; no network or process.
"""
from __future__ import annotations

from pathlib import Path
import re

from . import lightning_adapter as adapter
from . import lightning_store as store

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


def _read_run(home: Path | None, run_id: str, refusal: str | None) -> list[dict]:
    run = store.RunStore(home, run_id)
    tasks = _tasks(run)
    attempts: dict[str, set[str]] = {}
    for event in run.read('event'):
        attempts.setdefault(event.attempt_id, set()).add(event.rollout_id)
    items = []
    for attempt_id in sorted(attempts):
        rollouts = attempts[attempt_id]
        if len(rollouts) != 1:  # the adapter reads by attempt, so a shared attempt id would mix two rollouts
            raise ExportError('An attempt spans more than one rollout', 'source-invalid')
        rollout_id = next(iter(rollouts))
        if rollout_id not in tasks:
            raise ExportError('A rollout has events but no rollout record', 'source-invalid')
        task_id, group_id = tasks[rollout_id]
        for index, triplet in enumerate(adapter.rollout_triplets(home, run_id, attempt_id)):
            items.append({'runId': run_id, 'taskId': task_id, 'groupId': group_id, 'rolloutId': rollout_id,
                          'attemptId': triplet['attemptId'], 'turnIndex': index, 'gateRefusal': refusal,
                          'triplet': triplet})
    return items
