# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 trace adapter: the consent gate (REQ-002, T003).

Without consent `redacted` (a missing or invalid profile reads as `none`), or for a source the owner did not
list, the adapter emits only content-free records and reports why. Reading sources is SPEC-074 T007/T008.
"""
from __future__ import annotations

from pathlib import Path

from . import lightning_config as config
from . import lightning_store as store

CONTENT_REFUSAL = 'content-consent-required'
SOURCE_REFUSAL = 'source-not-consented'


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
