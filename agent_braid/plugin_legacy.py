# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit migration delegates removal to the existing receipt-owned lifecycle."""
from __future__ import annotations
import json
import os
from pathlib import Path
from .plugin_registry import RegistryError, _pairs, _safe
from .tooling_install import Selection, _load_receipt, plan, apply


def selection(host, receipt, destination=None):
    receipt = _safe(Path(receipt), directory=False)
    if receipt.stat().st_size > 2 * 1024 * 1024:
        raise RegistryError('Legacy receipt exceeds its size bound')
    with receipt.open('rb') as stream:
        payload = stream.read(2 * 1024 * 1024 + 1)
    if len(payload) > 2 * 1024 * 1024:
        raise RegistryError('Legacy receipt exceeds its size bound')
    value = json.loads(payload, object_pairs_hook=_pairs)
    if not isinstance(value, dict) or any(not isinstance(value.get(key), str) or not value[key]
                                         for key in ('host', 'scope', 'sourceRoot', 'resultRoot', 'serverName')):
        raise RegistryError('Legacy receipt must contain a valid owned selection')
    if value.get('host') != host or value.get('scope') != 'user':
        raise RegistryError('Select a matching user-scoped legacy receipt')
    selected = Selection(host=host, scope='user', source_root=Path(value['sourceRoot']),
        result_root=Path(value['resultRoot']), name=value['serverName'], receipt=receipt, destination=destination)
    config, skills, _ = selected.paths()
    _load_receipt(receipt, selected, config, skills)
    return selected


def inventory(host, destination=None):
    if destination is not None:
        directory = Path(destination) / 'receipts'
    elif host == 'codex':
        directory = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'agent-braid-receipts'
    else:
        directory = Path.home() / '.claude/agent-braid-receipts'
    _safe(directory, directory=True)
    if not directory.exists():
        return {'receipts': [], 'truncated': False}
    result = []
    count = 0
    # Bound every inspected entry, including non-receipt files.
    with os.scandir(directory) as entries:
        for entry in entries:
            count += 1
            if count > 64:
                break
            if entry.is_file(follow_symlinks=False) and entry.name.endswith('.json'):
                path = Path(entry.path)
                try:
                    selected = selection(host, path, destination)
                    result.append({'receipt': str(path), 'sourceRoot': str(selected.source_root),
                                   'resultRoot': str(selected.result_root), 'serverName': selected.name, 'status': 'owned-selection'})
                except (ValueError, KeyError, TypeError, OSError):
                    result.append({'receipt': str(path), 'status': 'unavailable; inspect without adopting'})
    return {'receipts': result, 'truncated': count > 64}


def migrate(host, receipt, *, destination=None, digest=None, do_apply=False, source_checkout=False):
    selected = selection(host, receipt, destination)
    transaction = plan(selected, operation='uninstall', source_checkout=source_checkout)
    return apply(transaction, preview_digest=digest) if do_apply else transaction.preview()
