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


_GATE_REASONS = {adapter.CONTENT_REFUSAL: 'consent-none', adapter.SOURCE_REFUSAL: 'no-consent'}


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
    if adapter.CONTENT_REFUSAL in losses:
        return 'consent-none'
    if adapter.SOURCE_REFUSAL in losses:
        return 'no-consent'
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


def read_runs(home: Path | None, run_ids: list[str]) -> list[dict]:
    """One item per model call of every attempt in the runs: source ids, its turn index and the adapter triplet."""
    items = []
    refusal = adapter.gate(home, 'rollout')['refusal']
    for run_id in run_ids:
        try:
            run = store.RunStore(home, run_id)
            tasks = _tasks(run)
            attempts = sorted({(e.rollout_id, e.attempt_id) for e in run.read('event')})
        except store.StoreError as exc:
            raise ExportError('Run refused', exc.code) from None
        for rollout_id, attempt_id in attempts:
            if rollout_id not in tasks:
                raise ExportError('A rollout has events but no rollout record', 'source-invalid')
            task_id, group_id = tasks[rollout_id]
            try:
                triplets = adapter.rollout_triplets(home, run_id, attempt_id)
            except adapter.AdapterError as exc:
                raise ExportError('Adapter refused a source', exc.code) from None
            for index, triplet in enumerate(triplets):
                items.append({'runId': run_id, 'taskId': task_id, 'groupId': group_id, 'rolloutId': rollout_id,
                              'attemptId': triplet['attemptId'], 'turnIndex': index, 'gateRefusal': refusal,
                              'triplet': triplet})
    return items
